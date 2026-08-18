/* SPDX-License-Identifier: MIT */

#ifndef __SMP_H__
#define __SMP_H__

#include "types.h"
#include "utils.h"

#define MAX_CPUS     24
#define MAX_EL3_CPUS 4

#define SECONDARY_STACK_SIZE 0x10000
extern u8 *secondary_stacks[MAX_CPUS];
extern u8 *secondary_stacks_el3[MAX_EL3_CPUS];

void smp_secondary_entry(void);
void smp_secondary_prep_el3(void);

void smp_start_secondaries(void);
void smp_stop_secondaries(bool deep_sleep);

#define smp_call0(i, f)          smp_call4(i, f, 0, 0, 0, 0)
#define smp_call1(i, f, a)       smp_call4(i, f, a, 0, 0, 0)
#define smp_call2(i, f, a, b)    smp_call4(i, f, a, b, 0, 0)
#define smp_call3(i, f, a, b, c) smp_call4(i, f, a, b, c, 0)

void smp_call4(int cpu, void *func, u64 arg0, u64 arg1, u64 arg2, u64 arg3);

u64 smp_wait(int cpu);

bool smp_is_alive(int cpu);
uint64_t smp_get_mpidr(int cpu);
u64 smp_get_release_addr(int cpu);
void smp_set_wfe_mode(bool new_mode);
void smp_send_ipi(int cpu);

/*
 * LOCAL ONLY - NOT FOR SUBMISSION: per-cpu breadcrumbs for the t8142 SMP=1
 * secondary-wedge hunt. The park loop heartbeats into smp_park_dbg; every
 * exception entry records itself into exc_crumb BEFORE trying to print (a
 * wedged secondary's own prints never make it out). smp_call4's kick loop
 * dumps both from the primary when a callee goes unresponsive.
 */
struct smp_park_dbg {
    u64 beat;
    u64 daif;
};
extern struct smp_park_dbg smp_park_dbg[MAX_CPUS];

struct exc_crumb {
    u64 count;
    u64 kind;
    u64 esr;
    u64 elr;
    u64 spsr;
};
extern struct exc_crumb exc_crumb[MAX_CPUS];

static inline int smp_id(void)
{
    if (in_el3())
        return mrs(TPIDR_EL3);
    else if (in_el2())
        return mrs(TPIDR_EL2);
    else
        return mrs(TPIDR_EL1);
}

extern int boot_cpu_idx;
#endif
