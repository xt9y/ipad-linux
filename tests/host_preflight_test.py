#!/usr/bin/env python3

import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "host-preflight.py"


class HostPreflightTest(unittest.TestCase):
    def test_ci_host_report_is_machine_readable(self):
        result = subprocess.run(
            [sys.executable, str(TOOL), "--json"],
            text=True,
            capture_output=True,
        )
        # GitHub-hosted tests run on Linux; if this ever moves to another host,
        # a clean unsupported-host exit is still acceptable as long as JSON is
        # produced and the result remains explicit.
        self.assertIn(result.returncode, (0, 2), result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["schema"], 1)
        self.assertEqual(data["target"], "iPad13,16 / J407AP / T8103")
        self.assertIn("host_supported", data)
        self.assertIn("m1n1_usb_devices", data)
        self.assertIn("initial_entry_status", data)
        self.assertNotIn("hostname", data["host"])
        self.assertNotIn("username", data["host"])


if __name__ == "__main__":
    unittest.main()
