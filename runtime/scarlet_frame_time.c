/* Native presentation clock and validated Scarlet clock-1 time supply.
 * Gameplay speed and the other clock domains still require validation. */
#include "platform.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "cpu.h"

#ifdef SCARLET_AOT
extern int g_scarlet_target_fps;
static uint64_t measured_ns = 33333334;
static uint64_t accepted_presents;
static uint64_t submitted_frames, supplied_steps, supplied_ns;

/* Bounded coordinate observation for a private scripted movement run. Setter
 * requests are not actual post-physics coordinates or a player identity. */
void scarlet_position_observe(Cpu *c, uint64_t site) {
    const char *range = getenv("SCARLET_POSITION_TRACE");
    if (!range) return;
    unsigned long long first, last;
    if (sscanf(range, "%llu:%llu", &first, &last) != 2 || last < first || last - first > 1200) return;
    uint64_t frame = __atomic_load_n(&submitted_frames, __ATOMIC_RELAXED);
    if (frame < first || frame > last) return;
    static uint64_t samples;
    uint64_t sample = __atomic_add_fetch(&samples, 1, __ATOMIC_RELAXED);
    if (sample > 20000) {
        if (sample == 20001) fprintf(stderr, "[scarlet-position] truncated=1 limit=20000\n");
        return;
    }
    float xyz[3];
    const int readback = site == 0x19756f8;
    uint64_t object = c->x[readback ? 20 : 19], subject;
    memcpy(&subject, (const void *)(uintptr_t)(object + 8), sizeof subject);
    memcpy(xyz, &c->v[readback ? 0 : 2], sizeof xyz);
    fprintf(stderr, "[scarlet-position] site=%llx kind=%s object=%llx subject=%llx frame=%llu x=%.9g y=%.9g z=%.9g wall_ns=%llu\n",
            (unsigned long long)site, readback ? "readback" : "set_request",
            (unsigned long long)object, (unsigned long long)subject,
            (unsigned long long)frame, xyz[0], xyz[1], xyz[2],
            (unsigned long long)plat_now_ns());
}

/* Observe the downstream selector after FCSEL, before the original LDP.
 * This is effective input to d07a7c's work loop, not completed simulation.
 * The game's object flag/mode can select a fixed step; do not override it
 * until the flag's gameplay meaning is established. */
void scarlet_timing_effective(Cpu *c) {
    if (!getenv("SCARLET_TIMING_TRACE")) return;
    static _Thread_local uint64_t calls, total_ns;
    float dt;
    memcpy(&dt, &c->v[8], sizeof dt);
    if (!(dt >= 0.0f && dt <= 1.0f)) return;
    ++calls;
    total_ns += (uint64_t)((double)dt * 1e9 + 0.5);
    if (calls <= 8 || calls % 60 == 0)
        fprintf(stderr, "[scarlet-timing-effective] site=d07ad8 object=%llx thread=%llx flag=%llu mode=%llu seconds=%.9f calls=%llu supplied_ns=%llu wall_ns=%llu completion=unvalidated\n",
                (unsigned long long)c->x[20], (unsigned long long)(uintptr_t)c->thread,
                (unsigned long long)c->x[8],
                (unsigned long long)c->x[21], dt, (unsigned long long)calls,
                (unsigned long long)total_ns, (unsigned long long)plat_now_ns());
}

/* The getter returns a record, not elapsed simulation. Trace its consumers. */
void scarlet_timing_read(Cpu *c) {
    static _Thread_local uint64_t callers[64];
    static _Thread_local uint64_t indices[64];
    static _Thread_local unsigned samples[64];
    if (!getenv("SCARLET_TIMING_TRACE")) return;
    unsigned slot;
    for (slot = 0; slot < 64; ++slot) {
        if (callers[slot] == c->x[30] && indices[slot] == c->x[1]) break;
        if (!callers[slot]) { callers[slot] = c->x[30]; indices[slot] = c->x[1]; break; }
    }
    if (slot == 64 || samples[slot] >= 4) return;
    ++samples[slot];
    uint64_t record[2];
    memcpy(record, (const void *)(uintptr_t)c->x[0], sizeof record);
    fprintf(stderr, "[scarlet-timing-read] caller=%llx index=%llu record=%llx first=%llu step_ns=%llu wall_ns=%llu\n",
            (unsigned long long)c->x[30], (unsigned long long)c->x[1],
            (unsigned long long)c->x[0], (unsigned long long)record[0],
            (unsigned long long)record[1], (unsigned long long)plat_now_ns());
}

/* Accepted by Vulkan's presentation queue; not a display scan-out timestamp. */
void scarlet_present_accepted(void) {
    __atomic_add_fetch(&accepted_presents, 1, __ATOMIC_RELAXED);
}

