/* Scarlet-only left-stick magnitude guard.
 *
 * Keyboard WASD maps each direction to +/-32767. Without a circular
 * bound, a simultaneous horizontal/vertical input has magnitude
 * 32767*sqrt(2), potentially accelerating diagonal movement.
 *
 * Pure function: no game state, no timing changes, no camera effects.
 */
#ifndef SCARLET_STICK_NORMALIZE_H
#define SCARLET_STICK_NORMALIZE_H

#include <math.h>
#include <stdint.h>

static inline void scarlet_normalize_left_stick(int32_t *x, int32_t *y) {
    const int64_t max = 32767;
    const int64_t xx = (int64_t)*x;
    const int64_t yy = (int64_t)*y;
    const int64_t squared = xx * xx + yy * yy;
    if (squared <= max * max) return;
    const double scale = (double)max / sqrt((double)squared);
    /* Truncation avoids rounding a result just outside the stick circle. */
    *x = (int32_t)((double)xx * scale);
    *y = (int32_t)((double)yy * scale);
}

#endif /* SCARLET_STICK_NORMALIZE_H */
