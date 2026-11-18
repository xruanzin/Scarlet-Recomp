# Scarlet 4.0.0 — native adaptive 60 FPS prototype

The existing **60 FPS** launcher option enables the Scarlet-Recomp host's own adaptive frame clock. It is implemented in C and runs as part of the native Windows/Vulkan runtime. **No third-party mod, .pchtxt file, additional launcher setting, or special AOT library is required.**

## What actually changed

- The runtime still validates Scarlet 4.0.0 and initializes a 60 Hz frame period.
- A native present-clock estimator samples frame presentation timing, smooths short scheduler jitter, and bounds unusually slow frames. A steady 60 FPS remains fixed at 16,666,667 ns; sustained sub-60 cadence can gradually adjust the period up to 33,333,334 ns.
- The current native prototype atomically updates the **already-validated Scarlet frame-period guest field** at `MAIN+0x03c2fbb0`. No new guest code, copyrighted game data, or third-party ASM bytes are added. The 30 FPS path is unchanged.
- The clock's pure timing estimator has standalone regression tests in `tools/test_scarlet_native_frame_clock.c`, independent of game files.
- An older user-controlled `SCARLET_DFPS_PCHTXT` experimental path is retained separately for historical A/B tests, but the native launcher does **not require, import, or activate** a mod.

## Current limitations

**This is not a port of Fl4sh's entire 153-entry ASM patch.** That patch changes multiple game timing and movement sites; our native prototype currently adjusts only the known game frame-period field. It is an independently implemented host-side timing approach, **not proof** that the character/camera shaking is fixed. No game-code or mod payload is distributed.

The game itself still needs to be tested at 60 FPS. In particular, writing the guest period from the presentation thread while the simulation reads it needs Windows runtime and concurrency validation before merging. Review whether this period is the right simulation-time source; if the camera's smoothing is calculated elsewhere, a second native hook at a validated timing consumer may be needed. Do not ship as a stable gameplay fix until then.

## Build and A/B validation

Work from an **isolated test build**, not the known-good ZIP. The source branch is `feature/scarlet-native-auto-dfps-60fps-20261110`; its PR stays draft pending testing. Maintain 60 FPS in the existing launcher. No patch installation step is needed.

Check `user/log/scarlet-game.log` for:

```text
[scarlet-fps] requested 60 FPS, period 16666667 ns
[scarlet-fps] native adaptive frame clock selected (experimental, no external patch)
[scarlet-fps] native 60 FPS adaptive frame-period update enabled (A/B experimental)
```

On the same saved game and graphics settings compare:
1. 30 FPS walking, camera still; 30 FPS standing, rotating camera
2. Known-good static 60 FPS walking and camera rotation
3. Native adaptive 60 FPS (test build) walking and camera rotation

Record actual FPS/frametime; watch for unnatural character motion, battles, animation speed, textures/eyebrows, chair animation, flicker and pauses. If symptoms worsen, revert to the known-good ZIP. Passing isolated unit tests is **not** validation of frame pacing, animation physics or graphics in the game.

## License and credits

The external Dynamic FPS mod ZIP was examined as a behavioral reference, but none of its ASM payload was included in Scarlet-Recomp's code or public assets. Credit to Fl4sh for the separate community Dynamic FPS work; the native estimator is an independent implementation and does not claim to reproduce the entire mod.
