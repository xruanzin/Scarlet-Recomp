/* Standalone camera Lua constant guard test; no game data included. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../runtime/scarlet_camera_script_patch.h"

int main(void) {
    size_t n = SCARLET_CAMERA_STEP_OFFSET + 64;
    uint8_t *original = malloc(n);
    assert(original);
    memset(original, 0x5a, n);
    const uint64_t t30 = SCARLET_CAMERA_STEP_30;
    memcpy(original + SCARLET_CAMERA_STEP_OFFSET, &t30, 8);

    assert(!scarlet_camera_patch_60(NULL, n));
    assert(!scarlet_camera_patch_60(original, SCARLET_CAMERA_STEP_OFFSET + 7));

    uint8_t *changed = malloc(n);
    assert(changed);
    memcpy(changed, original, n);
    assert(scarlet_camera_patch_60(changed, n));
    uint64_t actual;
    memcpy(&actual, changed + SCARLET_CAMERA_STEP_OFFSET, 8);
    assert(actual == SCARLET_CAMERA_STEP_60);
    assert(!memcmp(original, changed, SCARLET_CAMERA_STEP_OFFSET));
    assert(!memcmp(original + SCARLET_CAMERA_STEP_OFFSET + 8,
                   changed + SCARLET_CAMERA_STEP_OFFSET + 8,
                   n - SCARLET_CAMERA_STEP_OFFSET - 8));
    assert(!scarlet_camera_patch_60(changed, n)); /* no double patch */

    changed[SCARLET_CAMERA_STEP_OFFSET] = 0x00;
    assert(!scarlet_camera_patch_60(changed, n));
    free(original);
    free(changed);
    puts("camera script patch guards OK");
    return 0;
}
