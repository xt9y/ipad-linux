#!/usr/bin/env python3

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools" / "dfu-fuzz.py"


class DfuFuzzOfflineTest(unittest.TestCase):
    def run_tool(self, *flags):
        return subprocess.run(
            [sys.executable, str(HARNESS), *flags],
            text=True, capture_output=True,
        )

    def test_offline_pass_is_usb_free_and_repeats_capture(self):
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("offline mode: physical capture mirror (no USB)", result.stdout)
        self.assertIn("GETSTATUS,0x03,0,0,OK,[0, 50, 0, 0, 2, 0]", result.stdout)
        self.assertIn("GETSTATE,0x05,0,0,OK,[2]", result.stdout)
        self.assertIn("UPLOAD(16),0x02,0,0,TIMEOUT,-", result.stdout)
        self.assertIn("offline pass complete", result.stdout)

    def test_device_mode_requires_explicit_allow(self):
        result = self.run_tool("--device")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--allow-device", result.stderr)

    def test_device_mode_without_device_fails_cleanly(self):
        result = self.run_tool("--device", "--allow-device")
        # No device attached in CI/local: expected clean 'exit 2', not a crash
        self.assertIn(result.returncode, (0, 2))
        self.assertNotIn("DNLOAD", result.stdout)
        self.assertNotIn("0x01,", result.stdout.splitlines()[1] if result.stdout else "")

    def test_vectors_never_include_write_side_requests(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "dfu_fuzz", ROOT / "tools" / "dfu-fuzz.py")
        assert spec and spec.loader
        dfu_fuzz = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dfu_fuzz)

        for vector in dfu_fuzz.build_vectors():
            self.assertNotIn(vector.b_request, dfu_fuzz.VN_FORBIDDEN)
            self.assertIn(vector.b_request, dfu_fuzz.READ_SIDE_REQUESTS)


if __name__ == "__main__":
    unittest.main()
