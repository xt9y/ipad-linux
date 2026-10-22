#!/usr/bin/env python3

import hashlib
import pathlib
import plistlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
DIFF_TOOL = ROOT / "tools" / "j407-firmware-diff.py"


def write_manifest(root: pathlib.Path, manifest: dict) -> pathlib.Path:
    root.mkdir(parents=True, exist_ok=True)
    with open(root / "BuildManifest.plist", "wb") as handle:
        plistlib.dump(manifest, handle)
    return root


def build_manifest(
    product_version: str,
    build_number: str,
    iboot_digest: bytes,
    unique_build_id: bytes,
    nerd_gate: str,
    nerd_ecid: int,
) -> dict:
    component = {
        "Digest": iboot_digest,
        "BuildNumber": "iBoot-8963.140.26",
        "Info": {
            "Path": "Firmware/dfu/iBoot.dfu.imag3",
            "Personalize": True,
            "RestoreRequestRules": [
                {"Actions": [{"Action": {"Personalize": {"Affects": ["iBoot"]}}}]}
            ],
        },
    }
    sep = {
        "Digest": bytes(range(32)),
        "BuildNumber": "sep firmware",
        "Info": {"Path": "Firmware/sep/os/sepos.imap"},
    }
    return {
        "ProductType": "iPad13,16",
        "ProductVersion": product_version,
        "ManifestVersion": 3,
        "UniqueBuildID": unique_build_id,
        "NeRDGate": nerd_gate,
        "NeRDECIDGate": nerd_ecid,
        "ECDID": 0,
        "BuildIdentities": [
            {
                "ApChipID": 0x8103,
                "ApBoardID": 0x10,
                "ApSecurityDomain": 1,
                "Info": {
                    "Variant": "Customer IPSW",
                    "RestoreBehavior": "Update",
                    "BuildNumber": build_number,
                    "DeviceClass": "J407AP",
                },
                "Manifest": {"iBoot": component, "SE.OS": sep},
            }
        ],
    }


class FirmwareDiffTest(unittest.TestCase):
    def run_tool(self, manifest_a: pathlib.Path, manifest_b: pathlib.Path, *flags: str):
        return subprocess.run(
            [sys.executable, str(DIFF_TOOL), str(manifest_a), str(manifest_b), *flags],
            text=True,
            capture_output=True,
        )

    def test_diff_reports_changes_and_redacts_device_unique_values(self):
        manifest_a = build_manifest(
            "27.0.1",
            "24A446",
            b"\xaa" * 20,
            b"\x01\x02\x03\x04",
            "open",
            1234567,
        )
        manifest_b = build_manifest(
            "27.0.2",
            "24A500",
            b"\xcc" * 20,
            b"\x11\x22\x33\x44",
            "closed",
            1234567,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path_a = write_manifest(pathlib.Path(tmp, "a"), manifest_a)
            path_b = write_manifest(pathlib.Path(tmp, "b"), manifest_b)
            result = self.run_tool(path_a, path_b)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("product_type: same: iPad13,16", result.stdout)
        self.assertIn(
            "product_version: changed: 27.0.1 -> 27.0.2", result.stdout
        )
        a_prefix = hashlib.sha256(b"\x01\x02\x03\x04").hexdigest()[:16]
        b_prefix = hashlib.sha256(b"\x11\x22\x33\x44").hexdigest()[:16]
        self.assertIn(f"unique_build_id: changed: {a_prefix} -> {b_prefix}", result.stdout)
        self.assertIn("policy (NeRD-type fragments across the manifest)", result.stdout)
        self.assertIn("changed:   NeRDGate: open -> closed", result.stdout)
        self.assertIn("NeRDECIDGate=<redacted>", result.stdout)
        a_digest = hashlib.sha256(b"\xaa" * 20).hexdigest()[:16]
        b_digest = hashlib.sha256(b"\xcc" * 20).hexdigest()[:16]
        self.assertIn(f"[changed]   iBoot  digest {a_digest} -> {b_digest}", result.stdout)
        sep_prefix = hashlib.sha256(bytes(range(32))).hexdigest()[:16]
        self.assertIn(f"[identical] SE.OS  build=sep firmware  digest={sep_prefix}", result.stdout)
        self.assertIn("rules=1", result.stdout)
        self.assertIn("Personalize", result.stdout)
        self.assertIn("      build_number: changed: 24A446 -> 24A500", result.stdout)
        self.assertIn("      chipid: same: 33027", result.stdout)
        # Nothing device-unique may ever appear in the report.
        self.assertNotIn("1234567", result.stdout)

    def test_identical_manifests_are_reported_as_no_differences(self):
        manifest = build_manifest(
            "27.0.1", "24A446", b"\xaa" * 20, b"\x01\x02\x03\x04", "open", 1234567
        )
        with tempfile.TemporaryDirectory() as tmp:
            path_a = write_manifest(pathlib.Path(tmp, "a"), manifest)
            path_b = write_manifest(pathlib.Path(tmp, "b"), manifest)
            result = self.run_tool(path_a, path_b, "--fail-on-difference")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("result: no differences", result.stdout)
        self.assertIn("differences: 0", result.stdout)

    def test_fail_on_difference_flag_returns_one(self):
        manifest_a = build_manifest(
            "27.0.1", "24A446", b"\xaa" * 20, b"\x01\x02\x03\x04", "open", 1234567
        )
        manifest_b = build_manifest(
            "27.0.2", "24A446", b"\xaa" * 20, b"\x01\x02\x03\x04", "open", 1234567
        )
        with tempfile.TemporaryDirectory() as tmp:
            path_a = write_manifest(pathlib.Path(tmp, "a"), manifest_a)
            path_b = write_manifest(pathlib.Path(tmp, "b"), manifest_b)
            result = self.run_tool(path_a, path_b, "--fail-on-difference")

        self.assertEqual(result.returncode, 1)
        self.assertIn("differences: 1", result.stdout)

    def test_directory_input_and_missing_manifest_handling(self):
        manifest = build_manifest(
            "27.0.1", "24A446", b"\xaa" * 20, b"\x01\x02\x03\x04", "open", 1234567
        )
        with tempfile.TemporaryDirectory() as tmp:
            dir_a = write_manifest(pathlib.Path(tmp, "a"), manifest)
            dir_b = write_manifest(pathlib.Path(tmp, "b"), manifest)
            result = self.run_tool(dir_a, dir_b)
            self.assertEqual(result.returncode, 0, result.stderr)

            missing = self.run_tool(dir_a, pathlib.Path(tmp, "b", "Nope.plist"))
            self.assertEqual(missing.returncode, 2)
            self.assertIn("no manifest at", missing.stderr)


if __name__ == "__main__":
    unittest.main()
