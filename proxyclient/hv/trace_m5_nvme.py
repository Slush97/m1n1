# SPDX-License-Identifier: MIT
#
# t8142 (M5, J704): find the ANS I/O completion doorbell.
#
# The firmware asserts "CQ (Host I/O) DB error" the first time the host
# completion queue wraps, and `head` tracks whatever depth we configure. That
# is the signature of a doorbell the firmware never sees: the CQ head never
# advances on its side, so the wrap looks like a full queue. The driver writes
# it to nvme + 0x100c.
#
# Modes, selected with M5_NVME_TRACE:
#
#   observe   (default) decode every access to the nvme and nvmmu windows
#   mirror    additionally repeat each IOCQ doorbell write to the candidate
#             addresses in M5_NVME_MIRROR (comma-separated names or hex
#             offsets into the nvmmu window), to test a guess without
#             rebuilding the kernel
#   sync      observe, but with a host round trip per access
#
# observe traces ASYNC. SYNC stops the guest for a proxy round trip on every
# access, and on t8142 the guest timer FIQ is injected by hand from the
# exception path, so the milliseconds spent in EL2 cost ticks: a SYNC run
# reached CC enable, read CSTS once, and the probe never woke from its first
# sleep.
#
# Example:
#   M5_NVME_TRACE=mirror M5_NVME_MIRROR=alias \
#   M1N1_SMP=0 proxyclient/tools/run_guest_kernel.sh /home/esoc/linux-m5 \
#       "console=tty1 idle=nop maxcpus=1 loglevel=7" -m hv/trace_m5_nvme.py
#
# The RTKit syslog carrying the assert comes out on the guest console, so the
# ASC window is deliberately not traced: it would double the trap count for
# something already timestamped in dmesg.

import os

from m1n1.hv import TraceMode
from m1n1.trace import ADTDevTracer
from m1n1.utils import *

MODE = os.environ.get("M5_NVME_TRACE", "observe")
MIRROR_SPEC = os.environ.get("M5_NVME_MIRROR", "alias")

# t8142 orders /arm-io/ans reg[] differently from t8103: 0 is the coproc "ans"
# window, 3 the nvmmu, 9 the nvme BAR. ADTDevTracer indexes REGMAPS by reg
# index, hence the holes.
IDX_COPROC, IDX_NVMMU, IDX_NVME = 0, 3, 9

IOCQ_DB = 0x100C


class NVMERegs(RegMap):
    CAP = 0x0000, Register64
    VS = 0x0008, Register32
    INTMS = 0x000C, Register32
    INTMC = 0x0010, Register32
    CC = 0x0014, Register32
    CSTS = 0x001C, Register32
    AQA = 0x0024, Register32
    ASQ = 0x0028, Register64
    ACQ = 0x0030, Register64

    ASQ_DB = 0x1000, Register32
    ACQ_DB = 0x1004, Register32
    IOSQ_DB = 0x1008, Register32
    IOCQ_DB = 0x100C, Register32

    IOSQ_REGISTER = 0x1200, Register64
    IOCQ_REGISTER = 0x1208, Register64
    MAX_PEND_CMDS_CTRL = 0x1210, Register32

    BOOT_STATUS = 0x1300, Register32


class NVMMURegs(RegMap):
    UNKNOWN_CTRL = 0x24008, Register32
    LINEAR_SQ_CTRL = 0x24908, Register32
    LINEAR_ASQ_DB = 0x2490C, Register32
    LINEAR_IOSQ_DB = 0x24910, Register32

    NUM_TCBS = 0x28100, Register32
    ASQ_TCB_BASE = 0x28108, Register64
    IOSQ_TCB_BASE = 0x28110, Register64
    TCB_INVAL = 0x28118, Register32
    TCB_STAT = 0x28120, Register32


