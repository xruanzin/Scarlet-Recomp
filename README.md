<div align="center">

# Scarlet-Recomp

**Pokémon Scarlet 4.0.0 — native Windows runtime**

Static recompilation (AOT) · Vulkan · Windows 11 x64

[Português (Brasil)](README.pt-BR.md) · [Release notes](docs/RELEASE-v1.0.0.md) · [Build & setup](docs/BUILD-windows.md) · [Issues](https://github.com/xruanzin/Scarlet-Recomp/issues)

</div>

---

> [!IMPORTANT]
> **v1.0.0 is in preparation.** The game runs in local development tests, but the portable ZIP and first-run setup have **not** been verified on a clean Windows installation. There is no published, validated release yet.

## About

Scarlet-Recomp is an **unofficial, community-developed native Windows port** of Pokémon Scarlet 4.0.0. It recompiles code from the player's own game files ahead of time and runs it with a Windows/Vulkan runtime, rather than using a suyu-based emulator.

Based on the architecture of [PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp) and [LASRecomp](https://github.com/peiikai/LASRecomp), with Scarlet-specific integration and graphics work.

## Current state

| Component | Status |
| --- | --- |
| Native Windows/Vulkan runtime | Boots and runs in local development tests |
| Custom launcher and NSP/XCI importer | Implemented; clean-install workflow not yet verified |
| Pokémon Scarlet update 4.0.0 | Targeted version |
| 30 FPS | Recommended baseline |
| 60 FPS / 120 FPS / 240 FPS | Experimental targets; timing and physics may differ |
| Public portable ZIP | In preparation; no verified release published |

**Known issues:** eyes and eyebrows may disappear in some cutscenes; the enrollment-form portrait may appear black; other graphical or stability issues remain possible. Some earlier character-animation and fullscreen flicker problems were resolved in specific local builds, but require verification in the packaged v1.0.0.

**Built-in native 60 FPS timing (experimental):** the existing **60 FPS** selection now uses a host-side adaptive frame clock. No mod, `.pchtxt`, extra FPS option, or new game-code AOT build is required. [Design and test limits](docs/SCARLET-NATIVE-DYNAMIC-60FPS.md). It still needs gameplay testing for character/camera jitter.

## Requirements and setup

You need **Windows 11 x64**, a Vulkan-capable GPU/driver, **your own legally obtained Pokémon Scarlet base game and update 4.0.0**, and your own keys if required for local import.

When a validated package is available, it will appear in [Releases](https://github.com/xruanzin/Scarlet-Recomp/releases). Its launcher is designed to import the player's files and generate the game-specific AOT library locally.

> [!NOTE]
> This repository **does not distribute** the game, NSP/XCI dumps, keys, RomFS, saves, or a game-derived `lasgame.dll`. Initial setup can take time and is not yet validated on an unrelated Windows PC.

## Development and documentation

The Windows packaging workflow for maintainers is:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_release_candidate.ps1
```

That command assumes a configured development environment and existing AOT build. It is **not** an end-user install command.

[Windows build guide](docs/BUILD-windows.md) · [v1.0.0 preparation checklist](docs/RELEASE-CHECKLIST-v1.0.0.md) · [Dependencies](docs/RELEASE-DEPENDENCIES-v1.0.0.md) · [Development notes](docs/SCARLET-BOOTSTRAP.md)

## Credits

Developed by **xruanzin**, with technical assistance from **ChatGPT (OpenAI)**. Thanks to the developers and contributors of [PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp), [LASRecomp](https://github.com/peiikai/LASRecomp) and the other upstream components.

This is an independent project, **not affiliated with Nintendo, Game Freak, or The Pokémon Company**. See [LICENSE](LICENSE); source-code licensing does not grant rights to redistribute game content.
