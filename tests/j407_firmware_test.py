#!/usr/bin/env python3

import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "check-j407-firmware.py"


class J407FirmwareCheckerTest(unittest.TestCase):
    def run_checker(self, files: tuple[str, ...], strict: bool = True) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for name in files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test")

            command = [sys.executable, str(CHECKER)]
            if strict:
                command.append("--strict")
            command.append(str(root))
            return subprocess.run(command, text=True, capture_output=True)

    def test_board_specific_wifi_and_bluetooth_satisfy_required_classes(self):
        result = self.run_checker(
            (
                "brcm/brcmfmac4387c2-pcie.apple,lycheea.bin",
                "brcm/brcmfmac4387c2-pcie.apple,lycheea.txt",
                "brcm/brcmbt4387c2-apple,lycheea.bin",
            )
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("required classes missing: 0", result.stdout)

    def test_generic_wifi_fallback_is_accepted(self):
        result = self.run_checker(
            (
                "brcm/brcmfmac4387c2-pcie.bin",
                "brcm/brcmfmac4387c2-pcie.txt",
                "brcm/brcmbt4387c2-apple,lycheea-vendor.bin",
            )
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_bluetooth_firmware_fails_strict_mode(self):
        result = self.run_checker(
            (
                "brcm/brcmfmac4387c2-pcie.apple,lycheea.bin",
                "brcm/brcmfmac4387c2-pcie.apple,lycheea.txt",
            )
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[MISSING] Bluetooth firmware", result.stdout)

    def test_optional_blobs_do_not_fail_strict_mode(self):
        result = self.run_checker(
            (
                "brcm/brcmfmac4387c2-pcie.apple,lycheea.bin",
                "brcm/brcmfmac4387c2-pcie.apple,lycheea.txt",
                "brcm/brcmbt4387c2-apple,lycheea.bin",
            )
        )
        self.assertIn("optional-missing", result.stdout)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
