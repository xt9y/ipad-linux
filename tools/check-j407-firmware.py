#!/usr/bin/env python3
"""Inspect a local Linux firmware tree for J407 BCM4387 candidates.

This tool does not download, extract, or redistribute firmware. It only reports
whether a user-supplied firmware tree contains filenames which current Linux
would consider for the J407 BCM4387C2 Wi-Fi/Bluetooth devices.
"""

from __future__ import annotations

import argparse
import fnmatch
import pathlib
import sys

BOARD_TYPE = "apple,lycheea"
WIFI_BASE = "brcmfmac4387c2-pcie"


class Requirement:
    def __init__(self, name: str, patterns: tuple[str, ...], required: bool = True):
        self.name = name
        self.patterns = patterns
        self.required = required


REQUIREMENTS = (
    Requirement(
        "Wi-Fi firmware",
        (
            f"brcm/{WIFI_BASE}.{BOARD_TYPE}.bin",
            f"brcm/{WIFI_BASE}.bin",
        ),
    ),
    Requirement(
        "Wi-Fi NVRAM",
        (
            f"brcm/{WIFI_BASE}.{BOARD_TYPE}.txt",
            f"brcm/{WIFI_BASE}.{BOARD_TYPE}-*.txt",
            f"brcm/{WIFI_BASE}.txt",
        ),
    ),
    Requirement(
        "Wi-Fi CLM regulatory blob",
        (
            f"brcm/{WIFI_BASE}.{BOARD_TYPE}.clm_blob",
            f"brcm/{WIFI_BASE}.clm_blob",
        ),
        required=False,
    ),
    Requirement(
        "Wi-Fi TX capability blob",
        (
            f"brcm/{WIFI_BASE}.{BOARD_TYPE}.txcap_blob",
            f"brcm/{WIFI_BASE}.txcap_blob",
        ),
        required=False,
    ),
    Requirement(
        "Bluetooth firmware",
        (
            f"brcm/brcmbt4387*-{BOARD_TYPE}-*.bin",
            f"brcm/brcmbt4387*-{BOARD_TYPE}.bin",
        ),
    ),
    Requirement(
        "Bluetooth PTB",
        (
            f"brcm/brcmbt4387*-{BOARD_TYPE}-*.ptb",
            f"brcm/brcmbt4387*-{BOARD_TYPE}.ptb",
        ),
        required=False,
    ),
)


def relative_files(root: pathlib.Path) -> list[str]:
    files: list[str] = []
    for path in root.rglob("*"):
        if path.is_file():
            files.append(path.relative_to(root).as_posix())
    return sorted(files)


def matches(files: list[str], patterns: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for filename in files:
        if any(fnmatch.fnmatchcase(filename, pattern) for pattern in patterns):
            found.append(filename)
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware_root", type=pathlib.Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit nonzero when a required firmware class is missing",
    )
    args = parser.parse_args()

    if not args.firmware_root.is_dir():
        print(f"not a directory: {args.firmware_root}", file=sys.stderr)
        return 2

    files = relative_files(args.firmware_root)
    required_missing = 0

    print(f"J407 board type: {BOARD_TYPE}")
    print(f"files scanned: {len(files)}")

    for requirement in REQUIREMENTS:
        found = matches(files, requirement.patterns)
        state = "FOUND" if found else ("MISSING" if requirement.required else "optional-missing")
        print(f"\n[{state}] {requirement.name}")
        for pattern in requirement.patterns:
            print(f"  pattern: {pattern}")
        for filename in found:
            print(f"  match:   {filename}")

        if requirement.required and not found:
            required_missing += 1

    print(f"\nrequired classes missing: {required_missing}")
    if args.strict and required_missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
