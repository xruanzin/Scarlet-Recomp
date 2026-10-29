#!/usr/bin/env python3
"""Validate local Pokémon Scarlet ExeFS before any AOT or runtime work.

This reads NSO headers and NSP/PFS0 container metadata; it never decrypts NCAs.
Version labels are provisional fingerprints obtained from project boot logs.
"""
import argparse
import json
import struct
import sys
from pathlib import Path

# Known 16-hex-character main NSO build ID prefixes from Scarlet project logs.
# Do not equate an NSP filename or PFS0 header with proof of an update version.
KNOWN_MAIN_PREFIXES = {
    "1.0.0": "ca44e7dd62e61a2a",
    "4.0.0": "421c5411b487eb4d",
}


def exefs_at(path):
    path = Path(path)
    return path / "exefs" if (path / "exefs").is_dir() else path


def nso_build_id(file):
    with open(file, "rb") as f:
        header = f.read(0x60)
    if len(header) < 0x60 or header[:4] != b"NSO0":
        raise ValueError(f"{file}: not a valid NSO0 header")
    build_id = header[0x40:0x60].hex()
    if not any(header[0x40:0x60]):
        raise ValueError(f"{file}: NSO build ID is empty")
    return build_id


def exefs_info(path):
    exefs = exefs_at(path)
    if not exefs.is_dir():
        raise ValueError(f"ExeFS folder does not exist: {exefs}")
    missing = [name for name in ("main", "sdk", "main.npdm") if not (exefs / name).is_file()]
    if missing:
        raise ValueError(f"{exefs}: missing required file(s): {', '.join(missing)}")
    main_id = nso_build_id(exefs / "main")
    sdk_id = nso_build_id(exefs / "sdk")
    modules = sorted(p.name for p in exefs.iterdir() if p.is_file() and p.name.startswith("subsdk"))
    versions = [v for v, prefix in KNOWN_MAIN_PREFIXES.items() if main_id.startswith(prefix)]
    return {
        "exefs": str(exefs.resolve()),
        "main_build_id": main_id,
        "sdk_build_id": sdk_id,
        "recognized_version": versions[0] if versions else None,
        "subsdk_modules": modules,
    }


def nsp_info(path):
    """Read only the PFS0 index, not the potentially huge encrypted NCA data."""
    path = Path(path)
    with path.open("rb") as f:
        hdr = f.read(16)
        if len(hdr) != 16 or hdr[:4] != b"PFS0":
            raise ValueError(f"{path}: not an NSP PFS0 container")
        n, string_bytes = struct.unpack_from("<II", hdr, 4)
        if not 1 <= n <= 8192 or string_bytes > 32 * 1024 * 1024:
            raise ValueError(f"{path}: invalid NSP index dimensions")
        index_len = n * 24 + string_bytes
        if 16 + index_len > path.stat().st_size:
            raise ValueError(f"{path}: truncated NSP index")
        entries = f.read(n * 24)
        strings = f.read(string_bytes)
    if len(entries) != n * 24 or len(strings) != string_bytes:
        raise ValueError(f"{path}: truncated PFS0 directory")
    names = []
    data_start = 16 + index_len
    total = path.stat().st_size
    for i in range(n):
        offset, length, str_off, _ = struct.unpack_from("<QQII", entries, i * 24)
        if str_off >= len(strings):
            raise ValueError(f"{path}: bad filename index")
        end = strings.find(b"\0", str_off)
        if end < 0:
            raise ValueError(f"{path}: unterminated filename")
        if offset > total - data_start or length > total - data_start - offset:
            raise ValueError(f"{path}: PFS0 entry exceeds NSP size")
        names.append(strings[str_off:end].decode("utf-8", errors="replace"))
    ncas = [name for name in names if name.lower().endswith(".nca")]
    return {
        "path": str(path.resolve()),
        "pfs0_valid": True,
        "nca_count": len(ncas),
        "ticket_count": sum(name.lower().endswith(".tik") for name in names),
        "version_verified": False,
    }


def inspect(base, update_exefs=None, update_nsp=None):
    report = {"target": "Pokemon Scarlet 4.0.0", "ready_for_aot": False, "errors": [], "warnings": []}
    try:
        report["base"] = exefs_info(base)
    except (OSError, ValueError) as exc:
        report["errors"].append(str(exc))
    if update_nsp is not None:
        try:
            report["update_nsp"] = nsp_info(update_nsp)
            report["warnings"].append(
                "NSP/PFS0 validation does not decrypt NCAs or prove the update version."
            )
        except (OSError, ValueError) as exc:
            report["errors"].append(str(exc))
    if update_exefs is not None:
        try:
            report["update"] = exefs_info(update_exefs)
        except (OSError, ValueError) as exc:
            report["errors"].append(str(exc))
    selected = report.get("update") or report.get("base")
    if selected:
        report["selected_exefs"] = selected["exefs"]
        report["selected_build_id"] = selected["main_build_id"]
        if selected["recognized_version"] != "4.0.0":
            report["errors"].append(
                "The selected main NSO is not the known Scarlet 4.0.0 build "
                f"(got {selected['main_build_id'][:16]}; expected "
                f"{KNOWN_MAIN_PREFIXES['4.0.0']}). Extract the UPDATE Program NCA ExeFS "
                "with your own keys and supply --update-exefs; the base game's ExeFS "
                "cannot be used to claim a 4.0.0 AOT build."
            )
        if selected["subsdk_modules"]:
            report["warnings"].append(
                "Extra subsdk modules found; the existing runtime loads only main/sdk. "
                "Module relocation and AOT coverage must be extended before gameplay."
            )
    if "update" in report:
        report["warnings"].append(
            "Updated RomFS layering/patch merge is not implemented; updated ExeFS alone "
            "does not produce a playable 4.0.0 port."
        )
    report["ready_for_aot"] = not report["errors"] and selected is not None
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True, type=Path, help="Base extracted root or ExeFS directory")
    ap.add_argument("--update-nsp", type=Path, help="Own update NSP, checked as PFS0 only")
    ap.add_argument("--update-exefs", type=Path, help="Updated *decrypted* ExeFS root or directory")
    ap.add_argument("--json", action="store_true", help="Output a structured local report")
    a = ap.parse_args(argv)
    report = inspect(a.base, a.update_exefs, a.update_nsp)
    if a.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("Scarlet 4.0.0 ExeFS preflight")
        for label in ("base", "update"):
            if label in report:
                info = report[label]
                print(f"  {label}: {info['recognized_version'] or 'unknown'} "
                      f"main={info['main_build_id'][:16]} sdk={info['sdk_build_id'][:16]}")
        if "update_nsp" in report:
            print(f"  NSP: {report['update_nsp']['nca_count']} NCAs; "
                  "encrypted contents/version not verified")
        for msg in report["warnings"]:
            print(f"  WARNING: {msg}")
        for msg in report["errors"]:
            print(f"  ERROR: {msg}", file=sys.stderr)
        print("  AOT input: READY" if report["ready_for_aot"] else "  AOT input: BLOCKED")
    return 0 if report["ready_for_aot"] else 2


if __name__ == "__main__":
    sys.exit(main())
