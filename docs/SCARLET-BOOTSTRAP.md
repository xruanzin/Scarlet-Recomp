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

Successful linking produces `build/scarlet/<id>/scarlet.exe`,
`lasgame.dll`, `scarlet-link.log`, and a
`scarlet-link-complete.json` marker. **This is only an experimental link
of the existing Z-A-derived runtime**: startup/HLE, Scarlet NPDM/FS
assumptions, updated RomFS, graphics and playable frames are not yet
validated. The resulting `scarlet.exe` is not a Scarlet release and should not
be distributed as a working port.

## First Scarlet boot: SDK malloc before TLS is ready (experimental)

A local Windows boot loaded and relocated `main`, `sdk`, and `subsdk0`,
but crashed during SDK `DT_INIT` at `main!malloc` (guest
`f_7002b7d830`). The SDK imports `malloc` through its PLT; the main
allocator reads `TPIDR_EL0 + 0x30` before `TPIDR_EL0` has been set.
The SDK itself later installs the real thread pointer from the thread-local
region's `+0x1f0` field. This is an initialization-order defect, **not**
proof of a playable game.

For a controlled one-boot probe only, set `SCARLET_EARLY_TLS_PROBE=1`.
Before running the SDK init callback, the runtime checks the existing
`TLR.ThreadPointer` field and uses it if available. Otherwise it supplies
a **temporary, zeroed, guest-mapped 0x1000-byte TLS buffer** to the CPU's
`TPIDR_EL0`; it intentionally does **not** write a fake pointer to the
SDK-owned `TLR.ThreadPointer` slot, and does not change the normal Z-A/LA
path. Its size/layout are unverified, and booting further does not prove
allocator correctness. Do not enable this by default or ship it as a fix.

After `git pull --ff-only`, rerun `link_probe.py --jobs 2` with the
**existing cache ID** to incrementally relink only the changed runtime.
No `build_aot.py`, `extend_subsdk0.py`, or game code generation is required.
Then set the environment variable only for a short supervised boot; inspect
the `[scarlet/tls]` lines and the **first new crash**, if any. Unset it
(`Remove-Item Env:SCARLET_EARLY_TLS_PROBE`) to return to prior behavior.

## Second boot crash: early main!malloc singleton (A/B experiment)

The first opt-in `SCARLET_EARLY_TLS_PROBE=1` passed the initial null
`TPIDR_EL0 + 0x30` read, but the **same** guest `main!malloc` crashed
on a null address later, after visiting its guarded allocator singleton.
In the v4.0.0 generated `main_942.c`, the allocator uses the guarded
pointer at guest `0x7004759430` and a backing pointer at
`0x7004759418`. This suggests the main allocator's backing state
is not initialized at the point the SDK calls `malloc`.

`SCARLET_MAIN_INIT_FIRST=1` is an **additional diagnostic A/B option
for this exact Scarlet program ID**: it logs those three allocator
globals and runs main's `DT_INIT` before SDK's `DT_INIT`. It guards
against a second main initialization in the later callback, but does
not change `subsdk0` initialization. This is **not** the proven correct
runtime-loader initialization order, and main's initializer can depend
on SDK state: crashes or hang may still occur. Do not ship it enabled.
Keep `SCARLET_EARLY_TLS_PROBE=1` for a consistent A/B run.

Relink the existing cache with `link_probe.py --jobs 2` (only
`runtime/main.c` changed), then inspect the earliest
`[scarlet/alloc]` and `[scarlet/init]` messages, `init` lines,
and first new exception. Disable both environment variables after
the isolated test. The first boot test's `romfs` junction pointed
at ExeFS, **not real merged Scarlet RomFS**. Replace that with actual
merged RomFS before trying content loading or declaring gameplay.

## Scarlet v4.0.0 malloc bootstrap — diagnostic only

Inspection of the game's merged NSO symbol tables proves that only main
exports malloc (guest 0x7002b7d830). Both sdk and subsdk0 import it:
the loader's symbol binding is correct.

The temporary TPIDR probe got past the read of TPIDR_EL0+0x30 but
failed deeper in main!malloc; moving main DT_INIT before sdk DT_INIT
failed too, because main's constructors themselves allocate.

An **opt-in diagnostic** (environment SCARLET_BOOTSTRAP_ALLOCATOR=1)
adds an allocator object into the *temporary* thread-local area at
TPIDR_EL0+0x30. The object provides the observed allocator vtable
allocate method (offset +0x10), using guest-mapped allocations in the
existing HLE heap. This allows an isolated experiment without rebuilding
the AOT modules. It is incomplete: it has no free/realloc, lifetime, or
allocator ownership semantics. It is **not** a fix for a playable game,
must never be enabled in a release, and advancing to a later init phase
does not establish correctness.

Relink only the changed runtime with link_probe.py --jobs 2 and cache
eb6deb908752b9c6. For this probe enable both
SCARLET_EARLY_TLS_PROBE=1 and SCARLET_BOOTSTRAP_ALLOCATOR=1.
Ensure SCARLET_MAIN_INIT_FIRST is **unset**. Capture startup logs and
the first new crash, then unset both experimental variables.
The executable still uses the inherited ZA host and its RomFS setup
is not yet a correct Scarlet content mount.

## First successful SDK / Vulkan init and csrng busy-loop

