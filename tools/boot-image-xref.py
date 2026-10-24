#!/usr/bin/env python3
"""PC-relative data-reference map for J407 boot payloads.

Resolves ADRP (+ optional immediate-ADD) address-formation pairs and
literal LDRs — all PC-relative, so results are image offsets that do
NOT depend on the unknown load base — then maps the most-referenced
data pages to their resident strings. This is the first concrete
code-to-data cross-reference for the unified image and the stepping
stone toward handler-cluster mapping. Text-only; operates on a raw
payload stored outside the repository.
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys

import capstone

WORD = 4
STRING_RE = re.compile(rb"[A-Za-z][A-Za-z0-9_./-]{5,63}")
PAGE = 0x1000


def decode_rows(data: bytes):
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    md.detail = False
    rows = []
    offset = 0
    while offset < len(data):
        got = 0
        for insn in md.disasm(data[offset:], offset):
            rows.append(insn)
            got += insn.size
        offset += got if got else WORD
    return rows


def string_map(data: bytes) -> dict[int, str]:
    return {
        m.start(): m.group(0).decode("ascii", "replace")
        for m in STRING_RE.finditer(data)
    }


def resolve_adrp_add(rows) -> list[tuple[int, int]]:
    """Return (target_img_offset, adrp_pc) pairs. ADRP alone gives a
    page; a following ADD with the same dest register refines to the
    exact address (image-coordinate, load-base independent)."""
    pairs: list[tuple[int, int]] = []
    i = 0
    while i < len(rows):
        row = rows[i]
        if row.mnemonic == "adrp" and i + 1 < len(rows):
            nxt = rows[i + 1]
            try:
                reg = row.op_str.split(", ")[0]
                imm = int(row.op_str.split(", ")[1].lstrip("#"), 16)
            except (IndexError, ValueError):
                i += 1
                continue
            if nxt.op_str.startswith(reg + ", " + reg + ", #"):
                try:
                    a_imm = int(nxt.op_str.rsplit("#", 1)[1].split(",")[0].strip(), 16)
                except ValueError:
                    a_imm = 0
                pairs.append(((row.address & ~(PAGE - 1)) + imm + a_imm, row.address))
                i += 2
                continue
        i += 1
    return pairs


def count_literal_loads(rows) -> int:
    """LDR with an immediate (literal-pool fetch) — pointer-heavy code."""
    n = 0
    for row in rows:
        if row.mnemonic.startswith("ldr") and row.op_str.startswith(("x", "w")) \
                and ", #" in row.op_str:
            n += 1
    return n


def analyze(data: bytes) -> str:
    lines: list[str] = []
    try:
        rows = decode_rows(data)
    except Exception as exc:  # pragma: no cover
        return f"decode failed: {exc}"

    pairs = resolve_adrp_add(rows)
    pages = collections.Counter(target // PAGE for target, _ in pairs)
    strings = string_map(data)
    literals = count_literal_loads(rows)

    lines.append("## pc-relative data-reference map")
    lines.append(f"instructions decoded: {len(rows)}")
    lines.append(f"adrp(+add) data references resolved: {len(pairs)} "
                f"to {len(pages)} distinct target pages")
    lines.append(f"literal-pool LDR instructions: {literals} (pointer traffic "
                 "without resolved values — pool constants need the load base)")
    lines.append("")
    lines.append("top referenced pages with resident strings (candidates for "
                 "string/config tables and handler data):")
    for page, n in pages.most_common(20):
        base = page * PAGE
        residents = sorted(
            (strings[off] for off in strings if base <= off < base + PAGE),
            key=len, reverse=True)[:3]
        label = "; ".join(f'"{s}"' for s in residents) if residents else "(no strings)"
        lines.append(f"  page+0x{page:x}: {n:>4} refs  {label}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, default=None)
    args = parser.parse_args()
    data = args.image.read_bytes()
    report = analyze(data)
    if args.out:
        args.out.write_text(report)
        print(f"report -> {args.out}")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
