#!/usr/bin/env python3
# Section 5 reads, ordered safest/highest-value first so a hang can't cost us the headline.
import sys, pathlib, traceback

sys.path.append(str(pathlib.Path(__file__).resolve().parents[0]))

from m1n1.setup import *


def step(name, fn):
    print(f"\n===== {name} =====", flush=True)
    try:
        fn()
    except Exception:
        print(f"!! FAILED: {name}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()


# --- 2. chip identity ---
def chipid():
    print(
        "chip_id      :", hex(u.adt["/chosen"].chip_id), "(expect 0x8142)", flush=True
    )
    print("target_type  :", u.adt.target_type, "(expect J704)", flush=True)
    try:
        print("board_id     :", hex(u.adt["/chosen"].board_id), flush=True)
    except Exception:
        pass


step("2. chip identity", chipid)


# --- 3. THE HEADLINE: i2c/uart MMIO bases ---
def mmio():
    armio = u.adt["/arm-io"]
    print("arm-io ranges:", flush=True)
    for r in armio.ranges:
        print(
            f"   bus 0x{r.bus_addr:x} -> parent 0x{r.parent_addr:x} len 0x{r.size:x}",
            flush=True,
        )
    for node in ("uart0", "i2c0", "i2c1", "i2c2", "i2c3", "i2c4"):
        try:
            reg = u.adt[f"/arm-io/{node}"].reg
            base = reg[0].addr
            print(f"   {node:6s} bus 0x{base:x}", flush=True)
        except Exception as e:
            print(f"   {node:6s} -- absent ({e})", flush=True)


step("3. HEADLINE: arm-io MMIO bases", mmio)


# --- 4. full on-hardware ADT ---
def adtdump():
    data = u.adt.build()
    open("m5-adt-live.bin", "wb").write(data)
    print(f"wrote m5-adt-live.bin ({len(data)} bytes)", flush=True)


step("4. live ADT dump", adtdump)


# --- 1a. boot-core MIDR ---
def midr_boot():
    v = u.mrs(MIDR_EL1)
    print(f"boot core MIDR_EL1 = 0x{v:x}  part=0x{(v >> 4) & 0xFFF:x}", flush=True)


step("1a. boot core MIDR", midr_boot)


# --- 1b. per-core MIDR (riskiest, last) ---
def midr_all():
    cpus = [n for n in u.adt["/cpus"]]
    print(f"{len(cpus)} cpu nodes in ADT", flush=True)
    for n in cpus:
        try:
            print(
                f"   {n.name:12s} cpu-id={getattr(n, 'cpu_id', '?')} "
                f"cluster={getattr(n, 'cluster_id', '?')} compat={getattr(n, 'compatible', '?')}",
                flush=True,
            )
        except Exception:
            pass
    p.smp_start_secondaries()
    for i in range(1, len(cpus)):
        try:
            if not p.smp_is_alive(i):
                print(f"   cpu{i}: not alive", flush=True)
                continue
            v = u.mrs(
                MIDR_EL1, call=lambda addr, *a, cpu=i: p.smp_call_sync(cpu, addr, *a)
            )
            print(
                f"   cpu{i}: MIDR_EL1 = 0x{v:x}  part=0x{(v >> 4) & 0xFFF:x}",
                flush=True,
            )
        except Exception as e:
            print(f"   cpu{i}: FAILED {e}", flush=True)


step("1b. per-core MIDR", midr_all)

print("\n===== done =====", flush=True)
