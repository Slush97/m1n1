/* SPDX-License-Identifier: MIT */

#ifndef __SOC_H__
#define __SOC_H__

#include "../config.h"

#define S5L8960X 0x8960
#define T7000    0x7000
#define T7001    0x7001
#define S8000    0x8000
#define S8001    0x8001
#define S8003    0x8003
#define T8010    0x8010
#define T8011    0x8011
#define T8012    0x8012
#define T8015    0x8015

#define T8103 0x8103
#define T8112 0x8112
#define T8122 0x8122
#define T8132 0x8132
#define T8140 0x8140
#define T8142 0x8142 // M5 "Hidra" (H17G); board J704 / Mac17,2
#define T6000 0x6000
#define T6001 0x6001
#define T6002 0x6002
#define T6020 0x6020
#define T6021 0x6021
#define T6022 0x6022
#define T6030 0x6030
#define T6031 0x6031
#define T6034 0x6034
#define T6040 0x6040

// T8142 (M5 "Hidra") SoC. ID confirmed from hardware (Mac17,2 IORegistry:
// platform-name "t8142", compatible "J704AP"/"Mac17,2"). A minimal "first boot"
// scaffold is now in place so the universal m1n1.macho can identify and start on
// this SoC; the values below are placeholders/conservative defaults that get
// CONFIRMED on the first real boot (none of them block bring-up — see notes):
//   - src/midr.h:     MIDR_PART_T8142_HIDRA_{E,P}CORE — GUESSED 0x62/0x63. init_cpu()
//                     falls back to "Unknown" on a mismatch (still boots); the first
//                     boot's "CPU part: 0x__" print reveals the true value.
//   - src/chickens.c: table entries use NULL init + features_m4 (conservative), exactly
//                     as the M4 Donan / A18 Tahiti siblings do. TODO(m5): real feature bits.
//   - src/smp.c:      `case T8142:` added to the T8112-family start-cpu path.
//   - src/soc.h:      EARLY_UART_BASE below, DERIVED + ADT-confirmed.
// Values marked DERIVED come from the machine's own ADT (re/M5-FINDINGS.md); GUESSED
// values are best-effort and self-correcting on first boot. Nothing here is "supported"
// until it runs on hardware.

#ifdef TARGET

#if TARGET == T8103
#define EARLY_UART_BASE 0x235200000
#elif TARGET == T6000 || TARGET == T6001 || TARGET == T6002 || TARGET == T6020 ||                  \
    TARGET == T6021 || TARGET == T6022
#define EARLY_UART_BASE 0x39b200000
#elif TARGET == T8112
#define EARLY_UART_BASE 0x235200000
#elif TARGET == T8122
#define EARLY_UART_BASE 0x2a1200000
#elif TARGET == T8132
#define EARLY_UART_BASE 0x3ad200000
#elif TARGET == T8140
#define EARLY_UART_BASE 0x385200000
#elif TARGET == T8142
// M5 Hidra: DERIVED from this machine's ADT (uart0 off 0x195200000 + arm-io ranges
// base 0x210000000); ADT-confirmed against the uart-1,samsung node. Only used for
// a TARGET==T8142 debug build; the universal m1n1.macho reads the UART from the ADT.
#define EARLY_UART_BASE 0x3a5200000
#elif TARGET == T6034 || TARGET == T6031
#define EARLY_UART_BASE 0x391200000
#elif TARGET == T8015
#define EARLY_UART_BASE 0x22e600000
#elif TARGET == T6030
#define EARLY_UART_BASE 0x289200000
#elif TARGET == T6040
#define EARLY_UART_BASE 0x429200000
#elif TARGET == T7000 || TARGET == T7001 || TARGET == S8000 || TARGET == S8001 ||                  \
    TARGET == S8003 || TARGET == T8010 || TARGET == T8011
#if TARGET == T7000 && defined(TARGET_BOARD) && TARGET_BOARD == 0x34 // Apple TV HD
#define EARLY_UART_BASE 0x20a0d8000
#else
#define EARLY_UART_BASE 0x20a0c0000
#endif

#elif TARGET == T8012
#define EARLY_UART_BASE 0x20a600000
#elif TARGET == S5L8960X
#define EARLY_UART_BASE 0x20a0a0000
#endif

#endif
#endif
