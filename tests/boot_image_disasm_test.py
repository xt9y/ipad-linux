#!/usr/bin/env python3

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

import importlib.util


def load_module():
    spec = importlib.util.spec_from_file_location(
        "boot_image_disasm", ROOT / "tools" / "boot-image-disasm.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boot_image_disasm = load_module()


class BootImageDisasmTest(unittest.TestCase):
    def test_kown_encodings_decode(self):
        # NOP, RET, B +8 — canonical AArch64 encodings, little-endian.
        data = bytes.fromhex("1f2003d5")   # nop
        data += bytes.fromhex("c0035fd6")  # ret
        data += bytes.fromhex("02000014")  # b  +8
        report = boot_image_disasm.analyze(data)
        self.assertIn("## coverage", report)
        self.assertIn("decoded instructions: 3", report)
        self.assertIn("nop", report)
        self.assertIn("ret", report)
        self.assertIn("## mnemonic histogram", report)
        self.assertIn("## call landscape", report)

    def test_coverage_percent_line_present(self):
        data = bytes.fromhex("1f2003d5")
        report = boot_image_disasm.analyze(data)
        self.assertRegex(report, r"decode coverage: \d+\.\d%")

    def test_literal_pool_constant_scan(self):
        # nop x2, a udf (zeros) run, then a planted DRAM-base constant and
        # more zero padding, closed by ret.
        data = bytes.fromhex("1f2003d5") * 2            # 0..8
        data += bytes(16)                                # udf run 8..24
        data += (0x800000000).to_bytes(8, "little")      # constant @24
        data += bytes(16)                                # udf run 32..48
        data += bytes.fromhex("c0035fd6")                # ret @48

        report = boot_image_disasm.analyze(data)
        self.assertIn("## literal-pool address-constant candidates", report)
        self.assertIn("DRAM region (base 0x800000000)", report)
        # LE constant 0x800000000 rendered as 0x%016x
        self.assertIn("0x0000000800000000", report)
        self.assertIn("udf-run spans", report)

    def test_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "image.bin"
            src.write_bytes(bytes.fromhex("1f2003d5") * 4)
            out = Path(tmp) / "report.txt"
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "boot-image-disasm.py"),
                 str(src), "--out", str(out)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("## coverage", out.read_text())


if __name__ == "__main__":
    unittest.main()
