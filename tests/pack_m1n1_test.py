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


def build_fdt(compatible: bytes = b"apple,j407") -> bytes:
    """Build a minimal flattened device tree with one root compatible entry."""
    strings = b"compatible\x00"
    total_strings = len(strings)

    header_len = 40  # magic, totalsize, off_dt_struct, off_dt_strings,
    #                   off_mem_rsvmap, version, last_comp, boot_cpuid,
    #                   size_dt_strings, size_dt_struct
    off_mem_rsvmap = header_len
    mem_rsv = b"\x00" * 16  # empty reserve block terminator
    off_dt_struct = off_mem_rsvmap + len(mem_rsv)

    struct_block = bytearray()
    struct_block += b"\x00\x00\x00\x01"           # FDT_BEGIN_NODE
    struct_block += b"\x00" + b"\x00" * 3          # root name "" + padding
    value = compatible + b"\x00"
    prop_len = len(value)
    struct_block += b"\x00\x00\x00\x03"            # FDT_PROP
    struct_block += prop_len.to_bytes(4, "big")
    struct_block += (0).to_bytes(4, "big")         # name offset 0 = compatible
    struct_block += value
    while len(struct_block) % 4:
        struct_block += b"\x00"
    struct_block += b"\x00\x00\x00\x02"            # FDT_END_NODE
    struct_block += b"\x00\x00\x00\x09"            # FDT_END
    size_dt_struct = len(struct_block)

    off_dt_strings = off_dt_struct + size_dt_struct
    total = off_dt_strings + total_strings
    if total % 4:
        total += 4 - (total % 4)

    header = bytearray()
    header += b"\xd0\x0d\xfe\xed"                  # FDT magic
    header += total.to_bytes(4, "big")
    header += off_dt_struct.to_bytes(4, "big")
    header += off_dt_strings.to_bytes(4, "big")
    header += off_mem_rsvmap.to_bytes(4, "big")
    header += (17).to_bytes(4, "big")
    header += (16).to_bytes(4, "big")
    header += (0).to_bytes(4, "big")
    header += total_strings.to_bytes(4, "big")
    header += size_dt_struct.to_bytes(4, "big")

    data = bytearray(header)
    data += mem_rsv
    data += struct_block
    data += strings
    while len(data) < total:
        data += b"\x00"
    return bytes(data)


def fake_dtb() -> bytes:
    return build_fdt(b"apple,j407")


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

    def test_rejects_dtb_without_j407_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            initramfs = gzip.compress(b"070701")

            m1n1 = directory / "m1n1.bin"
            dtb = directory / "j407.dtb"
            initrd = directory / "initramfs.cpio.gz"
            image = directory / "Image"
            output = directory / "packed.bin"

            m1n1.write_bytes(b"M1N1")
            # Anything other than the live J407 target-type is rejected:
            # m1n1's inline scan would boot the kernel without a devicetree.
            dtb.write_bytes(build_fdt(b"apple,j318"))
            initrd.write_bytes(initramfs)
            image.write_bytes(fake_image())

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
            self.assertIn("apple,j407", result.stderr)

    def test_multi_string_root_compatible_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            initramfs = gzip.compress(b"070701")
            result, paths, m1n1, dtb, image = self.run_packer(
                directory, initramfs
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            # Re-pack with the production-style compatible list.
            dtb = directory / "j407-full.dtb"
            dtb.write_bytes(
                build_fdt(b"apple,j407\x00apple,t8103\x00apple,arm-platform")
            )
            result = subprocess.run(
                [
                    sys.executable, str(PACKER),
                    "--m1n1", str(paths["m1n1"]),
                    "--dtb", str(dtb),
                    "--initramfs", str(paths["initramfs"]),
                    "--image", str(paths["image"]),
                    "--output", str(paths["output"]),
                    "--manifest", str(paths["manifest"]),
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

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
