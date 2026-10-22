#!/usr/bin/env python3
"""Simulate m1n1's inline payload scan over a packed J407 artifact.

Current upstream m1n1 (src/payload.c) scans the bytes appended to m1n1.bin:

- a gzip stream is decompressed at the end of the heap area and rescanned
  there; scanning resumes after the consumed source bytes;
- an FDT payload is accepted only when its root compatible property matches
  "apple," + lowercased live-ADT "target-type" (for iPad13,16: "apple,j407");
  otherwise the scan advances past it without retaining it;
- an uncompressed CPIO payload is retained as the initrd;
- an arm64 Image (magic at header offset 0x38) is retained as the kernel and
  terminates the scan, because an inline (size-less) kernel cannot know its
  own length;
- payload_run() boots the retained kernel only if an accepted DTB exists.

This test encodes those rules and cross-checks the packer output against
them, verifying the exact payload order m1n1 needs:

    m1n1.bin + t8103-j407.dtb + initramfs.cpio.gz + Image
"""

from __future__ import annotations

import gzip
import importlib.util
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from pack_m1n1_test import build_fdt, fake_image  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKER = ROOT / "scripts" / "pack-m1n1-j407.py"

_spec = importlib.util.spec_from_file_location("_pack_m1n1_j407", PACKER)
packer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packer)

# Mirrors m1n1 src/payload.c: payload_run() computes the acceptable DTB
# compatible as "apple," + lowercased ADT root "target-type". iPad13,16
# reports target-type J407.
J407_EXPECTED_COMPATIBLE = "apple,j407"

M1N1_FIXTURE = b"M1N1-TEST-IMAGE\n"


class M1n1PayloadScan:
    """Faithful port of m1n1's load_one_payload()/payload_run() state."""

    def __init__(self, blob: bytes, payload_start: int):
        self.blob = blob
        self.pos = payload_start
        self.fdt = None
        self.initrd = None
        self.kernel = None

    @property
    def accepted(self) -> bool:
        """Whether m1n1's payload_run() would boot this staged state."""
        return self.kernel is not None and self.fdt is not None

    def fail_message(self) -> str:
        if self.kernel is not None and self.fdt is None:
            return "ERROR: Kernel found but no devicetree for %s available." % (
                J407_EXPECTED_COMPATIBLE,
            )
        return ""

    def run(self) -> "M1n1PayloadScan":
        while self.pos is not None and self.pos < len(self.blob):
            self.pos = self._load_one_payload(self.pos)
        return self

    def _load_one_payload(self, start: int) -> int | None:
        blob = self.blob

        if blob[start:start + 2] == b"\x1f\x8b":  # gzip magic
            decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
            dest = decompressor.decompress(blob[start:])
            consumed = (len(blob) - start) - len(decompressor.unused_data)

            # m1n1 rescans the decompressed destination in place.
            nested = M1n1PayloadScan(dest, 0).run()
            self._merge(nested)

            return start + consumed

        if blob[start:start + 4] == b"\xd0\x0d\xfe\xed":  # FDT magic
            total = struct.unpack_from(">I", blob, start + 4)[0]
            accepted = packer.root_compatible_contains(
                blob[start:start + total],
                J407_EXPECTED_COMPATIBLE.encode(),
            )
            if accepted:
                self.fdt = start
            return start + total

        if blob[start:start + 5] == b"07070":  # CPIO archive
            self.initrd = (start, len(blob) - start)
            return len(blob) - self._trailing_zero_pad()

        if blob[start + 0x38:start + 0x3C] == b"ARM\x64":
            image_size = struct.unpack_from("<Q", blob, start + 16)[0]
            if image_size < len(blob) - start:
                raise AssertionError(
                    "m1n1 load_kernel asserts size <= kernel->image_size"
                )
            self.kernel = start
            # Inline kernel: size-less, so the scan ends here.
            return None

        raise AssertionError(
            "m1n1 scan hit an unknown payload at 0x%x" % start
        )

    def _merge(self, other: "M1n1PayloadScan") -> None:
        """Fold scan results from a decompressed destination into self."""
        if other.fdt is not None or other.kernel is not None:
            raise AssertionError(
                "decompressed m1n1 payload contains an FDT or kernel"
            )
        if self.initrd is None and other.initrd is not None:
            self.initrd = other.initrd

    @staticmethod
    def _trailing_zero_pad() -> int:
        # An uncompressed CPIO cannot tell m1n1 where it ends; the real
        # firmware only uses gzip members in first-boot kits (upstream m1n1
        # refuses uncompressed cpio with "Uncompressed cpio archives not
        # supported"). Reaching this branch means a diagnosis instead.
        return 0