class M5NVMETracer(ADTDevTracer):
    DEFAULT_MODE = TraceMode.SYNC if MODE == "sync" else TraceMode.ASYNC

    REGMAPS = [None] * 10
    REGMAPS[IDX_NVMMU] = NVMMURegs
    REGMAPS[IDX_NVME] = NVMERegs

    NAMES = [None] * 10
    NAMES[IDX_NVMMU] = "nvmmu"
    NAMES[IDX_NVME] = "nvme"

    def init_state(self):
        self.state.cq_writes = 0
        self.state.wraps = 0
        self.state.last_head = None
        self.state.submits = 0
        self.state.completes = 0

    def start(self):
        self.nvme_base, self.nvme_size = self.dev.get_reg(IDX_NVME)
        self.nvmmu_base, self.nvmmu_size = self.dev.get_reg(IDX_NVMMU)
        self.candidates = {
            # The two windows are exactly 1 GiB apart and the ADT calls one of
            # them a secure BAR, so they are very likely aliases of the same
            # register file. If the doorbell only lands on one of them, this is
            # the cheapest explanation.
            "alias": self.nvmmu_base + IOCQ_DB,
            # t8132 moved the submission doorbells out to 0x2490c/0x24910. If
            # the completion doorbells followed, they land next door.
            "lsq": self.nvmmu_base + 0x24914,
            "lsq2": self.nvmmu_base + 0x24918,
        }
        self.mirrors = []

        self.log(f"nvme  {self.nvme_base:#x} +{self.nvme_size:#x}")
        self.log(f"nvmmu {self.nvmmu_base:#x} +{self.nvmmu_size:#x}")

        if MODE != "mirror":
            super().start()
        else:
            # Every trap costs a proxy round trip, and a mirror run has to get
            # through a 64 MiB read to prove anything. Hook the doorbell page
            # and nothing else.
            for spec in MIRROR_SPEC.split(","):
                spec = spec.strip()
                if not spec:
                    continue
                addr = self.candidates.get(spec)
                if addr is None:
                    addr = self.nvmmu_base + int(spec, 16)
                self.mirrors.append((spec, addr))
                self.log(f"mirroring IOCQ head to {spec} @ {addr:#x}")

            self.hv.add_tracer(
                irange(self.nvme_base, 0x4000),
                self.ident + ".mirror",
                TraceMode.HOOK,
                None,
                self.mirror_w,
            )

    def mirror_w(self, addr, val, width, **kwargs):
        self.hv.u.write(addr, val, width)
        if addr - self.nvme_base != IOCQ_DB:
            return
        self.note_head(val)
        for name, target in self.mirrors:
            self.hv.u.write(target, val, 32)

    def w_IOCQ_DB(self, r):
        self.note_head(r.value)

    def note_head(self, head):
        self.state.cq_writes += 1
        prev = self.state.last_head
        self.state.last_head = head
        if prev is not None and head < prev:
            self.state.wraps += 1
            self.log(
                f"*** IOCQ head WRAPPED {prev} -> {head} (wrap #{self.state.wraps}, "
                f"db write #{self.state.cq_writes}, "
                f"{self.state.submits} submitted, {self.state.completes} completed)"
            )
        elif MODE != "mirror":
            self.log(f"IOCQ head {head} (db write #{self.state.cq_writes})")

    def w_LINEAR_IOSQ_DB(self, r):
        self.state.submits += 1
        self.log(f"IOSQ tag {r.value} (#{self.state.submits})")

    def w_TCB_INVAL(self, r):
        self.state.completes += 1
        self.log(f"TCB inval tag {r.value} (#{self.state.completes})")

    def r_TCB_STAT(self, r):
        pass

    def r_BOOT_STATUS(self, r):
        pass

    def w_IOCQ_REGISTER(self, r):
        self.log(f"IOCQ registered at {r.value:#x}")

    def w_IOSQ_REGISTER(self, r):
        self.log(f"IOSQ registered at {r.value:#x}")


M5NVMETracer = M5NVMETracer._reloadcls()
m5_nvme = M5NVMETracer(hv, "/arm-io/ans", verbose=2)
m5_nvme.start()


def m5_nvme_dbs():
    """Read back the doorbell page and the linear-SQ block from the host."""
    for off in range(0x1000, 0x1014, 4):
        print(f"nvme +{off:#06x} = {hv.p.read32(m5_nvme.nvme_base + off):#010x}")
    for off in (0x24908, 0x2490C, 0x24910, 0x24914, 0x24918):
        print(f"nvmmu+{off:#06x} = {hv.p.read32(m5_nvme.nvmmu_base + off):#010x}")
    for off in range(0x1000, 0x1014, 4):
        print(f"alias+{off:#06x} = {hv.p.read32(m5_nvme.nvmmu_base + off):#010x}")


print(f"m5 nvme trace armed: mode={MODE}")
