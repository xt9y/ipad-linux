#!/usr/bin/env python3
"""Offline boot-image recon for J407 payloads.

Runs entirely on a *local raw payload* passed by path (the raw firmware
binaries are NOT part of this repository — they live outside it, e.g.
~/research/j407-bootchain/). Produces a text report suitable for
checking into docs/: sizes, digest prefixes, build tags, keyword
corpus and short-identifier frequency. No device access, no writes.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import pathlib
import re
import sys

MIN_LEN = 6
KEYWORDS = (
    "getenv", "setenv", "dfu", "usb", "dart", "uart", "pmgr", "secure",
    "srom", "spmi", "nand", "aes", "ed25519", "rsa", "heap", "task",
    "malloc", "boot", "debug", "patch", "killvoltage", "barrier", "ecid",
)

BUILD_RE = re.compile(rb"(mBoot|SecureROM|iBoot)-[0-9][0-9a-zA-Z.\-]{3,}")
ID_RE = re.compile(rb"[A-Za-z][A-Za-z0-9_./-]{5,63}")
SHORT_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,15}$")


def printable_strings(data: bytes) -> list[bytes]:
    out = []
    for m in ID_RE.finditer(data):
        out.append(m.group(0))
    return out


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    table = [0] * 256
    for b in data:
        table[b] += 1
    n = len(data)
    ent = 0.0
    for c in table:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return min(ent, 8.0)


def analyze(data: bytes) -> str:
    lines: list[str] = []
    lines.append("## header")
    lines.append(f"size: {len(data)} bytes")
    lines.append(f"sha256: {hashlib.sha256(data).hexdigest()[:16]} (prefix)")
    lines.append(f"first-32-bytes: {data[:32].hex()}")
    lines.append(f"tail-16-bytes: {data[-16:].hex()}")

    strings = printable_strings(data)
    unique = sorted(set(strings))
    lines.append("")
    lines.append("## strings")
    lines.append(f"total printable tokens: {len(strings)} (unique {len(unique)})")

    lines.append("")
    lines.append("## build identities")
    builds: list[str] = [m.group(0).decode() for m in BUILD_RE.finditer(data)]
    for b in sorted(set(builds))[:12]:
        lines.append(f"  {b}")

    lines.append("")
    lines.append("## keyword corpus")
    for kw in KEYWORDS:
        needle = re.compile(rb"(?<![A-Za-z0-9_])" + kw.encode() + rb"(?![A-Za-z0-9_])")
        hits = [s.decode() for s in unique if needle.search(s)]
        if hits:
            lines.append(f"  [{len(hits):>3}] {kw}: " + "; ".join(sorted(hits)[:24]))

    short_counts: dict[str, int] = {}
    for s in strings:
        try:
            txt = s.decode("ascii")
        except UnicodeDecodeError:
            continue
        if SHORT_ID_RE.match(txt):
            short_counts[txt] = short_counts.get(txt, 0) + 1
    frequent = sorted(short_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    top = [(name, n) for name, n in frequent if n >= 2][:60]
    lines.append("")
    lines.append("## short identifiers (frequency >= 2, top 60)")
    for name, n in top:
        lines.append(f"  {n:>3}x {name}")

    lines.append("")
    lines.append("## entropy (48 KiB windows)")
    window = 49152
    vals: list[float] = []
    for off in range(0, len(data), window):
        chunk = data[off : off + window]
        vals.append(shannon_entropy(chunk))
    if vals:
        hi = sum(v > 3.0 for v in vals)
        lines.append(f"  windows: {len(vals)} high-entropy(>3.0): {hi} low: {len(vals) - hi}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=pathlib.Path, help="path to a raw payload (outside the repo)")
    parser.add_argument("--out", type=pathlib.Path, default=None)
    args = parser.parse_args()

    data = args.image.read_bytes()
    report = analyze(data)

    if args.out:
        args.out.write_text(report)
        print(f"report -> {args.out}")
    else:
        sys.stdout.write(report)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
