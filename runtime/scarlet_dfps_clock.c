/* First-sample initialization for the exact verified Scarlet 4.0.0 ASM.
 * Called ONLY through loader.c's main import after all 153 entries validate.
 * SDK GetSystemTick is MRS X0,CNTPCT_EL0; RET, i.e. rt_ticks() in this port.
 * No change to the clock, subsequent deltas, coordinates, or physics factors.
 */
#ifdef SCARLET_AOT
#include "rt.h"

void scarlet_dfps_system_tick(Cpu *c) {
    uint64_t tick = rt_ticks();
    c->x[0] = tick;
    /* 1760ED8 loads previous tick into D1, 1760EDC calls the SDK import;
     * after return the ASM computes (tick-D1)/19200000 and applies its EMA.
     * Its initial zero D1 instead measures host uptime. Bootstrap one nominal
     * 60-Hz sample and the EMA together, on the simulation thread, once.
     * Checking the scratch zeros also handles an in-place game reboot. */
    const uint64_t scratch = MAIN_BASE + UINT64_C(0x438f000);
    if (c->x[30] != MAIN_BASE + UINT64_C(0x1760ee0) || c->x[19] != scratch ||
        tick < 320000 || !g_nmodules || g_modules[0].base != MAIN_BASE ||
        g_modules[0].size < 0x438f068) return;
    double previous, stored_tick, smooth, frequency;
    memcpy(&previous, &c->v[1], sizeof previous);
    memcpy(&stored_tick, (void *)(uintptr_t)(scratch + 0x18), sizeof stored_tick);
    memcpy(&smooth, (void *)(uintptr_t)(scratch + 0x60), sizeof smooth);
    memcpy(&frequency, (void *)(uintptr_t)(scratch + 0x38), sizeof frequency);
    if (previous != 0.0 || stored_tick != 0.0 || smooth != 0.0 || frequency != 19200000.0) return;
    previous = (double)tick - 320000.0;
    smooth = 1.0 / 60.0;
    memcpy(&c->v[1], &previous, sizeof previous);
    memcpy((void *)(uintptr_t)(scratch + 0x60), &smooth, sizeof smooth);
    fputs("[scarlet-dfps] initialized first clock sample and EMA at 1/60 s\n", stderr);
}
#endif
