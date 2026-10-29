# Scarlet 4.0.0 graphics: resource detail / vertex / shader investigation

Branch: fix/scarlet-visual-sampling-20261029
Based on origin/scarlet/bootstrap-4.0.0-20261029 at d936550.
IMPORTANT: The Windows user's local commit 5468714 (setjmp/longjmp fix)
was NOT pushed to the upstream branch. This graphics branch is intentionally
separate. Merge/cherry-pick onto that local commit; do not reset local Git.

## Grounded evidence (2026-10-29)

- With LARECOMP_VK_XFB_MIRROR=0 the log ran to frame 10022 at
  ~30 FPS and ended "window closed", not FATAL. Screenshots still show
  jagged stripes on the player, nearby ground, walls and NPCs.
- The user saw less corruption at distance, more as they approached.
  That is consistent with near LOD assets and base mip usage, but
  does not by itself prove which component is defective.
- With LARECOMP_NO_SHADOW=1 stripes remained. EQUAL_TOL also failed.
- The xfb-mirror-test log selected bilinear, 2x internal resolution,
  SMAA, and switched the runtime high texture filtering on/off via F1.
  Graphics quality varied between tests. All A/B comparisons must
  use identical F1 settings, camera position, lighting and scene.
- LARECOMP_VK_COPY_VERTICES=1 and LARECOMP_LOD_MIN=2 are existing
  diagnostic options, not fixes to turn on permanently.

## Reviewed and changed code — runtime only

1. runtime/nvn/vulkan/exec.c guest_direct(kind,...): a windowed
   import shortcut could read INDEX buffers from the XFB mirror,
   even though its usage lacks INDEX_BUFFER and it can contain stale
   index data. Changed shortcut to kind == 0 (vertex) only.
   No change to AOT and no forced copies in the normal path.
   Explicit LARECOMP_VK_XFB_MIRROR=0/1 is now logged.
2. runtime/nvn/maxwell/translate.c: the per-shader disk cache key
   omitted the LARECOMP_VK_EXACT_H2F setting, despite this setting
   generating different GLSL in fragment/compute stages. Include
   the toggle in the cache hash: A/B with and without exact half
   conversion can now coexist, without deleting the old cache.
3. runtime/nvn/vulkan/textures.c: when LARECOMP_LOD_MIN overrides
   a sampler's minLod, also clamp maxLod to minLod if necessary,
   avoiding an invalid min > max LOD interval. The override is an
   A/B aid to test near/base mip data; it stays off by default.
4. runtime/nvn/vulkan/exec.c LARECOMP_VK_VERTEX_AUDIT=1 logs up to
   80 vertex layouts with unsupported RGB3-to-RGBA4 fallback or
   attributes extending beyond an input stream's stride. The audit
   does not silently repack guest data: that needs correct GPU/CPU
   handling and a proven bad layout, and may require more code.

These fixes target concrete defects and give a reliable diagnosis.
**No claim that they remove all stripes**: that must be tested
visually on the user's RTX 5060. A good frame counter doesn't prove
correct rendering. Do not ship the early TLS allocator probe as a
production memory allocator; its lifecycle/free semantics are incomplete.

## Safely integrate with the *local* unpushed setjmp fix

On Windows PowerShell, with the normal local scarlet bootstrap branch:

    cd D:\Scarlet-Recomp
    git status --short
    git branch --show-current
    git fetch origin fix/scarlet-visual-sampling-20261029
    git cherry-pick d936550..origin/fix/scarlet-visual-sampling-20261029

Stop if tracked modifications exist and have not been safely
committed/stashed by their owner. The untracked scarlet-boot-test/
directory must stay untouched. Cherry-pick does not remove the
existing local commit 5468714. In case of conflict, resolve
rather than using git reset --hard.

Build ONLY the native runtime executable (use UCRT64 environment
already installed; no make all, no gen-scarlet, no clean):

    $env:MSYSTEM = 'UCRT64'
    $env:PATH = 'C:\msys64\ucrt64\bin;C:\msys64\usr\bin;' + $env:PATH
    make -j2 GEN=generated-scarlet/eb6deb908752b9c6 B=build/scarlet/eb6deb908752b9c6 GENOPT=-O1 GENARCH=-march=x86-64-v3 SCARLET_AOT=1 build/scarlet/eb6deb908752b9c6/scarlet.exe

Do not rebuild lasgame.dll or any generated-scarlet/ object.
Compare the DLL hash against the baseline when checking preservation.

## Comparable visual A/B cases — no rebuild between cases

At F1 choose 1x resolution and the same fixed anti-aliasing
and texture filtering each time. The launcher clears previously
set diagnostic flags INSIDE ITS OWN child PowerShell process,
so the parent terminal's environment is not polluted. To run:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_ab.ps1 -Mode baseline
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_ab.ps1 -Mode mip2
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_ab.ps1 -Mode half-exact
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_ab.ps1 -Mode vertex-copy
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_ab.ps1 -Mode vertex-audit

Use one case per run. Screenshot the SAME nearby wall/character
and distant object. Keep the window running to the scene and
close normally. Logs stay in scarlet-boot-test/graphics*.stderr.log.
If mip2 removes stripes but makes textures blurry, investigate
base-level texture swizzle/decode/row pitches and missing mip
uploads, NOT a permanent LOD clamp. If half-exact fixes the issue,
focus on shader translation / precisions (and measure performance).
If vertex-copy changes geometry, trace host-import/coherency and
XFB-written stream reads. If vertex-audit shows UNSAFE_FALLBACK
or OUTSIDE_STRIDE for a near mesh, implement a real per-format
repack/vertex-fetch path: never simply fetch four components from
a three-component source. Retain all results without deleting
the GLSL or pipeline cache.

F9 framebuffer/pass capture and F10 screenshot (when supported
by this build) can identify the first bad draw if tests are
inconclusive. Background shader compile hitches must be compared
separately from steady-state frame times.

## Verification limitations

The GitHub changes were inspected at source level and committed
to an isolated branch. This environment does not have access to
the Windows checkout, RTX 5060, or prebuilt AOT DLL. Runtime
compilation and gameplay visual validation on Windows remain
required; until then the code changes should be considered
unverified in the game's renderer.
