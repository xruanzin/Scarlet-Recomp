# Scarlet-Recomp v1.0.0 — draft release notes

**STATUS: DRAFT — do not publish/tag until the release checklist is complete.**

## Overview

First public version proposed for the Windows/Vulkan native Scarlet-Recomp project, targeting **Pokémon Scarlet update 4.0.0**. The host uses AOT static recompilation and a dedicated Vulkan runtime.

## Implemented

- Native Windows launcher with local game package selection and configuration
- Scarlet-specific import workflow for locally supplied NSP/XCI, update 4.0.0 and optional DLC
- Keyboard/controller input, including player-name entry
- 30 FPS baseline and experimental 60 / 120 / 240 FPS targets
- Vulkan rendering and iterative character/hair/sky graphics corrections

## Known issues

- **Enrollment-form portrait is black.** The original in-game portrait generator is not fixed. The optional external-image portrait fallback from the experimental branch is excluded.
- Remaining rendering defects may occur; additional screenshots, cutscenes and effects are not comprehensively validated.
- High FPS settings may affect gameplay timing, animations or physics.
- First-run setup and installation on a clean Windows computer have not been validated as a consumer workflow.

## Distribution restriction

Distribute **only redistributable runtime/tool code and dependency files whose licenses permit it**. Do not include Pokémon game content, any NSP/XCI, dumped/extracted RomFS or ExeFS, console keys/tickets or user-generated game-derived AOT `lasgame.dll` / `lasgame.dll.id`. Users must use their own legally acquired inputs and generate their own AOT output where applicable.

The current `tools/scarlet/build_next_version.ps1` requires an existing local `lasgame.dll`, so a binary-only ZIP is **not** currently a complete plug-and-play installer.

## Final release metadata (pending owner approval)

- **Tag:** `v1.0.0`
- **Title:** `Scarlet-Recomp v1.0.0`
- **Target branch:** `release/v1.0.0-preparation-20261101` (until approved)
- **Pre-release checkbox:** decide after test matrix and package plan
- **Binary attachment:** TBD after clean, lawful and reproducible packaging is verified
- **Publishing:** not performed as part of this draft
