"""Exercise actual texture recorders/Vulkan target binding, without a GPU.

Payload producers and consumers are extracted from production, not reimplemented.
The identity registry is linked directly. No game data is needed.
"""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
record = (root / 'runtime/nvn/cmdbuf.c').read_text()
execute = (root / 'runtime/nvn/vulkan/exec.c').read_text()
textures = (root / 'runtime/nvn/vulkan/textures.c').read_text()

def between(s, start, end):
    return s[s.index(start):s.index(end, s.index(start))]

snap = between(record, 'typedef struct { uint64_t x[8]; float f[4]; } Snap;', 'static CmdRec *record(')
rt = between(record, 'typedef NvnRtRec RtRec;', '// viewports/scissors')
copies = between(record, 'typedef NvnTexRefRec TexRef;', 'PLAIN(nvnCommandBufferCopyBufferToBuffer')
bind = between(execute, '        case CMD_SET_RENDER_TARGETS:', '        case CMD_SET_VIEWPORTS:')
destroy = between(textures, 'void backend_texture_destroyed(NvnTexture *t)', '// Reboot (device.c')
source = r'''
#include <assert.h>
#include "runtime/nvn/nvn.h"
#undef NVN
#define NVN(name) void name(Cpu *c)
void backend_texture_view_format(NvnTexture *t, uint32_t fmt) { (void)t; (void)fmt; }
typedef struct { void *pending_rgba; } TexBackend;
static int invalidations;
void vk_alias_texture_destroyed(NvnTexture *t) { (void)t; invalidations++; }
void vk_exec_texture_destroyed(NvnTexture *t) { (void)t; invalidations++; }
void vk_device_texture_destroyed(NvnTexture *t) { (void)t; invalidations++; }
static void hd_forget(NvnTexture *t) { (void)t; invalidations++; }
static void live_remove(TexBackend *b) { (void)b; }
static void destroy_image(TexBackend *b) { (void)b; }
'''+destroy+r'''
typedef struct {
    int ncolor;
    NvnTexture *color[8], *depth;
    NvnTextureView cview[8], dview;
    uint8_t has_cview[8], has_dview;
} RtState;
static struct { RtState rt; bool rt_dirty; } st;
static union { max_align_t align; unsigned char bytes[2048]; } memory;
'''+snap+r'''
static CmdRec *record(Cpu *c, uint32_t op, uint32_t extra, Snap *s) {
    (void)c;
    assert(sizeof(CmdRec) + extra <= sizeof memory);
    memset(&memory, 0, sizeof memory);
    CmdRec *r = (void *)memory.bytes;
    r->op = op; r->size = sizeof(*r) + extra;
    memcpy(r->x, s->x + 1, sizeof r->x);
    return r;
}
'''+rt+copies+r'''
static void execute(CmdRec *r) {
    const void *x = r->extra;
    switch(r->op) {
'''+bind+r'''
    default: assert(0);
    }
}
int main(void) {
    NvnTexture t = {0};
    backend_texture_destroyed(&t);
    assert(invalidations == 4); // lazy backend never created: still forget bound state
    uint64_t guest = (uintptr_t)&t, colors[1] = {(uintptr_t)&guest};
    Cpu c = {0};
    nvn_texture_publish(&t);
    c.x[1]=1; c.x[2]=(uintptr_t)colors; c.x[4]=(uintptr_t)&guest;
    nvnCommandBufferSetRenderTargets(&c);
    CmdRec *r = (void *)memory.bytes;
    execute(r);
    assert(st.rt.color[0] == &t && st.rt.depth == &t);
    nvn_texture_retire(&t);
    execute(r);
    assert(!st.rt.color[0] && !st.rt.depth && st.rt_dirty);
    nvn_texture_publish(&t); // same address, different object generation
    execute(r);
    assert(!st.rt.color[0] && !st.rt.depth);
    memset(&c, 0, sizeof c);
    c.x[1]=(uintptr_t)&guest; c.x[4]=(uintptr_t)&guest;
    nvnCommandBufferCopyTextureToTexture(&c);
    NvnTexRefRec *refs = (void *)r->extra;
    assert(refs[0].lifetime_id && refs[0].lifetime_id == refs[1].lifetime_id);
    assert(nvn_texture_resolve_command(refs[0].tex, refs[0].lifetime_id, "copy") == &t);
    nvn_texture_retire(&t);
    t.backend=(void *)(uintptr_t)UINT64_MAX;
    assert(!nvn_texture_resolve_command(refs[1].tex, refs[1].lifetime_id, "copy"));
    puts("PASS: production RT/copy recording, live binding, retired/ABA targets, copy identity");
}
'''
with tempfile.TemporaryDirectory(prefix='scarlet-texture-') as tmp:
    src = Path(tmp) / 'test.c'
    exe = Path(tmp) / 'test.exe'
    src.write_text(source)
    subprocess.run([os.environ.get('CC', 'clang'), '-O2', '-Wall', '-Wextra', '-Werror',
                    '-I', str(root), str(src), str(root / 'runtime/nvn/texture_lifetime.c'),
                    '-lpthread', '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
