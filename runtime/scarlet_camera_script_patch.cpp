/* KarPur-inspired script timing fix for Scarlet's own decoded main.blua.
 *
 * Injection point: before Lua 5.4's luaL_loadbufferx sees the main script.
 * Not an external mod: the original script file is never edited. A private,
 * immutable copy is made only after checking the *whole original* SHA-256,
 * then one proven controller scheduler value is updated.
 *
 * Default at 60 FPS: on; opt out with SCARLET_INDOOR_CAMERA_60=0.
 * This is intentionally an experiment; indoor gameplay still needs A/B
 * validation for camera motion, animation duration and battle timing.
 */
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <mutex>
#include <new>
#include <string>

#include "cpu.h"
#include "cache_sha256.h"
#include "scarlet_camera_script_patch.h"

extern "C" int g_scarlet_target_fps;

extern "C" void scarlet_lua_camera_before_load(Cpu *c) {
#ifdef SCARLET_AOT
    if (g_scarlet_target_fps != 60 || !c) return;
    static int enable = -1;
    if (enable == -1) {
        const char *setting = getenv("SCARLET_INDOOR_CAMERA_60");
        enable = !(setting && !strcmp(setting, "0"));
        fprintf(stderr, "[scarlet-camera] main.blua targeted 60 Hz script step %s\n",
                enable ? "enabled" : "disabled");
    }
    if (!enable) return;

    /* luaL_loadbufferx(L, const char *buff, size_t size, const char *name, const char *mode)
     * guest x0..x4. Do not modify any argument other than x1.
     */
    const uint64_t count = c->x[2];
    const uintptr_t address = (uintptr_t)c->x[1];
    if (count < SCARLET_CAMERA_STEP_OFFSET + 8 ||
        count > 64ull * 1024 * 1024 ||
        address < 0x10000 ||
        address > UINTPTR_MAX - count) return;

    static std::mutex mutex;
    static std::unique_ptr<uint8_t[]> corrected;
    static size_t corrected_size;
    static uint64_t patched_loads;
    std::lock_guard<std::mutex> held(mutex);
    const uint8_t *const script = (const uint8_t *)address;

    /* If another Lua state already received the same immutable script,
     * we still validate the next source buffer. No source is overwritten.
     */
    const uint64_t candidate_word = SCARLET_CAMERA_STEP_OFFSET;
    uint64_t current;
    memcpy(&current, script + candidate_word, sizeof current);
    if (current != SCARLET_CAMERA_STEP_30) return;

    CacheSha256 hash;
    hash.add(script, (size_t)count);
    if (hash.finish() != SCARLET_CAMERA_SCRIPT_SHA256) {
        static bool warned;
        if (!warned) {
            warned = true;
            fprintf(stderr, "[scarlet-camera] script SHA differs; refusing 60 Hz patch\n");
        }
        return;
    }

    if (!corrected || corrected_size != count) {
        std::unique_ptr<uint8_t[]> updated(new (std::nothrow) uint8_t[(size_t)count]);
        if (!updated) {
            fprintf(stderr, "[scarlet-camera] cannot allocate private script buffer; unchanged\n");
            return;
        }
        memcpy(updated.get(), script, (size_t)count);
        if (!scarlet_camera_patch_60(updated.get(), (size_t)count)) {
            fprintf(stderr, "[scarlet-camera] script content guard failed; unchanged\n");
            return;
        }
        corrected_size = (size_t)count;
        corrected = std::move(updated);
        fprintf(stderr, "[scarlet-camera] applied in-memory camera script step 1/30 -> 1/60 "
                        "at main.blua +0x%zx; original SHA verified\n",
                SCARLET_CAMERA_STEP_OFFSET);
    }
    c->x[1] = (uint64_t)(uintptr_t)corrected.get();
    if (++patched_loads <= 8)
        fprintf(stderr, "[scarlet-camera] supplied corrected main.blua to Lua, load %llu\n",
                (unsigned long long)patched_loads);
#else
    (void)c;
#endif
}
