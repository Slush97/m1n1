# t8142: find how far Linux gets before it goes silent under the hv.
#
# uart0 (0x3a5200000) is deliberately NOT traced — the hv already reserves that
# range for the vuart, and Linux's earlycon writes come out on /dev/m1n1-sec.

from m1n1.utils import irange

# AIC3, 1/2 dies, reg_size 0x40004 per m1n1's own probe. Top suspect.
trace_range(irange(0x381000000, 0x44000), mode=TraceMode.SYNC, name="aic")

# pmgr and the watchdogs, both touched early by the kernel.
trace_range(irange(0x380700000, 0x10000), mode=TraceMode.SYNC, name="pmgr")
trace_range(irange(0x3882B0000, 0x10000), mode=TraceMode.SYNC, name="wdt")

print("m5 early trace armed: aic, pmgr, wdt (SYNC)")
