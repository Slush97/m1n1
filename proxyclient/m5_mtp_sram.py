#!/usr/bin/env python3
# Read-only probe: is the MTP firmware actually in SRAM, and what state did
# iBoot leave the MTP DART in before Linux ever runs?
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[0]))

from m1n1.setup import *
from m1n1.proxy import GUARD

DART = 0x394800000
ASC = 0x394600000
FW_TEXT = 0x394C00000  # ADT segment-ranges __TEXT phys
FW_DATA = 0x394C54000  # ADT segment-ranges __DATA phys
# Do NOT probe 0x394e00000 (what t8142.dtsi currently calls "sram"): that
# address is unmapped and a read takes an unrecoverable SYNC exception.


def guarded(fn, *args):
    p.set_exc_guard(GUARD.SKIP | GUARD.SILENT)
    before = p.get_exc_count()
    try:
        val = fn(*args)
    finally:
        after = p.get_exc_count()
        p.set_exc_guard(GUARD.OFF)
    if after != before:
        return None
    return val


def r32(addr):
    return guarded(p.read32, addr)


def show(label, addr):
    val = r32(addr)
    if val is None:
        print(f"{label:28} @ 0x{addr:x} = FAULT")
    else:
        print(f"{label:28} @ 0x{addr:x} = {val:08x}")


print("===== MTP ASC =====")
show("CPU_CONTROL", ASC + 0x44)
show("CPU_STATUS", ASC + 0x48)

print()
print("===== dart-mtp registers (pristine, pre-Linux) =====")
show("PARAMS1", DART + 0x00)
show("PARAMS2", DART + 0x04)
show("PROTECT", DART + 0x200)
show("PROTECT_LOCK", DART + 0x208)
show("ENABLE_STREAMS", DART + 0xC00)
show("ERROR", DART + 0x100)
for sid in range(16):
    tcr = r32(DART + 0x1000 + sid * 4)
    ttbr = r32(DART + 0x1400 + sid * 4)
    tcr_s = "FAULT" if tcr is None else f"{tcr:08x}"
    ttbr_s = "FAULT" if ttbr is None else f"{ttbr:08x}"
    valid = "" if ttbr in (None, 0) else ("  VALID" if ttbr & 1 else "  (invalid)")
    print(f"  sid {sid:2}  TCR={tcr_s}  TTBR0={ttbr_s}{valid}")


def dump(label, base, offset, count):
    print(f"===== {label} @ 0x{base + offset:x} =====")
    words = [r32(base + offset + i * 4) for i in range(count)]
    if all(w is None for w in words):
        print("  all reads FAULT")
        return words
    for row in range((count + 3) // 4):
        chunk = words[row * 4 : row * 4 + 4]
        cells = " ".join("--------" if w is None else f"{w:08x}" for w in chunk)
        print(f"  +0x{offset + row * 16:04x}: {cells}")
    print(f"  nonzero: {sum(1 for w in words if w)}/{count}")
    print()
    return words


print()
# +0 held 0x140000a5 ("b +0x294") on the first probe; follow the branch target.
dump("__TEXT head", FW_TEXT, 0x0, 16)
dump("__TEXT branch target", FW_TEXT, 0x294, 32)
dump("__DATA head", FW_DATA, 0x0, 16)

print("===== scanning __TEXT for a Mach-O header =====")
found = False
for off in range(0, 0x4000, 4):
    val = r32(FW_TEXT + off)
    if val in (0xFEEDFACF, 0xFEEDFACE):
        print(f"  Mach-O magic {val:08x} at +0x{off:x}")
        found = True
        break
if not found:
    print("  no Mach-O magic in the first 16 KiB")
