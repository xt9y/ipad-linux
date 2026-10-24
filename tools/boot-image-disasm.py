#!/usr/bin/env python3
"""Address-base-free disassembly pass for J407 boot payloads.

Like tools/boot-image-recon.py this operates on a raw payload stored
OUTSIDE the repository and emits text only. Decodes the image with
Capstone (AArch64) and summarizes: coverage, mnemonic histogram,
system-register access surface, branch/BL landscape, and ADR(P)-cluster
pages (candidate string tables / handler clusters). All addresses are
reported as image offsets (load base unresolved by design; resolve is a
later, formally separate analysis step).
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import sys

import capstone

WORD = 4


def decode(data: bytes):
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    md.detail = False
    rows = []
    offset = 0
    # Capstone stops at the first undecodable word; restart past it so we
    # cover the whole blob (gap words are literal pools / bounds data).
    while offset < len(data):
        got = 0
        for insn in md.disasm(data[offset:], offset):
            rows.append(insn)
            got += insn.size
        if got == 0:
            offset += WORD
        else:
            offset += got
    return md, rows


def analyze(data: bytes) -> str:
    lines: list[str] = []
    try:
        _, rows = decode(data)
    except Exception as exc:  # pragma: no cover
        return f"decode failed: {exc}"

    total_words = len(data) // WORD
    decoded_words = len(rows)
    lines.append("## coverage")
    lines.append(f"image words: {total_words}, decoded instructions: {decoded_words}")
    if total_words:
        pct = 100.0 * decoded_words / total_words
        lines.append(f"decode coverage: {pct:.1f}% (rest = literal pools/bounds data)")

    hist = collections.Counter(row.mnemonic for row in rows)
    lines.append("")
    lines.append("## mnemonic histogram (top 24)")
    for mnem, n in hist.most_common(24):
        lines.append(f"  {n:>7} {mnem}")

    reg_lines = collections.Counter()
    for row in rows:
        if row.mnemonic in ("msr", "mrs"):
            ops = row.op_str.split(", ", 1)
            if len(ops) == 2:
                reg_lines[f"{row.mnemonic} {ops[1]}"] += 1
    lines.append("")
    lines.append("## system-register access surface (all)")
    for key, n in sorted(reg_lines.items())[:64]:
        lines.append(f"  {n:>5} {key}")

    bl_targets = collections.Counter()
    for row in rows:
        if row.mnemonic in ("bl", "blr"):
            bl_targets[row.op_str] += 1
    lines.append("")
    lines.append("## call landscape")
    lines.append(f"  bl/blr instructions: {sum(bl_targets.values())}")
    lines.append(f"  distinct bl targets: {len([t for t in bl_targets if t != '—'])}")

    adrp_pages = collections.Counter()
    for row in rows:
        if row.mnemonic in ("adr", "adrp"):
            # e.g. "x0, #0x1200" -> page-relative target bucket
            try:
                off = int(row.op_str.split(", ")[1].lstrip("#"), 16)
                adrp_pages[off // 0x1000] += 1
            except (IndexError, ValueError):
                pass
    lines.append("")
    lines.append("## adrp/adr page-cluster histogram (top 16, page-relative buckets)")
    for page, n in adrp_pages.most_common(16):
        lines.append(f"  {n:>5} page+0x{page:x}")

    movz_set = collections.Counter()
    for row in rows:
        if row.mnemonic == "movk":
            try:
                imm = row.op_str.split("#", 1)[1].split(",")[0].strip()
                movz_set[imm] += 1
            except IndexError:
                pass
    lines.append("")
    lines.append("## movk shift-histogram (top 16)")
    for imm, n in movz_set.most_common(16):
        lines.append(f"  {n:>5} {imm}")

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
