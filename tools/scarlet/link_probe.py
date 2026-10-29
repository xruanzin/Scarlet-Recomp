#!/usr/bin/env python3
"""Link an experimental Windows runtime + Scarlet AOT DLL using existing objects.

This is an opt-in LINK/BUILD probe, not a playable Scarlet port. It only
builds executables and does not launch the game or modify extracted assets.
The source runtime still contains ZA-specific code.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from build_aot import ROOT, AOT_FLAGS, run_logged
from extend_subsdk0 import existing_cache
from preflight import exefs_info, nso_build_id


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exefs", type=Path, required=True, help="Merged Pokemon Scarlet 4.0.0 ExeFS")
    p.add_argument("--cache-id", required=True, help="Existing completed AOT cache identifier")
    p.add_argument("--jobs", type=int, default=2)
    p.add_argument("--check-only", action="store_true")
    a = p.parse_args(argv)
    if not 1 <= a.jobs <= 4:
        p.error("jobs must be between 1 and 4 (RAM-conscious native link)")
    try:
        info = exefs_info(a.exefs)
        if info["recognized_version"] != "4.0.0":
            raise ValueError("Not Scarlet 4.0.0")
        if "subsdk0" not in info["subsdk_modules"]:
            raise ValueError("subsdk0 NSO is absent")
        gen, build = existing_cache(a.cache_id, info["main_build_id"])
        sub_stamp = build / "subsdk0-complete.json"
        if not sub_stamp.is_file():
            raise ValueError("First complete the incremental subsdk0 AOT extension")
        sub = json.loads(sub_stamp.read_text(encoding="utf-8"))
        if sub.get("cache_id") != a.cache_id or sub.get("main_build_id") != info["main_build_id"]:
            raise ValueError("subsdk0 cache ID differs from the main/sdk AOT")
        if sub.get("subsdk0_build_id") != nso_build_id(Path(info["exefs"]) / "subsdk0"):
            raise ValueError("subsdk0 compiled code and merged ExeFS are different")
        for mod in ("main", "sdk", "subsdk0"):
            if not (build / "obj" / mod / (mod + "_table.o")).is_file():
                raise ValueError(f"Missing table object for {mod}")
        if not (build / "obj" / "tools" / "gamelib_entry.o").is_file():
            raise ValueError("Missing AOT DLL entry point object")
        print("Verified main/sdk/subsdk0 AOT cache, preserving all existing objects.", flush=True)
        if a.check_only:
            print("READY for experimental link probe; no code will be compiled.")
            return 0
        if os.name != "nt":
            raise ValueError("Link probe is intended for Windows 11/MSYS2 UCRT64 only")
        print("Building the inherited Vulkan runtime and linking Scarlet AOT (not launching).", flush=True)
        cmd = [
            "make", f"-j{a.jobs}",
            f"GEN={gen.relative_to(ROOT).as_posix()}",
            f"B={build.relative_to(ROOT).as_posix()}",
            *AOT_FLAGS, "SCARLET_AOT=1", "all",
        ]
        run_logged(cmd, build / "scarlet-link.log")
        exe = build / "lasrecomp.exe"
        dll = build / "lasgame.dll"
        if not (exe.is_file() and dll.is_file() and (build / "lasgame.dll.id").is_file()):
            raise RuntimeError("Build returned success but executable or AOT DLL is missing")
        result = {
            "main_build_id": info["main_build_id"],
            "cache_id": a.cache_id,
            "runtime_executable": str(exe),
            "compiled_game_library": str(dll),
            "gameplay_validated": False,
            "runtime_is_scarlet_native": False,
            "warning": "Inherited ZA runtime was linked for diagnostics only; not a validated Scarlet boot.",
        }
        (build / "scarlet-link-complete.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("EXPERIMENTAL LINK COMPLETE: " + str(exe))
        print("Not yet playable; the inherited ZA runtime needs Scarlet startup/service adaptation.")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as e:
        print("ERROR:", e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
