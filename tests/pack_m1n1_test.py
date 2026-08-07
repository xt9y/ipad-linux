#!/usr/bin/env python3

import gzip
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKER = ROOT / "scripts" / "pack-m1n1-j407.py"


def fake_dtb() -> bytes:
    data = bytearray(8)
    data[0:4] = b"\xd0\x0d\xfe\xed"
    struct.pack_into(">I", data, 4, len(data))
    return bytes(data)


def fake_image() -> bytes:
    data = bytearray(64)
    struct.pack_into("<Q", data, 8, 0x80000)
    struct.pack_into("<Q", data, 16, 0x1000)
    data[0x38:0x3C] = b"ARM\x64"
    return bytes(data)


class PackerTest(unittest.TestCase):
    def run_packer(self, directory: pathlib.Path, initramfs: bytes):
        m1n1 = b"M1N1-TEST"
        dtb = fake_dtb()
        image = fake_image()

        paths = {
            "m1n1": directory / "m1n1.bin",
            "dtb": directory / "j407.dtb",
            "initramfs": directory / "initramfs.cpio.gz",
            "image": directory / "Image",
            "output": directory / "packed.bin",
            "manifest": directory / "manifest.txt",
        }

        paths["m1n1"].write_bytes(m1n1)
        paths["dtb"].write_bytes(dtb)
        paths["initramfs"].write_bytes(initramfs)
        paths["image"].write_bytes(image)

        result = subprocess.run(
            [
                sys.executable,
                str(PACKER),
                "--m1n1", str(paths["m1n1"]),
                "--dtb", str(paths["dtb"]),
                "--initramfs", str(paths["initramfs"]),
                "--image", str(paths["image"]),
                "--output", str(paths["output"]),
                "--manifest", str(paths["manifest"]),
            ],
            text=True,
            capture_output=True,
        )

        return result, paths, m1n1, dtb, image

    def test_exact_upstream_concatenation_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            initramfs = gzip.compress(b"070701ipad-linux-test")
            result, paths, m1n1, dtb, image = self.run_packer(directory, initramfs)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                paths["output"].read_bytes(),
                m1n1 + dtb + initramfs + image,
            )
            manifest = paths["manifest"].read_text(encoding="utf-8")
            self.assertIn("order=m1n1,dtb,gzip-initramfs,image", manifest)

    def test_rejects_uncompressed_initramfs(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            result, paths, *_ = self.run_packer(directory, b"070701not-gzip")

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(paths["output"].exists())
            self.assertIn("gzip-compressed", result.stderr)

    def test_rejects_non_arm64_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            initramfs = gzip.compress(b"070701")

            m1n1 = directory / "m1n1.bin"
            dtb = directory / "j407.dtb"
            initrd = directory / "initramfs.cpio.gz"
            image = directory / "Image"
            output = directory / "packed.bin"

            m1n1.write_bytes(b"M1N1")
            dtb.write_bytes(fake_dtb())
            initrd.write_bytes(initramfs)
            image.write_bytes(b"not-an-arm64-image")

            result = subprocess.run(
                [
                    sys.executable, str(PACKER),
                    "--m1n1", str(m1n1),
                    "--dtb", str(dtb),
                    "--initramfs", str(initrd),
                    "--image", str(image),
                    "--output", str(output),
                ],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
