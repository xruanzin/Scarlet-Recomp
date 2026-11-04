/* Experimental Scarlet 4.0.0 Dynamic FPS adapter.
 * The user supplies the original .pchtxt; game/mod bytes never ship with the runtime.
 * Parse and verify the entire patch before writing to decompressed guest memory.
 */
#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DFPS_MAX 192
#define DFPS_FNV_OFFSET UINT64_C(0xcbf29ce484222325)
#define DFPS_FNV_PRIME UINT64_C(0x100000001b3)
#define DFPS_EXPECTED_HASH UINT64_C(0x005c31864d041832)
#define DFPS_EXPECTED_COUNT 153

struct DfpsEntry { uint32_t off; uint8_t size, data[8]; };

static int dfps_hex(int ch) {
    if (ch >= '0' && ch <= '9') return ch - '0';
    if (ch >= 'a' && ch <= 'f') return ch - 'a' + 10;
    if (ch >= 'A' && ch <= 'F') return ch - 'A' + 10;
    return -1;
}
static uint64_t dfps_hash_byte(uint64_t h, uint8_t b) {
    return (h ^ b) * DFPS_FNV_PRIME;
}
static int dfps_valid_region(uint32_t off, uint32_t len, const uint32_t seg[3][3], uint32_t bss) {
    for (int i = 0; i < 3; ++i) {
        const uint64_t lo = seg[i][1], hi = lo + seg[i][2];
        if (off >= lo && (uint64_t)off + len <= hi) return 1;
    }
    const uint64_t lo = (uint64_t)seg[2][1] + seg[2][2];
    return off >= lo && (uint64_t)off + len <= lo + bss;
}

