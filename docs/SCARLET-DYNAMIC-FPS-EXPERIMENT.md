# Scarlet 4.0.0 — experimental Dynamic FPS ASM adapter

**Not part of Scarlet-Recomp v1.0.0. This is not gameplay-validated.**

This branch adds an opt-in adapter for the **user-supplied, original**
**[Dynamic FPS Scarlet v4.0.0][ASM] Final Release** mod by Fl4sh.
The user must own/provide that .pchtxt. Neither the patch payload nor any
Nintendo game code, NSP/XCI, keys or derived DLL is committed or released.

## Why an adapter rather than dropping .pchtxt into a mods folder?

Scarlet-Recomp statically translates the AArch64 NSO into native C, then
compiles it into lasgame.dll. Patching only the loaded guest instruction bytes
cannot change already-compiled C. In the experimental mode:

1. lasgen loads the player's unmodified Scarlet 4.0.0 main NSO into memory.
2. It checks the exact full main Build ID and a reviewed **153-entry** patch
   fingerprint, then applies the patch **to the in-memory NSO image**.
3. Instruction discovery and code generation use the modified image.
4. On game start, the host repeats the validated patch into private guest
   memory, before relocations and guest init.
5. Patched and original lasgame.dll have different IDs; caches also track the
   supplied patch file, so they cannot be silently mixed.
6. Scarlet's older static 16.67-ms constant patch is disabled in DFPS mode.

No original ExeFS file is overwritten. Other FPS patches must NOT be combined
with the dynamic one. **Only 60 FPS** is admitted in this experiment.

## Work on a separate copy

Finish the baseline 30-FPS installation test first. Use a **separate test folder**
for the experimental runtime, game files and saves. Do not overwrite your
known-working ZIP or game directory.

Fetch and check out the experimental branch from a clean working tree:

    git fetch origin
    git switch experimental/scarlet-dynamic-fps-4.0.0-20261103

If Git refuses to switch due to local changes, preserve those changes first;
do not reset or clean the working tree.

Extract the file **without modifying it** from the player's own mod ZIP:

    [Dynamic FPS Scarlet v4.0.0][ASM] Final Release/
      exefs/3.0.1-4.0.0.pchtxt

Save it in a private path, for example
D:\Scarlet-Test\mods\scarlet-dfps-v4.pchtxt.
The file must have the exact reviewed payload; unrelated mods and the
Exlaunch subsdk3 are not accepted.

Validate the original ZIP:

    py -3.13 tools\scarlet\test_dfps_patch.py "D:\Downloads\pokemon_scarlet_mods.zip"

Validate the extracted patch:

    py -3.13 tools\scarlet\dfps_patch.py "D:\Scarlet-Test\mods\scarlet-dfps-v4.pchtxt"

The tests check syntax, Build ID, patch count, content fingerprint and an
in-memory synthetic NSO. No Nintendo game data is used by the tests.

## Build the experimental executables on Windows

After switching to the experimental branch:

- Rebuild the Scarlet-specific host executable with
  tools/scarlet/build_next_version.ps1 -SkipImporter, assuming that the existing
  developer build has its required lasgame.dll. Preserve local changes.
- **Also rebuild the bundled lasgen.exe**. Older helpers do not know the new
  --scarlet-dfps-pchtxt argument. From MSYS2 UCRT64 at the repository root,
  run make gen-helper. Python/PyInstaller requirements must be present.
- Place the experimental host executables and freshly built lasgen/ helper in
  a **separate** test installation. Do not call this v1.0.0 or overwrite the
  stable ZIP.

## Compile and launch the experiment

PowerShell in the separate experimental test installation:

    $base = "D:\Scarlet-Test\Scarlet-Recomp"
    $game = "$base\scarlet-games\active"
    $env:SCARLET_DFPS_PCHTXT = "D:\Scarlet-Test\mods\scarlet-dfps-v4.pchtxt"
    $env:SCARLET_TARGET_FPS = "60"

    & "$base\scarlet.exe" --prepare-aot $game
    if ($LASTEXITCODE -ne 0) { throw "Experimental AOT failed: inspect the log" }
    & "$base\scarlet.exe" --play $game

This regenerates game code for the patch and may be slow. If the patch is
missing, changed, out of bounds or for another Build ID, the experiment must
fail rather than run unverified instructions.

To return to baseline, close the game and unset both variables. The mode
suffix prevents cross-loading; a baseline game library must be built again
if you switched the same directory. Separate installs are safer.

## Required validation before declaring the experiment functional

- Clean 4.0.0 AOT completes and emits lasgame.dll and its .id file.
- Check scarlet-dfps and scarlet-fps runtime log messages.
- Compare the same battle and camera motion at 30 and experimental 60 FPS:
  character vibration, camera judder, animation speed and flashing effects.
- Repeat after warming shader cache; compare Vulkan FIFO and MAILBOX to
  separate frame presentation from broken game logic.
- Test walking, menus, NPCs, cutscenes, saves, evolution and reboot.
- Verify first-run build cancellation/resumption and baseline rollback.

**Limitations:** correct patch bytes are not proof of gameplay compatibility.
The ARM64 patch targets Switch/emulator behavior, not this Vulkan runtime.
Its branches may expose AOT translation problems. It will not necessarily fix
independent shader compilation, temporal anti-aliasing or frame pacing bugs.
A Windows build and in-game playtest are still REQUIRED.

Original mod credit: Fl4sh, https://github.com/Fl4sh9174.
No mod payload was copied into this repository.

## Intro-bedroom animation/physics A/B (unconfirmed)

At native 60 fps, the protagonist may briefly move above the floor in the
opening bedroom sequence, then return to normal. Other motion is smoother.
This is **not yet fixed** and does not establish whether root motion, physics,
or animation interpolation is at fault.

An independent native-port report for *Violet* found that an ASM 60-fps patch
could still leave jump physics at 30-fps parameters:
https://github.com/seedds/nxnative/issues/436
It points to the separately documented frame-rate mode at main+0x05BEFCE4,
which is OUTSIDE Scarlet's currently loaded main NSO image. Never blindly
dereference, allocate or write this address; it may be unmapped.

Experimental Win32 host-only probe (disabled by default):

- SCARLET_DFPS_INTRO_MODE=probe: check VirtualQuery, then read the mode if
  committed/readable. Log a sample every 60 presented frames and transitions.
  No modifications.
- SCARLET_DFPS_INTRO_MODE=force60: A/B experiment only. If committed and
  writable, and its current 32-bit value is exactly 2, write 1 (60-mode).
  It refuses to change any other value, any inaccessible or read-only
  mapping, and leaves original files unchanged. Reasserted on presenting
  frames, and might cause OTHER gameplay timing problems. Test only in an
  isolated copy with separate saves, and never enable for release.
- No variable: exact prior behavior, no probing or writes.

The host code lives in runtime/scarlet_dfps_intro_mode.c and is called from
runtime/nvn/pace.c. It changes neither tools/gen.py nor the generated AOT
code, so it requires **only a runtime rebuild**, not a new lasgame.dll.
Before trying force60, first run probe and look for
'[scarlet-intro-mode] present=... value=2'. If the site is unmapped, there is
no safe override to test; do not force memory mapping.

A confirmed improvement in the opening scene, with no regression in jumps,
battles, or cutscenes, is needed before implementing any automatic fix. The
runtime must eventually identify the actual scene and root cause rather than
apply the experimental override globally.
