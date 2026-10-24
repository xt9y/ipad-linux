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
    gaps = []
    udf_spans = []
    udf_start = None
    offset = 0
    # Capstone stops at the first undecodable word; restart past it so we
    # cover the whole blob (gap words are literal pools / bounds data).
    while offset < len(data):
        bank_start = offset
        got = 0
        for insn in md.disasm(data[offset:], offset):
            rows.append(insn)
            got += insn.size
            if insn.mnemonic == "udf":
                if udf_start is None:
                    udf_start = insn.address
            elif udf_start is not None:
                udf_spans.append((udf_start, insn.address))
                udf_start = None
        if got == 0:
            offset += WORD
        else:
            offset += got
        if got == 0:
            # Coalesce adjacent failing words into one gap span.
            if gaps and gaps[-1][1] == bank_start:
                gaps[-1] = (gaps[-1][0], offset)
            else:
                gaps.append((bank_start, offset))
            if udf_start is not None:
                udf_spans.append((udf_start, bank_start))
                udf_start = None
    if udf_start is not None:
        udf_spans.append((udf_start, offset))
    return md, rows, gaps, udf_spans


def address_family(value: int) -> str | None:
    """Classify an absolute-looking constant into known T8103 memory-map
    families (public Asahi/dtb knowledge).

    The image's data regions are full of packed 2x u32 config-table
    pairs, so the scan keys on the HIGH 32 bits: all real T8103
    physical addresses are < 2^40, making the high word the region
    selector. Packed pairs with a small non-address high word are
    rejected; DRAM hits additionally require 4 KiB page alignment.
    """
    if value < 0x100000000:
        return None
    high = value >> 32
    low = value & 0xFFFFFFFF
    if high == 0x8 and (low & 0xFFF) == 0:
        return "DRAM region (base 0x800000000)"
    if high == 0x2:
        return "peripherals/MMIO (base 0x200000000)"
    if high in (0x5, 0x6):
        return "upper MMIO/PCIe window"
    return None


def pool_constants(data: bytes, spans) -> list[tuple[int, int, str]]:
    """Extract 8-byte-aligned absolute-looking constants from data spans
    (undecoded gap words and long udf runs — the literal pools). A qword
    must lie fully inside a span; the all-ones sentinel is dropped.
    Returns (offset, value, family)."""
    out: list[tuple[int, int, str]] = []
    for start, end in spans:
        if end - start < 8:
            continue
        first = ((start + 7) // 8) * 8
        for off in range(first, end - 7, 8):
            value = int.from_bytes(data[off : off + 8], "little")
            if value == 0xFFFFFFFFFFFFFFFF:
                continue
            family = address_family(value)
            if family is not None:
                out.append((off, value, family))
    return out


def fourcc_tags(data: bytes):
    """Scan aligned words for `movz w?, #imm16` + `movk w?, #imm16,
    lsl #16` pairs building a printable 4-byte word (register-built
    word identifiers). Encoding-based (capstone 5 renames `movz` to
    `mov`), so this is matched on the raw instruction words:
      movz w?, hw=0  -> word & 0xFFE00000 == 0x52800000
      movk w?, hw=1  -> word & 0xFFE00000 == 0x72A00000
    Returns (tag_counter, first_site). Pairs over data regions decode
    spuriously; tags are candidates, not proven keys."""
    tags = collections.Counter()
    first_site: dict[str, int] = {}
    for off in range(0, max(0, len(data) - 7), 4):
        w1 = int.from_bytes(data[off : off + 4], "little")
        if w1 & 0xFFE00000 != 0x52800000:
            continue
        w2 = int.from_bytes(data[off + 4 : off + 8], "little")
        if w2 & 0xFFE00000 != 0x72A00000 or w1 & 0x1F != w2 & 0x1F:
            continue
        lo = (w1 >> 5) & 0xFFFF
        hi = (w2 >> 5) & 0xFFFF
        raw = ((hi << 16) | lo).to_bytes(4, "little")
        if all(0x20 <= c < 0x7F for c in raw):
            tag = raw.decode()
            tags[tag] += 1
            first_site.setdefault(tag, off)
    return tags, first_site


def analyze(data: bytes) -> str:
    lines: list[str] = []
    try:
        _, rows, gaps, udf_spans = decode(data)
    except Exception as exc:  # pragma: no cover
        return f"decode failed: {exc}"

    total_words = len(data) // WORD
    decoded_words = len(rows)
    lines.append("## coverage")
    lines.append(f"image words: {total_words}, decoded instructions: {decoded_words}")
    if total_words:
        pct = 100.0 * decoded_words / total_words
        lines.append(f"decode coverage: {pct:.1f}% (rest = literal pools/bounds data)")
    lines.append(f"  undecoded gap spans: {len(gaps)}, udf-run spans: {len(udf_spans)}")

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
    direct = sum(n for t, n in bl_targets.items() if t.startswith("#"))
    indirect = sum(n for t, n in bl_targets.items() if not t.startswith("#"))
    lines.append("")
    lines.append("## call landscape")
    lines.append(f"  bl/blr instructions: {sum(bl_targets.values())} (direct bl: {direct}, register-indirect: {indirect})")
    lines.append(f"  distinct direct bl targets: {sum(1 for t in bl_targets if t.startswith('#'))}")

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

    constants = pool_constants(data, sorted(gaps + udf_spans))
    fam_counts = collections.Counter(family for _, _, family in constants)
    lines.append("")
    lines.append("## literal-pool address-constant candidates (known families only)")
    lines.append(f"  scan spans (gaps + udf runs): {len(gaps) + len(udf_spans)}, address-like pool constants: {len(constants)}")
    for family, n in fam_counts.most_common():
        lines.append(f"  {n:>5} {family}")
    family_rank = {name: rank for rank, name in enumerate(fam_counts)}
    seen: set[int] = set()
    shown = 0
    for off, value, family in sorted(constants, key=lambda c: (family_rank[c[2]], c[0])):
        if value in seen:
            continue
        seen.add(value)
        lines.append(f"    0x{value:016x} @ +0x{off:x}  {family}")
        shown += 1
        if shown >= 32:
            lines.append("    ... (truncated at 32 unique values)")
            break

    tags, first_site = fourcc_tags(data)
    lines.append("")
    lines.append("## fourcc-style word tags (movz+movk w?, lsl #16, printable)")
    lines.append("  register-built printable word tags; pairs over data regions")
    lines.append("  decode spuriously - tags are candidates, not proven keys")
    lines.append(f"  distinct tags: {len(tags)}, occurrences: {sum(tags.values())}")
    for tag, n in sorted(tags.items(), key=lambda kv: (-kv[1], kv[0]))[:40]:
        lines.append(f"  {n:>5} \"{tag}\"  first +0x{first_site[tag]:x}")

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
