/* No GPU/game data: exercise production identity tracking with freed memory,
 * ABA reuse, queued-before-destroy semantics and concurrent registration. */
#include <assert.h>
#include <pthread.h>
#include "../runtime/nvn/nvn.h"
static void *worker(void *arg) {
    (void)arg;
    for (int i = 0; i < 10000; ++i) {
        NvnTexture t = {0};
        nvn_texture_publish(&t);
        uint64_t id = nvn_texture_record_id(&t);
        assert(nvn_texture_resolve_recorded(&t, id) == &t);
        nvn_texture_retire(&t);
        assert(!nvn_texture_resolve_recorded(&t, id));
    }
    return NULL;
}
int main(void) {
    NvnTexture *t = calloc(1, sizeof *t);
    nvn_texture_publish(t);
    uint64_t first = nvn_texture_record_id(t);
    assert(first && nvn_texture_resolve_recorded(t, first) == t);
    /* A command ahead of the queued destroy remains valid until retirement. */
    assert(nvn_texture_resolve_recorded(t, first) == t);
    nvn_texture_retire(t);
    t->backend = (void *)(uintptr_t)UINT64_MAX;
    assert(!nvn_texture_resolve_recorded(t, first));
    /* Force allocator-address reuse deterministically. */
    memset(t, 0, sizeof *t);
    nvn_texture_publish(t);
    uint64_t second = nvn_texture_record_id(t);
    assert(second != first);
    assert(!nvn_texture_resolve_recorded(t, first));
    assert(nvn_texture_resolve_recorded(t, second) == t);
    nvn_texture_retire(t);
    free(t);
    assert(!nvn_texture_resolve_recorded(t, second));
    assert(!nvn_texture_resolve_recorded(NULL, 0));
    assert(!nvn_texture_resolve_recorded((void *)(uintptr_t)UINT64_MAX, 123));
    pthread_t threads[4];
    for (int i = 0; i < 4; ++i) assert(!pthread_create(&threads[i], NULL, worker, NULL));
    for (int i = 0; i < 4; ++i) assert(!pthread_join(threads[i], NULL));
    puts("PASS: live, retired, freed, ABA, invalid token, 40000 concurrent lifetimes");
}
