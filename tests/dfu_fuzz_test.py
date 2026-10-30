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
        self.assertIn("UPLOAD(16),0x02,0,0,TIMEOUT,2 s timeout; no DFU error latch (steady state)", result.stdout)
        self.assertIn("GETSTATUS(wrong-interface),0x03,0,1,ENOENT,immediate Errno 2; not a timeout", result.stdout)
        self.assertIn("GETSTATE(wrong-interface),0x05,0,1,ENOENT,immediate Errno 2; not a timeout", result.stdout)
        self.assertIn("ABORT,0x06,0,0,I/O-ERROR,detaches within 250 ms; re-enumerates as 05ac:12ab composite personality (n=2)", result.stdout)
        self.assertIn("CLRSTATUS,0x04,0,0,I/O-ERROR,detaches <250 ms; 05ac:12ab ~15 s later (n=3, deterministic)", result.stdout)
        # every vector in the set is recorded; nothing stays UNRECORDED
        self.assertNotIn("UNRECORDED", result.stdout)
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
            if vector.b_request in (0x04, 0x06):  # CLRSTATUS/ABORT: host-to-device
                self.assertEqual(vector.bm_request_type, 0x21)
            else:
                self.assertEqual(vector.bm_request_type, 0xA1)


if __name__ == "__main__":
    unittest.main()
