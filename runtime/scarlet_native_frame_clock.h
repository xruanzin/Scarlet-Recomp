/* Scarlet 4.0.0 native host frame clock (independent implementation).
 * This is NOT the third-party ASM mod and contains no mod/game instructions.
 * It estimates a bounded host frame period for a gameplay A/B experiment.
 */
#ifndef SCARLET_NATIVE_FRAME_CLOCK_H
#define SCARLET_NATIVE_FRAME_CLOCK_H
#include <stdint.h>

#define SCARLET_FRAME_BASE_NS UINT64_C(16666667)
#define SCARLET_FRAME_MAX_NS UINT64_C(33333334)

typedef struct ScarletNativeFrameClock {
    uint64_t last_ns;
    uint64_t filtered_ns;
} ScarletNativeFrameClock;

static inline void scarlet_native_clock_reset(ScarletNativeFrameClock *c) {
    c->last_ns = 0;
    c->filtered_ns = SCARLET_FRAME_BASE_NS;
}

/* A constant 60-Hz target is preferable to feeding sub-millisecond host
 * scheduler noise into character/camera movement. Follow sustained slower
 * periods, but discard outliers caused by loading, minimized windows, or
 * late background-thread scheduling. The algorithm is side-effect free.
 */
static inline uint32_t scarlet_native_clock_step(ScarletNativeFrameClock *c, uint64_t now_ns) {
    if (!c->filtered_ns) c->filtered_ns = SCARLET_FRAME_BASE_NS;
    if (!c->last_ns) {
        c->last_ns = now_ns;
        return (uint32_t)SCARLET_FRAME_BASE_NS;
    }
    const uint64_t elapsed = now_ns > c->last_ns ? now_ns - c->last_ns : 0;
    c->last_ns = now_ns;
    if (elapsed < UINT64_C(8000000) || elapsed > UINT64_C(100000000)) {
        // Duplicate/abnormal present or loading hitch; maintain the current timebase.
        return c->filtered_ns <= SCARLET_FRAME_BASE_NS + UINT64_C(900000)
                   ? (uint32_t)SCARLET_FRAME_BASE_NS : (uint32_t)c->filtered_ns;
    }
    const uint64_t bounded = elapsed < SCARLET_FRAME_BASE_NS ? SCARLET_FRAME_BASE_NS
                              : elapsed > SCARLET_FRAME_MAX_NS ? SCARLET_FRAME_MAX_NS
                              : elapsed;
    if (bounded > c->filtered_ns)
        c->filtered_ns += (bounded - c->filtered_ns + 7) / 8;
    else
        c->filtered_ns -= (c->filtered_ns - bounded + 7) / 8;
    // Dead zone prevents a nominal 60-FPS camera from bouncing at 16-17 ms.
    return c->filtered_ns <= SCARLET_FRAME_BASE_NS + UINT64_C(900000)
               ? (uint32_t)SCARLET_FRAME_BASE_NS : (uint32_t)c->filtered_ns;
}
#endif
