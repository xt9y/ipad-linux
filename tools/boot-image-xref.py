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


OF_INTEREST = (
    "getenv", "setenv", "boot-", "boot-command", "boot-stage", "boot-nonce",
    "debug-enabled", "secure-boot", "dfu", "dart-", "SysConfig",
    "DERDecode", "DART", "iBoot", "mBoot",
)


def interesting_strings(strings: dict[int, str], of_interest=OF_INTEREST):
    return {
        off: txt for off, txt in strings.items()
        if any(p in txt for p in of_interest)
    }


def reverse_index(pairs) -> dict[int, list[int]]:
    """target page -> referencing instruction PCs (image offsets)."""
    refs: dict[int, list[int]] = collections.defaultdict(list)
    for target, pc in pairs:
        refs[target // PAGE].append(pc)
    return refs


REGIONS = 0x4000  # 16 KiB code windows for the region usage map


def region_usage(pairs):
    """code region -> Counter of referenced data pages."""
    usage = collections.defaultdict(collections.Counter)
    for target, pc in pairs:
        usage[pc // REGIONS][target // PAGE] += 1
    return usage


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

    refs = reverse_index(pairs)
    interesting = interesting_strings(strings)
    if interesting:
        lines.append("")
        lines.append("## string-anchored references")
        lines.append("pages of interest that ADRP(+ADD) formation pairs target,")
        lines.append("with the referencing code pages (page-level attribution: a")
        lines.append("pair targets one address; residents of the same page are shown):")
        by_page = collections.defaultdict(list)
        for off, txt in interesting.items():
            by_page[off // PAGE].append((off, txt))
        for page in sorted(by_page, key=lambda p: -len(refs.get(p, [])))[:24]:
            residents = ", ".join(f'"{t}"' for _, t in sorted(by_page[page]))[:90]
            code_pages = sorted({pc for pc in refs.get(page, [])})
            shown = "; ".join(f"+0x{pc:x}" for pc in code_pages[:6])
            extra = f" (+{len(code_pages) - 6} more)" if len(code_pages) > 6 else ""
            lines.append(f'  page+0x{page:x}: {len(refs.get(page, [])):>3} refs from {shown}{extra}  strings: [{residents}]')

    usage = region_usage(pairs)
    if usage:
        lines.append("")
        lines.append("## code-region data-usage map")
        lines.append(f"16 KiB code windows -> their most-referenced data pages")
        pages_of_interest = {p for p in interesting}
        for region in sorted(usage)[:16]:
            top = usage[region].most_common(3)
            parts = []
            for page, n in top:
                anchor = ""
                if page in pages_of_interest:
                    resident = sorted(t for _, t in interesting.items()
                                      if _ // PAGE == page)[:1]
                    if resident:
                        anchor = f'("{";".join(resident)[:28]}")'
                parts.append(f"0x{page:x}:{n}{anchor}")
            lines.append(f"  code+0x{region * REGIONS:x}: {', '.join(parts)}")

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
