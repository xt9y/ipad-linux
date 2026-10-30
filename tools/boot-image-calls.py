#!/usr/bin/env python3
"""BL-edge callgraph for ARM64 boot payloads.

Collects unconditional call edges (bl) and pacibsp prologue positions
(function starts) from a decoded code region, then answers caller/callee
questions: which functions reach a routine of interest, which routines a
function reaches, and which routines are called most often. This is the
control-flow complement to boot-image-xref's data-reference map. Text
only; operates on a raw payload stored outside the repository.
"""

from __future__ import annotations

import argparse
import bisect
import collections
import pathlib
import sys

import capstone

WORD = 4


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


def _target(op_str: str) -> int | None:
    text = op_str.strip()
    if not text.startswith("#"):
        return None
    try:
        return int(text[1:], 16)
    except ValueError:
        return None


def bl_edges(rows, code_end: int | None = None) -> list[tuple[int, int]]:
    """(caller_pc, target) for every unconditional bl edge."""
    edges = []
    for row in rows:
        if row.mnemonic != "bl":
            continue
        if code_end is not None and row.address >= code_end:
            continue
        target = _target(row.op_str)
        if target is None:
            continue
        edges.append((row.address, target))
    return edges


def function_starts(rows, code_end: int | None = None) -> list[int]:
    """Addresses of pacibsp prologues — function starts in a build
    compiled with ARMv8.3 pointer authentication prologues."""
    return sorted(
        row.address for row in rows
        if row.mnemonic == "pacibsp"
        and (code_end is None or row.address < code_end)
    )


def enclosing(pc: int, starts: list[int]) -> int | None:
    idx = bisect.bisect_right(starts, pc) - 1
    if idx < 0:
        return None
    return starts[idx]


def caller_functions(
    edges: list[tuple[int, int]], starts: list[int]
) -> dict[int, list[tuple[int, int]]]:
    """Group call edges by the pacibsp function that contains them."""
    NO_FN = -1
    grouped: dict[int, list[tuple[int, int]]] = collections.defaultdict(list)
    for edge in edges:
        fn = enclosing(edge[0], starts)
        grouped[NO_FN if fn is None else fn].append(edge)
    return dict(grouped)


def callees_of(edges: list[tuple[int, int]]) -> dict[int, int]:
    """Call-target -> number of call sites."""
    return dict(collections.Counter(target for _, target in edges))


def callers_of(edges: list[tuple[int, int]]) -> dict[int, int]:
    """Caller-pc count per target."""
    return dict(collections.Counter(pc for pc, _ in edges))


def reverse_levels(
    target: int,
    edges: list[tuple[int, int]],
    starts: list[int],
    max_level: int = 5,
) -> dict[int, set[int]]:
    """Functions that reach `target` through 1..max_level bl hops,
    grouped by hop distance (level 1 = direct callers)."""
    by_target: dict[int, list[tuple[int, int]]] = collections.defaultdict(list)
    for edge in edges:
        by_target[edge[1]].append(edge)
    frontier = {target}
    seen = {target}
    levels: dict[int, set[int]] = {}
    for level in range(1, max_level + 1):
        nxt: set[int] = set()
        for node in frontier:
            for pc, _ in by_target.get(node, ()):
                fn = enclosing(pc, starts)
                if fn is None or fn in seen:
                    continue
                seen.add(fn)
                nxt.add(fn)
        if not nxt:
            break
        levels[level] = nxt
        frontier = nxt
    return levels


def call_histogram(edges: list[tuple[int, int]], limit: int = 12):
    return collections.Counter(t for _, t in edges).most_common(limit)


def caller_histogram(edges, starts, limit: int = 12):
    grouped = caller_functions(edges, starts)
    return collections.Counter(
        {fn: len(sites) for fn, sites in grouped.items()}
    ).most_common(limit)


def _hex(value: int) -> str:
    return f"+0x{value:x}" if value >= 0 else f"-0x{-value:x}"


def analyze(data: bytes, code_end: int | None = None, limit: int = 12) -> str:
    rows = decode_rows(data)
    edges = bl_edges(rows, code_end)
    starts = function_starts(rows, code_end)
    out: list[str] = []
    out.append("## bl edge census")
    out.append(f"bl call edges: {len(edges)}")
    out.append("")
    out.append("## pacibsp function starts")
    out.append(f"pacibsp function starts: {len(starts)}")
    out.append("")
    out.append(f"## most-called routines (top {limit})")
    for target, count in call_histogram(edges, limit):
        out.append(f"  {_hex(target)}: {count}")
    out.append("")
    out.append(f"## most-calling functions (top {limit})")
    for fn, count in caller_histogram(edges, starts, limit):
        out.append(f"  {_hex(fn) if fn != -1 else '<no prologue>'}: {count}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=pathlib.Path,
                        help="raw image to analyze (kept outside the repo)")
    parser.add_argument("--code-end", type=lambda s: int(s, 0), default=None,
                        help="optional end offset of the code region")
    parser.add_argument("--callers-of", type=lambda s: int(s, 0), default=None,
                        help="report functions calling this target directly")
    parser.add_argument("--chain", type=lambda s: int(s, 0), default=None,
                        help="report bl caller levels reaching this target")
    parser.add_argument("--depth", type=int, default=5,
                        help="max caller levels for --chain (default 5)")
    parser.add_argument("--report", type=pathlib.Path, default=None,
                        help="write the full report to this file")
    args = parser.parse_args(argv)

    data = args.image.read_bytes()
    sections: list[str] = [analyze(data, args.code_end)]

    edges = bl_edges(decode_rows(data), args.code_end)
    starts = function_starts(decode_rows(data), args.code_end)
    if args.callers_of is not None:
        direct = [(pc, target) for pc, target in edges
                  if target == args.callers_of]
        fns = sorted({enclosing(pc, starts) for pc, _ in direct})
        lines = [f"## direct callers of {_hex(args.callers_of)}"]
        for fn in fns:
            lines.append(f"  fn {_hex(fn) if fn is not None else '<no prologue>'}")
        for pc, target in direct[:24]:
            lines.append(f"    site {_hex(pc)} -> {_hex(target)}")
        sections.append("\n".join(lines))
    if args.chain is not None:
        levels = reverse_levels(args.chain, edges, starts, args.depth)
        lines = [f"## caller levels reaching {_hex(args.chain)} "
                 f"(depth {args.depth})"]
        for level in sorted(levels):
            fns = sorted(levels[level])
            head = ", ".join(_hex(fn) for fn in fns[:16])
            more = f" (+{len(fns) - 16})" if len(fns) > 16 else ""
            lines.append(f"  level {level} ({len(fns)} fns): {head}{more}")
        sections.append("\n".join(lines))

    full = "\n\n".join(sections) + "\n"
    if args.report:
        args.report.write_text(full)
    else:
        print(full, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
