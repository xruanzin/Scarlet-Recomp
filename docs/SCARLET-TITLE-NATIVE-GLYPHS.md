# Scarlet — native title-screen button glyphs (no overlay)

## Problem / correction

The previous experimental implementation drew a large opaque ImGui panel over
the title screen while the original game's "PRESS A BUTTON" / translated
"PRESSIONE A PARA COMEÇAR" continued underneath. That solution is removed
completely in this branch (runtime/ui/menu.mm restored before the title panel
was introduced).

Instead, the build helper creates **native button glyphs** from a TrueType font:
- Xbox: circled A, B, X and Y;
- PlayStation: cross, circle, square and triangle;
- Keyboard: framed K, J, L, I (or single-letter custom bindings);
- Steam Deck: circled A, B, X and Y;
- Nintendo: the original game/console fonts are untouched.

The tool `tools/scarlet/native_title_glyphs.py` uses only the Python standard
library and writes `fonts/nintendo_ext_003_scarlet_<style>.ttf` locally.
It starts from the player's own NintendoExt font if available, preserving
all other original glyphs, or the bundled OFL DejaVu font when absent.
It appends 4 native vector glyphs, maps both outline and filled NintendoExt
private-use codepoints U+E0A0–E0A3 and U+E0E0–E0E3, and validates the resulting
font tables. No game textures, RomFS, NSP, AOT library or save files are modified.

`runtime/hle/pl.c` selects this generated font through the original
`nn::pl::GetSharedFontAddress(SharedFontType_NintendoExt)` mechanism.
The chosen font is attached to the game's own layout: there is **no new
ImGui title widget or second "PRESS A" prompt**. The logical face-button
remapping of the previous branch remains in place.

**Technical boundary:** this affects the native title prompt *only if*
the game/translation actually draws its button using NintendoExt glyphs.
If that particular title uses an independent art texture or a game-owned
font, this code cannot replace it. The logs differentiate successful font
installation and whether the game requests NintendoExt, but only a runtime
test on the user's own game can establish visual success. Do not claim a
complete tested fix without that result.

## Build/play test (Windows)

Close the running Scarlet and use a clean working tree:

```powershell
cd "D:\Scarlet-Recomp-Window-Test"
git status --short
git fetch origin "refs/heads/fix/scarlet-native-title-glyph-no-overlay-20261117"
git switch -c fix/scarlet-native-title-glyph-no-overlay-20261117 FETCH_HEAD
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_play_f1_white.ps1
```

The PowerShell helper compiles only `scarlet.exe` and then generates local
title icon fonts with Python (no pip dependencies). It preserves the existing
`lasgame.dll`, `lasgame.dll.id`, FPS behavior, controls, and saves.

Check console logs:

- `[scarlet-native-title] <style> native glyphs=...`: four fonts generated
- `[scarlet-native-title] native NintendoExt button glyph font: <style>`:
  selected font loaded by HLE
- `[scarlet-native-title] game requested NintendoExt shared-font glyphs`:
  the game asked for system NintendoExt (not proof that title uses it)

Select Xbox / PlayStation / Keyboard under F1 -> Controls -> Button icons and
restart game to reload native shared fonts. Nintendo remains original.

## Visual acceptance

1. No opaque overlay, floating panel, duplicated hint or covered background.
2. The title's original line keeps its placement and typography. Its button
   glyph shows the effective selected device, including PS × and keyboard K.
3. Xbox A / PS Cross confirms and Xbox B / PS Circle cancels within the game;
   Nintendo A (right) / B (bottom) remains unchanged.
4. If original title stays unchanged, this identifies an unsupported title
   asset path requiring an exact native game texture or font resource survey.
   Do not fake this with a fixed-position rectangle again.

**Validation:** native glyph writer's sfnt algorithm, vector outlines and
glyph mapping were exercised with DejaVu TrueType and parsed with fontTools,
and corresponding samples rendered on Linux. Windows build and the user's
specific title asset have not yet been inspected live.
