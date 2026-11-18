<div align="center">

<img src="launcher/assets/scarlet_launcher_background.jpg" alt="Scarlet-Recomp launcher artwork" width="820">

# Scarlet-Recomp

**Pokémon Scarlet on Windows, with PC-friendly controls and extra performance options.**

Independent port for **Pokémon Scarlet 4.0.0** · Windows 11 · Vulkan

[Português (Brasil)](README.pt-BR.md) · [Releases](https://github.com/xruanzin/Scarlet-Recomp/releases) · [What's new](CHANGELOG.md) · [Report an issue](https://github.com/xruanzin/Scarlet-Recomp/issues)

</div>

---

**Scarlet-Recomp** is a community project that runs Pokémon Scarlet natively on Windows. It prepares the game from files provided by the player; original game content is not included.

The goal is a more comfortable PC experience, with familiar controller layouts, graphics settings and optional higher frame rates.

> **Current status:** the controller build passed a portable ZIP smoke test and has run in local playtests. First-time setup on a separate clean Windows installation and some features still need verification. A public download will be listed under **Releases** once that work is done.

## Features

- **PC controls:** keyboard and mouse, Xbox, PlayStation and Nintendo controllers, with remapping in the F1 menu.
- **Controller icons:** select the device style in F1 to replace supported in-game button symbols. Start/Select and face-button mappings follow the selected layout.
- **Custom F1 menu:** clean light interface with Scarlet accents; display, audio and control options in **English and Portuguese**.
- **30 and 60 FPS:** a 60 FPS mode is available for testing alongside the traditional 30 FPS option.
- **120 and 240 FPS:** available in the launcher, but **highly experimental**; stable gameplay and correct timing are not guaranteed.
- **Graphics options:** resolution, scaling, sharpening, filtering and other controls.
- **Launcher:** select your own base game, update 4.0.0, optional DLCs and required keys for local installation.
- **FPS counter:** optional overlay in F1.

## Performance tests

| Graphics card | Reported result |
| --- | --- |
| **GeForce RTX 5060** | **60 FPS** in local tests |
| **GeForce RTX 3050** | **60 FPS** in tests reported to the project |

These are test results, not minimum requirements or guaranteed performance. CPU, resolution, drivers and in-game scenes matter. Even at 60 FPS, some game behaviour remains experimental.

## Screenshots

The image above is **launcher artwork**, not a gameplay screenshot. We're preparing a gallery of real Scarlet gameplay, F1 settings and controller prompts.

[Gallery and screenshot submission guide](docs/showcase/README.md)

## Known issues

- **Player portrait at the beginning:** the player photo in the enrollment form may be black or missing. **This is a known visual bug to be fixed**, not a disabled feature.
- **Faces and effects:** eyes, eyebrows and some visual effects may render incorrectly in certain scenes.
- **Title-screen button:** *“PRESS A TO START”* may still use the original Switch A icon even if F1 is set to Xbox, PlayStation or keyboard.
- **High FPS:** 120 and 240 FPS are experimental and may affect animations, physics and game speed.

## Getting started

When ready, the public package will be posted on [Releases](https://github.com/xruanzin/Scarlet-Recomp/releases). You will need **64-bit Windows 11**, a Vulkan-capable GPU, **your own** Pokémon Scarlet base game and update **4.0.0**, plus keys from your own setup where required.

The launcher includes tools to prepare the game locally. First-time preparation may take a while and has not yet been fully validated on a separate clean PC.

**No NSP/XCI, game files, keys, saves or game-derived compiled DLL are distributed.**

## Credits

Developed by **[xruanzin](https://github.com/xruanzin)**, building on [PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp), [LASRecomp](https://github.com/peiikai/LASRecomp) and their contributors. The F1 menu was adapted from their original work. Development included assistance from AI tools.

Unofficial community project; not affiliated with Nintendo, Game Freak or The Pokémon Company. See the [license](LICENSE) and third-party notices.
