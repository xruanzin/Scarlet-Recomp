// NVN 16-bit packed colour texture conversion (low-bit red channel).
// These formats are not byte-identical to Vulkan's similarly named PACK16 types.
#ifndef SCARLET_NVN_PACKED16_H
#define SCARLET_NVN_PACKED16_H
#include <stddef.h>
#include <stdint.h>

// NVN RGBA4: R bits 0..3, G 4..7, B 8..11, A 12..15.
static inline void nvn_unpack_rgba4(uint8_t *dst, const uint8_t *src, size_t pixels) {
    for (size_t i = 0; i < pixels; i++) {
        uint16_t v = (uint16_t)src[i * 2] | ((uint16_t)src[i * 2 + 1] << 8);
        for (unsigned c = 0; c < 4; c++) {
            uint8_t n = (uint8_t)((v >> (4 * c)) & 0xF);
            dst[i * 4 + c] = (uint8_t)(n | (n << 4));
        }
    }
}

// NVN RGB5A1: R bits 0..4, G 5..9, B 10..14, A bit 15.
static inline void nvn_unpack_rgb5a1(uint8_t *dst, const uint8_t *src, size_t pixels) {
    for (size_t i = 0; i < pixels; i++) {
        uint16_t v = (uint16_t)src[i * 2] | ((uint16_t)src[i * 2 + 1] << 8);
        for (unsigned c = 0; c < 3; c++) {
            uint8_t n = (uint8_t)((v >> (5 * c)) & 0x1F);
            dst[i * 4 + c] = (uint8_t)((n << 3) | (n >> 2));
        }
        dst[i * 4 + 3] = (v & 0x8000) ? 255 : 0;
    }
}
#endif
