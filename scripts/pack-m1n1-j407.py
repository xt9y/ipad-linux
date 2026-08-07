#!/usr/bin/env python3
"""Pack a self-contained m1n1 payload chain for J407.

m1n1's payload scanner walks data appended at _payload_start. For our first
bring-up image the safe order is:

    m1n1.bin
    t8103-j407.dtb
    m1n1_initramfs + <u32 little-endian byte size> + initramfs.cpio.gz
    Linux Image

The kernel is intentionally last because m1n1 cannot infer the end of an
uncompressed inline Linux Image and therefore stops scanning once it finds it.
At that point both the FDT and initramfs have already been registered.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import sys

FDT_MAGIC = b"\xd0\x0d\xfe\xed"
ARM64_IMAGE_MAGIC = b"ARM\x64"
INITRAMFS_MAGIC = b"m1n1_initramfs"


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
        validate_image(image, args.image)

        if len(initramfs) > 0xFFFFFFFF:
            raise ValueError("initramfs is too large for m1n1's u32 payload size")

        initrd_record = INITRAMFS_MAGIC + struct.pack("<I", len(initramfs)) + initramfs
        packed = m1n1 + dtb + initrd_record + image

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(packed)

        manifest = (
            "J407 m1n1 Linux payload chain\n"
            f"m1n1_size={len(m1n1)} sha256={sha256(m1n1)}\n"
            f"dtb_size={len(dtb)} sha256={sha256(dtb)}\n"
            f"initramfs_size={len(initramfs)} sha256={sha256(initramfs)}\n"
            f"image_size={len(image)} sha256={sha256(image)}\n"
            f"packed_size={len(packed)} sha256={sha256(packed)}\n"
            "order=m1n1,dtb,initramfs-record,image\n"
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
