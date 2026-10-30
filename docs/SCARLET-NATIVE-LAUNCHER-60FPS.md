# Scarlet-Recomp: Native launcher and 60 FPS development

Branch: feature/scarlet-launcher-packages-fps-20261030. Windows 11/Vulkan.

## Implemented

- SDL3/ImGui dark centered Scarlet launcher patterned on the earlier compact scarlet_pc interface. No graphics or upscaling controls.
- File pickers for base NSP/XCI, update 4.0.0 NSP, two DLC NSPs, prod.keys and optional title.keys. Selected paths remembered locally in scarlet-games/selection.txt.
- Dedicated LibHac importer, tools/scarletimport (.NET 8; LibHac 0.19.0). Extracts updated ExeFS, patch-merged romfs.bin and DLC aoc/titleid.bin from the user's local game dump. Validates game title 0100A3D008C5C000, main Build ID 421C5411B487EB4D and Control NACP display version 4.0.0. 3.0.1 and 4.0.0 may have the same main Build ID, so that alone is not sufficient.
- Stages in scarlet-games/.installing, promotes on success to scarlet-games/active. Previous installs moved to scarlet-games/previous (not deleted); interrupted imports preserved in failed staging. Original game dumps, old test roots, saves and AOT are not modified.
- PLAY is disabled until a matching updated 4.0.0 ExeFS and a compatible lasgame.dll plus lasgame.dll.id are found. The importer does not compile the AOT or download copyrighted game data.
- User-verified hair correction: exact shader aa68a5939321c84a / stencil material 3 automatically uses albedo chroma in SCARLET_AOT. Default sky 3D texture 32x128x32 already uses block depth 0.
- For Windows SCARLET_AOT, default large data root is beside scarlet.exe on its installation drive, unless LARECOMP_DATA_ROOT overrides it.

## One command to build

Requirements: working Windows 11 MSYS2 UCRT64 clang/make/SDL3/Vulkan, existing Scarlet 4.0.0 lasgame.dll and .id, and .NET 8 SDK for the standalone importer.

    cd D:\Scarlet-Recomp
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_next_version.ps1

The script stores .NET/NuGet temporary files in D:\Scarlet-Recomp\build, publishes the standalone importer beside scarlet.exe, and builds the existing runtime incrementally. It does not regenerate the heavy AOT library.

Run D:\Scarlet-Recomp\build\scarlet\eb6deb908752b9c6\scarlet.exe directly (without --play). Direct --play paths and graphics_verify.ps1 still intentionally bypass the launcher for tests.

## Experimental native 60 FPS

The Scarlet 4.0.0 community FPS cheat for main Build ID 421C5411B487EB4D uses 16,666,667 ns instead of 33,333,334 ns at MAIN+0x03C2FBB0. The code guards the write by game ID, committed module size, and expected original value 0x01FCA056, before writing 0x00FE502B. The corresponding host NVN window present interval becomes 1 (vs 2 at 30 Hz) ONLY when that patch was accepted.

Reference: https://github.com/HamletDuFromage/switch-cheats-db

The community cheat also writes MAIN+0x05BEFCE4=1. This offset lies outside the main module's committed size in the observed AOT runtime, so this port deliberately does NOT dereference it; the host NVN present interval handles the display-side change instead. Correct game simulation at 60 FPS is unverified: this is a selectable, OFF-by-default experimental mode with 30 FPS as the safe default, not a promise of native 60 FPS performance.

A GPU can present up to 60 frames only if both game code and PC deliver each frame within 16.7 ms. CPU bottlenecks may prevent that. Test world walking distance, in-game time, animations, menus, battles, captures, cutscenes, audio synchronization and loading. Never infer native 60 FPS just from changing the NVN present interval.

Do not reuse Z-A or Let's Go address-specific 60 FPS hooks on Scarlet.

## Before merging this branch

1. Compile the Windows runtime/importer; verify new UI and file dialogs.
2. Import legal local base+update 4.0.0 and optional DLC dumps; inspect local import.log.
3. Verify game starts on matching lasgame.dll and extracted updated ExeFS, and survives game restarts.
4. Check daytime, sunset and night sky and natural hair without -HairMode switches.
5. Compare 30 vs experimental 60 FPS game-speed and stability using the same save.
6. Confirm original test installation, saves, git changes and AOT files were not touched.

The code is published, but full build and first-run gameplay validation require the user's Windows environment with their private game dumps. No ROMs, keys or executable game patches are committed.
