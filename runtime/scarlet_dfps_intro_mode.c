/* Scarlet 4.0.0 Dynamic FPS: guarded diagnostic of the engine frame-mode word.
 * Experimental and opt-in. Does not infer scene identity or change game files.
 * Community FPS cheats label MAIN+0x05BEFCE4 as the frame-rate mode
 * (1=60, 2=30). Unlike the patched frame period, this site lies beyond
 * the currently loaded main NSO image. Never blindly dereference or commit it.
 */
#if defined(SCARLET_AOT) && defined(_WIN32)
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SCARLET_FPS_MODE_ADDR ((uintptr_t)(UINT64_C(0x7000000000) + UINT64_C(0x05BEFCE4)))

/* Called from the presenting thread. No work unless explicitly opted in. */
void scarlet_dfps_intro_mode_frame(void) {
    static int mode = -1; /* 0 disabled, 1 passive, 2 guarded force60 A/B */
    static unsigned long long frames;
    static uint32_t previous;
    static int have_previous, reported_invalid, reported_unmapped, reported_write_fail;
    if (mode < 0) {
        mode = 0;
        const char *patch = getenv("SCARLET_DFPS_PCHTXT");
        const char *e = getenv("SCARLET_DFPS_INTRO_MODE");
        if (patch && *patch && e && !strcmp(e, "probe")) mode = 1;
        else if (patch && *patch && e && !strcmp(e, "force60")) mode = 2;
        if (mode) fprintf(stderr, "[scarlet-intro-mode] %s active (diagnostic / A-B only); MAIN+0x05BEFCE4\n",
                          mode == 1 ? "probe" : "force60");
    }
    if (!mode) return;
    frames++;
    /* Passive probe: once per 60 presents; A/B test: on each present. */
    if (mode == 1 && frames % 60 != 1) return;

    const void *site = (const void *)SCARLET_FPS_MODE_ADDR;
    MEMORY_BASIC_INFORMATION mbi = {0};
    SIZE_T got = VirtualQuery(site, &mbi, sizeof mbi);
    uintptr_t start = (uintptr_t)mbi.BaseAddress;
    uintptr_t end = start + mbi.RegionSize;
    DWORD protection = mbi.Protect & 0xff;
    if (!got || mbi.State != MEM_COMMIT || (mbi.Protect & PAGE_GUARD) ||
        protection == PAGE_NOACCESS || start > SCARLET_FPS_MODE_ADDR ||
        end < SCARLET_FPS_MODE_ADDR + sizeof(uint32_t)) {
        if (!reported_unmapped) {
            reported_unmapped = 1;
            fprintf(stderr, "[scarlet-intro-mode] site not safely mapped: probe unavailable; no writes\n");
        }
        return;
    }
    uint32_t value;
    SIZE_T read_count = 0;
    if (!ReadProcessMemory(GetCurrentProcess(), site, &value, sizeof value, &read_count) ||
        read_count != sizeof value) {
        if (!reported_unmapped) {
            reported_unmapped = 1;
            fprintf(stderr, "[scarlet-intro-mode] read failed; no writes\n");
        }
        return;
    }
    if (!have_previous || value != previous || frames % 600 == 1) {
        fprintf(stderr, "[scarlet-intro-mode] present=%llu value=%u (1=60-mode, 2=30-mode)\n",
                frames, value);
        previous = value;
        have_previous = 1;
    }
    if (mode != 2 || value == 1) return;
    if (value != 2) {
        if (!reported_invalid) {
            reported_invalid = 1;
            fprintf(stderr, "[scarlet-intro-mode] unexpected value: refusing to modify\n");
        }
        return;
    }
    if (protection != PAGE_READWRITE && protection != PAGE_WRITECOPY &&
        protection != PAGE_EXECUTE_READWRITE && protection != PAGE_EXECUTE_WRITECOPY) {
        if (!reported_write_fail) {
            reported_write_fail = 1;
            fprintf(stderr, "[scarlet-intro-mode] field is not writable; refusing to modify\n");
        }
        return;
    }
    const uint32_t sixty = 1;
    SIZE_T written = 0;
    if (!WriteProcessMemory(GetCurrentProcess(), (void *)site, &sixty, sizeof sixty, &written) ||
        written != sizeof sixty) {
        if (!reported_write_fail) {
            reported_write_fail = 1;
            fprintf(stderr, "[scarlet-intro-mode] write failed; no override\n");
        }
        return;
    }
    static unsigned long long nwrite;
    if (++nwrite == 1 || nwrite % 600 == 0)
        fprintf(stderr, "[scarlet-intro-mode] A/B changed 30-mode (2) -> 60-mode (1); writes=%llu\n", nwrite);
}
#endif
