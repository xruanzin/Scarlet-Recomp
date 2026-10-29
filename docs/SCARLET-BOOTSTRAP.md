# Pokémon Scarlet 4.0.0 — native AOT bootstrap (development branch)

**Status (2026-10-29): NOT PLAYABLE.** The existing repository is Pokémon Legends: Z-A's port.
This branch starts the separate Scarlet integration without rewriting or removing that code.
There is no claim of title screen, in-game frames, audio, or 30 FPS.

## Inspected starting point

- Original `pokemon-za` at `cff8364822617d8fea53549ccef8b4ba4383234a`.
- Reusable: `tools/nso.py`, `tools/gen.py` (ARM64 -> C), memory/relocation loader,
  thread and service HLE framework, SDL3, NVN/Maxwell -> Vulkan renderer,
  incremental C/object compilation.
- **Not reusable as-is:** the Z-A-specific startup, `za_patches.py`, the
  Link's Awakening address tables, per-game HLE hooks, RomFS assumptions,
  module layout and launcher metadata. Do not attempt to run Scarlet via
  `build/lasrecomp.exe` from the Z-A build.

## 4.0.0 identity: first hard gate

The following **main NSO build ID prefixes** are derived from earlier Scarlet
boot diagnostics (not from an NSP filename and not externally authenticated):

| Version | main NSO build ID prefix |
| --- | --- |
| Base 1.0.0 | `ca44e7dd62e61a2a` |
| Update 4.0.0 | `421c5411b487eb4d` |

Read directly from bytes `0x40..0x5f` in the decrypted `exefs/main`
NSO0 header. The verifier reads the whole 32-byte header build-ID field,
and uses the *16-character prefix* as a guard, not cryptographic proof of
update contents. The exact update NSP is encrypted, so reading PFS0
entries proves the container structure **only**, not its title, version,
correct update application or signature.

If `D:\Pokemon Scarlet\Extracted\Base\exefs\main` is 1.0.0, you **must**
extract the Program NCA from your own update NSP into, for example:

```text
D:\Pokemon Scarlet\Extracted\Update4.0.0\exefs\main
D:\Pokemon Scarlet\Extracted\Update4.0.0\exefs\sdk
D:\Pokemon Scarlet\Extracted\Update4.0.0\exefs\main.npdm
```

Use keys from **your own Switch** with a compatible decryptor. Never
commit the dump, tickets, prod.keys, title.keys, RomFS, or lifted game code.
Copying the NSP beside the base files does **not** apply the update.

## Reproducible Windows 11 checks

Run PowerShell in the repository root:

```powershell
py -3 tools\scarlet\preflight.py --base "D:\Pokemon Scarlet\Extracted\Base" --update-nsp "D:\Pokemon Scarlet\Pokemon Scarlet v4.0.0.nsp" --json
```

With just the base ExeFS, this should refuse AOT (exit code 2), even if
the NSP is well-formed. Once the **updated** ExeFS has been extracted:

```powershell
py -3 tools\scarlet\preflight.py --base "D:\Pokemon Scarlet\Extracted\Base" --update-nsp "D:\Pokemon Scarlet\Pokemon Scarlet v4.0.0.nsp" --update-exefs "D:\Pokemon Scarlet\Extracted\Update4.0.0" --json
```

The report must show `"ready_for_aot": true`,
`"recognized_version": "4.0.0"` in `update`, and a selected
`main_build_id` beginning with `421c5411b487eb4d`.

One-time toolchain setup if needed, in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup_windows.ps1
```

From the **MSYS2 UCRT64** shell opened at the repository root, compile
**only** the game's translated object files (this is not yet a runnable
Scarlet application):

```bash
export PATH="/c/msys64/ucrt64/bin:/c/msys64/usr/bin:$PATH"
python tools/scarlet/build_aot.py \
  --base "D:/Pokemon Scarlet/Extracted/Base" \
  --update-nsp "D:/Pokemon Scarlet/Pokemon Scarlet v4.0.0.nsp" \
  --update-exefs "D:/Pokemon Scarlet/Extracted/Update4.0.0" \
  --jobs 4
```

If `python` points to a non-Windows MSYS interpreter, call your native
Windows Python 3 interpreter instead. The generator itself uses the
`tools/venv/Scripts/python.exe` created by setup.

The generator is explicitly called with `--game scarlet`; no Z-A/LA
patches or randomizer hooks may be inherited. Generated chunks and
compiled object files live in distinct, content-addressed directories:

```text
generated-scarlet/<sha-prefix>/main/
generated-scarlet/<sha-prefix>/sdk/
build/scarlet/<sha-prefix>/obj/
build/scarlet/<sha-prefix>/aot-build.log
build/scarlet/<sha-prefix>/aot-complete.json
```

Same sources and tool ABI yield the same cache directory, and existing
object files are reused. Changed inputs produce a **new** directory rather
than deleting old AOT. The fingerprint is a build-cache key, not proof of
functional equivalence. Some original runtime dependencies remain game
specific; a `gen-objs` success is *only* successful translation and object
compilation. On a disk-constrained PC, remove only old **Scarlet** caches
after backing them up; do not delete the original ZA build cache.

Synthetic unit tests (no copyrighted game files):

```bash
python tools/scarlet/test_preflight.py
```

## Remaining blockers before a playable port

1. Update extraction and program identity on the actual Windows files;
   check `sdk`, `subsdk*`, NPDM and dynamic import coverage.
2. Replace the Z-A/Link's Awakening game version selection, game-specific
   HLE hooks, startup and randomizer with a genuine Scarlet boot path.
3. Adapt nn::svc, nn::os, nn::fs, nn::hid, nn::audio, nn::swkbd and
   NVN dispatch to the Scarlet binary's *observed* imports; don't return
   invented success results from unimplemented services.
4. Implement merged update 4.0.0 RomFS mount semantics, and test content
   access using correctly applied update resources.
5. Link the AOT against the Scarlet runtime, launch under Vulkan with
   logs, triage the first crash and proceed iteratively to game menus and
   actual 3D frames; validate keyboard overlay, controller, sound and FPS.
6. Run a 30 FPS gameplay capture on real Windows hardware with CPU/RAM/GPU
   metrics; only then discuss a higher frame-rate mode.

**No game executable or first gameplay has been validated in this environment.**
The development environment has no access to the user's D: drive, NSP
contents, Windows 11 installation or Vulkan graphics driver. Do not
interpret a CI pass or AOT output as a playable game.
