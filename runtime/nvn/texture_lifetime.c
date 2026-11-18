/* Recorded commands outlive NVN objects. Check identity without dereferencing
 * a recorded (possibly freed/reused) pointer. Destruction and execution are
 * serialized by the render queue, or exec_lock with the queue disabled.
 * The mutex additionally protects recording/publication on game threads.
 */
#include <pthread.h>
#include "nvn.h"
#define LIFE_BUCKETS 1024
static NvnTexture *live[LIFE_BUCKETS];
static uint64_t next_lifetime = 1;
static pthread_mutex_t lifetime_lock = PTHREAD_MUTEX_INITIALIZER;
static size_t lifetime_bucket(const NvnTexture *t) {
    return ((uintptr_t)t >> 4) % LIFE_BUCKETS;
}
void nvn_texture_publish(NvnTexture *t) {
    pthread_mutex_lock(&lifetime_lock);
    size_t h = lifetime_bucket(t);
    t->lifetime_id = next_lifetime++;
    t->lifetime_next = live[h];
    live[h] = t;
    pthread_mutex_unlock(&lifetime_lock);
}
void nvn_texture_retire(NvnTexture *t) {
    pthread_mutex_lock(&lifetime_lock);
    for (NvnTexture **p = &live[lifetime_bucket(t)]; *p; p = &(*p)->lifetime_next)
        if (*p == t) { *p = t->lifetime_next; break; }
    pthread_mutex_unlock(&lifetime_lock);
}
uint64_t nvn_texture_record_id(NvnTexture *t) {
    uint64_t id = 0;
    pthread_mutex_lock(&lifetime_lock);
    for (NvnTexture *p = live[lifetime_bucket(t)]; p; p = p->lifetime_next)
        if (p == t) { id = p->lifetime_id; break; }
    pthread_mutex_unlock(&lifetime_lock);
    return id;
}
NvnTexture *nvn_texture_resolve_recorded(NvnTexture *t, uint64_t id) {
    return id && nvn_texture_record_id(t) == id ? t : NULL;
}
NvnTexture *nvn_texture_resolve_command(uint64_t ptr, uint64_t id, const char *op) {
    NvnTexture *t = nvn_texture_resolve_recorded((NvnTexture *)(uintptr_t)ptr, id);
    // Called only on the serialized executor; bounded, no per-frame output.
    static unsigned logs;
    if (ptr && !t && logs < 8) {
        logs++;
        LOG("[nvn] %s: retired/reused texture reference ignored (id=%llu)%s\n",
            op, (unsigned long long)id, logs == 8 ? " (further ones not logged)" : "");
    }
    return t;
}
RT_ON_RESET(texture_lifetime_reset) {
    /* All guest/render work has stopped before runtime reset. Keep IDs unique. */
    memset(live, 0, sizeof live);
}