/* Returns zero only when all 153 checked entries were applied. */
int scarlet_dfps_apply_guest(const char *path, const uint8_t build_id[32], uint64_t base,
                            uint64_t image_size, const uint32_t seg[3][3], uint32_t bss,
                            char *why, size_t why_len) {
    static const char build[] = "421C5411B487EB4D049DD065FEC9547773E8E598";
    if (!path || !*path) { snprintf(why, why_len, "missing patch path"); return -1; }
    for (unsigned i = 0; i < 20; ++i) {
        if (build_id[i] != (uint8_t)((dfps_hex(build[2*i]) << 4) | dfps_hex(build[2*i+1]))) {
            snprintf(why, why_len, "Dynamic FPS requires Scarlet 4.0.0 main build ID");
            return -1;
        }
    }
    FILE *f = fopen(path, "rb");
    if (!f) { snprintf(why, why_len, "cannot open user-supplied .pchtxt"); return -1; }
    struct DfpsEntry entries[DFPS_MAX];
    size_t n = 0;
    uint64_t hash = DFPS_FNV_OFFSET;
    int have_id = 0, have_shift = 0, enabled = 0, stopped = 0, bad = 0;
    char line[512];
    while (fgets(line, sizeof line, f)) {
        if (!strchr(line, '\n') && !feof(f)) { bad = 1; break; }
        char *comment = strstr(line, "//"); if (comment) *comment = '\0';
        char *p = line; while (isspace((unsigned char)*p)) ++p;
        char *end = p + strlen(p);
        while (end > p && isspace((unsigned char)end[-1])) --end;
        *end = '\0';
        if (!*p || *p == '#' || !strncmp(p, "@Fl4sh_", 7) || !strncmp(p, "https:", 6)) continue;
        if (!strncmp(p, "@nsobid-", 8)) {
            if (have_id++ || strcmp(p + 8, build)) { bad = 1; break; }
            continue;
        }
        if (!strcmp(p, "@flag print_values")) continue;
        if (!strncmp(p, "@flag offset_shift", 18)) {
            if (have_shift++ || strcmp(p, "@flag offset_shift 0x100")) { bad = 1; break; }
            continue;
        }
        if (!strcmp(p, "@enabled")) {
            if (enabled || stopped) { bad = 1; break; }
            enabled = 1; continue;
        }
        if (!strcmp(p, "@stop")) {
            if (!enabled || stopped) { bad = 1; break; }
            enabled = 0; stopped = 1; continue;
        }
        if (!enabled || n >= DFPS_MAX) { bad = 1; break; }
        char *q = p;
        if (strlen(q) < 10) { bad = 1; break; }
        for (int i = 0; i < 8; i++) if (dfps_hex(q[i]) < 0) { bad = 1; break; }
        if (bad || !isspace((unsigned char)q[8])) { bad = 1; break; }
        uint32_t off = 0;
        for (int i = 0; i < 8; i++) off = (off << 4) | dfps_hex(q[i]);
        q += 8; while (isspace((unsigned char)*q)) ++q;
        size_t hexlen = strlen(q);
        if (hexlen != 8 && hexlen != 16) { bad = 1; break; }
        const uint8_t len = (uint8_t)(hexlen / 2);
        if (off & 3) { bad = 1; break; }
        for (size_t j = 0; j < n; j++) if (entries[j].off == off) bad = 1;
        if (bad) break;
        struct DfpsEntry *e = &entries[n++];
        e->off = off; e->size = len;
        for (size_t i = 0; i < hexlen; i += 2) {
            int a = dfps_hex(q[i]), b = dfps_hex(q[i+1]);
            if (a < 0 || b < 0) { bad = 1; break; }
            e->data[i/2] = (uint8_t)((a << 4) | b);
        }
        if (bad || (uint64_t)off + len > image_size ||
            !dfps_valid_region(off, len, seg, bss)) { bad = 1; break; }
        for (int i = 0; i < 4; ++i) hash = dfps_hash_byte(hash, (uint8_t)(off >> (i*8)));
        hash = dfps_hash_byte(hash, len);
        for (int i = 0; i < len; ++i) hash = dfps_hash_byte(hash, e->data[i]);
    }
    if (ferror(f)) bad = 1;
    fclose(f);
    if (bad || !have_id || !have_shift || !stopped || n != DFPS_EXPECTED_COUNT ||
        hash != DFPS_EXPECTED_HASH) {
        snprintf(why, why_len, "unsupported/modified Dynamic FPS ASM patch or NSO offset (%zu entries)", n);
        return -1;
    }
    /*
     * Opt-in A/B experiment for the intro's positive-Y amplification:
     * the reviewed 153-entry Fl4sh ASM stores float32 1.95 at MAIN+0x0438f010.
     * Its AOT-translated code reads this value from guest memory at runtime.
     * A value of 1.0 disables ONLY this gain while keeping all other verified
     * instructions unchanged. Not a gameplay-validated permanent fix.
     *
     * Never accept a modified .pchtxt or a different NSO: verify the original
     * fingerprint first and require the original constant at its exact site.
     */
    const char *neutral_y_env = getenv("SCARLET_DFPS_NEUTRAL_Y");
    const int neutral_y = neutral_y_env && !strcmp(neutral_y_env, "1");
    if (neutral_y_env && *neutral_y_env && !neutral_y && strcmp(neutral_y_env, "0")) {
        snprintf(why, why_len, "SCARLET_DFPS_NEUTRAL_Y must be 0 or 1");
        return -1;
    }
    if (neutral_y) {
        static const uint8_t original_gain[4] = {0x9a, 0x99, 0xf9, 0x3f};
        int found_gain = 0;
        for (size_t i = 0; i < n; ++i) {
            if (entries[i].off != UINT32_C(0x0438f010)) continue;
            if (entries[i].size != sizeof original_gain ||
                memcmp(entries[i].data, original_gain, sizeof original_gain)) {
                snprintf(why, why_len, "unexpected Scarlet DFPS Y gain bytes");
                return -1;
            }
            found_gain = 1;
            break;
        }
        if (!found_gain || (uint64_t)UINT32_C(0x0438f010) + 4 > image_size) {
            snprintf(why, why_len, "Scarlet DFPS Y gain site missing");
            return -1;
        }
    }
    for (size_t i = 0; i < n; ++i)
        memcpy((void *)(uintptr_t)(base + entries[i].off), entries[i].data, entries[i].size);
    if (neutral_y) {
        static const uint8_t unity_gain[4] = {0x00, 0x00, 0x80, 0x3f};
        memcpy((void *)(uintptr_t)(base + UINT32_C(0x0438f010)),
               unity_gain, sizeof unity_gain);
        fprintf(stderr,
                "[scarlet-dfps] intro A/B: MAIN+0x0438f010 Y gain 1.95 -> 1.0 "
                "(experimental, not scene gated)\n");
    }
    return 0;
}
