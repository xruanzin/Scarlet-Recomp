/*
 * Standalone regression test: verified user-owned Fl4sh Scarlet 4.0.0 ASM.
 * Compile together with runtime/scarlet_dfps_guest.c. The supplied .pchtxt
 * stays on disk; no game data, recompilation, or binary distribution needed.
 */
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int scarlet_dfps_apply_guest(const char *path, const uint8_t build_id[32],
                            uint64_t base, uint64_t image_size,
                            const uint32_t seg[3][3], uint32_t bss,
                            char *why, size_t why_len);

#define IMAGE_SIZE UINT32_C(0x047d4000)
#define GAIN_OFF UINT32_C(0x0438f010)
#define LIMIT_OFF UINT32_C(0x0438f014)
#define BRANCH_OFF UINT32_C(0x00cce37c)

static void set_mode(const char *value) {
#ifdef _WIN32
    if (_putenv_s("SCARLET_DFPS_NEUTRAL_Y", value)) abort();
#else
    if (setenv("SCARLET_DFPS_NEUTRAL_Y", value, 1)) abort();
#endif
}
static int check(const char *name, const uint8_t *actual, const uint8_t expected[4]) {
    if (memcmp(actual, expected, 4)) {
        fprintf(stderr, "FAIL: %s: got %02x %02x %02x %02x\\n",
                name, actual[0], actual[1], actual[2], actual[3]);
        return 0;
    }
    return 1;
}
int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: test_dfps_y_gain original-patch.pchtxt\\n");
        return 2;
    }
    const uint8_t build[32] = {
        0x42, 0x1c, 0x54, 0x11, 0xb4, 0x87, 0xeb, 0x4d,
        0x04, 0x9d, 0xd0, 0x65, 0xfe, 0xc9, 0x54, 0x77,
        0x73, 0xe8, 0xe5, 0x98
    };
    const uint32_t segments[3][3] = {
        {0, 0, IMAGE_SIZE}, {0, IMAGE_SIZE, 0}, {0, IMAGE_SIZE, 0}
    };
    const uint8_t original_gain[4] = {0x9a, 0x99, 0xf9, 0x3f};
    const uint8_t unity_gain[4] = {0x00, 0x00, 0x80, 0x3f};
    const uint8_t limit[4] = {0x00, 0x00, 0xa4, 0x41};
    const uint8_t branch[4] = {0x28, 0x4b, 0x2a, 0x14};
    uint8_t *image = calloc(1, IMAGE_SIZE);
    char why[256] = "";
    if (!image) { fprintf(stderr, "allocation failed\\n"); return 2; }
    for (int test = 0; test < 4; test++) {
        memset(image, 0, IMAGE_SIZE);
        const char *mode = test == 0 ? "0" : test == 1 ? "1" : test == 2 ? "invalid" : "1";
        uint8_t wrong_build[32];
        memcpy(wrong_build, build, sizeof build);
        if (test == 3) wrong_build[0] ^= 0xff;
        set_mode(mode);
        memset(why, 0, sizeof why);
        int ret = scarlet_dfps_apply_guest(argv[1], test == 3 ? wrong_build : build,
                (uint64_t)(uintptr_t)image, IMAGE_SIZE, segments, 0, why, sizeof why);
        if (test < 2) {
            if (ret || !check("Y gain", image + GAIN_OFF,
                             test == 0 ? original_gain : unity_gain) ||
                !check("Y limit", image + LIMIT_OFF, limit) ||
                !check("original DFPS branch", image + BRANCH_OFF, branch)) {
                fprintf(stderr, "FAIL: case %d: %s\\n", test, why);
                free(image); return 1;
            }
        } else if (!ret || image[GAIN_OFF] || image[BRANCH_OFF]) {
            fprintf(stderr, "FAIL: invalid mode/build should fail closed (%s)\\n", why);
            free(image); return 1;
        }
    }
    free(image);
    puts("PASS: original 1.95; opt-in 1.0; other ASM unchanged; invalid settings rejected");
    return 0;
}
