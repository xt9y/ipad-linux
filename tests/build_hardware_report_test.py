#!/usr/bin/env python3

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "build-hardware-report.py"
ANALYZER = ROOT / "tools" / "analyze-first-boot.py"


def sample_log() -> str:
    return """
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
    """


class HardwareReportBuilderTest(unittest.TestCase):
    def run_report(self, tool: pathlib.Path, tmpdir: pathlib.Path) -> tuple[dict, str]:
        boot = tmpdir / "boot.log"
        boot.write_text(sample_log(), encoding="utf-8")
        commits = tmpdir / "SOURCE_COMMITS"
        commits.write_text("ipad-linux=abc\nlinux=def\nm1n1=ghi\n", encoding="utf-8")
        sums = tmpdir / "SHA256SUMS"
        sums.write_text("deadbeef  Image\n", encoding="utf-8")
        prefix = tmpdir / "report"

        subprocess.run(
            [
                sys.executable,
                str(tool),
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
        return data, text

    def assert_report(self, data: dict, text: str) -> None:
        self.assertEqual(data["schema"], 1)
        self.assertEqual(data["target"]["product_type"], "iPad13,16")
        self.assertEqual(data["target"]["ipad_os"], "26.5 (23F77)")
        self.assertEqual(data["boot_analysis"]["last_stage"], "diagnostics")
        self.assertEqual(data["boot_analysis"]["wlan_interface"], "PRESENT")
        self.assertIn("J407 physical boot report", text)
        self.assertIn("ipad-linux=abc", text)
        self.assertNotIn(platform_hostname(), text)

    def test_builds_json_and_markdown_from_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, text = self.run_report(TOOL, pathlib.Path(tmp))
            self.assert_report(data, text)

    def test_builds_report_when_tools_are_bundled_as_siblings(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = pathlib.Path(tmp)
            kit = tmpdir / "kit"
            kit.mkdir()
            shutil.copy2(TOOL, kit / "build-hardware-report.py")
            shutil.copy2(ANALYZER, kit / "analyze-first-boot.py")
            data, text = self.run_report(kit / "build-hardware-report.py", tmpdir)
            self.assert_report(data, text)


def platform_hostname() -> str:
    # The report builder should never request or embed the hostname.
    import socket

    return socket.gethostname()


if __name__ == "__main__":
    unittest.main()
