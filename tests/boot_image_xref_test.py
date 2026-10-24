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
        "boot_image_xref", ROOT / "tools" / "boot-image-xref.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boot_image_xref = load_module()


class BootImageXrefTest(unittest.TestCase):
    def synthetic_image(self) -> bytes:
        code = bytes.fromhex("a00000b0")   # adrp x0, page +0x15 (img coords)
        code += bytes.fromhex("00000b91")  # add  x0, x0, #0x2c0 -> 0x152c0
        code += bytes.fromhex("1f2003d5") * 2  # 2 nops
        data = code + bytes(0x152c8 - len(code))
        data += b"BOOT-COMMAND-TABLE\x00"  # resident string inside page 0x15
        data += b"getenv\x00"
        return data

    def test_adrp_add_pair_resolves_to_target_page(self):
        rows = boot_image_xref.decode_rows(self.synthetic_image())
        pairs = boot_image_xref.resolve_adrp_add(rows)
        self.assertEqual(len(pairs), 1)
        target, pc = pairs[0]
        self.assertEqual(target, 0x152C0)
        self.assertEqual(pc, 0x0)

    def test_report_names_referenced_page_and_strings(self):
        report = boot_image_xref.analyze(self.synthetic_image())
        self.assertIn("## pc-relative data-reference map", report)
        self.assertIn("adrp(+add) data references resolved: 1", report)
        self.assertIn("page+0x15", report)
        self.assertIn('"BOOT-COMMAND-TABLE"', report)

    def test_string_anchored_references(self):
        report = boot_image_xref.analyze(self.synthetic_image())
        self.assertIn("## string-anchored references", report)
        self.assertIn('"getenv"', report)
        # the page holding getenv is referenced once, from pc 0x0
        self.assertIn("page+0x15:   1 refs", report)
        self.assertIn("from +0x0", report)

    def test_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "image.bin"
            src.write_bytes(self.synthetic_image())
            out = Path(tmp) / "report.txt"
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "boot-image-xref.py"),
                 str(src), "--out", str(out)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("## pc-relative data-reference map", out.read_text())


if __name__ == "__main__":
    unittest.main()
