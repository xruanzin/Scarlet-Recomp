"""Production present watchdog with simulated WSI: no GPU or real performance claim."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ap = argparse.ArgumentParser()
ap.add_argument('--ref', help='Older Git revision, for reproducing the regression')
args = ap.parse_args()
root = Path(__file__).resolve().parents[1]
path = 'runtime/nvn/vulkan/device.c'
s = (subprocess.check_output(['git', 'show', f'{args.ref}:{path}'], cwd=root, text=True)
     if args.ref else (root/path).read_text())
fn = s[s.index('void vk_present_watch(uint64_t id) {'):s.index('// The window thread (ui_run)')]
recover = s[s.index('    bool unseen = atomic_exchange('):s.index('    cur_frame.ok = false;', s.index('    bool unseen = atomic_exchange('))] if '    bool unseen = ' in s else '''
    if (atomic_exchange(&g_present_unseen, false)) present_recover(g_present_unseen_why);
    if (atomic_exchange(&g_screen_stale, false)) present_recover("screen");
'''
source = r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdatomic.h>
#include <vulkan/vulkan.h>
#define ENV getenv
#define LOG(...) fprintf(stderr, __VA_ARGS__)
typedef uint64_t SDL_WindowFlags;
enum {SDL_WINDOW_MINIMIZED=1, SDL_WINDOW_HIDDEN=2, SDL_WINDOW_INPUT_FOCUS=4, SDL_WINDOW_OCCLUDED=8};
static struct { VkDevice dev; VkSwapchainKHR swapchain; } g_vk;
static void *window;
static uint64_t now, g_present_generation;
static SDL_WindowFlags flags=SDL_WINDOW_INPUT_FOCUS;
static _Atomic bool g_present_unseen, g_screen_stale;
static char g_present_unseen_why[96];
static uint64_t SDL_GetTicksNS(void) { return now; }
static SDL_WindowFlags SDL_GetWindowFlags(void *w) { (void)w; return flags; }
static int queries, recoveries;
static VkResult result=VK_TIMEOUT;
static VkResult wait_present(VkDevice d, VkSwapchainKHR s, uint64_t id, uint64_t timeout) {
    (void)d; (void)s; (void)id; assert(!timeout); queries++; return result;
}
static PFN_vkWaitForPresentKHR g_present_wait=wait_present;
static void present_recover(const char *why) { (void)why; recoveries++; }
'''+fn+r'''
static void check_recovery(void) {
'''+recover+r'''
}
int main(void) {
    g_present_generation=1; vk_present_watch(10); assert(!queries);
    now=4000000000ull; g_present_generation=2; vk_present_watch(20);
    (void)g_present_generation;
    assert(!queries && !g_present_unseen); // old ID must not be queried on new chain
    flags=0; now+=4000000000ull; vk_present_watch(21);
    flags=SDL_WINDOW_INPUT_FOCUS; vk_present_watch(22);
    assert(!queries && !g_present_unseen); // returning focus starts a new timed probe
    now+=2999999999ull; vk_present_watch(23); assert(!g_present_unseen);
    now+=1; vk_present_watch(24); assert(g_present_unseen); // real stall still recovers
    g_screen_stale=true; check_recovery();
    assert(recoveries==1 && !g_screen_stale && !g_present_unseen);
    vk_present_watch(25); result=VK_SUCCESS; vk_present_watch(26);
    assert(!g_present_unseen);
    flags=SDL_WINDOW_MINIMIZED; vk_present_watch(27);
    puts("PASS: new swapchain, focus loss, true timeout, successful present, one recovery for two reports");
}
'''
with tempfile.TemporaryDirectory(prefix='scarlet-present-') as td:
    src=Path(td)/'test.c'; exe=Path(td)/'test.exe'
    src.write_text(source)
    subprocess.run([os.environ.get('CC','clang'), '-O2', '-Wall', '-Wextra', '-Werror',
                    str(src), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
