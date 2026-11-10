"""Compile the actual runtime setjmp registry and exercise host longjmp (no game/AOT).

Run: python tools/test_dispatch_jmp.py [--cc PATH]
Requires a C compiler and pthreads; on Windows defaults to MSYS2 UCRT64 clang.
The extracted registry uses the unchanged public RtJmp layout and minimal Cpu fields.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <setjmp.h>
#include <pthread.h>
#include <stdatomic.h>
typedef struct { uint64_t x[32], sp, pc; } Cpu;
typedef struct RtJmp { jmp_buf host; uint64_t buf, ret, sp; } RtJmp;
#define FATAL(...) do { fprintf(stderr, __VA_ARGS__); exit(2); } while (0)
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
static atomic_int allocations;
static void *test_calloc(size_t n, size_t s) {
    void *p = calloc(n, s);
    if (p) atomic_fetch_add(&allocations, 1);
    return p;
}
static void test_free(void *p) {
    if (p) atomic_fetch_sub(&allocations, 1);
    free(p);
}
#define calloc test_calloc
#define free test_free
'''
HARNESS = r'''
#undef calloc
#undef free
static void jump_to(uint64_t ret, uint64_t sp) {
    Cpu c = {.pc = ret, .sp = sp};
    RtJmp *j = rt_findjmp(&c);
    CHECK(j != NULL);
    longjmp(j->host, 1);
}
static void many_buffers(void) {
    Cpu c = {.x = {0x1000}, .sp = 0x800000};
    if (!setjmp(rt_setjmp_site(&c, 0x7000026ca4)->host)) {
        for (int i = 1; i <= 256; i++) {
            Cpu inner = {.x = {0x1000 + (uint64_t)i * 0x100},
                         .sp = 0x800000 - (uint64_t)i * 0x200};
            (void)rt_setjmp_site(&inner, 0x7000026ca4);
        }
        jump_to(0x7000026ca4, 0x800000);
    }
}
static void nested(int depth) {
    Cpu c = {.x = {0x100000 + (uint64_t)depth * 0x100},
             .sp = 0x900000 - (uint64_t)depth * 0x200};
    if (!setjmp(rt_setjmp_site(&c, 0x7000030000)->host)) {
        if (depth < 96) nested(depth + 1);
        else jump_to(0x7000030000, 0x900000);
        CHECK(0);
    }
    CHECK(depth == 0);
}
static void reuse_and_mismatch(void) {
    Cpu c = {.x = {0x200000}, .sp = 0xa00000, .pc = 0x4000};
    RtJmp *first = rt_setjmp_site(&c, c.pc);
    CHECK(rt_findjmp(&c) == first);
    c.pc++;
    CHECK(rt_findjmp(&c) == NULL);
    c.pc--;
    c.sp++;
    CHECK(rt_findjmp(&c) == NULL);
    c.sp--;
    CHECK(rt_setjmp_site(&c, 0x5000) == first);
    CHECK(rt_findjmp(&c) == NULL);
    c.pc = 0x5000;
    CHECK(rt_findjmp(&c) == first);
}
static void *worker(void *unused) {
    (void)unused;
    Cpu c = {.pc = 0x7000026ca4, .sp = 0x800000};
    CHECK(rt_findjmp(&c) == NULL); /* parent uses these exact guest values */
    many_buffers();
    nested(0);
    reuse_and_mismatch();
    return NULL;
}
int main(void) {
    many_buffers();
    nested(0);
    reuse_and_mismatch();
    int parent_allocations = atomic_load(&allocations);
    CHECK(parent_allocations > 32);
    pthread_t threads[4];
    for (int i = 0; i < 4; i++) CHECK(!pthread_create(&threads[i], NULL, worker, NULL));
    for (int i = 0; i < 4; i++) CHECK(!pthread_join(threads[i], NULL));
    CHECK(atomic_load(&allocations) == parent_allocations); /* thread destructor */
    void *head = jmp_sites();
    CHECK(!pthread_setspecific(jmp_key, NULL));
    jmp_sites_free(head);
    CHECK(atomic_load(&allocations) == 0);
    puts("PASS: 256 buffers, 96 nested frames, reuse, ret/SP mismatch, 4 threads, cleanup");
    return 0;
}
'''
LEGACY = r'''
static RtJmp old_sites[32];
static unsigned old_next;
RtJmp *rt_setjmp_site(Cpu *c, uint64_t ret) {
    RtJmp *j = NULL;
    for (int i = 0; i < 32 && !j; i++) if (old_sites[i].buf == c->x[0]) j = &old_sites[i];
    if (!j) j = &old_sites[old_next++ % 32];
    j->buf = c->x[0]; j->ret = ret; j->sp = c->sp;
    return j;
}
static RtJmp *rt_findjmp(Cpu *c) {
    for (int i = 0; i < 32; i++)
        if (old_sites[i].buf && old_sites[i].ret == c->pc && old_sites[i].sp == c->sp) return &old_sites[i];
    return NULL;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", default=os.environ.get("CC") or (r"C:\msys64\ucrt64\bin\clang.exe" if os.name == "nt" else "clang"))
    args = parser.parse_args()
    compiler = shutil.which(args.cc)
    if not compiler:
        parser.error(f"compiler unavailable: {args.cc}")
    source = (ROOT / "runtime" / "dispatch.c").read_text(encoding="utf-8")
    start = source.index("// Guest setjmp sites")
    end = source.index("__attribute__((noinline)) static GuestFn dispatch_slow", start)
    registry = source[start:end]
    env = dict(os.environ)
    env["PATH"] = str(Path(compiler).parent) + os.pathsep + env.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="scarlet-jmp-test-") as tmp:
        for name, code, expected in (
            ("registry", PREFIX + registry + HARNESS, 0),
            ("legacy", PREFIX[:PREFIX.index("static atomic_int")] + LEGACY + HARNESS[:HARNESS.index("static void nested")] + "\nint main(void) { many_buffers(); return 0; }\n", 1),
        ):
            cfile = Path(tmp) / f"{name}.c"
            exe = Path(tmp) / (name + (".exe" if os.name == "nt" else ""))
            cfile.write_text(code, encoding="utf-8")
            subprocess.run([compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-pthread", str(cfile), "-o", str(exe)], check=True, env=env)
            result = subprocess.run([str(exe)], capture_output=True, text=True, env=env)
            if result.returncode != expected:
                raise SystemExit(f"{name}: expected exit {expected}, got {result.returncode}\n{result.stdout}{result.stderr}")
            if name == "legacy":
                print("PASS: legacy 32-slot registry reproduces lost outer context (expected failure)")
            else:
                print(result.stdout.strip())


if __name__ == "__main__":
    main()
