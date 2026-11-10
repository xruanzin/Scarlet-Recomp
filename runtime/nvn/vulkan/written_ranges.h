#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

// Exact byte coverage of the current frame's transform feedback mirror.
// A partial write must not validate neighbouring bytes in the same allocation.
#define WRITTEN_RANGE_CAP 8192
typedef struct { uint64_t lo, hi; } WrittenRange;
typedef struct {
    WrittenRange ranges[WRITTEN_RANGE_CAP];
    uint64_t frame;
    unsigned count;
    bool overflow;
} WrittenRanges;

static inline void written_add(WrittenRanges *w, uint64_t frame, uint64_t lo, uint64_t size) {
    if (w->frame != frame) { w->frame = frame; w->count = 0; w->overflow = false; }
    if (!size || lo > UINT64_MAX - size || w->overflow) return;
    uint64_t hi = lo + size;
    unsigned first = 0;
    while (first < w->count && w->ranges[first].hi < lo) first++;
    unsigned end = first;
    while (end < w->count && w->ranges[end].lo <= hi) {
        if (w->ranges[end].lo < lo) lo = w->ranges[end].lo;
        if (w->ranges[end].hi > hi) hi = w->ranges[end].hi;
        end++;
    }
    if (end == first && w->count == WRITTEN_RANGE_CAP) { w->overflow = true; return; }
    memmove(w->ranges + first + 1, w->ranges + end, (w->count - end) * sizeof *w->ranges);
    w->count = w->count - (end - first) + 1;
    w->ranges[first] = (WrittenRange){lo, hi};
}

static inline bool written_contains(const WrittenRanges *w, uint64_t frame, uint64_t lo, uint64_t size) {
    if (!size || lo > UINT64_MAX - size || w->frame != frame || w->overflow) return false;
    unsigned a = 0, b = w->count;
    while (a < b) {
        unsigned mid = a + (b - a) / 2;
        if (w->ranges[mid].lo <= lo) a = mid + 1; else b = mid;
    }
    return a && lo + size <= w->ranges[a - 1].hi;
}
