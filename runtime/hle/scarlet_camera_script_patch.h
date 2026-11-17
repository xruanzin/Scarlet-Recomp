/* Per-build Scarlet 4.0.0 script timing adjustment.
 *
 * This does not touch the Oodle decoder or any on-disk game file.
 * Host code checks the original chunk's entire SHA-256 before using it.
 * Only the 0.17518 controller scheduler's 1/30 Lua double is changed.
 */
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define SCARLET_CAMERA_SCRIPT_SHA256 "c1a4f4e2625912cf0b739a642a79ba3357df0557a544b92da22a6cb139de2815"
#define SCARLET_CAMERA_STEP_OFFSET ((size_t)0x7efc05)
#define SCARLET_CAMERA_STEP_30 UINT64_C(0x3fa1111111111111)
#define SCARLET_CAMERA_STEP_60 UINT64_C(0x3f91111111111111)

static inline int scarlet_camera_patch_60(uint8_t *data, size_t size) {
    if (!data || size < SCARLET_CAMERA_STEP_OFFSET + sizeof(uint64_t))
        return 0;
    uint64_t original;
    memcpy(&original, data + SCARLET_CAMERA_STEP_OFFSET, sizeof original);
    if (original != SCARLET_CAMERA_STEP_30) return 0;
    const uint64_t target = SCARLET_CAMERA_STEP_60;
    memcpy(data + SCARLET_CAMERA_STEP_OFFSET, &target, sizeof target);
    return 1;
}
