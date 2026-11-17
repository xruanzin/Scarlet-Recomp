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

The new `interior-camera-bindings.json` **resolves the first static link**:
root PCs 427257–427261 load namespace `CD9AE7C27B00EB066`,
member `SF667EA15F51B1676`, create `CLOSURE 0.30688` and
`SETTABLE`. Thus the registered interpolator and the method looked up
at `0.17567:31–37` are statically associated. The same member is also
read by prototype `0.18722` (at PC 351–352), so the interpolator is
**not proven exclusive** to this controller.

**Still unverified:** whether `0.17567` is invoked for the indoor camera
during gameplay, which arguments represent camera-only state, and the
original real-time smoothing coefficient. There is no safe basis yet for
changing `0.30688` globally or replacing the scheduler's `1/30`
step. In particular `0.30688` skips interpolation for a zero count;
changing alpha alone does not make it update every 60-FPS frame.

`tools/scarlet/verify_interior_camera_binding.py` checks these exact
registration and call-site relationships, including their Lua registers,
from the exported JSON. It verifies static code linkage, not camera
behavior or game runtime execution.

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

## 2026-11-17 — 60-FPS live report and proven diagonal input defect

Manual gameplay with 60 FPS enabled reports **three separate symptoms**:
interior-camera shake, faster-than-cardinal diagonal running, and some
interior animations finishing too early. The manual runtime log shows
`[scarlet-fps] requested 60 FPS, period 16666667 ns`, with near-steady
~59 FPS accepted presents and `clock1_supplied_ns` near 1:1 wall time.
This is **not** evidence that all gameplay or animation clock domains are
correct. No automatic gameplay-speed correction has been verified.

Review of `runtime/hle/input.c` found a concrete host-input bug:
`recompute_keyboard()` independently sets each WASD left-stick axis to
±32767. Diagonals had magnitude `sqrt(32767² + 32767²)`, approximately
141% of the unit circle, and the assembled Npad state did not bound the
left-stick vector. The d-pad movement path already normalized diagonals,
but normal WASD keyboard input did not.

Added `runtime/hle/scarlet_stick_normalize.h` and a Scarlet-only
normalization in `runtime/hle/input.c`, after combining keyboard,
gamepad and scripted inputs but before recording/output to Npad state.
The helper preserves cardinal and all in-circle analog inputs. It clamps
only out-of-circle vectors to radius 32767. This is **not** an adjustment
to animation playback, global game speed or the camera.

- Default in the Scarlet AOT build: enabled.
- To compare old behavior at runtime: set
  `SCARLET_NORMALIZE_LSTICK=0` before launching; no recompile is
  required to toggle once the patched EXE has been built.
- `tools/scarlet/test_left_stick_normalization.c` covers cardinal,
  diagonal, signs, analog inputs, borderline values and zero.
- A standalone Linux C compile and execution of the same helper/test
  cases passed; **Windows Scarlet game integration has not yet been
  tested**.

Only the runtime EXE must be rebuilt; do not regenerate game code or
overwrite an unrelated `lasgame.dll`. In the user's Windows MSYS2
UCRT64 terminal, from the repository root:

```sh
make -j4 SCARLET_AOT=1 B=build/window-full-20261112 build/window-full-20261112/scarlet.exe
```

Keep a backup of `build/window-full-20261112/scarlet.exe` before linking.
For validation, check `[scarlet-input] circular left-stick limit enabled`
and run gameplay with `SCARLET_TARGET_FPS=60`, then compare straight
and diagonal movement at an identical speed mode. A visual improvement
in diagonal movement alone does **not** solve or validate the camera and
premature-animation reports.

The A/B test wrapper additionally had an instrumentation bug:
`SCARLET_POSITION_TRACE` requires `first:last`, but the script passed
`first,last`. That delimiter is corrected; its earlier runs therefore
did not collect this optional bounded position trace. The legacy 30-FPS
test timing out after 85 seconds is not a game crash, because the probe
intentionally stops still-running sessions.

For the remaining issues, check per-scene animation tick counts and
controller-specific camera updates at the presentation and simulation
boundaries. Do not apply the uploaded dynamic-FPS ASM or all Lua 1/30
replacements to the AOT binary without a verified, native equivalent.

## Controller-specific argument mapping

The supplied Lua prototype dump gives a more specific opportunity than
changing the shared interpolation helper:

`0.17567:31–37` calls the verified `0.30688` method with:

1. `self[42]` as the current three-component position.
2. A locally computed three-component target vector.
3. `self[41]` as the smoothing blend coefficient.
4. The controller method's second parameter as the integer step count.

If that count is zero, `0.30688` does not blend any position. At 60 FPS,
a scheduler that only advances once per 30-Hz tick **could** cause repeated
camera positions followed by a jump. This remains a hypothesis; no timed
indoor view-matrix sequence has yet demonstrated it.

The separate `1/30` function `0.17747` is registered in a *different
hashed class*, `C51C789C764D66E76`. The present files do not prove that
its step count is the argument supplied to `0.17567`. A direct linkage
must be traced instead of assuming these two schedulers are the same.

