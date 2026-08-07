#!/usr/bin/env python3

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "analyze-first-boot.py"


class FirstBootAnalyzerTest(unittest.TestCase):
    def analyze(self, log: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "boot.log"
            path.write_text(log, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ANALYZER), "--json", str(path)],
                text=True,
                capture_output=True,
                check=True,
            )
            return json.loads(result.stdout)

    def test_complete_first_boot(self):
        result = self.analyze(
            """
            m1n1 version test
            Linux version 6.x-test
            ipad-linux early userspace
              cpu_nodes=8 (expected 8 for full J407 SMP)
              block_devices=2
              nvme_controllers=1
              graphics_entries=1
              usb_entries=4
              typec_entries=1
              pci_functions=3
              SMP=PASS
              ANS2/NVMe=DETECTED
              USB=ENUMERATED
              TYPEC=REGISTERED
              BCM4387-WIFI=DETECTED
              BCM4387-BT=DETECTED
              framebuffer/DRM=ENUMERATED
            ipad-linux: FIRST_BOOT_DIAGNOSTICS_COMPLETE
            """
        )

        self.assertEqual(result["last_stage"], "diagnostics")
        self.assertEqual(result["cpu_nodes"], 8)
        self.assertEqual(result["smp"], "PASS")
        self.assertEqual(result["nvme"], "DETECTED")
        self.assertEqual(result["usb"], "ENUMERATED")
        self.assertEqual(result["typec"], "REGISTERED")
        self.assertEqual(result["typec_entries"], 1)
        self.assertEqual(result["wifi4387"], "DETECTED")
        self.assertEqual(result["bt4387"], "DETECTED")
        self.assertEqual(result["pci_functions"], 3)
        self.assertEqual(result["graphics"], "ENUMERATED")
        self.assertFalse(result["linux_panic"])

    def test_kernel_only_failure(self):
        result = self.analyze(
            """
            m1n1
            Linux version 6.x-test
            Kernel panic - not syncing: No working init found
            """
        )

        self.assertEqual(result["last_stage"], "linux")
        self.assertTrue(result["linux_panic"])
        self.assertEqual(result["smp"], "unknown")
        self.assertEqual(result["usb"], "unknown")
        self.assertEqual(result["typec"], "unknown")
        self.assertEqual(result["wifi4387"], "unknown")

    def test_stage2_exception(self):
        result = self.analyze(
            """
            ipad-linux: AArch64 exception
              ESR=0x0000000096000004
            """
        )

        self.assertEqual(result["last_stage"], "no-known-marker")
        self.assertTrue(result["aarch64_exception"])


if __name__ == "__main__":
    unittest.main()
