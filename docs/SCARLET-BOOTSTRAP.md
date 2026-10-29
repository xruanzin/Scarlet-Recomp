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

## How the three reference projects apply

- [PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp/tree/pokemon-za):
  primary native layout (guest memory, kernel/HLE, loader, NVN/Vulkan and
  launcher). It is also the source code of this fork; its game-specific
  functions are *not* compatible with Scarlet without adaptation.
- [LASRecomp](https://github.com/peiikai/LASRecomp): LLVM/clang-compatible
  lifted function and AOT dispatch design. The existing `gen.py`, generated
  C chunks, `lasgame` interfaces and Makefile build are inherited from it.
- [SavageWindRecomp](https://github.com/Revivedx/SavageWindRecomp): its
  `runtime/nvn/vulkan/precompile.c` budgets shader compilation memory and
  orders pipeline jobs to avoid simultaneous peak allocations; `exec.c`
  caches dynamic Vulkan state, and `perfmon.c` measures frame times.
  These are concrete optimization candidates **after Scarlet first boots**.
  The BOTW shader archive assumptions and gameplay-specific constants must
  *not* be blindly copied.

## Extending the user's already compiled AOT with subsdk0 (incremental)

The merged 4.0.0 dump has been validated locally by the user: `main`
build ID `421c5411b487eb4d...`, updated `sdk`, and `subsdk0`.
Its ExeFS files are **directly in** `D:\\Pokemon Scarlet\\base=update`;
do not attempt to apply the encrypted NSP again.

The completed *main/sdk* AOT cache is `eb6deb908752b9c6`. **Do not
run the full `build_aot.py` again** after updating the Makefile, because its
source fingerprint changes and will create a new cache. After updating this
branch in `D:\\Scarlet-Recomp`, run from PowerShell with MSYS2 UCRT64 on PATH:

```powershell
cd "D:\\Scarlet-Recomp"
git status --short
git pull --ff-only
$env:MSYSTEM = "UCRT64"
$env:PATH = "C:\\msys64\\ucrt64\\bin;C:\\msys64\\usr\\bin;$env:PATH"
py -3 tools\\scarlet\\extend_subsdk0.py --exefs "D:\\Pokemon Scarlet\\base=update" --cache-id eb6deb908752b9c6 --jobs 2
```

The script requires an existing successful `aot-complete.json`, checks the
actual cached main ID, and generates/compiles **only** `subsdk0` at guest
base `0x7010000000`. The other two modules' C and objects are retained.
`subsdk0-complete.json` records this separate incremental stage. A
`--check-only` option can validate the cache with no generation.

On this development branch, the AOT library interface now has an optional
third function-address table (ABI 2), and the loader/dispatcher load,
relocate, dispatch, and initialize `subsdk0` when the table is present.
The original Z-A/LA build path has no third table. This code is
syntax-checked in CI, **not** game-tested. The current runtime is still
largely ZA-specific, so do not interpret the extra objects as a complete
Windows Scarlet build, or run the original ZA launcher as a Scarlet port.

## Experimental Windows link probe (reuses all three AOT modules)

When `subsdk0-complete.json` exists and the source branch has been updated,
the next non-destructive stage is to compile the inherited Vulkan runtime
and link the local recompiled game objects into `lasgame.dll`. It does **not**
launch Scarlet, apply extra patches, or rewrite `D:\\Pokemon Scarlet\\base=update`.

```powershell
cd "D:\\Scarlet-Recomp"
git pull --ff-only
$env:MSYSTEM = "UCRT64"
$env:PATH = "C:\\msys64\\ucrt64\\bin;C:\\msys64\\usr\\bin;$env:PATH"
py -3 tools\\scarlet\\link_probe.py --exefs "D:\\Pokemon Scarlet\\base=update" --cache-id eb6deb908752b9c6 --check-only
py -3 tools\\scarlet\\link_probe.py --exefs "D:\\Pokemon Scarlet\\base=update" --cache-id eb6deb908752b9c6 --jobs 2
```

Successful linking produces `build/scarlet/<id>/lasrecomp.exe`,
`lasgame.dll`, `scarlet-link.log`, and a
`scarlet-link-complete.json` marker. **This is only an experimental link
of the existing Z-A-derived runtime**: startup/HLE, Scarlet NPDM/FS
assumptions, updated RomFS, graphics and playable frames are not yet
validated. The resulting executable is not a Scarlet release and should not
be distributed as a working port.

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
