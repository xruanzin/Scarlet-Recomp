// Small, header-only selector for targeted fragment-shader draw captures.
// Included by the Vulkan executor; no effect unless SCARLET_CAPTURE_FSHASH
// explicitly names one or more shader hashes and a frame capture is active.
#ifndef SCARLET_DRAW_CAPTURE_H
#define SCARLET_DRAW_CAPTURE_H

#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <ctype.h>
#include <string.h>

enum { DRAW_CAPTURE_MAX_HASHES = 16, DRAW_CAPTURE_MAX_DRAWS = 24 };

typedef struct {
    uint64_t hashes[DRAW_CAPTURE_MAX_HASHES];
    unsigned nhashes;
    uint64_t frame;
    unsigned used;
} DrawCapture;

// Accept a comma-separated list of 1 to 16 hex shader hashes. Reject an
// invalid or partially parsed list without leaving capture enabled.
static inline bool draw_capture_parse(DrawCapture *capture, const char *spec) {
    if (!capture) return false;
    memset(capture, 0, sizeof *capture);
    if (!spec || !*spec) return false;

    DrawCapture parsed = {0};
    const char *p = spec;
    while (*p) {
        while (isspace((unsigned char)*p)) ++p;
        if (!isxdigit((unsigned char)*p) || parsed.nhashes >= DRAW_CAPTURE_MAX_HASHES)
            return false;

        // strtoull accepts a leading 0x but requires at least a hex digit
        // afterward; validate the full token below before accepting it.
        const char *begin = p;
        if (p[0] == '0' && (p[1] == 'x' || p[1] == 'X')) p += 2;
        const char *digits = p;
        unsigned ndigits = 0;
        while (isxdigit((unsigned char)*p)) {
            if (++ndigits > 16) return false;
            ++p;
        }
        if (p == digits) return false;
        char *end = NULL;
        uint64_t hash = (uint64_t)strtoull(begin, &end, 16);
        if (!end || end != p) return false;

        while (isspace((unsigned char)*p)) ++p;
        if (*p && *p != ',') return false;
        parsed.hashes[parsed.nhashes++] = hash;
        if (!*p) break;
        ++p;
        if (!*p) return false;
    }
    if (!parsed.nhashes) return false;
    *capture = parsed;
    return true;
}

// Limit captures per presentation frame; only count matching shader draws.
// The caller gates this on its existing debug-capture flag, so normal
// gameplay incurs no readback or draw-capture I/O.
static inline bool draw_capture_take(DrawCapture *capture, bool eligible,
                                     uint64_t frame, uint64_t fs_hash) {
    if (!capture || !eligible || !capture->nhashes) return false;
    if (capture->frame != frame) {
        capture->frame = frame;
        capture->used = 0;
    }
    if (capture->used >= DRAW_CAPTURE_MAX_DRAWS) return false;
    for (unsigned i = 0; i < capture->nhashes; ++i) {
        if (capture->hashes[i] == fs_hash) {
            ++capture->used;
            return true;
        }
    }
    return false;
}

#endif  // SCARLET_DRAW_CAPTURE_H