An isolated boot with SCARLET_EARLY_TLS_PROBE=1 and
SCARLET_BOOTSTRAP_ALLOCATOR=1 advanced past main/sdk/subsdk0 constructors,
initialized NVN/Vulkan, the window, controller, audio, fonts, and guest
threads. The next captured log had **5,733 identical calls** to
STUB csrng cmd 0: the old fallback returned success without writing
random data to the request's output B buffer. This is not a valid
implementation and plausibly causes the busy-loop.

A real registered service now handles csrng cmd 0 with the operating
system's CSPRNG: BCryptGenRandom on Windows and /dev/urandom on Unix.
It fills B/C output buffers and reports error when the descriptor is
invalid or the OS request fails. It logs the first three successful
calls only. This fixes the bogus stub, **not** the guest TLS allocator;
both experimental bootstrap variables are still required for the
next controlled first-boot comparison, never for a production release.

Retest after an incremental link_probe.py --jobs 2 with the same AOT
cache ID. Check for [csrng] filled ..., further game-service logs,
and any new exception; no main/sdk/subsdk0 regeneration is needed.

**Critical content caveat:** the current test root's romfs junction
was incorrectly pointed at the ExeFS. The log served 38 files from
that junction; those are not validated Scarlet RomFS assets. Replace
the junction with an extracted, correctly merged base+update Scarlet
RomFS before drawing conclusions about game visuals or gameplay.
Do not use these diagnostic results as proof the game is playable.

## Next guest abort after csrng: btm:u object and SetTerminateResult

The next Windows log confirmed that csrng now fills 4 random bytes
instead of repeating 5,733 fake responses. The guest progressed until
btm:u cmd 0, followed immediately by application functions cmd 22
and svcBreak with a zero Result.

Verified Horizon IPC contracts:
- btm:u cmd 0 is GetCore and must return IBtmUserCore (an IPC object).
  The former generic stub returned no object while claiming success.
- IApplicationFunctions cmd 22 is SetTerminateResult (u32), not the
  failure's origin. Reporting Result 0 does not diagnose the cause.

New btm:u implementation returns an actual IBtmUserCore object, an
unsignalled event and valid success flag for its BLE event acquisitions,
and zero discovered devices for supported query commands. It does not
emulate BLE hardware; unsupported commands now return an error rather
than silent success. The applet service logs SetTerminateResult and
its input value, without swallowing the guest's own abort.

Build the **runtime only**, with the existing AOT cache:
  py -3 tools/scarlet/link_probe.py --exefs "D:\Pokemon Scarlet\base=update" --cache-id eb6deb908752b9c6 --jobs 2

To compare the new startup trace, temporarily enable
SCARLET_EARLY_TLS_PROBE=1 and SCARLET_BOOTSTRAP_ALLOCATOR=1, and
keep SCARLET_MAIN_INIT_FIRST unset. The two TLS/allocator probes are
not production-ready.

The test RomFS junction still targets ExeFS (38 files); never treat
those reads as evidence that Scarlet's actual assets are mounted.
Use correctly merged 4.0.0 RomFS before the next real game-content test.

## 2026-10-29: first presented frames; fix test RomFS before judging gameplay

The next local Windows trace with corrected btm:u reached shader pipelines,
NVN presents and at least frame 80 with no guest abort. The profiler
reported around 13.9-14.7 fps during shader-heavy startup, ~483-514
draws, ~2,325-2,740 passes and 372-443 flushes in selected frames.
This verifies real guest rendering calls but **not yet valid Scarlet
graphics or playable game content**. The test process was explicitly
terminated by the PowerShell harness after 15 s, so no later exit
or crash should be inferred.

The user's test link still points to the merged ExeFS:
  scarlet-boot-test/romfs -> D:/Pokemon Scarlet/base=update

That folder has 38 files, including executable modules, NOT the
Scarlet game's resource RomFS. The host's virtual RomFS image builder
happily indexed these unrelated files, causing misleading graphics
and filesystem experiments. Fix this before investigating blank or
incorrect visuals. Do **not** copy gigabytes of data into the
Scarlet-Recomp build tree or rerun the AOT.

A safe Windows PowerShell helper is available:

1. In D:/Scarlet-Recomp run:
   .\tools\scarlet\romfs_link.ps1
   It lists possible extracted RomFS folder paths, without changing
   anything.
2. Once a real extracted and *correctly base+update 4.0.0 merged*
   RomFS folder is available:
   .\tools\scarlet\romfs_link.ps1 -Candidate "D:\REAL\RomFS"
   This validates a plausible folder and rejects ExeFS.
3. If valid, run the same command with -Apply.
   It replaces **only the test junction**, keeping original game files.

The helper does **not** extract or merge NS(P/X) content and cannot
prove update version from the folder alone. A raw romfs.bin file
requires a separate setup: the inherited runtime accepts a
romfs.bin next to exefs, but the junction helper only handles folders.
Inspect the actual extracted base/update data before choosing a source.

Once RomFS is correct, enable LARECOMP_LOG_FILES=1 for the next
controlled 15-30 s boot so the log shows real asset paths. Report
whether the displayed frames show the correct Scarlet image; do not
infer it from frame counters alone. The early TLS and allocator
environment switches remain diagnostic-only and lack correct
guest-heap lifecycle/free semantics.

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
