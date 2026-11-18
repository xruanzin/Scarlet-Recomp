/* Host-only regression tests for the native Scarlet frame clock. No game files. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "../runtime/scarlet_native_frame_clock.h"

int main(void) {
    ScarletNativeFrameClock clock = {0};
    uint64_t now = UINT64_C(1000000000);
    assert(scarlet_native_clock_step(&clock, now) == (uint32_t)SCARLET_FRAME_BASE_NS);
    for (unsigned i=0; i<100; ++i) {
        now += (i & 1) ? UINT64_C(16000000) : UINT64_C(17333334);
        assert(scarlet_native_clock_step(&clock, now) == (uint32_t)SCARLET_FRAME_BASE_NS);
    }
    uint32_t period = 0;
    for (unsigned i=0; i<60; ++i) {
        now += UINT64_C(20000000);
        period = scarlet_native_clock_step(&clock, now);
    }
    assert(period >= 19000000u && period <= 20100000u);
    now += UINT64_C(250000000);
    assert(scarlet_native_clock_step(&clock, now) <= 20100000u);
    scarlet_native_clock_reset(&clock);
    assert(scarlet_native_clock_step(&clock, now + UINT64_C(16666667)) == (uint32_t)SCARLET_FRAME_BASE_NS);
    puts("PASS: Scarlet native 60 FPS clock resists scheduler jitter, adapts to slower frames and ignores stalls.");
    return 0;
}
