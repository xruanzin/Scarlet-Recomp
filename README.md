<div align="center">

# Scarlet-Recomp

**Native Windows runtime for Pokémon Scarlet 4.0.0, based on static recompilation and Vulkan.**

[Português (Brasil)](README.pt-BR.md) · [Known limitations](#known-limitations) · [Release preparation](docs/RELEASE-v1.0.0.md)

</div>

> **v1.0.0 preparation — not a verified public installer.** The existing Windows build runs Pokémon Scarlet 4.0.0 in development tests, but a clean-machine installation, the public package and broader compatibility still need verification. Do not label it a finished, universally playable release.

## What this project is

Scarlet-Recomp is an independent, unofficial effort to run **Pokémon Scarlet 4.0.0** on Windows using ahead-of-time (AOT) recompilation of code from a user's own game dump. The host runtime implements Nintendo Switch services and NVN graphics through Vulkan; the goal is not to launch the game inside a suyu-based emulator.

The repository retains an architecture derived from [PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp) and [LASRecomp](https://github.com/peiikai/LASRecomp), with Scarlet-specific runtime changes, an NSP/XCI importer, and a custom Windows launcher.

## Current features

- Windows 11 native runtime using Vulkan and AOT-compiled guest modules
- Scarlet launcher with file/folder selection for NSP/XCI, local key-file pickers and import status
- Automatic Scarlet-specific early TLS/allocator startup: no experimental toggle or boot environment variables required
- Base game + **update 4.0.0** import path, with optional DLC handling
- Keyboard/controller handling and a virtual keyboard for name entry
- Selectable 30 / 60 / 120 / 240 FPS **targets**; 30 FPS is the tested baseline and higher targets are experimental
- Vulkan graphical fixes and optional upscaling features under development

Features above describe implemented development paths, not a guarantee that they work across all PCs, game scenes or configurations.

## Requirements and game files

- Windows 11 64-bit; a Vulkan-capable graphics driver
- A local, legally obtained copy of Pokémon Scarlet and the matching **4.0.0** update
- Your own decryption keys for the local importer, where required
- A game-derived `lasgame.dll` AOT build generated **locally from your own game files**, not distributed by this project

**No NSP/XCI, extracted game files, decryption keys, tickets, saves, or game-derived AOT DLL should be committed or attached to a public release.**

## Official prerequisite downloads

- [Microsoft Visual C++ Redistributable x64](https://aka.ms/vc14/vc_redist.x64.exe) — if required by Windows
- [NVIDIA graphics driver](https://www.nvidia.com/Download/index.aspx) or [AMD graphics driver](https://www.amd.com/en/support/download/drivers.html) — up-to-date Vulkan support
- [Python for Windows](https://www.python.org/downloads/windows/), [MSYS2](https://www.msys2.org/) and [.NET 8 SDK](https://dotnet.microsoft.com/en-us/download/dotnet/8.0) — for **compilation and local AOT generation**, not for running an already built launcher
- [Full prerequisites and credits](docs/RELEASE-DEPENDENCIES-v1.0.0.md)

The runtime ZIP includes redistributable support DLLs and the self-contained importer, but **is not currently plug-and-play**: the game-derived `lasgame.dll` still has to be built locally from the player's own copy.

## Preparing the distributable runtime ZIP

After locally building the Windows runtime, the maintainer can run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\create_release_zip.ps1
```

The package explicitly excludes game dumps, keys, saves and `lasgame.dll`. Audit the included third-party licenses and test on a clean Windows machine before publishing.

## Building for development

This is **not yet a standalone binary installation guide**. The current incremental build assumes the owner's existing AOT output:

```powershell
# Windows, with development dependencies and an existing Scarlet AOT build
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_next_version.ps1
```

It does **not** create `lasgame.dll` on its own. For the AOT preparation and requirements, see [Scarlet bootstrap notes](docs/SCARLET-BOOTSTRAP.md) and [Windows launcher details](docs/SCARLET-ORIGINAL-LAUNCHER.md). Those documents contain historical development notes, not a verified clean-install tutorial.

## Known limitations

- **The character photograph on the enrollment/matriculation form is black.** The original in-game photograph generation remains unresolved. No external-image fallback is part of this release plan.
- Visual issues may remain in some character, sky or intermediate rendering passes.
- Higher FPS options have not been validated for physics, timing, animation and stability.
- Import, AOT setup and launch need clean Windows machine verification before distributing a ready-to-use download.

See [v1.0.0 release draft](docs/RELEASE-v1.0.0.md) and [release checklist](docs/RELEASE-CHECKLIST-v1.0.0.md).

## Credits and legal

This is a **community project**, not affiliated with Nintendo, Game Freak or The Pokémon Company. Pokémon and all associated game content belong to their respective rights holders.

Architecture and underlying source come from [PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp), [LASRecomp](https://github.com/peiikai/LASRecomp) and other upstream contributors. Retain upstream notices and third-party licenses. See [LICENSE](LICENSE); its permission does not extend to proprietary Pokémon Scarlet game content.
