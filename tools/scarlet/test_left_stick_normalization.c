/* Tests the real Scarlet left-stick normalization helper without game data. */
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include "../../runtime/hle/scarlet_stick_normalize.h"

static int64_t norm2(int32_t x, int32_t y) {
    return (int64_t)x * x + (int64_t)y * y;
}

static void expect_within_circle(int32_t x, int32_t y) {
    assert(norm2(x, y) <= (int64_t)32767 * 32767);
}

int main(void) {
    int32_t x, y;

    x = 32767; y = 0;
    scarlet_normalize_left_stick(&x, &y);
    assert(x == 32767 && y == 0);

    x = 0; y = -32767;
    scarlet_normalize_left_stick(&x, &y);
    assert(x == 0 && y == -32767);

    x = 32767; y = 32767;
    assert(norm2(x, y) > (int64_t)32767 * 32767);
    scarlet_normalize_left_stick(&x, &y);
    expect_within_circle(x, y);
    assert(x > 23160 && x < 23180 && y == x);

    x = -32767; y = 32767;
    scarlet_normalize_left_stick(&x, &y);
    expect_within_circle(x, y);
    assert(-x == y);

    x = 15000; y = 10000;
    scarlet_normalize_left_stick(&x, &y);
    assert(x == 15000 && y == 10000);

    x = 32767; y = 100;
    scarlet_normalize_left_stick(&x, &y);
    expect_within_circle(x, y);

    x = 0; y = 0;
    scarlet_normalize_left_stick(&x, &y);
    assert(x == 0 && y == 0);

    return 0;
}