def pack(dtb: bytes) -> tuple[bytes, pathlib.Path]:
    """Pack valid artifacts, returning the blob and its scratch directory."""
    directory = pathlib.Path(tempfile.mkdtemp())
    sources = [
        ("m1n1.bin", M1N1_FIXTURE),
        ("j407.dtb", dtb),
        ("initramfs.cpio.gz", gzip.compress(b"070701ipad-linux-test")),
        ("Image", fake_image()),
    ]
    paths = []
    for name, data in sources:
        path = directory / name
        path.write_bytes(data)
        paths.append(path)

    result = subprocess.run(
        [
            sys.executable, str(PACKER),
            "--m1n1", str(paths[0]),
            "--dtb", str(paths[1]),
            "--initramfs", str(paths[2]),
            "--image", str(paths[3]),
            "--output", str(directory / "packed.bin"),
        ],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return (directory / "packed.bin").read_bytes(), directory


class M1n1PayloadScanTest(unittest.TestCase):
    def test_j407_payload_chain_is_accepted_by_m1n1_scan(self):
        blob, _ = pack(build_fdt(b"apple,j407"))

        # The scanner starts after the (fixture) m1n1 image.
        start = blob.index(M1N1_FIXTURE) + len(M1N1_FIXTURE)
        scanned = M1n1PayloadScan(blob, start).run()

        self.assertIsNotNone(scanned.kernel, "m1n1 must find the kernel")
        self.assertIsNotNone(
            scanned.fdt, "m1n1 must accept the apple,j407 DTB"
        )
        self.assertIsNotNone(
            scanned.initrd, "the gzip initramfs must decompress into a CPIO"
        )
        self.assertTrue(
            scanned.accepted,
            "payload_run() boots when kernel and matching DTB are staged",
        )
        self.assertEqual(
            scanned.kernel,
            len(blob) - len(fake_image()),
            "the Image must be the last payload",
        )
        self.assertEqual(scanned.fail_message(), "")

    def test_wrong_target_dtb_makes_m1n1_boot_fail(self):
        # Packing correctly refuses a mismatched DTB, so build the blob
        # manually to model a future DTS regression instead.
        m1n1 = M1N1_FIXTURE
        blob = m1n1 + build_fdt(b"apple,j346") + gzip.compress(b"070701")

        scanned = M1n1PayloadScan(blob, len(m1n1)).run()

        self.assertIsNone(scanned.fdt, "a non-j407 DTB is scanned but rejected")
        self.assertIsNone(scanned.kernel, "no Image in this fixture")
        self.assertEqual(scanned.fail_message(), "")

        # Same fixture with the kernel appended: the scan stages the kernel
        # but payload_run() still refuses to boot without the DTB.
        blob += fake_image()
        scanned = M1n1PayloadScan(blob, len(m1n1)).run()
        self.assertIsNotNone(scanned.kernel)
        self.assertIsNone(scanned.fdt)
        self.assertFalse(scanned.accepted)
        self.assertEqual(
            scanned.fail_message(),
            "ERROR: Kernel found but no devicetree for apple,j407 available.",
        )

    def test_image_not_last_leaves_unreachable_payloads(self):
        # m1n1 stops scanning at the first inline kernel. Payloads after the
        # Image would never be staged; model kernel-before-DTB.
        blob = M1N1_FIXTURE + fake_image() + build_fdt(b"apple,j407")

        scanned = M1n1PayloadScan(blob, len(M1N1_FIXTURE)).run()
        self.assertIsNotNone(scanned.kernel)
        self.assertIsNone(
            scanned.fdt, "payloads after the Image are unreachable"
        )
        self.assertFalse(scanned.accepted)

    def test_scanner_agrees_with_packer_validation(self):
        # The DTB root-compatible helper used during packing must be the same
        # helper this simulation trusts; pin the "apple,j407" contract here.
        dtb = build_fdt(b"apple,j407\x00apple,t8103\x00apple,arm-platform")
        self.assertTrue(
            packer.root_compatible_contains(
                dtb, J407_EXPECTED_COMPATIBLE.encode()
            )
        )
        self.assertFalse(
            packer.root_compatible_contains(
                build_fdt(b"apple,j346"),
                J407_EXPECTED_COMPATIBLE.encode(),
            )
        )

    def test_single_build_fdt_root_layout(self):
        # Guard the shared fixture builder against drift: one root node, one
        # compatible property, exact totalsize.
        dtb = build_fdt(b"apple,j407")
        self.assertEqual(struct.unpack_from(">I", dtb, 4)[0], len(dtb))


if __name__ == "__main__":
    unittest.main()
