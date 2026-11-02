// Compile: gcc -std=c11 -Wall -Wextra -Werror -I. tools/test_scarlet_packed16.c -o packed16-test.exe
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "runtime/nvn/packed16.h"
static void test_rgba4(void) {
    const uint8_t in[] = {0x0f, 0xf0, 0x21, 0x43, 0x00, 0x00, 0xff, 0xff};
    uint8_t out[16] = {0};
    const uint8_t expected[] = {255, 0, 0, 255, 17, 34, 51, 68, 0, 0, 0, 0, 255, 255, 255, 255};
    nvn_unpack_rgba4(out, in, 4);
    for (unsigned i = 0; i < sizeof out; i++) assert(out[i] == expected[i]);
}
static void test_rgb5a1(void) {
    const uint8_t in[] = {0x1f, 0x80, 0xe0, 0x83, 0x00, 0xfc, 0xff, 0xff};
    uint8_t out[16] = {0};
    const uint8_t expected[] = {255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255, 255, 255, 255, 255};
    nvn_unpack_rgb5a1(out, in, 4);
    for (unsigned i = 0; i < sizeof out; i++) assert(out[i] == expected[i]);
}
int main(void) {
    test_rgba4(); test_rgb5a1();
    puts("PASS: NVN RGBA4 and RGB5A1 packed16 -> RGBA8");
    return 0;
}
