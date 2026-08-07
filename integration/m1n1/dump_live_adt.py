#!/usr/bin/env python3
"""Dump the live Apple Device Tree through an already-running m1n1 proxy.

Run this with m1n1's proxyclient directory on PYTHONPATH and M1N1DEVICE set.
The script deliberately uses ProxyUtils.get_adt(), which derives the physical
ADT address from Apple's boot arguments exactly as upstream m1n1 does.

This helper does not establish the initial m1n1 execution path and does not
modify target hardware state.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output",
        nargs="?",
        type=pathlib.Path,
        default=pathlib.Path("j407-live-adt.bin"),
        help="output path (default: j407-live-adt.bin)",
    )
    args = parser.parse_args()

    try:
        from m1n1.setup import u
    except Exception as exc:  # m1n1 prints connection diagnostics itself
        print(f"dump_live_adt: could not initialize m1n1 proxy: {exc}", file=sys.stderr)
        return 1

    try:
        data = bytes(u.get_adt())
    except Exception as exc:
        print(f"dump_live_adt: could not read ADT: {exc}", file=sys.stderr)
        return 1

    if len(data) < 8:
        print("dump_live_adt: ADT is unexpectedly small", file=sys.stderr)
        return 1

    try:
        args.output.write_bytes(data)
    except OSError as exc:
        print(f"dump_live_adt: {exc}", file=sys.stderr)
        return 1

    digest = hashlib.sha256(data).hexdigest()
    print(f"wrote {len(data)} bytes to {args.output}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
