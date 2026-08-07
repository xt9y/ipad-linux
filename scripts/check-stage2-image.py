#!/usr/bin/env python3
"""Verify invariants of the relocatable flat diagnostic Stage 2 image."""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys


REQUIRED_SYMBOLS = (
    "__image_start",
    "__image_end",
    "__bss_start",
    "__bss_end",
    "__stack_bottom",
    "__stack_top",
)


def symbols(elf: pathlib.Path, nm: str) -> dict[str, int]:
    output = subprocess.check_output([nm, "-n", str(elf)], text=True)
    result: dict[str, int] = {}

    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        name = fields[-1]
        if name in REQUIRED_SYMBOLS:
            result[name] = int(fields[0], 16)

    missing = [name for name in REQUIRED_SYMBOLS if name not in result]
    if missing:
        raise ValueError("missing linker symbols: " + ", ".join(missing))
    return result


def check_relocations(elf: pathlib.Path, readelf: str) -> None:
    output = subprocess.check_output([readelf, "-r", str(elf)], text=True)
    if re.search(r"\bR_AARCH64_", output):
        raise ValueError("ELF contains AArch64 runtime relocations")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--elf", required=True, type=pathlib.Path)
    parser.add_argument("--bin", required=True, type=pathlib.Path)
    parser.add_argument("--nm", default="llvm-nm")
    parser.add_argument("--readelf", default="llvm-readelf")
    args = parser.parse_args()

    try:
        syms = symbols(args.elf, args.nm)
        check_relocations(args.elf, args.readelf)

        image_start = syms["__image_start"]
        image_end = syms["__image_end"]
        bss_start = syms["__bss_start"]
        bss_end = syms["__bss_end"]
        stack_bottom = syms["__stack_bottom"]
        stack_top = syms["__stack_top"]

        if image_start != 0:
            raise ValueError(f"image is not linked at zero: 0x{image_start:x}")
        if not (image_start <= bss_start <= bss_end <= stack_bottom < stack_top <= image_end):
            raise ValueError("invalid image/BSS/stack linker ordering")
        if stack_top - stack_bottom != 65536:
            raise ValueError(
                f"bootstrap stack is {stack_top - stack_bottom} bytes, expected 65536"
            )

        expected_size = image_end - image_start
        actual_size = args.bin.stat().st_size
        if actual_size != expected_size:
            raise ValueError(
                f"flat binary is {actual_size} bytes but linker image footprint is "
                f"{expected_size} bytes"
            )

        print(
            "Stage 2 image OK: "
            f"size=0x{actual_size:x} bss=0x{bss_end - bss_start:x} "
            f"stack=0x{stack_top - stack_bottom:x}"
        )
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"check-stage2-image: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
