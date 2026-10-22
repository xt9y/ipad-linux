#!/usr/bin/env python3
"""Pack a self-contained m1n1 payload chain for J407.

Upstream m1n1 supports payloads by simple concatenation. Our first-boot chain
uses only formats that its normal payload scanner already understands:

    m1n1.bin
    t8103-j407.dtb
    initramfs.cpio.gz
    Linux Image

The uncompressed kernel is intentionally last: m1n1 can recognize it, but
cannot infer where a size-less inline Image ends. The compressed initramfs is
placed before it, so m1n1 can decompress/recognize the CPIO and continue
scanning to the final kernel.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import sys

FDT_MAGIC = b"\xd0\x0d\xfe\xed"
FDT_BEGIN_NODE = b"\x00\x00\x00\x01"
FDT_END_NODE = b"\x00\x00\x00\x02"
FDT_END = b"\x00\x00\x00\x09"
ARM64_IMAGE_MAGIC = b"ARM\x64"
GZIP_MAGIC = b"\x1f\x8b"

# m1n1's inline payload scanner accepts a DTB only when its root "compatible"
# property contains "apple," + lowercased live-ADT "target-type" (see
# AsahiLinux/m1n1 src/payload.c payload_run()). For iPad13,16/J407 the live
# target-type is J407, so a first-boot DTB must advertise "apple,j407" or
# m1n1 aborts after loading the kernel ("Kernel found but no devicetree").
J407_EXPECTED_COMPATIBLE = b"apple,j407\x00"


def read(path: pathlib.Path) -> bytes:
    data = path.read_bytes()
    if not data:
        raise ValueError(f"{path}: empty file")
    return data


def validate_dtb(data: bytes, path: pathlib.Path) -> None:
    if len(data) < 8 or data[:4] != FDT_MAGIC:
        raise ValueError(f"{path}: not a flattened device tree")
    total = struct.unpack_from(">I", data, 4)[0]
    if total != len(data):
        raise ValueError(
            f"{path}: FDT totalsize is {total}, file contains {len(data)} bytes; "
            "payload chaining requires an exact DTB"
        )
    if not root_compatible_contains(data, J407_EXPECTED_COMPATIBLE):
        raise ValueError(
            f"{path}: root compatible does not advertise 'apple,j407'; "
            "m1n1 only accepts a payload DTB matching the live Apple Device "
            "Tree target-type ('apple,' + lowercased target-type)"
        )


def root_compatible_contains(data: bytes, wanted: bytes) -> bool:
    """Return True when the FDT root node's compatible list contains `wanted`.

    This mirrors the minimal flattened-device-tree walk m1n1 relies upon for
    its payload scan (big-endian tokens in the header-referenced structure
    block). Only the root node's properties are inspected and the walk is
    fail-closed: any structural surprise means "does not contain".
    """
    if len(data) < 40 or data[:4] != FDT_MAGIC:
        return False
    off_struct = struct.unpack_from(">I", data, 8)[0]
    off_strings = struct.unpack_from(">I", data, 12)[0]
    size_struct = struct.unpack_from(">I", data, 36)[0]
    if not off_struct or off_struct >= len(data) or not size_struct:
        return False
    if not off_strings or off_strings >= len(data):
        return False

    end = min(off_struct + size_struct, len(data))
    if struct.unpack_from(">I", data, off_struct)[0] != 0x1:  # FDT_BEGIN_NODE
        return False
    pos = off_struct + 4
    nul = data.find(b"\x00", pos, end)
    if nul < 0:  # root node name ("" here) not terminated
        return False
    pos = nul + 1
    pos += (-pos % 4)

    strings = data[off_strings:]
    wanted_entry = wanted.rstrip(b"\x00")
    while pos + 4 <= end:
        token = struct.unpack_from(">I", data, pos)[0]
        if token in (0x2, 0x9):  # FDT_END_NODE / FDT_END
            break
        if token != 0x3:  # FDT_PROP
            return False
        if pos + 12 > end:
            return False
        prop_len = struct.unpack_from(">I", data, pos + 4)[0]
        nameoff = struct.unpack_from(">I", data, pos + 8)[0]
        if pos + 12 + prop_len > end:
            return False
        if nameoff >= len(strings):
            return False
        name_end = strings.find(b"\x00", nameoff)
        if name_end < 0:
            return False
        name = strings[nameoff:name_end]
        value = data[pos + 12:pos + 12 + prop_len]
        if name == b"compatible":
            entries = [
                entry
                for entry in value.rstrip(b"\x00").split(b"\x00")
                if entry
            ]
            for entry in entries:
                if entry == wanted_entry:
                    return True
            return False
        pos += 12 + prop_len
        pos += (-pos % 4)

    return False


def validate_initramfs(data: bytes, path: pathlib.Path) -> None:
    if not data.startswith(GZIP_MAGIC):
        raise ValueError(
            f"{path}: first-boot initramfs must be gzip-compressed for native "
            "m1n1 payload scanning"
        )


def validate_image(data: bytes, path: pathlib.Path) -> None:
    if len(data) < 0x40 or data[0x38:0x3C] != ARM64_IMAGE_MAGIC:
        raise ValueError(f"{path}: not an uncompressed arm64 Linux Image")

    text_offset, image_size = struct.unpack_from("<QQ", data, 8)
    if image_size == 0:
        raise ValueError(f"{path}: Image header reports zero image_size")
    if image_size < len(data):
        raise ValueError(
            f"{path}: Image header size 0x{image_size:x} is smaller than file "
            f"size 0x{len(data):x}"
        )
    if text_offset >= (1 << 32):
        raise ValueError(f"{path}: implausible text_offset 0x{text_offset:x}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m1n1", required=True, type=pathlib.Path)
    parser.add_argument("--dtb", required=True, type=pathlib.Path)
    parser.add_argument("--initramfs", required=True, type=pathlib.Path)
    parser.add_argument("--image", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--manifest", type=pathlib.Path)
    args = parser.parse_args()

    try:
        m1n1 = read(args.m1n1)
        dtb = read(args.dtb)
        initramfs = read(args.initramfs)
        image = read(args.image)

        validate_dtb(dtb, args.dtb)
        validate_initramfs(initramfs, args.initramfs)
        validate_image(image, args.image)

        packed = m1n1 + dtb + initramfs + image

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(packed)

        manifest = (
            "J407 m1n1 Linux payload chain\n"
            f"m1n1_size={len(m1n1)} sha256={sha256(m1n1)}\n"
            f"dtb_size={len(dtb)} sha256={sha256(dtb)}\n"
            f"initramfs_size={len(initramfs)} sha256={sha256(initramfs)}\n"
            f"image_size={len(image)} sha256={sha256(image)}\n"
            f"packed_size={len(packed)} sha256={sha256(packed)}\n"
            "order=m1n1,dtb,gzip-initramfs,image\n"
        )

        manifest_path = args.manifest or args.output.with_suffix(args.output.suffix + ".txt")
        manifest_path.write_text(manifest, encoding="utf-8")
        sys.stdout.write(manifest)
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"pack-m1n1-j407: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
