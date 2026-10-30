#!/usr/bin/env python3

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

import importlib.util


def load_module():
    spec = importlib.util.spec_from_file_location(
        "boot_image_recon", ROOT / "tools" / "boot-image-recon.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boot_image_recon = load_module()


def synthetic_payload() -> bytes:
    # A miniature fake "bootloader" image exercising every recon section:
    blob = bytearray()
    blob += bytes.fromhex("4a309070") + bytes(12)  # header-ish first 16 bytes
    blob += b"mBoot-20457.2.37\x00"
    blob += b"getenv\x00usage\x00command\x00"
    blob += b"boot-command\x00boot-args\x00usb-device\x00"
    blob += b"dartsomething-unused\x00"
    return bytes(blob)


class BootImageReconTest(unittest.TestCase):
    def test_report_sections_and_digests(self):
        data = synthetic_payload()
        report = boot_image_recon.analyze(data)

        self.assertIn("## header", report)
        self.assertIn("## strings", report)
        self.assertIn("## build identities", report)
        self.assertIn("mBoot-20457.2.37", report)
        self.assertIn("## keyword corpus", report)
        self.assertIn("getenv", report)
        self.assertIn("## short identifiers", report)
        self.assertIn(f"sha256: {hashlib.sha256(data).hexdigest()[:16]}", report)
        self.assertIn("## entropy", report)

    def test_keyword_rows_shown_for_matches(self):
        report = boot_image_recon.analyze(synthetic_payload())
        self.assertRegex(report, r"\[ *\d+\] getenv:")
        self.assertRegex(report, r"\[ *\d+\] boot:")

    def test_cli_writes_report_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "image.bin"
            src.write_bytes(synthetic_payload())
            out = Path(tmp) / "report.txt"
            import subprocess
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "boot-image-recon.py"),
                 str(src), "--out", str(out)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.exists())
            self.assertIn("## header", out.read_text())


if __name__ == "__main__":
    unittest.main()
