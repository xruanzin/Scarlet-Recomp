# Scarlet 4.0.0 — interior camera timing (experimental)

**Status: not connected to gameplay; indoor jitter is not yet fixed.**

This work branch starts from
`checkpoint/codex-native-fps-20261117-090601` (commit `729e094`).
The checkpoint contains the native clock-1 supply, AOT observations, private
diagnostics, and removal of the old Dynamic FPS ASM. It does not contain a
proven fix for the indoor camera.

## Evidence available

- The November 17 diagnostic linked an interior scene descriptor to
  `InteriorCameraBehavior.hx`; this identifies a likely camera controller,
  not the runtime call site of every interpolator.
- The original private Scarlet 4.0.0 `main.blua` SHA-256 is
  `c1a4f4e2625912cf0b739a642a79ba3357df0557a544b92da22a6cb139de2815`.
- Lua prototype `0.30688` (four parameters) contains a repeated
  three-component interpolation using the loop count. Prototype `0.17747`
  contains a `1/30` constant; the available evidence does **not** establish
  that changing it is safe or isolates the indoor camera.
- Exterior motion samples were about 6.184 units/s at 30 FPS and 6.119
  units/s at 60 FPS. These are evidence for exterior movement **only**,
  not camera jitter, battle timing or animation completion.

The raw `main.blua`, ROMFS, saves and game keys remain **private and
uncommitted**; the repo contains no copyrighted game code or data.

## Detailed Lua dump supplied on 2026-11-17

The full text dump of prototypes `0.17567`, `0.17747`, and `0.30688`
confirms:

- `0.17567`, at PCs 31-37, reads global `CD9AE7C27B00EB066`,
  looks up member `SF667EA15F51B1676`, and calls it with four input
  arguments. This routine also reads `SUB_STICK` input. **The target
  function identity and exclusive interior-camera ownership have not yet
  been proven** from the dump alone.
- `0.30688` has four parameters. It repeats a three-component lerp:
  `current[i] += (target[i] - current[i]) * alpha`, with an integer
  iteration count. When the count is zero it does not interpolate.
- `0.17747` accumulates its delta time in object field 23, compares
  to `1/30`, counts due steps and subtracts `1/30` per step. It passes
  that step count to a downstream method; changing this global scheduler
  could affect other gameplay components.

The remaining static link is whether `0.30688` is the function registered
as `CD9AE7C27B00EB066.SF667EA15F51B1676`, and whether the call at
`0.17567:37` is actually used by `InteriorCameraBehavior.hx`.

The new read-only `trace_interior_camera_bindings.py` prints the root
`CLOSURE` registration windows and relevant hashed-member uses to
investigate that link. Run it against the user's **private** decoded Lua:

```powershell
& .\.venv-scarlet-aot-fixed\Scripts\python.exe tools/scarlet/trace_interior_camera_bindings.py build/scarlet-script-analysis/21977-be21e65463b9a98f.blua > build/scarlet-script-analysis/interior-camera-bindings.json
```

The output contains only structural evidence; it does not enable a camera
hook or confirm that gameplay jitter has been fixed.

## Time-consistent interpolation implementation

The reference implementation in
`tools/scarlet/interior_camera_timing.py` derives a blend for a duration
`dt` from the original 30-Hz per-step blend `alpha30`:

```text
alpha(dt) = 1 - (1 - alpha30) ^ (30 * dt)
camera = camera + (target - camera) * alpha(dt)
```

At 30 Hz (`dt=1/30`) it is exactly the original one-step blend. At
60 Hz (`dt=1/60`) two steps yield the same result as one 30-Hz step
for a **fixed target**. Variable frame durations combine consistently.
This fixes a mathematical model of the hold/jump problem, **not the actual
interior runtime**: the real `alpha30`, update ordering, count consumers
and camera ownership must be recovered before connecting a hook.

This conversion is *not* equivalent to changing every `1/30` to `1/60`,
nor to forcing integer fixed-step counts from 0 to 1. Either could change
game speed or break other systems.

## Tests runnable without Codex

From the repo root in PowerShell:

```powershell
& .venv-scarlet-aot-fixed/Scripts/python.exe tools/scarlet/test_interior_camera_timing.py
```

The five deterministic tests cover 30-Hz equivalence, two 60-Hz substeps,
equal wall time, variable delta, and invalid input. They do **not** execute
Scarlet's gameplay.

To inspect the previously decoded private Lua file *without modifying it*:

```powershell
& .venv-scarlet-aot-fixed/Scripts/python.exe tools/scarlet/inspect_interior_camera.py build/scarlet-script-analysis/21977-be21e65463b9a98f.blua
```

It checks the exact decoded SHA-256 and recorded bytecode structure. If
the input differs, it stops instead of guessing offsets.

## Integration criteria before a native camera fix

1. Reproduce interior jitter with a **private save starting inside a house**
   (the existing world-open save does not prove an indoor failure).
2. Trace the camera controller's active Lua call path and its effective
   per-frame alpha/count, camera target, and post-update view transform.
   Distinguish this from player position and the Havok AI clock path.
3. Confirm the correct original `alpha30` and whether other subsystems use
   the interpolation helper. Use a *controller-specific* hook, with exact
   Scarlet build/script identity guards and a safe fallback.
4. In that proven path, supply the frame-rate-independent alpha above while
   retaining the 30-FPS behavior. Do not ship a blanket Lua constant patch or
   external `.pchtxt` dependency.
5. Rebuild, compare indoor camera trajectories at 30/60 with identical
   input and time, and check for shake, speedup, teleports and regressions
   outside and in battle. Keep the earlier backup intact.

**Known limitation:** this work branch only contains the mathematical
correction, its tests, an identity-checked inspector, and an unrelated
fix to the duplicated `--game scarlet` generator argument. There is no
active camera hook yet, so installing this branch **will not remove the
house jitter by itself**.
