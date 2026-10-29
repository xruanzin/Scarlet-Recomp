#!/usr/bin/env python3
"""Compile Scarlet 4.0.0 AOT chunks into a distinct, content-addressed build cache.

This builds only translated game object files, NOT the game/runtime executable.
Invoke from Windows MSYS2 UCRT64 with make, clang and the tools venv installed.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from preflight import inspect

ROOT = Path(__file__).resolve().parents[2]
# Changes to these files may change emitted instructions or output ABI.
AOT_TOOLS = [
    "tools/gen.py", "tools/nso.py", "tools/lifter.py", "tools/analyze.py",
    "tools/passes.py", "tools/flagfuse.py", "tools/regpromote.py",
    "tools/simd_c.py", "tools/za_patches.py",
    "tools/scarlet/preflight.py", "runtime/hle/hle_symbols.txt",
    "runtime/cpu.h", "runtime/simd.h", "runtime/simd_fp.h",
    "tools/gamelib_entry.c", "Makefile",
]
# Fixed defaults; changing flags must change cache keys instead of silently
# using stale object files. This option is intentionally conservative.
AOT_FLAGS = ("GENOPT=-O1", "GENARCH=-march=x86-64-v3")


def fingerprint(exefs):
    digest = hashlib.sha256()
    files = [exefs / "main", exefs / "sdk", exefs / "main.npdm"]
    files += sorted(exefs.glob("subsdk*"))
    files += [ROOT / file for file in AOT_TOOLS]
    for file in files:
        if not file.is_file():
            raise ValueError(f"Missing AOT fingerprint input: {file}")
        digest.update(str(file.relative_to(exefs) if file.parent == exefs else file.relative_to(ROOT)).encode())
        with file.open("rb") as source:
            while True:
                block = source.read(4 * 1024 * 1024)
                if not block:
                    break
                digest.update(block)
    digest.update((";".join(AOT_FLAGS) + ";x86_64-windows;scarlet-4.0.0").encode())
    return digest.hexdigest()


def make_cmd(target, gen, build, jobs, exefs=None):
    cmd = ["make", f"-j{jobs}", f"GEN={gen}", f"B={build}", *AOT_FLAGS]
    if exefs is not None:
        cmd.append(f"SCARLET_EXEFS={exefs}")
    cmd.append(target)
    return cmd


def run_logged(cmd, log_file):
    print("+ " + " ".join(str(s) for s in cmd), flush=True)
    with log_file.open("a", encoding="utf-8") as log:
        log.write("\nCOMMAND: " + repr(cmd) + "\n")
        try:
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    encoding="utf-8", errors="replace")
        except OSError as exc:
            raise RuntimeError(f"Cannot execute {cmd[0]}: {exc}") from exc
        for line in proc.stdout:
            print(line, end="", flush=True)
            log.write(line)
        rc = proc.wait()
    if rc:
        raise RuntimeError(f"{cmd[-1]} failed with exit code {rc}; see {log_file}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True, type=Path, help="D:/Pokemon Scarlet/Extracted/Base")
    p.add_argument("--update-nsp", type=Path, help="For index validation, not extraction")
    p.add_argument("--update-exefs", type=Path, help="Decrypted ExeFS from the update Program NCA")
    p.add_argument("--jobs", type=int, default=4, help="Limit parallel clang jobs (default 4)")
    p.add_argument("--preflight-only", action="store_true")
    a = p.parse_args(argv)
    if not 1 <= a.jobs <= 32:
        p.error("--jobs must be from 1 to 32")
    result = inspect(a.base, a.update_exefs, a.update_nsp)
    for warning in result["warnings"]:
        print("WARNING:", warning)
    if not result["ready_for_aot"]:
        for error in result["errors"]:
            print("ERROR:", error, file=sys.stderr)
        print("AOT blocked. Never use the ZA launcher with these game files.", file=sys.stderr)
        return 2
    exefs = Path(result["selected_exefs"])
    print(f"Verified candidate Scarlet 4.0.0 main NSO: {result['selected_build_id']}")
    if a.preflight_only:
        return 0
    try:
        stamp = fingerprint(exefs)
        gen = f"generated-scarlet/{stamp[:16]}"
        build = f"build/scarlet/{stamp[:16]}"
        output = ROOT / build
        output.mkdir(parents=True, exist_ok=True)
        log = output / "aot-build.log"
        done = output / "aot-complete.json"
        if done.exists():
            saved = json.loads(done.read_text(encoding="utf-8"))
            if saved.get("fingerprint") == stamp and (output / "obj/main/main_table.o").is_file() and (output / "obj/sdk/sdk_table.o").is_file():
                print(f"AOT cache hit; checking incremental objects: {output}")
                run_logged(make_cmd("gen-objs", gen, build, a.jobs), log)
                return 0
        run_logged(make_cmd("gen-scarlet", gen, build, 1, str(exefs)), log)
        run_logged(make_cmd("gen-objs", gen, build, a.jobs), log)
        meta = {
            "fingerprint": stamp, "game": "Pokemon Scarlet", "version": "4.0.0",
            "main_build_id": result["selected_build_id"],
            "generated_dir": gen, "objects_dir": build,
            "runtime_linked": False, "gameplay_validated": False,
            "notice": "Translated AOT objects only; a Scarlet-specific kernel/renderer boot remains.",
        }
        done.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"AOT object compilation complete: {output}")
        print("NOT PLAYABLE YET: runtime/loader/service/GPU Scarlet adaptation not validated.")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
