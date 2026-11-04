## Update after visual test — 2026-11-04

**Result: rejected as a fix for the bedroom stand-up bug.** The player
reported that setting the Y gain to 1.0 did not eliminate the problem.
More precise reproduction: after sitting at the bedroom desk, the player
stands **automatically** as part of the scripted introduction, and
the upward displacement occurs **during that stand-up transition**.
The original 30 FPS build does not exhibit the error.

Do not enable `SCARLET_DFPS_NEUTRAL_Y=1` for normal play.
The prior test does not establish that this multiplier belongs to the
player actor or that modifying it is safe. Keep the original patch.

Next engineering step: inspect the generated AOT functions around
`f_7000cce39c`, `f_700176101c` and their callers, aligning the
scripted transition against the known-good 30 FPS behavior.
A read-only source audit is implemented in
`tools/scarlet/intro_standup_aot_audit.py`, without requiring Codex.
This is diagnostic work, **not** a claim of a completed fix.

# Scarlet 4.0.0 Dynamic FPS: controlled positive-Y gain experiment

Status: **implemented, not yet gameplay-validated** (2026-11-04).

## Evidence and hypothesis

The original stable 30 FPS build ran the initial bedroom scene without
floating. The DFPS AOT experimental build at 60 FPS produced floating.
These runs used different executable/DLL builds, so the comparison does
not prove which instruction causes the difference.

The user-owned Fl4sh 4.0.0 ASM patch (153 entries, fingerprint
`0x005c31864d041832`) includes one float32 `1.95`
(`9A 99 F9 3F`) at MAIN+`0x0438F010`; the previously examined
patched vector code uses a positive-Y compensation before the vector
is stored. Whether that vector belongs to the player remains unproven.

## Surgical A/B

In `runtime/scarlet_dfps_guest.c`, only after all 153 original patch
entries and the exact main Build ID validate, the opt-in
`SCARLET_DFPS_NEUTRAL_Y=1` replaces the guest-memory float at
MAIN+`0x0438F010` with `1.0f` (`00 00 80 3F`).

- Does not alter the original .pchtxt, NSO or AOT DLL.
- Does not alter 152 other entries nor any ASM instructions.
- Does not require rebuilding `lasgame.dll` because it replaces a
  guest-memory constant read by the already-translated patched code.
- Does require compiling the runtime (`scarlet.exe`) once.
- Has an explicit opt-in, and validates the original value/address.
- Is **not scene-gated** and could affect other vertical motion.
- Must not be enabled by default until comparisons establish that it
  fixes the intro without other regressions.

`SCARLET_DFPS_NEUTRAL_Y=0` or unset: original verified patch.
`SCARLET_DFPS_NEUTRAL_Y=1`: test neutral gain. Other values fail closed.

## Building and testing on the owner's Windows machine

From PowerShell, on this branch with local Codex changes preserved:

```powershell
cd D:\Scarlet-Recomp
$env:PATH = "C:\msys64\ucrt64\bin;C:\msys64\usr\bin;$env:PATH"
& C:\msys64\usr\bin\make.exe -j4 SCARLET_AOT=1 "GEN=generated-scarlet/eb6deb908752b9c6" "B=build/scarlet-dfps-test" "build/scarlet-dfps-test/scarlet.exe"
if ($LASTEXITCODE -ne 0) { throw "runtime build failed" }

# Real game, fresh saves and logs for each condition:
powershell -NoProfile -ExecutionPolicy Bypass -File tools\scarlet\run_dfps_y_ab.ps1 -Mode neutral
powershell -NoProfile -ExecutionPolicy Bypass -File tools\scarlet\run_dfps_y_ab.ps1 -Mode original
```

The runner opens a normal visible window, uses unique
`D:\Scarlet-DFPS-Experiment\y-gain-ab-<mode>-<timestamp>\data` folders,
does not replace save files, and records stderr/stdout alongside each
temporary run. The original condition must not print the override line;
the neutral condition must print:

```text
[scarlet-dfps] intro A/B: MAIN+0x0438f010 Y gain 1.95 -> 1.0 (experimental, not scene gated)
```

Optional unit test (requires local user-owned .pchtxt):

```powershell
& C:\msys64\ucrt64\bin\gcc.exe -std=c11 -O2 -Wall -Wextra -Werror runtime\scarlet_dfps_guest.c tools\scarlet\test_dfps_y_gain.c -o build\test_dfps_y_gain.exe
& .\build\test_dfps_y_gain.exe D:\Scarlet-DFPS-Experiment\mods\scarlet-dfps-v4.pchtxt
```

## Interpreting results

- **Intro grounded with neutral, floating with original**: strong
  evidence the positive-Y gain causes the symptom. Validate other
  animations/physics before accepting as a permanent fix; instrument
  ownership/scene to scope appropriately.
- **Both float**: this particular multiplier is not sufficient.
  Restore the default; investigate call-site timing, root motion,
  initial transform and remaining patch differences.
- **Neutral introduces new artifacts**: disable the experiment and
  record logs; do not ship the change.
- **Different framerate, poor performance or failed startup**:
  collect runtime logs, verify each test actually reached the scene
  at comparable FPS, and do not infer animation behavior.

No claim of a completed gameplay fix is made before user-side
visual A/B confirmation.
