// Standalone regression tests for the optional draw-capture selector.
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "../runtime/nvn/vulkan/draw_capture.h"

int main(void) {
    DrawCapture c = {0};
    assert(draw_capture_parse(&c, "deadcafe, 0123456789abcdef"));
    assert(c.nhashes == 2);
    assert(draw_capture_take(&c, true, 100, UINT64_C(0xdeadcafe)));
    assert(c.used == 1 && c.frame == 100);
    assert(!draw_capture_take(&c, true, 100, 0));
    assert(!draw_capture_take(&c, false, 100, UINT64_C(0xdeadcafe)));
    for (unsigned i = 1; i < DRAW_CAPTURE_MAX_DRAWS; ++i)
        assert(draw_capture_take(&c, true, 100, UINT64_C(0xdeadcafe)));
    assert(!draw_capture_take(&c, true, 100, UINT64_C(0xdeadcafe)));
    assert(draw_capture_take(&c, true, 101, UINT64_C(0xdeadcafe)));
    assert(c.used == 1 && c.frame == 101);
    assert(!draw_capture_parse(&c, "not-a-hash"));
    assert(c.nhashes == 0);
    assert(!draw_capture_parse(&c, "deadcafe,"));
    assert(!draw_capture_parse(&c, ""));
    assert(!draw_capture_parse(&c, "abcdefabcdefabcdef"));
    puts("PASS draw capture parser and per-frame capture limit");
    return 0;
}
