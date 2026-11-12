# Scarlet 4.0.0: window sizing and FSR 3.1 Vulkan audit (experimental)

## Window fix implemented

The Scarlet AOT runtime started at `1280x720` in `runtime/nvn/vulkan/device.c` regardless of the chosen 3D render resolution. The window and renderer image size are separate concerns.

This branch defaults Scarlet to **1920x1080 physical window pixels**, offers F1 > **Window size / Tamanho da janela** (720p, 900p, 1080p, 1440p, 4K) and writes `window_size = WIDTHxHEIGHT` to `larecomp.ini`. It uses `SDL_GetWindowPixelDensity` to translate physical pixels into SDL logical window coordinates, clamps to usable display bounds to avoid pushing the title bar off-screen, then synchronizes and logs `[window] actual drawable`. In fullscreen, the display chooses the actual size. Existing `LARECOMP_WINDOW=...` test overrides remain authoritative; the resize still occurs on SDL's main thread and feeds the existing Vulkan swapchain recreation path.

**A 1366×768 or other small display cannot physically fit a decorated 1920×1080 window.** This branch deliberately fits that window while keeping its 1080p *3D renderer* mode separate. It does not change the physical monitor resolution.

Run source checks: `python tools/test_scarlet_window_size.py`.
**Not yet verified**: Windows compilation, multi-monitor DPI behavior, fullscreen/window transitions, actual UI test on 1080p and smaller monitors, guest launch. Do not merge without these tests.

## FSR 3.1 / FidelityFX API: verified implementation gaps

Reference upstream:
- https://github.com/Revivedx/SavageWindRecomp/blob/main/runtime/nvn/vulkan/framegen.cpp (FidelityFX SDK 1.1.4, *direct contexts*, not the official Vulkan frame interpolation swapchain)
- https://github.com/Revivedx/SavageWindRecomp/blob/main/runtime/nvn/vulkan/fsr3.cpp (FSR 3.1 upscaler using its vendored SDK)
- https://github.com/Revivedx/SavageWindRecomp/blob/main/docs/SAVAGE-WIND.md#frame-generation-amd-fsr-3
- https://gpuopen.com/manuals/fsr_sdk/techniques/frame-interpolation-swap-chain/ (AMD official FSR Vulkan swapchain)
- https://gpuopen.com/manuals/fidelityfx_sdk/getting-started/migrating-to-fsr-3-1/ (ffx-api API migration)
- https://gpuopen.com/amd-fsr-sdk/ (current official SDK loader and redistribution requirements)

The SavageWindRecomp feature uses Vulkan GPU optical flow, motion reconstruction from a BotW-specific camera uniform, a scene depth texture, a HUD-less snapshot and FSR frame interpolation SDK contexts. Its *own present thread* shows the interpolated and real image in order. It explicitly does NOT use the official `ffx-api` frame interpolation swapchain. The BotW camera uniform offsets, hero position and scene composite signatures are game-specific; directly copying them into Scarlet would not yield correct motion vectors, image history or HUD masking.

### Scarlet renderer audit

1. `Makefile` currently compiles `runtime/nvn/vulkan/*.c` and `*.cpp`, links the existing vendored FSR 2 backend from `third_party/fsr2`; no FidelityFX `ffx-api` or FSR 3 SDK libraries are linked.
2. `runtime/nvn/vulkan/device.c:create_device` **normally requests only 1 queue**. This branch adds a developer-only `SCARLET_FSR3_PREPARE=1` opt-in: if at least 3 queues are available in the graphics/present family, it creates separate `g_fsr3_present_queue` and `g_fsr3_acquire_queue` handles. It never submits on them yet. Actual FFX swapchain queue ownership, barriers, queue-family transfer and synchronization remain unimplemented. The old `vkCreateSwapchainKHR`, `vkAcquireNextImageKHR`, `rec_QueuePresentKHR` paths still own presentation.
3. `create_swapchain` may use SDR 8-bit UNORM or HDR10/scRGB. FI needs to handle these formats and recreate its context on size, HDR and present-mode changes while respecting `rec_drain` / `vkDeviceWaitIdle` and g_vk image/view lifetimes.
4. `backend_present_now` currently composites the game's **already HUD-inclusive** `NvnTexture` into the window, then draws ImGui F1 and HUD overlays on the same swapchain image. Delaying only ImGui cannot remove the game's HUD from the interpolation inputs. Identify the *pre-HUD game scene* separately, and provide that plus UI into the SDK's UI-composition callback or compose after generated frames.
5. FSR 2 depth/motion input extraction in `exec.c` is conditioned on the Z-A frame hook. It does **not** establish Scarlet 4.0.0's scene depth, near/far, projection matrices, per-object motion or jitter handling. Motion reconstructed **only** from camera view/projection captures static geometry motion but cannot represent moving characters, foliage or particles; optical flow must supplement it, and disocclusion/reset cases need testing.
6. The AMD Vulkan FI swapchain needs `VK_FORMAT_R16G16B16A16_UNORM` storage-image capabilities; this branch logs that and available graphics queues at initialization using `[fsr3] preflight`. These logs **do not activate FSR 3 or change device queues**.
7. The **current** AMD FSR SDK distributes signed loader/effect DLLs on Windows (`amd_fidelityfx_loader_vk.dll`, related effects). Do not silently copy legacy SavageWind SDK files or substitute an outdated provider for the requested official `ffx-api` integration without confirming the version/API and redistribution instructions.

### Acceptance criteria before exposing F1 > AMD FSR 3.1

- Introduce a pinned official AMD SDK dependency and Vulkan link/load integration. Feature-test on Windows, prove runtime loading and explicit error handling; retain working FSR1/FSR2 fallback.
- Reserve compatible present/acquire queues at Vulkan device creation, create the official FI swapchain context, replace acquire/present function pointers, pass the exact game/async/present/acquire queue handles, implement context destroy/recreate on resize, HDR or VSync transitions.
- Find Scarlet's authoritative world-camera matrices and scene depth with capture logs; render reprojected motion textures and, where possible, true per-object vectors; validate direction, scaling, jitter cancellation, reset and near/far depth.
- Add scene/overlay segregation for **both the game's own HUD and ImGui**; provide the UI composition callback or present pass after interpolation and test minimap, text, pause and F1.
- Dispatch FSR 3.1 **upscaling** and **frame generation** with proper color, depth, motion, reactive and jitter inputs and compatible UAV formats. Decouple generated FPS from simulated FPS. Handle menus/loading, camera cuts, frame pacing and real/presented rate overlays separately.
- Enable F1 controls **only when the above is implemented and SDK capabilities pass**. Never present an inert checkbox as working FSR 3.1.
- Test 30/60 game frames with/without FG, frame pacing, HDR, 720p/1080p/4K resize, suspend/minimize/recover, battle, chairs and walking; check validation layers, VRAM and crashes on the user's GPU.

### Explicit current state

**Completed**: independent 1080p window default + F1 physical window size settings, runtime capability logging and developer-opt-in reservation of 2 additional Vulkan queues for later FSR work.
**Not completed**: FSR 3.1 SDK dependencies, game-side motion input, FI swapchain replacement, upscaler, frame generation and F1 FSR on/off controls.

This branch preserves the original swapchain and FPS timing, so there is no claim that it provides generated frames.