`tools/scarlet/trace_interior_camera_state.py` performs read-only Lua
dataflow checks of these four arguments and searches class methods for
writes to `self[41]` or `self[42]`. Its results can narrow the
controller-only modification point, avoiding changes to the shared
`0.30688` helper. No active camera patch is added in this stage.

```powershell
& .\.venv-scarlet-aot-fixed\Scripts\python.exe tools/scarlet/trace_interior_camera_state.py build/scarlet-script-analysis/21977-be21e65463b9a98f.blua > build/scarlet-script-analysis/interior-camera-state.json
```

## DelayFactor initialization and actual scheduler candidate (2026-11-17)

The user's `interior-camera-state.json` resolves the controller's local
interpolation inputs more precisely:

- `0.17566` initializes `self[41]` using the configuration key
  `DelayFactor`, read via the object's accessor. This is a smoothing
  **coefficient**, not a clock interval. Its actual runtime value and range
  have not been measured.
- `0.17567` passes `self[42]`, a computed target vector,
  `self[41]` and its own third parameter to the previously verified
  shared interpolator. It writes a new `self[42]` vector after
  interpolation.
- `0.17518` explicitly calls the `FC0150FC2959FFA71` method
  (the root-registered `0.17567`) with its own method argument plus
  `self[22]` at PCs 32–35. Its bytecode contains a distinct
  `1/30` constant at `0x7efc05`, consistent with a per-controller
  scheduler. The registration/class membership of `0.17518` still
  needs an identity-checked read of the private Lua chunk.
- The previously studied `0.17747` is **not** thereby established as
  the scheduler for this camera. It belongs to another class. Avoid
  changing it as a shortcut.

This sharpens the hypothesis: if `0.17518` supplies alternating
0/1 step counts to `0.17567` at ~60 FPS, the interpolator skips
the zero-count frames. A controller-specific solution would require
a timed camera interpolation every presented frame, with
`alpha(dt) = 1-(1-alpha30)^(30*dt)` and correct treatment of
the camera's target and update ordering. Merely multiplying the
smoothing coefficient by 0.5 or changing only the 1/30 constant
would not preserve the original behavior.

The new read-only tool `tools/scarlet/trace_interior_camera_scheduler.py`
validates the Lua call instruction sequence, 30-Hz constant and root
method registrations, then prints the scheduler class identity and the
field references for `self[21]`/`self[22]`. No gameplay patch or
copyrighted scripts are committed.

```powershell
& .\.venv-scarlet-aot-fixed\Scripts\python.exe tools/scarlet/trace_interior_camera_scheduler.py build/scarlet-script-analysis/21977-be21e65463b9a98f.blua
```

## Verified scheduler registration and the next real-game test

The user ran the identity-checked read-only scheduler inspection on the
original decoded Scarlet 4.0.0 `main.blua`. All five synthetic scheduler
guard tests passed. The real script inspection reported:

| Prototype | Registered class | Function |
| --- | --- | --- |
| `0.17518` | `CEAB931B40E0610B8` | `F20A40E2F8B95D5F6` |
| `0.17566` | `CD00CF28AF6D6C9ED` | `F22C7B81A049FA20D` |
| `0.17567` | `CD00CF28AF6D6C9ED` | `FC0150FC2959FFA71` |

`0.17518` accumulates frame time in `self[21]`, stores the
integer number of elapsed 30-Hz steps in `self[22]` and
dispatches `self:FC0150FC2959FFA71(dt, self[22])`. The lookup of the
method `FC0150FC2959FFA71` can dynamically resolve to the camera
controller's `0.17567`, **but the different class registrations mean
that the base/derived instance relationship and the actual in-game
receiver are not established by the static test alone**.

The next requirement is a **real interior scene** to confirm 60-FPS
hold/jump behavior, not a further broad Lua constant search. A new
PowerShell wrapper `tools/scarlet/run_interior_camera_ab.ps1` is available
for an opt-in A/B test, using the existing native launcher. It:

1. Requires an existing local copy of a save positioned **inside a house**
   in a directory containing `save/`; it will not continue on a missing
   or empty save.
2. Runs 30 FPS and 60 FPS sequentially from **separate copies** of the
   same source save, using the previously built native binary and
   identical nominal movement duration.
3. Captures 16 consecutive screenshots per run, beginning at game frame
   1200 for 30 FPS or 2400 for 60 FPS, and records the exact output
   folders in a comparison manifest under ignored `build/`.
4. Refuses to run outside this experimental work branch, on a dirty
   source tree, or while `scarlet.exe` is running. It does not edit
   source saves or upload game content.

Example, once an **interior** test save exists:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/scarlet/run_interior_camera_ab.ps1 -SaveSource "D:\Path\To\PrivateInteriorSaveDirectory" -Seconds 85
```

This wrapper has been reviewed statically but **not run against Scarlet
in this environment**. Game screenshots, output folders and the
measured camera trajectory are needed to validate or reject the jitter
hypothesis. It is not an FPS patch. Do not publish saves, ROMs,
keys, copyrighted Lua scripts or userdata; share only requested
diagnostic summaries/screenshots after checking for personal data.

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
