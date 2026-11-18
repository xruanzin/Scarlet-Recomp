#!/usr/bin/env python3
"""Add Scarlet 4.0.0 subsdk0 AOT to an already completed main/sdk cache.

This deliberately does NOT invoke the full build_aot.py fingerprint path:
the user's 1500+ previously compiled objects must be reused.  The base
cache is identified by its successful aot-complete.json and main build ID.
No game bytes, keys or generated C are committed.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from build_aot import ROOT, AOT_FLAGS, make_cmd, run_logged
from preflight import KNOWN_MAIN_PREFIXES, exefs_info, nso_build_id

CACHE_ID = re.compile(r"^[0-9a-f]{16}$")
SUBSDK_BASE = "0x7010000000"


def existing_cache(cache_id, expected_build_id):
    if not CACHE_ID.fullmatch(cache_id):
        raise ValueError("Cache ID must be 16 lower-case hexadecimal digits")
    generated = ROOT / "generated-scarlet" / cache_id
    build = ROOT / "build" / "scarlet" / cache_id
    done = build / "aot-complete.json"
    if not done.is_file():
        raise ValueError(f"main/sdk AOT must complete first (missing {done})")
    meta = json.loads(done.read_text(encoding="utf-8"))
    if meta.get("game") != "Pokemon Scarlet" or meta.get("version") != "4.0.0":
        raise ValueError("Cache metadata is not for Scarlet 4.0.0")
    if meta.get("main_build_id") != expected_build_id:
        raise ValueError("Cache main build ID does not match the update ExeFS")
    if not (build / "obj" / "main" / "main_table.o").is_file():
        raise ValueError("Main AOT objects are incomplete")
    if not (build / "obj" / "sdk" / "sdk_table.o").is_file():
        raise ValueError("SDK AOT objects are incomplete")
    if not (generated / "main" / "main_build_id.txt").is_file():
        raise ValueError("Generated main build ID marker is missing")
    if (generated / "main" / "main_build_id.txt").read_text().strip().lower()[:16] != expected_build_id[:16]:
        raise ValueError("Generated main was built from a different NSO")
    return generated, build


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exefs", type=Path, required=True, help="Merged 4.0.0 ExeFS root; contains main, sdk, subsdk0")
    ap.add_argument("--cache-id", required=True, help="Existing completed main/sdk AOT cache (16 hex characters)")
    ap.add_argument("--jobs", type=int, default=2, help="Parallel object compilation (default: 2)")
    ap.add_argument("--check-only", action="store_true", help="Only check inputs and existing AOT cache")
    args = ap.parse_args(argv)
    if not 1 <= args.jobs <= 8:
        ap.error("--jobs must be between 1 and 8 (limited to avoid running out of RAM)")
    try:
        info = exefs_info(args.exefs)
        if info["recognized_version"] != "4.0.0":
            raise ValueError("Expected Scarlet main 4.0.0, got " + info["main_build_id"][:16])
        if "subsdk0" not in info["subsdk_modules"]:
            raise ValueError("The merged ExeFS is missing subsdk0")
        exefs = Path(info["exefs"])
        sub_build_id = nso_build_id(exefs / "subsdk0")
        generated, build = existing_cache(args.cache_id, info["main_build_id"])
        print(f"Scarlet main 4.0.0: {info['main_build_id'][:16]}")
        print(f"subsdk0 build ID: {sub_build_id[:16]}")
        print(f"Reusing main/sdk objects at: {build / 'obj'}")
        if args.check_only:
            print("READY: existing AOT cache can be extended without regenerating main/sdk.")
            return 0
        log = build / "subsdk0-build.log"
        stamp = build / "subsdk0-complete.json"
        sub_obj = build / "obj" / "subsdk0" / "subsdk0_table.o"
        entry_obj = build / "obj" / "tools" / "gamelib_entry.o"
        if stamp.is_file() and sub_obj.is_file() and entry_obj.is_file():
            old = json.loads(stamp.read_text(encoding="utf-8"))
            if old.get("subsdk0_build_id") == sub_build_id and old.get("cache_id") == args.cache_id:
                print("subsdk0 AOT already completed in this cache.")
                return 0
        print("Generating ONLY subsdk0 (main/sdk outputs will not be rewritten).", flush=True)
        run_logged(make_cmd("gen-scarlet-submodules", str(generated.relative_to(ROOT)).replace("\\", "/"),
                            str(build.relative_to(ROOT)).replace("\\", "/"), 1, str(exefs)), log)
        print("Compiling missing subsdk0 objects and updating AOT table entry.", flush=True)
        cmd = make_cmd("gen-objs", str(generated.relative_to(ROOT)).replace("\\", "/"),
                       str(build.relative_to(ROOT)).replace("\\", "/"), args.jobs)
        cmd.insert(-1, "SCARLET_AOT=1")
        run_logged(cmd, log)
        if not sub_obj.is_file() or not entry_obj.is_file():
            raise RuntimeError("The subsdk0 table or game library entry object was not produced")
        stamp.write_text(json.dumps({
            "cache_id": args.cache_id, "main_build_id": info["main_build_id"],
            "subsdk0_build_id": sub_build_id, "guest_base": SUBSDK_BASE,
            "subsdk0_aot_objects": True, "scarlet_runtime_linked": False,
            "gameplay_validated": False,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"subsdk0 AOT complete: {sub_obj}")
        print("Runtime code changed on GitHub; no native Scarlet executable/gameplay is validated yet.")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