/* Supply clock 1, then optionally record the selected temporal callback. */
void scarlet_timing_observe(Cpu *c, uint64_t site) {
    /* Proven Scarlet path: index 1 is consumed as signed integer ns and
     * divided by 1e9 at main+d07a4c..d07a60. The generator checks that code.
     * Keep zero-valued task gates and other clock domains untouched.
     * This counts supplied steps, not completion of physics or animation. */
    if (site == 0x92dd2c && c->x[1] == 1 && c->x[30] == UINT64_C(0x7002b7a934)) {
        uint64_t vtable, receiver;
        memcpy(&vtable, (const void *)(uintptr_t)c->x[0], 8);
        memcpy(&receiver, (const void *)(uintptr_t)(vtable + 16), 8);
        if (vtable == UINT64_C(0x7004440158) && receiver == UINT64_C(0x700092dd38) && c->x[2]) {
            uint64_t dt = __atomic_load_n(&measured_ns, __ATOMIC_RELAXED);
            if (!__atomic_load_n(&submitted_frames, __ATOMIC_RELAXED))
                dt = (1000000000ull + g_scarlet_target_fps - 1) / g_scarlet_target_fps;
            c->x[2] = dt;
            __atomic_add_fetch(&supplied_steps, 1, __ATOMIC_RELAXED);
            __atomic_add_fetch(&supplied_ns, dt, __ATOMIC_RELAXED);
        }
    }
    static int enabled = -1;
    static uint64_t calls[3];
    int on = __atomic_load_n(&enabled, __ATOMIC_RELAXED);
    if (on < 0) {
        on = getenv("SCARLET_TIMING_TRACE") != NULL;
        __atomic_store_n(&enabled, on, __ATOMIC_RELAXED);
    }
    if (!on) return;
    unsigned slot = site == 0x92dd2c ? 0 : site == 0x2b7b314 ? 1 : 2;
    uint64_t call = __atomic_add_fetch(&calls[slot], 1, __ATOMIC_RELAXED);
    if (call <= 16 || call % 300 == 0) {
        uint64_t vtable, receiver;
        memcpy(&vtable, (const void *)(uintptr_t)c->x[0], sizeof vtable);
        memcpy(&receiver, (const void *)(uintptr_t)(vtable + 16), sizeof receiver);
        fprintf(stderr, "[scarlet-timing-probe] site=%llx call=%llu caller=%llx object=%llx vtable=%llx receiver=%llx x1=%llu input_ns=%llu wall_ns=%llu measured_ns=%llu\n",
                (unsigned long long)site, (unsigned long long)call,
                (unsigned long long)c->x[30], (unsigned long long)c->x[0],
                (unsigned long long)vtable, (unsigned long long)receiver,
                (unsigned long long)c->x[1], (unsigned long long)c->x[2],
                (unsigned long long)plat_now_ns(),
                (unsigned long long)__atomic_load_n(&measured_ns, __ATOMIC_RELAXED));
    }
}

uint64_t scarlet_frame_time_ns(void) {
    return __atomic_load_n(&measured_ns, __ATOMIC_RELAXED);
}

void scarlet_frame_present(void) {
    static uint64_t last, history[8], report, previous_accepted, previous_supplied;
    static unsigned count, cursor, frames;
    const uint64_t period = (1000000000ull + g_scarlet_target_fps - 1) /
                            g_scarlet_target_fps;
    uint64_t now = plat_now_ns();
    if (last && now < last + period) {
        plat_sleep_until_ns(last + period);
        now = plat_now_ns();
    }
    uint64_t elapsed = last ? now - last : period;
    if (!last || elapsed > 250000000ull) {
        count = cursor = 0;
        elapsed = period;
    }
    last = now;
    __atomic_add_fetch(&submitted_frames, 1, __ATOMIC_RELAXED);
    if (elapsed > 100000000ull) elapsed = 100000000ull;
    if (elapsed < period) elapsed = period;
    history[cursor++ % 8] = elapsed;
    if (count < 8) ++count;
    uint64_t sum = 0;
    for (unsigned i = 0; i < count; ++i) sum += history[i];
    __atomic_store_n(&measured_ns, sum / count, __ATOMIC_RELAXED);
    if (!report) report = now;
    ++frames;
    if (now - report >= 1000000000ull) {
        uint64_t accepted = __atomic_load_n(&accepted_presents, __ATOMIC_RELAXED);
        uint64_t supplied = __atomic_load_n(&supplied_ns, __ATOMIC_RELAXED);
        fprintf(stderr, "[scarlet-frame] wall_ns=%llu submissions_fps=%.3f present_accepted_fps=%.3f mean_ms=%.3f clock1_supplied_steps=%llu clock1_supplied_ns=%llu supplied_wall_ratio=%.6f gameplay_speed=unvalidated\n",
                (unsigned long long)now,
                frames * 1e9 / (now - report),
                (accepted - previous_accepted) * 1e9 / (now - report),
                (sum / count) / 1e6,
                (unsigned long long)__atomic_load_n(&supplied_steps, __ATOMIC_RELAXED),
                (unsigned long long)supplied,
                (double)(supplied - previous_supplied) / (double)(now - report));
        previous_supplied = supplied;
        previous_accepted = accepted;
        report = now;
        frames = 0;
    }
}
#endif
