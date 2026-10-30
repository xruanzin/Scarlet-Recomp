"""Exercise production sampled-view selection on a shared feedback image, without a GPU."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'runtime/nvn/vulkan/textures.c').read_text()
selection = source[source.index('VkImageView vk_sample_view('):source.index('// 1x1 black textures')]
types = source[source.index('static VkImageViewType view_type_for('):source.index('// Format views of a')]
harness = r'''
#include <assert.h>
#include <stdio.h>
#include "runtime/nvn/vulkan/vk.h"
typedef struct { VkFormat vf; uint8_t expand_rgb, alpha_one; } VkFmt;
static VkFmt fmt_of(uint32_t f) { return (VkFmt){f == 0x38 ? VK_FORMAT_R8G8B8A8_SRGB : VK_FORMAT_R8G8B8A8_UNORM}; }
VkFormat vk_format(uint32_t f) { return fmt_of(f).vf; }
static bool vk_view_compatible(VkFormat a, VkFormat b) { return a == b; }
static struct { TexBackend *b; VkImageAspectFlags aspect; VkImageViewType type; VkComponentMapping sw; uint32_t lv, nlv, ly, nly; } got;
VkImageView vk_dummy_view(int t) { assert(!"unexpected dummy view"); return VK_NULL_HANDLE; }
VkImageView vk_image_view(TexBackend *b, VkImageViewType type, VkFormat fmt, uint32_t lv, uint32_t nlv,
                         uint32_t ly, uint32_t nly, VkComponentMapping sw, VkImageAspectFlags aspect) {
    got.b=b; got.aspect=aspect; got.type=type; got.sw=sw;
    got.lv=lv; got.nlv=nlv; got.ly=ly; got.nly=nly;
    return (VkImageView)(uintptr_t)aspect;
}
''' + types + selection + r'''
int main(void) {
    NvnTexture t={0}; t.format=0x35;
    TexBackend b={0}; b.format=VK_FORMAT_D24_UNORM_S8_UINT; b.levels=b.layers=b.samples=1;
    b.aspect=VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT; b.base_type=VK_IMAGE_VIEW_TYPE_2D;
    NvnTextureView v={0}; v.setmask=16; v.ds_mode=1;
    // Same snapshot, two descriptors: the stencil slot must not inherit the depth view.
    vk_sample_view(&t,&b,&v,true,TEXTYPE_2D);
    assert(got.b==&b && got.aspect==VK_IMAGE_ASPECT_STENCIL_BIT);
    v.ds_mode=0; vk_sample_view(&t,&b,&v,true,TEXTYPE_2D);
    assert(got.aspect==VK_IMAGE_ASPECT_DEPTH_BIT);
    t.ds_mode=1; vk_sample_view(&t,&b,&v,false,TEXTYPE_2D);
    assert(got.aspect==VK_IMAGE_ASPECT_STENCIL_BIT);
    // Explicit depth overrides the texture default, and a single-layer array is real storage.
    vk_sample_view(&t,&b,&v,true,TEXTYPE_2D_ARRAY);
    assert(got.aspect==VK_IMAGE_ASPECT_DEPTH_BIT && got.type==VK_IMAGE_VIEW_TYPE_2D_ARRAY && got.nly==1);
    b.format=VK_FORMAT_D32_SFLOAT_S8_UINT; v.ds_mode=1;
    vk_sample_view(&t,&b,&v,true,TEXTYPE_2D);
    assert(got.aspect==VK_IMAGE_ASPECT_STENCIL_BIT);
    // Color copies retain the NVN descriptor's swizzle and bounded subresource range.
    t.format=0x25; b.format=VK_FORMAT_R8G8B8A8_UNORM; b.aspect=VK_IMAGE_ASPECT_COLOR_BIT;
    b.levels=4; b.layers=3; b.base_type=VK_IMAGE_VIEW_TYPE_2D_ARRAY;
    v.setmask=8|1|2; v.swizzle[0]=4; v.swizzle[1]=3; v.swizzle[2]=2; v.swizzle[3]=1;
    v.base_level=2; v.num_levels=20; v.min_layer=1; v.num_layers=20;
    vk_sample_view(&t,&b,&v,true,TEXTYPE_2D_ARRAY);
    assert(got.sw.r==VK_COMPONENT_SWIZZLE_B && got.sw.a==VK_COMPONENT_SWIZZLE_ONE);
    assert(got.lv==2 && got.nlv==2 && got.ly==1 && got.nly==2);
    puts("feedback views: depth/stencil, overrides, D24/D32, array, swizzle and ranges passed");
}
'''
with tempfile.TemporaryDirectory(prefix='vk-feedback-') as tmp:
    src = Path(tmp) / 'test.c'
    exe = Path(tmp) / ('test.exe' if os.name == 'nt' else 'test')
    src.write_text(harness)
    subprocess.run(shlex.split(os.environ.get('CC', 'clang')) + ['-std=c11', '-I', str(root), str(src), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)

# Verify that the descriptor path actually uses this selection for each slot.
execution = (root / 'runtime/nvn/vulkan/exec.c').read_text()
assert 'vk_sample_view(e->tex, feedback_image[k], &e->view, e->has_view, st_->type)' in execution
assert 'feedback_view[' not in execution
