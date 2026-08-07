#!/usr/bin/env python3

import gzip
import hashlib
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "verify-first-boot-kit.py"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_kit(root: pathlib.Path) -> None:
    m1n1 = b"m1n1-test-image\0" * 32
    dtb = bytearray(64)
    dtb[:4] = b"\xd0\x0d\xfe\xed"
    struct.pack_into(">I", dtb, 4, len(dtb))

    image = bytearray(0x100)
    image[0x38:0x3C] = b"ARM\x64"
    initramfs = gzip.compress(b"070701" + b"0" * 128)

    (root / "m1n1.bin").write_bytes(m1n1)
    (root / "t8103-j407.dtb").write_bytes(dtb)
    (root / "initramfs.cpio.gz").write_bytes(initramfs)
    (root / "Image").write_bytes(image)
    (root / "ipad-linux-stage2.bin").write_bytes(b"stage2")
    (root / "linux.config").write_text("CONFIG_ARCH_APPLE=y\n", encoding="utf-8")
    (root / "SOURCE_COMMITS").write_text(
        "ipad-linux=0123456789abcdef\n"
        "linux=1111111111111111\n"
        "m1n1=2222222222222222\n",
        encoding="utf-8",
    )
    (root / "TARGET").write_text(
        "product_type=iPad13,16\n"
        "board_config=J407AP\n"
        "model=A2588\n"
        "soc=T8103 / Apple M1\n"
        "cpid=0x8103\n"
        "bdid=0x10\n"
        "reported_ipados=26.5\n"
        "public_26.5_build=23F77\n",
        encoding="utf-8",
    )
    for name in (
        "HARDWARE_TEST.md",
        "analyze-first-boot.py",
        "build-hardware-report.py",
        "host-preflight.py",
        "verify-first-boot-kit.py",
        "dump_live_adt.py",
    ):
        (root / name).write_text(f"test fixture: {name}\n", encoding="utf-8")

    (root / "j407-m1n1-linux.manifest.txt").write_text(
        "order=m1n1,dtb,gzip-initramfs,image\n", encoding="utf-8"
    )
    (root / "j407-m1n1-linux.bin").write_bytes(m1n1 + dtb + initramfs + image)

    names = sorted(path.name for path in root.iterdir() if path.name != "SHA256SUMS")
    (root / "SHA256SUMS").write_text(
        "".join(f"{sha256(root / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


class FirstBootKitVerifierTest(unittest.TestCase):
    def test_valid_kit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            make_kit(root)
            result = subprocess.run(
                [sys.executable, str(TOOL), str(root)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("J407 first-boot kit: VERIFIED", result.stdout)

    def test_corrupt_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            make_kit(root)
            packed = root / "j407-m1n1-linux.bin"
            data = bytearray(packed.read_bytes())
            data[-1] ^= 0xFF
            packed.write_bytes(data)

            # Update SHA256SUMS to prove the verifier also checks payload
            # composition independently from the checksum manifest.
            lines = []
            for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
                if line.endswith("  j407-m1n1-linux.bin"):
                    lines.append(f"{sha256(packed)}  j407-m1n1-linux.bin")
                else:
                    lines.append(line)
            (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(TOOL), str(root)],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Image differs", result.stderr)

    def test_wrong_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            make_kit(root)
            target = root / "TARGET"
            target.write_text(
                target.read_text(encoding="utf-8").replace("iPad13,16", "iPad13,17"),
                encoding="utf-8",
            )
            lines = []
            for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
                if line.endswith("  TARGET"):
                    lines.append(f"{sha256(target)}  TARGET")
                else:
                    lines.append(line)
            (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(TOOL), str(root)],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("product_type=iPad13,16", result.stderr)


if __name__ == "__main__":
    unittest.main()
