# Scarlet native launcher / window / custom icon repair (30 Oct 2026)

## User report and root cause

The user switched to the new feature branch but compilation stopped at
`dotnet publish` with `No .NET SDKs were found`. As a result the
new native launcher had not been compiled into `scarlet.exe` yet.
Starting the prior executable attempted game boot directly and led to
a nonresponsive black window. There was also a separate risk of
`LARECOMP_NO_LAUNCHER` inherited from diagnostic shells bypassing
the intended first-run setup.

## Repair

- `scarlet.exe` with **no arguments** now always opens the Scarlet
  launcher in a regular interactive start; tests with `--play` or
  `LARECOMP_INPUT` still boot without launcher.
- Diagnostic stdout includes
  `[scarlet] entering native Scarlet launcher before game boot`,
  `[scarlet-launcher] initializing...`,
  `[scarlet-launcher] native UI ready...`.
- ImGui/Vulkan launch errors show a message instead of silently
  leaving an apparently frozen black UI.
- SDL Vulkan window title is exactly **Scarlet** in native
  `SCARLET_AOT=1` builds. Same SDL window is used by game and launcher.
- Windows executable icon resource ID 1 uses
  `docs/icon/scarlet.ico` when that file exists in local checkout.
  This path is intentionally **not the upstream ZA icon**.
  The build helper can copy the user's custom ICO from
  `D:\Scarlet-Recomp\icon.ico` (or `-IconPath C:\path\icon.ico`) into
  `docs/icon/scarlet.ico`. Until user supplies that file, the
  upstream icon remains as fallback. **Do not claim the uploaded icon
  is committed into GitHub's text-only source patch.**
- The helper builds the *runtime before* downloading/installing
  the .NET 8 SDK and publishing the NSP/XCI importer. This means
  `-SkipImporter` gives a quick **launcher UI smoke test**
  without .NET prerequisite.
- Since GNU Make does not track CFLAGS changing from ZA to
  `SCARLET_AOT=1`, the helper deletes only six outdated **host
  .o files** once before the first Scarlet-native rebuild. It
  never deletes or recompiles `lasgame.dll`, extracted game content,
  saves or shader caches. A stamp prevents redundant rebuilds.

## Quick validation

1. Download the user-provided ICO artifact from ChatGPT and save as:
   `D:\Scarlet-Recomp\icon.ico`
2. Switch to the repair branch (or fetch it separately; never reset
   any working checkout).
3. Check first the UI **without** running the importer:

~~~powershell
cd D:\Scarlet-Recomp
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_next_version.ps1 -SkipImporter
& 'D:\Scarlet-Recomp\build\scarlet\eb6deb908752b9c6\scarlet.exe'
~~~

Expected: a **Scarlet** window and native ImGui launcher
with NSP/XCI, update 4.0.0, DLCs, keys, and experimental FPS switch.
Play may be disabled until an AOT-matching import completes. The icon
should be the supplied Windows ICO. If Explorer still caches the old icon,
check the icon resource with Resource Hacker or Windows Explorer file
Properties and restart Explorer; do not replace the icon arbitrarily.

4. To finish with automatic SDK and importer: run the same helper
   **without** `-SkipImporter`. It uses a local .NET 8 SDK under D:
   if none installed.

If black screen still appears with these new logs, inspect the actual
stderr and launch mode first. No claim of verified Windows compilation
or gameplay is made until the user reruns the test.
