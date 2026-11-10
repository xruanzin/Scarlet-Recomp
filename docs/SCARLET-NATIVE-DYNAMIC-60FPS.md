# Native 60 FPS: automatic Dynamic FPS AOT selection (Scarlet 4.0.0)

The existing **60 FPS** launcher selection automatically uses the player's locally installed, validated **Fl4sh Dynamic FPS Scarlet v4.0.0 ASM** patch. This is **not** another UI mode. It uses the project's existing static recompiler integration, so the altered ARM64 instructions are translated into the generated Windows game library and the same patch is applied to private guest memory. A plain emulator-style ExeFS mods folder would not work with AOT code.

## Install once, from your own original mod ZIP

The original author is **Fl4sh (@Fl4sh9174)**. Download the original patch yourself; this repository and the release ZIP **do not distribute** the author's patch contents. Only the validated **[ASM] Final Release / 3.0.1-4.0.0.pchtxt** variant is supported, and only for Scarlet's exact 4.0.0 main build. **Do not combine it with the static 60 FPS patch or Exlaunch variant.**

From a PowerShell console, in a cloned source checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass \
  -File .\tools\scarlet\import_dfps_zip.ps1 \
  -ModZip 'D:\Downloads\pokemon_scarlet_mods.zip' \
  -RuntimeDir 'D:\Scarlet-Recomp\build\dist\Scarlet-Recomp-windows\Scarlet-Recomp'
```

Replace `-ModZip` with the location of your own ZIP. The script verifies the patch's exact SHA-256 fingerprint and extracts **only** the 3,269-byte ASM text into `<runtime>\user\mods\scarlet-dfps-v4.pchtxt`. Neither the ZIP nor game assets are modified. You can alternatively manually extract the original 4.0.0 ASM patch to that exact path.

Launch Scarlet normally and select **60 FPS**. The launcher configures this FPS **before** background AOT generation. The runtime detects the local patch during both `--prepare-aot` and `--play`, and the existing generator/guest adapters verify the full 153-entry fingerprint before use. No extra toggle or manual `SCARLET_DFPS_PCHTXT` setting is required.

- At **30 FPS**, no automatic Dynamic FPS patch is applied.
- At **60 FPS** with a valid imported patch, the native Dynamic FPS AOT variant is used. Because its game-code ID ends in `-dfpsasm`, the launcher may need to recompile the game library when switching from 30 or static 60 FPS; it must not reuse an incompatible `lasgame.dll`.
- At **60 FPS** without that local patch, the existing static 60 FPS behavior remains as a fallback, with a message in the runtime log. It may exhibit the walking/camera jitter under investigation.
- At **120/240 FPS**, the patch is not activated; those targets remain separate experimental modes.

To diagnose, look in `user\log\scarlet-game.log` for:

```text
[scarlet-fps] 60 FPS native Dynamic ASM selected automatically from user/mods
[scarlet-fps] experimental Scarlet Dynamic FPS ASM active; static frame-period patch disabled
[scarlet-dfps] applied 153 verified ASM entries to private guest memory
```

## Test gates

This integration has **not yet been built or gameplay-tested on Windows**. The mod author reports fixes for walking/running stutter on emulators, but this does **not** guarantee the camera shake is fixed in a statically recompiled Vulkan runtime. Compare (1) walking at 30 FPS; (2) walking at static 60 FPS; (3) walking with native Dynamic 60 FPS, including turning the camera while standing still, battles and cutscenes. Verify the character's eyes/eyebrows and chair animation remain correct.

Do not publish the modified ZIP as a stable 60-FPS release before testing the new AOT build, clean installation, and proper author credit. Preserve your known-good build and saves throughout testing.
