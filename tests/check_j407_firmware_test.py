#!/usr/bin/env python3

import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "check-j407-firmware.py"


class FirmwareCheckerTest(unittest.TestCase):
    def run_checker(self, files: list[str], strict: bool = False):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for filename in files:
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test")

            command = [sys.executable, str(CHECKER)]
            if strict:
                command.append("--strict")
            command.append(str(root))
            return subprocess.run(command, text=True, capture_output=True)

    def test_board_specific_wifi_and_bluetooth_candidates(self):
        result = self.run_checker(
            [
                "brcm/brcmfmac4387c2-pcie.apple,lycheea.bin",
                "brcm/brcmfmac4387c2-pcie.apple,lycheea.txt",
                "brcm/brcmbt4387C2-apple,lycheea.bin",
            ],
            strict=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[FOUND] Wi-Fi firmware", result.stdout)
        self.assertIn("[FOUND] Wi-Fi NVRAM", result.stdout)
        self.assertIn("[FOUND] Bluetooth firmware", result.stdout)
        self.assertIn("required classes missing: 0", result.stdout)

    def test_generic_wifi_fallback_is_accepted(self):
        result = self.run_checker(
            [
                "brcm/brcmfmac4387c2-pcie.bin",
                "brcm/brcmfmac4387c2-pcie.txt",
                "brcm/brcmbt4387B0-apple,lycheea-vendor.bin",
            ],
            strict=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_strict_mode_rejects_missing_required_classes(self):
        result = self.run_checker([], strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[MISSING] Wi-Fi firmware", result.stdout)
        self.assertIn("[MISSING] Bluetooth firmware", result.stdout)


if __name__ == "__main__":
    unittest.main()
