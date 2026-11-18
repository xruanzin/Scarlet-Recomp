# Scarlet 60 FPS — phase-locked pacing trial (18 Nov 2026)

**Branch:** `fix/scarlet-60fps-phase-lock-20261118`  
**Status:** unverified Windows A/B experiment, not yet part of `main` or the public ZIP.

## What was observed

Existing Scarlet logs showed repeated `[scarlet-frame] submissions_fps` and `[vk] fps` values near **58.9–59.0** with a mean frame interval around **16.9–17.0 ms**, including before the portable ZIP packaging changes.

In `runtime/scarlet_frame_time.c`, the original pacing starts each next 16.67 ms wait from the **actual late wake-up** of the previous frame. Small timing overshoots can therefore become a permanent ~59 FPS ceiling even if rendering has headroom.

## What's different

Only the requested native **60 FPS** path uses an anchored presentation deadline. A late timer wake-up no longer adds its latency to every subsequent frame. If rendering falls more than one period behind, the deadline resynchronises rather than issuing a burst of catch-up frames.

The time measurement supplied to Scarlet remains based on real elapsed time. The original pacing logic stays available via `SCARLET_PHASE_LOCK=0`; native 30 / experimental 120 / 240 FPS are unchanged.

This is **not** a GPU performance fix: dips to 54–55 FPS may persist for other reasons. Actual gameplay, camera, audio and battles must be verified. No stable FPS claims should be made until the A/B test.

## Windows test with the existing AOT

Close Scarlet, keep `build/window-full-20261112/lasgame.dll` and saves intact, then from PowerShell:

```powershell
cd "D:\Scarlet-Recomp-Window-Test"
git status --short
git fetch origin "refs/heads/fix/scarlet-60fps-phase-lock-20261118:refs/remotes/origin/fix/scarlet-60fps-phase-lock-20261118"
git switch -c fix/scarlet-60fps-phase-lock-20261118 origin/fix/scarlet-60fps-phase-lock-20261118
Remove-Item Env:SCARLET_PHASE_LOCK -ErrorAction SilentlyContinue
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_play_f1_white.ps1
```

The existing script backs up `scarlet.exe` and **rebuilds only the runtime**, preserving `lasgame.dll` and saves.

To compare the **old pacing** with the *same newly compiled exe*, close the game and launch again:

```powershell
$env:SCARLET_PHASE_LOCK = '0'
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_play_f1_white.ps1
```

Remove that environment variable to reenable the test.

## What to compare

Run the same location, camera movement and settings for each test. Note the average and dips (e.g. 55 vs 59 vs 60), plus whether the game **feels** smoother. Check `[scarlet-frame]` submissions and accepted FPS in the logs, not only the on-screen rounded counter.

If phase lock brings a stable ~59.9–60 without increased stutter, the branch can be reviewed for `main`. If performance remains lower, keep the current working release unchanged and investigate GPU frame times, frame pacing modes and settings.

Do **not** publish an updated ZIP from this experiment until it passes a full gameplay test.
