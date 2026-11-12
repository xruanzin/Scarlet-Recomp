# Scarlet 4.0.0 — F1 graphics implementation and upstream study

Experimental workstream. Do not merge into the portable release until a Windows Vulkan build and gameplay tests pass. This branch is based on `release/v1.0.0-preparation-20261101` and does not incorporate or replace the independent experimental native FPS branches or local Codex changes.

## Implemented in this branch

- The existing F1 **3D render resolution** selector now has exact 720p and 1440p internal render presets, with 1080p (1x) and 2160p (2x) still available. Saved values `resolution = 720p` or `1440p` are recognized by `settings.c` and applied by `output_scale.c`. This is **renderer internal scaling**, not an increase/decrease of the guest's UI/swapchain resolution.
- Scarlet's optional Vulkan **sun shadow map** scaling is bounded to a candidate 2048x2048 depth texture and at most 4096x4096; F1 offers original 2048 or experimental 4096. This is **not** the Tera game-code `svshadow` change, and gameplay correctness is not established. The preexisting generic LA/ZA shadow controls remain.
- The existing **dynamic internal resolution** selector (`RES_DYNAMIC`) and shadow-sharpness settings remain present. Scarlet sharpness UI is bounded to native or 2x to match the optional 4096 map size.
- Source-level regression checks: `python tools/test_scarlet_f1_graphics.py`. These cannot establish rendering correctness.

## Confirmed differences

### Tera-recomp (MIT; Scarlet 4.0.0)

Sources:
- https://github.com/tukidev-lgtm/Tera-recomp/blob/main/recomp/patches-v400.txt
- https://github.com/tukidev-lgtm/Tera-recomp/blob/main/runtime/resolution.c
- https://github.com/tukidev-lgtm/Tera-recomp/blob/main/runtime/ui/menu.cpp
- https://github.com/tukidev-lgtm/Tera-recomp/blob/main/runtime/vk_exec_draw.c

`fps60` in the patch file changes the **base fixed simulation step**, the startup present interval and the per-frame rate controller at three verified instruction sites. It is not the same as merely forcing `present_interval=1`; verify against the exact Scarlet 4.0.0 NSO before trying it, and do not combine with conflicting Dynamic FPS systems. Tera's README still describes 30 FPS gameplay in its early alpha.

Tera's true **game resolution** uses the `svres` ARM64/AOT patch set to replace constants at several guest-code sites and change render-target/UI sizing, half-size targets, render target pool allocation and HUD handling. It is not implemented in this branch; the existing Scarlet-Recomp host upscale cannot substitute for it. Its `dynamic_res=game|max` concerns the game's own resolution controller, unlike the host `RES_DYNAMIC` estimator.

Tera's **pitch-black shadow fix** is connected to stencil values read through a float texture view: integer stencil bits require an exact bit-preserving reinterpretation to float. This must be adapted to the Scarlet-Recomp Vulkan renderer with captures and device tests; it is **not** implemented by the experimental sun shadow upscale.

### Hookshot (GPLv3; different graphics architecture)

Sources:
- https://github.com/NotRexed/Hookshot/blob/main/gpu/render/rx_framegen.cpp
- https://github.com/NotRexed/Hookshot/blob/main/gpu/render/rx_present_fx.cpp
- https://github.com/NotRexed/Hookshot/blob/main/LICENSE

Hookshot's 2x (optional 3x) frame interpolation uses **WebGPU/WGSL compute optical flow** based on consecutive presented game images, quarter-size luma, block-matched motion estimates and a separate display thread. It does not modify the simulation rate. Scarlet-Recomp uses Vulkan/SPIR-V, so copying that implementation directly will not compile or function; a correctly synchronized Vulkan implementation or an appropriately licensed interoperable module is required. A future F1 toggle must remain disabled/absent until the renderer pipeline exists. Respect the GPLv3 license: do not silently copy Hookshot's GPL source into a differently licensed project.

## Required follow-on implementation

1. In an isolated AOT build, match Tera's `fps60` instruction sites against the **actual verified 4.0.0 guest main** and establish a regression baseline for sitting, walking, camera and battles. Do not merge competing timing fixes.
2. Port `svres` with build-ID/expected-opcode guards and a guest patch page for 1280x720 through 3840x2160; calculate necessary guest render target memory and UI/HUD mapping. Add F1 choices that apply at restart. Test cutscenes and menus.
3. Port the stencil bit reinterpretation fix to Vulkan. Compare captured frame/mask values on the user's NVIDIA and AMD GPUs; only then promote "pitch black shadows fixed".
4. Add optional shadow-map resolutions below 2048 and 3072 by a game-code `svshadow` path if desired; do not claim that the current Vulkan 2048/4096 mode is the same.
5. Build a Vulkan optical-flow framegen pipeline with correct image lifetime, queue ownership, frame pacing and fallback, then expose its actual on/off state in F1. Benchmark original vs generated FPS and input latency.
6. Run the full Windows build and in-game A/B validation before merging or publishing a ZIP.

## How to test these preliminary changes

Run `python tools/test_scarlet_f1_graphics.py` in the repository. Compile a **separate experimental build**, not over the known-good ZIP. In F1 choose 720p/1440p and check the 3D scene changes while HUD remains readable. Restart when changing sun shadow map to 4096. Capture `[scale]` and `[vk] shadow map` log lines; check GPU memory, flicker, shadow alignment, walking, chair scenes and scene transitions. Any visual artifact: return F1 shadow map to the game's 2048 and restart.

No claim is made of completed frame generation, fixed black shadows or true in-game output resolution in this branch.
