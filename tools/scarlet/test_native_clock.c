/* Execute the actual runtime timing code against a deterministic host clock. */
#define SCARLET_AOT 1
#include <assert.h>
#include <windows.h>
#include "../../runtime/scarlet_frame_time.c"

int g_scarlet_target_fps = 60;
static uint64_t fake_now = 1000000000ull;
uint64_t plat_now_ns(void) { return fake_now; }
void plat_sleep_until_ns(uint64_t t) { if (fake_now < t) fake_now = t; }

int main(void) {
    void *page = VirtualAlloc((void *)(uintptr_t)0x7004440000ull, 0x10000,
                             MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    assert(page == (void *)(uintptr_t)0x7004440000ull);
    uint64_t *table = (uint64_t *)(uintptr_t)0x7004440158ull;
    table[2] = 0x700092dd38ull;
    uint64_t object[16] = {0x7004440158ull};
    Cpu c = {0};
    c.x[0] = (uintptr_t)object;
    c.x[1] = 1;
    c.x[2] = 33333334;
    c.x[30] = 0x7002b7a934ull;
    scarlet_timing_observe(&c, 0x92dd2c);
    assert(c.x[2] == 16666667); /* Correct even before first presentation. */
    for (int i=0; i<32; ++i) scarlet_frame_present();
    assert(scarlet_frame_time_ns() == 16666667);
    for (int i=0; i<16; ++i) { fake_now += 40000000; scarlet_frame_present(); }
    c.x[2] = 16666667;
    scarlet_timing_observe(&c, 0x92dd2c);
    assert(c.x[2] == 40000000); /* Slow frames advance proportionally. */
    c.x[2] = 0;
    scarlet_timing_observe(&c, 0x92dd2c);
    assert(c.x[2] == 0); /* Task suspension survives. */
    c.x[1] = 0; c.x[2] = 123;
    scarlet_timing_observe(&c, 0x92dd2c);
    assert(c.x[2] == 123); /* Other clock domains untouched. */
    c.x[1] = 1; c.x[30] = 1;
    scarlet_timing_observe(&c, 0x92dd2c);
    assert(c.x[2] == 123); /* Unknown producer untouched. */
    fake_now += 2000000000ull;
    scarlet_frame_present();
    assert(scarlet_frame_time_ns() == 16666667); /* No loading jump. */
    g_scarlet_target_fps = 30;
    for (int i=0; i<16; ++i) scarlet_frame_present();
    assert(scarlet_frame_time_ns() == 33333334);
    VirtualFree(page, 0, MEM_RELEASE);
    puts("PASS: runtime clock, slow frames, startup, stall reset, 30/60 caps and domain gates");
}
