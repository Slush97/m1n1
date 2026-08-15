#!/usr/bin/env python3
# t8142 (M5 Hidra) counter/timer register probe.
#
# Every access runs under m1n1's exception guard (GUARD.SKIP), so an undefined
# instruction is counted and stepped over instead of taking the machine down.
# Nothing here reboots the target.
#
# Answers: which of AGTCNTRDIR_EL1 / _EL12 actually undefs (chickens.c:259-263),
# and whether cntp_tval_el0 at EL2 undefs the way hv_arm_tick died.

import sys, pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parent))

from m1n1.setup import *
from m1n1.proxy import ProxyError

REGS = {
    "CurrentEL": "s3_0_c4_c2_2",
    "HCR_EL2": "s3_4_c1_c1_0",
    "ID_AA64MMFR0_EL1": "s3_0_c0_c7_0",
    "CNTFRQ_EL0": "s3_3_c14_c0_0",
    "CNTPCT_EL0": "s3_3_c14_c0_1",
    "CNTP_TVAL_EL0": "s3_3_c14_c2_0",
    "CNTP_CTL_EL0": "s3_3_c14_c2_1",
    "CNTP_CVAL_EL0": "s3_3_c14_c2_2",
    "CNTV_TVAL_EL0": "s3_3_c14_c3_0",
    "CNTV_CTL_EL0": "s3_3_c14_c3_1",
    "CNTHCTL_EL2": "s3_4_c14_c1_0",
    "CNTHP_TVAL_EL2": "s3_4_c14_c2_0",
    "CNTHP_CTL_EL2": "s3_4_c14_c2_1",
    "CNTHP_CVAL_EL2": "s3_4_c14_c2_2",
    "AGTCNTRDIR_EL1": "s3_1_c15_c1_5",
    "AGTCNTRDIR_EL12": "s3_4_c15_c14_6",
    "VM_TMR_FIQ_ENA_EL2": "s3_5_c15_c1_3",
    "CNTP_CTL_EL02": "s3_5_c14_c2_1",
    "CNTV_CTL_EL02": "s3_5_c14_c3_1",
}


def rd(name):
    try:
        val = u.mrs(REGS[name], silent=True)
    except ProxyError:
        print(f"  read   {name:17s} UNDEF")
        return None
    print(f"  read   {name:17s} = 0x{val:016x}")
    return val


def wr(name, val):
    try:
        u.msr(REGS[name], val, silent=True)
    except ProxyError:
        print(f"  write  {name:17s} <- 0x{val:x}  UNDEF")
        return False
    print(f"  write  {name:17s} <- 0x{val:x}  OK")
    return True


print("\n=== 1. context ===")
for r in ("CurrentEL", "HCR_EL2", "ID_AA64MMFR0_EL1"):
    v = rd(r)
    if r == "CurrentEL" and v is not None:
        print(f"         -> EL{(v >> 2) & 3}")
    if r == "HCR_EL2" and v is not None:
        print(f"         -> E2H={(v >> 34) & 1} TGE={(v >> 27) & 1}")
    if r == "ID_AA64MMFR0_EL1" and v is not None:
        print(f"         -> ECV={(v >> 60) & 0xF}")

print("\n=== 2. counter reads ===")
for r in ("CNTFRQ_EL0", "CNTPCT_EL0"):
    rd(r)

print("\n=== 3. AGTCNTRDIR — the chickens.c:259-263 pair ===")
rd("AGTCNTRDIR_EL1")
wr("AGTCNTRDIR_EL1", 0)
rd("AGTCNTRDIR_EL12")
wr("AGTCNTRDIR_EL12", 0)

print("\n=== 4. EL0 physical timer — what hv_arm_tick writes ===")
saved = rd("CNTP_TVAL_EL0")
rd("CNTP_CTL_EL0")
rd("CNTP_CVAL_EL0")
if wr("CNTP_TVAL_EL0", 0x7FFFFFFF) and saved is not None:
    wr("CNTP_TVAL_EL0", saved)
    print("         (original value restored)")

print("\n=== 5. virtual + EL2 physical timer, for comparison ===")
for r in (
    "CNTV_TVAL_EL0",
    "CNTV_CTL_EL0",
    "CNTHCTL_EL2",
    "CNTHP_TVAL_EL2",
    "CNTHP_CTL_EL2",
    "CNTHP_CVAL_EL2",
):
    rd(r)

print("\n=== 6. the register hv_update_fiq() dies on ===")
vm = rd("VM_TMR_FIQ_ENA_EL2")
wr("VM_TMR_FIQ_ENA_EL2", vm if vm is not None else 0)

print("\n=== 7. EL02 guest timer aliases hv_update_fiq() reads ===")
rd("CNTP_CTL_EL02")
rd("CNTV_CTL_EL02")

print("\ndone")
