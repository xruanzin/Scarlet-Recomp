#!/usr/bin/env python3
"""Local-only Scarlet intro stand-up AOT source audit.

Reads already generated C; writes a bounded text report.
No NSO/NSP/DLL/game files are modified or uploaded.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

DEFAULT_ROOT = Path("generated-scarlet/eb6deb908752b9c6/main")
TARGETS = (
    "f_7000ccdeac",  # baseline function containing the obj+0x510 stores
    "f_700176101c",  # Fl4sh patched positive-Y compensation path
    "f_7000cce39c",  # adjacent vector routine; NOT the obj+0x510 producer
    "f_7000cce248",  # nearby AOT function analyzed by Codex
    "f_700343c280",  # previously observed call-site
)
TOKENS = (
    "0x510ull", "0x510", "0x438f000", "0x438f010",
    "f_700176101c(", "f_7000cce39c(", "f_7000cce248(",
    "f_700343c280(",
)
DECL = re.compile(r"^\s*(?:static\s+)?void\s+(f_[0-9a-f]+)\s*\(Cpu\s*\*\s*c\s*\)\s*\{")

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--out", type=Path, default=Path("build/intro-standup-aot-audit.txt"))
    ap.add_argument("--dll", type=Path, help="Actual experimental DLL (read-only native audit)")
    ap.add_argument("--baseline-dll", type=Path, help="Actual baseline DLL (read-only native audit)")
    ap.add_argument("--objdump", default="C:/msys64/ucrt64/bin/objdump.exe")
    args = ap.parse_args()
    root = args.root
    if not root.is_dir():
        ap.error(f"generated C folder not found: {root}")
    files = sorted(root.glob("main_*.c"))
    if not files:
        ap.error(f"no main_*.c found in {root}")
    result: list[str] = [
        "# Scarlet 4.0.0 — stand-up animation AOT audit",
        f"# Source root: {root}",
        f"# C translation units found: {len(files)}",
        "# Local-only excerpts: generated source not copied to GitHub.",
        "# Inspect the standing-up scripted animation, not the idle/spawn position.",
    ]
    found: set[str] = set()
    all_refs: dict[str, list[str]] = {t: [] for t in TARGETS}
    for path in files:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        defs = [(i, m.group(1)) for i, line in enumerate(lines) if (m := DECL.match(line))]
        ends = {i: defs[j + 1][0] if j + 1 < len(defs) else len(lines)
                for j, (i, _) in enumerate(defs)}
        for start, name in defs:
            if name not in TARGETS or name in found:
                continue
            found.add(name)
            end = ends[start]
            result.append(f"\n## {name} — {path.name}:{start + 1}-{end}")
            # Focus on the entry, return and writes, plus 20 lines around critical operations.
            indices: set[int] = set(range(start, min(end, start + 45)))
            for i in range(start, end):
                if any(tok.lower() in lines[i].lower() for tok in TOKENS):
                    indices.update(range(max(start, i - 12), min(end, i + 16)))
            ordered = sorted(indices)
            if len(ordered) > 420:
                ordered = ordered[:420]
                result.append("# NOTE: excerpt capped at 420 lines")
            last = -2
            for i in ordered:
                if i != last + 1:
                    result.append("  ...")
                result.append(f"{i + 1:>7}: {lines[i]}")
                last = i
        for i, line in enumerate(lines):
            for target in TARGETS:
                if target + "(" in line:
                    if len(all_refs[target]) < 35:
                        all_refs[target].append(f"{path.name}:{i + 1}: {line.strip()[:180]}")
    result.append("\n## References and potential callers")
    for target in TARGETS:
        result.append(f"\n### {target}")
        result.append(f"definition found: {target in found}")
        result.extend(all_refs[target] or ["(no direct C reference found)"])
    result.append("\n## Coverage limits")
    result.append("Generated C is not proof of the loaded DLL variant. Missing definitions may be split blocks.")
    result.append("No execution trace: this audit cannot identify the first incorrect player transform.")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for label, dll in (("experimental", args.dll), ("baseline", args.baseline_dll)):
        if dll is None:
            continue
        if not dll.is_file():
            ap.error(f"DLL missing: {dll}")
        for target in TARGETS:
            proc = subprocess.run([args.objdump, "-d", "--disassemble=" + target, str(dll)],
                                  capture_output=True, text=True, check=True, timeout=90)
            output = args.out.parent / f"{label}-{target}.asm"
            output.write_text(proc.stdout, encoding="utf-8")
            present = f"<{target}>:" in proc.stdout
            result.append(f"{label} {target}: native symbol found={present}; {output.name}")
    args.out.write_text("\n".join(result) + "\n", encoding="utf-8")
    print(f"Audit generated: {args.out}")
    print("Functions found: " + ", ".join(sorted(found) or ["none"]))
    print(f"Output size: {args.out.stat().st_size} bytes")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
