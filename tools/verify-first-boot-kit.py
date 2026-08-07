#!/usr/bin/env python3
"""Verify a downloaded J407 first-boot artifact directory before hardware use."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import re
import struct
import sys


REQUIRED = (
    "Image",
    "t8103-j407.dtb",
    "initramfs.cpio.gz",
    "m1n1.bin",
    "ipad-linux-stage2.bin",
    "j407-m1n1-linux.bin",
    "j407-m1n1-linux.manifest.txt",
    "linux.config",
    "SOURCE_COMMITS",
    "SHA256SUMS",
)

FDT_MAGIC = b"\xd0\x0d\xfe\xed"
ARM64_IMAGE_MAGIC = b"ARM\x64"
GZIP_MAGIC = b"\x1f\x8b"


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_sums(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line)
        if not match:
            raise ValueError(f"{path}:{lineno}: malformed SHA256SUMS line")
        result[pathlib.Path(match.group(2)).name] = match.group(1).lower()
    return result


def check_format(root: pathlib.Path) -> None:
    dtb = (root / "t8103-j407.dtb").read_bytes()
    if len(dtb) < 8 or dtb[:4] != FDT_MAGIC:
        raise ValueError("t8103-j407.dtb: bad FDT magic")
    total = struct.unpack_from(">I", dtb, 4)[0]
    if total != len(dtb):
        raise ValueError(
            f"t8103-j407.dtb: totalsize={total}, actual={len(dtb)}"
        )

    initramfs = (root / "initramfs.cpio.gz").read_bytes()
    if not initramfs.startswith(GZIP_MAGIC):
        raise ValueError("initramfs.cpio.gz: missing gzip magic")
    try:
        payload = gzip.decompress(initramfs)
    except OSError as exc:
        raise ValueError(f"initramfs.cpio.gz: gzip decode failed: {exc}") from exc
    if b"070701" not in payload[:256]:
        raise ValueError("initramfs.cpio.gz: decompressed data is not newc CPIO")

    image = (root / "Image").read_bytes()
    if len(image) < 0x40 or image[0x38:0x3C] != ARM64_IMAGE_MAGIC:
        raise ValueError("Image: bad arm64 Linux Image magic")


def check_checksums(root: pathlib.Path) -> int:
    sums = parse_sums(root / "SHA256SUMS")
    checked = 0
    for name, expected in sums.items():
        candidate = root / name
        if not candidate.is_file():
            raise ValueError(f"SHA256SUMS references missing file: {name}")
        actual = sha256_file(candidate)
        if actual != expected:
            raise ValueError(
                f"checksum mismatch for {name}: expected {expected}, got {actual}"
            )
        checked += 1
    if not checked:
        raise ValueError("SHA256SUMS contains no file hashes")
    return checked


def check_payload_chain(root: pathlib.Path) -> None:
    pieces = [
        (root / "m1n1.bin").read_bytes(),
        (root / "t8103-j407.dtb").read_bytes(),
        (root / "initramfs.cpio.gz").read_bytes(),
        (root / "Image").read_bytes(),
    ]
    packed = (root / "j407-m1n1-linux.bin").read_bytes()

    expected_size = sum(map(len, pieces))
    if len(packed) != expected_size:
        raise ValueError(
            f"j407-m1n1-linux.bin: size={len(packed)}, expected={expected_size}"
        )

    offset = 0
    labels = ("m1n1", "dtb", "initramfs", "Image")
    for label, piece in zip(labels, pieces):
        end = offset + len(piece)
        if packed[offset:end] != piece:
            raise ValueError(
                f"j407-m1n1-linux.bin: {label} differs at payload offset 0x{offset:x}"
            )
        offset = end


def check_source_revisions(root: pathlib.Path) -> None:
    text = (root / "SOURCE_COMMITS").read_text(encoding="utf-8")
    for key in ("ipad-linux", "linux", "m1n1"):
        if not re.search(rf"^{re.escape(key)}=[0-9a-f]{{7,40}}$", text, re.MULTILINE):
            raise ValueError(f"SOURCE_COMMITS: missing valid {key}=<sha>")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_dir", type=pathlib.Path)
    args = parser.parse_args()
    root = args.artifact_dir

    try:
        if not root.is_dir():
            raise ValueError(f"not a directory: {root}")
        for name in REQUIRED:
            if not (root / name).is_file():
                raise ValueError(f"missing required artifact: {name}")
        checked = check_checksums(root)
        check_format(root)
        check_payload_chain(root)
        check_source_revisions(root)
    except (OSError, ValueError, struct.error) as exc:
        print(f"verify-first-boot-kit: FAIL: {exc}", file=sys.stderr)
        return 1

    print("J407 first-boot kit: VERIFIED")
    print(f"artifact_dir={root}")
    print(f"checksums_verified={checked}")
    print(f"packed_sha256={sha256_file(root / 'j407-m1n1-linux.bin')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
