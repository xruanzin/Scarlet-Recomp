# Scarlet-Recomp — native Xbox/PlayStation input and title prompt (17 Nov 2026)

This branch integrates **both** requested changes into the same executable:
1. The game itself interprets Xbox A / PlayStation Cross (south) as its logical Switch A (confirm), and Xbox B / PlayStation Circle (east) as Switch B (cancel); X/Square and Y/Triangle follow their own labelled buttons. Nintendo stays east=A and south=B. The game’s short-tap input path, texture renderer and F1 binding list use this same effective mapping. With all four face buttons left at their defaults, the effective mapping changes according to F1 → Controls → Button icons. Saved custom mappings of any of the four faces are respected as a group. Keyboard controls do not change.
2. The native title-screen's original "Press A" element is not one of the recognized action-button textures, so the native render pass covers just that title hint with a host-drawn, localized "PRESS [button] TO START" or "PRESSIONE [botão] PARA COMEÇAR". It uses the effective logical A button or the configured key/mouse button and disappears once the game first receives logical A. Nintendo retains the game's original title prompt. No copyrighted game texture or game save is rewritten.

The Battle moves by position setting is limited to Nintendo layout in the Scarlet build so holding ZL cannot silently undo native Xbox / PlayStation bindings.

## Expected default mapping

| Game logical input | Nintendo | Xbox | PlayStation |
| --- | --- | --- | --- |
| A — confirm/start | A (east) | A (south) | × (south) |
| B — back/cancel | B (south) | B (east) | ○ (east) |
| X | X (north) | X (west) | □ (west) |
| Y | Y (west) | Y (north) | △ (north) |

Keyboard defaults include K for logical A. A custom key binding follows `g_bind_key[BIND_A]`.

## Windows installation

On the test clone `D:\Scarlet-Recomp-Window-Test` (clean `git status --short`):

```powershell
git fetch origin "refs/heads/fix/scarlet-native-controller-layout-title-prompt-20261117:refs/remotes/origin/fix/scarlet-native-controller-layout-title-prompt-20261117"
git switch -c fix/scarlet-native-controller-layout-title-prompt-20261117 refs/remotes/origin/fix/scarlet-native-controller-layout-title-prompt-20261117
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_play_f1_white.ps1
```

The script backs up `scarlet.exe` and rebuilds it with `SCARLET_AOT=1`, keeping `lasgame.dll` / `lasgame.dll.id`, FPS and saves unchanged.

## Manual runtime acceptance

- In-game title: choose Xbox in F1 and restart the game: show the Xbox A badge; Xbox A enters save, B cancels in-game menus.
- PlayStation: show × at title, × confirms, ○ cancels. Verify □/△ for the upper face actions.
- Keyboard: title shows the key actually mapped to logical A (default K), or the mouse button if explicitly assigned.
- Nintendo: original title + right A confirms, bottom B cancels.
- Change F1 button family: game and UI glyphs follow the same effective mapping, including while ZL is held.
- User-customized face bindings are honored; to use the default native convention, restore default controller bindings.

**Status:** source implemented and reviewed; the Windows binary, on-screen placement and runtime behavior must be verified on the user's Windows machine. No full game build has been run in the GitHub connector environment.
