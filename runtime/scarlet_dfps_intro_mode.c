/* Passive Scarlet 4.0.0 DFPS telemetry. Addresses follow the verified ASM
 * data flow, not the unrelated/unmapped community frame-mode address.
 * No guest memory writes. Samples are asynchronous, not a simulation trace.
 */
#if defined(SCARLET_AOT) && defined(_WIN32)
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "rt.h"

static int intro_read(uint64_t address, void *out, size_t size) {
    MEMORY_BASIC_INFORMATION mbi;
    if (!VirtualQuery((void *)(uintptr_t)address, &mbi, sizeof mbi) ||
        mbi.State != MEM_COMMIT || (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))) return 0;
    uintptr_t start = (uintptr_t)mbi.BaseAddress;
    if (address < start || size > mbi.RegionSize || address - start > mbi.RegionSize - size) return 0;
    SIZE_T got = 0;
    return ReadProcessMemory(GetCurrentProcess(), (void *)(uintptr_t)address,
                             out, size, &got) && got == size;
}

void scarlet_dfps_intro_mode_frame(void) {
    static int enabled = -1;
    static uint64_t frame, last_ns, last_sample_ns;
    if (enabled < 0) {
        const char *patch = getenv("SCARLET_DFPS_PCHTXT");
        const char *mode = getenv("SCARLET_DFPS_INTRO_MODE");
        enabled = patch && *patch && mode && !strcmp(mode, "probe");
        if (mode && !strcmp(mode, "force60"))
            fprintf(stderr, "[scarlet-intro-mode] force60 retired: unsupported address; no reads or writes\n");
        if (enabled) fprintf(stderr, "[scarlet-intro-time] passive ASM telemetry; asynchronous samples, no object/scene identification\n");
    }
    if (!enabled) return;
    ++frame;
    uint64_t now = plat_now_ns(), elapsed = last_ns ? now - last_ns : 0;
    last_ns = now;
    /* Windows stderr is unbuffered. Per-frame formatted output stalls the
     * presenter with redirected pipes. Limit reads AND output by wall time,
     * including during startup or very slow frames, not by frame count. */
    if (frame != 1 && now - last_sample_ns < UINT64_C(1000000000)) return;
    last_sample_ns = now;
    if (g_program_id != UINT64_C(0x0100a3d008c5c000) || !g_nmodules ||
        g_modules[0].base != MAIN_BASE || g_modules[0].size < 0x438f068) return;
    unsigned char data[0x68];
    uint64_t period;
    if (!intro_read(MAIN_BASE + 0x438f000, data, sizeof data) ||
        !intro_read(MAIN_BASE + 0x3c2fbb0, &period, sizeof period)) {
        if (frame == 1 || frame % 600 == 0)
            fprintf(stderr, "[scarlet-intro-time] mapped ASM data unavailable; no writes\n");
        return;
    }
    uint32_t selector;
    double tick, previous, raw_dt, fps, requested, smooth;
    uint64_t clamped;
    memcpy(&selector, data, 4);
    memcpy(&tick, data + 0x18, 8);
    memcpy(&previous, data + 0x20, 8);
    memcpy(&raw_dt, data + 0x28, 8);
    memcpy(&fps, data + 0x30, 8);
    memcpy(&requested, data + 0x40, 8);
    memcpy(&clamped, data + 0x48, 8);
    memcpy(&smooth, data + 0x60, 8);
    char line[640];
    int len = snprintf(line, sizeof line, "[scarlet-intro-time] present=%llu wall_ms=%.3f selector=%u tick=%.0f previous=%.0f raw_dt=%.9g smooth_dt=%.9g estimated_fps=%.9g ns_scale=%.0f clamped_ns=%llu period_ns=%llu\n",
            (unsigned long long)frame, elapsed / 1e6, selector, tick, previous,
            raw_dt, smooth, fps, requested, (unsigned long long)clamped,
            (unsigned long long)period);
    if (len > 0 && (size_t)len < sizeof line) fwrite(line, 1, (size_t)len, stderr);
}
#endif
