# Contributing to Scarlet-Recomp

Thanks for helping make Scarlet-Recomp better. Whether you're fixing a bug, testing a controller, or sharing a graphics issue, contributions are welcome.

## Ways to help

- **Bug reports:** crashes, missing textures, camera issues, or problems during game setup.
- **Testing:** different GPUs, Xbox/PlayStation controllers, keyboard and mouse, and the 30/60 FPS modes.
- **Fixes and improvements:** graphics, input, launcher, performance, accessibility, and documentation.
- **Translations:** make labels and instructions clearer in English or Portuguese.

The **missing player portrait near the beginning of the game** is a known visual bug. Reports with reliable steps, screenshots, or a tested fix are especially helpful.

The **120 and 240 FPS options are experimental**. Please don't label them stable without gameplay testing.

## Reporting an issue

Before opening a new issue, check the [existing reports](https://github.com/xruanzin/Scarlet-Recomp/issues).

A useful report includes:

- What happened, what you expected, and how to reproduce it.
- Your Scarlet-Recomp version, **Pokémon Scarlet 4.0.0**, Windows version, CPU, GPU, and graphics driver.
- The selected FPS mode and controller type, if relevant.
- A screenshot or short video for visual bugs, and a short relevant log excerpt for crashes.

Please remove any personal information, file paths, keys, or save data from anything you share. Gameplay screenshots are welcome.

[Open an issue](https://github.com/xruanzin/Scarlet-Recomp/issues/new)

## Sending a change

1. Create a new branch from **`main`**.
2. Keep the change focused on one issue or feature.
3. Test it in the actual game whenever possible. A successful build alone doesn't confirm a graphics or gameplay fix.
4. Open a pull request **into `main`** and briefly describe the change, why it helps, and how you tested it.

For input changes, check the keyboard and controller layouts. For frame-rate changes, test at 30 and 60 FPS and pay attention to camera movement, animations, battles, and game speed. For graphics fixes, include before/after screenshots when possible.

Unverified experiments are welcome as discussions or draft pull requests, but should stay separate from the stable build.

## Building from source

The project targets Windows 11 with Vulkan. See the [Windows build guide](docs/BUILD-windows.md) for the development environment and build steps.

Useful areas of the repository:

- `launcher/` — Windows launcher.
- `runtime/` — native runtime, graphics, input, and in-game settings.
- `tools/scarlet/` and `tools/scarletimport/` — Scarlet setup and packaging tools.
- `docs/` — technical notes, testing, and release information.

Please follow the code style around the files you're editing. Prefer straightforward fixes to broad unrelated rewrites, and preserve upstream attribution where applicable.

## Game files and third-party content

**Do not commit or attach Nintendo game content**, including NSP/XCI files, extracted ExeFS/RomFS, encryption keys, game assets, generated game code, or the game-derived `lasgame.dll`.

Avoid including personal saves, private logs, or copyrighted assets from other projects without appropriate permission. Small gameplay screenshots and clips used to demonstrate a bug are fine.

Keep third-party credits and license notices intact.

## License

By submitting a contribution, you agree to license your code under the repository's [MIT License](LICENSE).
