#!/usr/bin/env python3

import struct
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

import importlib.util


def load_module():
    spec = importlib.util.spec_from_file_location(
        "boot_image_calls", ROOT / "tools" / "boot-image-calls.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boot_image_calls = load_module()

PACIBSP = 0xD503237F
NOP = 0xD503201F
RET = 0xD65F03C0


def bl_word(pc: int, target: int) -> int:
    return 0x94000000 | ((target - pc) >> 2)


class BootImageCallsTest(unittest.TestCase):
    def synthetic_image(self) -> bytes:
        # func1 @0x0: pacibsp; bl 0x108; nop; nop | pad nops to 0x108
        # func2 @0x108: pacibsp; bl 0x120; nop      | pad nops to 0x120
        # func3 @0x120: pacibsp; ret
        out = struct.pack("<IIII",
                          PACIBSP, bl_word(0x4, 0x108), NOP, NOP)
        out += struct.pack("<I", NOP) * ((0x108 - len(out)) // 4)
        out += struct.pack("<III", PACIBSP, bl_word(0x10C, 0x120), NOP)
        out += struct.pack("<I", NOP) * ((0x120 - len(out)) // 4)
        out += struct.pack("<II", PACIBSP, RET)
        return out

    def test_bl_edges_resolve_targets(self):
        rows = boot_image_calls.decode_rows(self.synthetic_image())
        edges = boot_image_calls.bl_edges(rows)
        self.assertEqual(edges, [(0x4, 0x108), (0x10C, 0x120)])

    def test_function_starts_and_enclosing(self):
        rows = boot_image_calls.decode_rows(self.synthetic_image())
        starts = boot_image_calls.function_starts(rows)
        self.assertEqual(starts, [0x0, 0x108, 0x120])
        self.assertEqual(boot_image_calls.enclosing(0x4, starts), 0x0)
        self.assertEqual(boot_image_calls.enclosing(0x10C, starts), 0x108)
        self.assertIsNone(boot_image_calls.enclosing(0x4, []))

    def test_reverse_levels_reaches_caller_chain(self):
        rows = boot_image_calls.decode_rows(self.synthetic_image())
        edges = boot_image_calls.bl_edges(rows)
        starts = boot_image_calls.function_starts(rows)
        levels = boot_image_calls.reverse_levels(0x120, edges, starts)
        self.assertEqual(levels.get(1), {0x108})
        self.assertEqual(levels.get(2), {0x0})
        self.assertNotIn(3, levels)

    def test_analyze_writes_census_report(self):
        report = boot_image_calls.analyze(self.synthetic_image())
        self.assertIn("## bl edge census", report)
        self.assertIn("bl call edges: 2", report)
        self.assertIn("pacibsp function starts: 3", report)
        self.assertIn("## most-called routines", report)
        self.assertIn("  +0x108: 1", report)
        self.assertIn("## most-calling functions", report)
        self.assertIn("  +0x0: 1", report)

    def test_cli_report_and_caller_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "img.bin"
            image.write_bytes(self.synthetic_image())
            report = Path(tmp) / "report.txt"
            rc = boot_image_calls.main(
                [str(image), "--report", str(report),
                 "--chain", "0x120", "--depth", "3"])
            self.assertEqual(rc, 0)
            text = report.read_text()
            self.assertIn("## bl edge census", text)
            self.assertIn("## caller levels reaching +0x120 (depth 3)",
                          text)
            self.assertIn("level 2 (1 fns): +0x0", text)


if __name__ == "__main__":
    unittest.main()
