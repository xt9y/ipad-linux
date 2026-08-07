#!/usr/bin/env python3
"""Validate a Linux Apple Z2/HBPP touchscreen firmware container.

This tool only reads a local file supplied by the user. It does not contain,
download or redistribute Apple firmware.
"""

from __future__ import annotations

import argparse
import pathlib
import struct
import sys

MAGIC = b"Z2FW"
VERSION = 1
LOAD_COMMAND_INIT_PAYLOAD = 0
LOAD_COMMAND_SEND_BLOB = 1
LOAD_COMMAND_SEND_CALIBRATION = 2


def align4(value: int) -> int:
    return (value + 3) & ~3


def validate(data: bytes) -> dict[str, int]:
    if len(data) < 8:
        raise ValueError("file is shorter than the Z2FW header")

    magic, version = struct.unpack_from("<4sI", data, 0)
    if magic != MAGIC:
        raise ValueError(f"bad magic {magic!r}; expected {MAGIC!r}")
    if version != VERSION:
        raise ValueError(f"unsupported Z2FW version {version}")

    offset = 8
    commands = 0
    init_payloads = 0
    blobs = 0
    calibrations = 0
    payload_bytes = 0

    while offset < len(data):
        if offset & 3:
            raise ValueError(f"command at unaligned offset 0x{offset:x}")
        if len(data) - offset < 8:
            raise ValueError(f"truncated command header at 0x{offset:x}")

        command, argument = struct.unpack_from("<II", data, offset)
        offset += 8
        commands += 1

        if command in (LOAD_COMMAND_INIT_PAYLOAD, LOAD_COMMAND_SEND_BLOB):
            size = argument
            if size > len(data) - offset:
                raise ValueError(
                    f"command {commands} payload overruns file: "
                    f"size=0x{size:x}, remaining=0x{len(data) - offset:x}"
                )

            payload_bytes += size
            if command == LOAD_COMMAND_INIT_PAYLOAD:
                init_payloads += 1
            else:
                blobs += 1

            offset += size
            padded = align4(offset)
            if padded > len(data):
                raise ValueError(f"truncated alignment padding after command {commands}")
            if any(data[offset:padded]):
                raise ValueError(f"non-zero alignment padding after command {commands}")
            offset = padded

        elif command == LOAD_COMMAND_SEND_CALIBRATION:
            # For this command the second u32 is the target address, not a size.
            calibrations += 1
        else:
            raise ValueError(f"unknown Z2FW command {command} at 0x{offset - 8:x}")

    if not commands:
        raise ValueError("container contains no firmware commands")

    return {
        "commands": commands,
        "init_payloads": init_payloads,
        "blobs": blobs,
        "calibrations": calibrations,
        "payload_bytes": payload_bytes,
        "file_bytes": len(data),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a locally extracted/converted Apple Z2FW touchscreen image"
    )
    parser.add_argument("firmware", type=pathlib.Path)
    parser.add_argument(
        "--require-init",
        action="store_true",
        help="fail unless at least one INIT_PAYLOAD command is present",
    )
    args = parser.parse_args()

    try:
        data = args.firmware.read_bytes()
        result = validate(data)
        if args.require_init and not result["init_payloads"]:
            raise ValueError("no INIT_PAYLOAD command found")
    except (OSError, ValueError) as exc:
        print(f"check-z2fw: {exc}", file=sys.stderr)
        return 1

    print(f"Z2FW OK: {args.firmware}")
    for key, value in result.items():
        print(f"  {key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
