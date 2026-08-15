#!/usr/bin/env python3
# Per-core MIDR_EL1 on t8142. E-cores first: 0x62 is the unverified guess.
# Uses the in-tree idiom (assemble -> writemem -> dc_cvau/ic_ivau -> smp_call_sync);
# the cache maintenance is what the previous attempt was missing.
import sys, pathlib, traceback

sys.path.append(str(pathlib.Path(__file__).resolve().parents[0]))

from m1n1.setup import *
from m1n1 import asm

code = u.malloc(0x1000)
c = asm.ARMAsm(
    """
    mrs x0, MIDR_EL1
    ret
""",
    code,
)
iface.writemem(code, c.data)
p.dc_cvau(code, len(c.data))
p.ic_ivau(code, len(c.data))
print(f"stub at 0x{code:x}", flush=True)

cpus = list(u.adt["cpus"])
order = [i for i in range(len(cpus)) if cpus[i].cluster_id == 0] + [
    i for i in range(len(cpus)) if cpus[i].cluster_id != 0
]

p.smp_start_secondaries()

for i in order:
    n = cpus[i]
    kind = "E" if n.cluster_id == 0 else "P"
    try:
        if n.state == "running":
            v = p.call(code)
        else:
            if not p.smp_is_alive(i):
                print(f"cpu{i} ({kind}): not alive", flush=True)
                continue
            v = p.smp_call_sync(i, code)
        print(
            f"cpu{i} ({kind}, {n.compatible[0]}): MIDR_EL1=0x{v:x} "
            f"part=0x{(v >> 4) & 0xFFF:x} rev=0x{v & 0xF:x}",
            flush=True,
        )
    except Exception as e:
        print(f"cpu{i} ({kind}): FAILED {e}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()
        break

print("\n===== done =====", flush=True)
