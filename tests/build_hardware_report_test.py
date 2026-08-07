#!/usr/bin/env python3

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "build-hardware-report.py"


class HardwareReportBuilderTest(unittest.TestCase):
    def test_builds_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = pathlib.Path(tmp)
            boot = tmpdir / "boot.log"
            boot.write_text(
                """
                m1n1 test
                Linux version 6.x
                ipad-linux early userspace
                  cpu_nodes=8 (expected 8 for full J407 SMP)
                  nvme_controllers=1
                  block_devices=2
                  graphics_entries=1
                  usb_entries=4
                  typec_entries=1
                  pci_functions=3
                  net_interfaces=2
                  wlan_interfaces=1
                  bluetooth_entries=1
                  input_entries=2
                  sound_entries=0
                  SMP=PASS
                  ANS2/NVMe=DETECTED
                  USB=ENUMERATED
                  TYPEC=REGISTERED
                  BCM4387-WIFI=DETECTED
                  BCM4387-BT=DETECTED
                  WLAN-INTERFACE=PRESENT
                  BLUETOOTH-CLASS=PRESENT
                  INPUT=ENUMERATED
                  SOUND=NOT_ENUMERATED
                  framebuffer/DRM=ENUMERATED
                ipad-linux: FIRST_BOOT_DIAGNOSTICS_COMPLETE
                """,
                encoding="utf-8",
            )
            commits = tmpdir / "SOURCE_COMMITS"
            commits.write_text("ipad-linux=abc\nlinux=def\nm1n1=ghi\n", encoding="utf-8")
            sums = tmpdir / "SHA256SUMS"
            sums.write_text("deadbeef  Image\n", encoding="utf-8")
            prefix = tmpdir / "report"

            subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--boot-log",
                    str(boot),
                    "--source-commits",
                    str(commits),
                    "--checksums",
                    str(sums),
                    "--ipad-os",
                    "26.5 (23F77)",
                    "--output-prefix",
                    str(prefix),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            data = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
            text = prefix.with_suffix(".md").read_text(encoding="utf-8")

            self.assertEqual(data["schema"], 1)
            self.assertEqual(data["target"]["product_type"], "iPad13,16")
            self.assertEqual(data["target"]["ipad_os"], "26.5 (23F77)")
            self.assertEqual(data["boot_analysis"]["last_stage"], "diagnostics")
            self.assertEqual(data["boot_analysis"]["wlan_interface"], "PRESENT")
            self.assertIn("J407 physical boot report", text)
            self.assertIn("ipad-linux=abc", text)
            self.assertNotIn(platform_hostname(), text)


def platform_hostname() -> str:
    # Keep the test independent of whether the hostname happens to occur in
    # unrelated generated data. The report builder should never request it.
    import socket

    return socket.gethostname()


if __name__ == "__main__":
    unittest.main()
