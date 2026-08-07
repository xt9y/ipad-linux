#!/usr/bin/env python3

import importlib.util
import pathlib
import struct
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check-z2fw.py"
SPEC = importlib.util.spec_from_file_location("check_z2fw", TOOL)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def pad4(data: bytes) -> bytes:
    return data + b"\0" * ((-len(data)) & 3)


def container(*records: bytes) -> bytes:
    return b"Z2FW" + struct.pack("<I", 1) + b"".join(records)


def payload_record(command: int, payload: bytes) -> bytes:
    return struct.pack("<II", command, len(payload)) + pad4(payload)


class Z2FWValidatorTest(unittest.TestCase):
    def test_valid_hbpp_style_container(self):
        data = container(
            payload_record(MODULE.LOAD_COMMAND_INIT_PAYLOAD, b"init"),
            payload_record(MODULE.LOAD_COMMAND_SEND_BLOB, b"\x01\x30payload"),
            struct.pack("<II", MODULE.LOAD_COMMAND_SEND_CALIBRATION, 0x12340000),
        )
        result = MODULE.validate(data)
        self.assertEqual(result["commands"], 3)
        self.assertEqual(result["init_payloads"], 1)
        self.assertEqual(result["blobs"], 1)
        self.assertEqual(result["calibrations"], 1)

    def test_rejects_bad_magic(self):
        with self.assertRaisesRegex(ValueError, "bad magic"):
            MODULE.validate(b"NOPE" + struct.pack("<I", 1) + b"\0" * 8)

    def test_rejects_unknown_version(self):
        with self.assertRaisesRegex(ValueError, "unsupported Z2FW version"):
            MODULE.validate(b"Z2FW" + struct.pack("<I", 2) + b"\0" * 8)

    def test_rejects_payload_overrun(self):
        data = container(struct.pack("<II", MODULE.LOAD_COMMAND_SEND_BLOB, 64) + b"short")
        with self.assertRaisesRegex(ValueError, "overruns file"):
            MODULE.validate(data)

    def test_rejects_nonzero_padding(self):
        data = container(
            struct.pack("<II", MODULE.LOAD_COMMAND_INIT_PAYLOAD, 1) + b"x\0\x01\0"
        )
        with self.assertRaisesRegex(ValueError, "non-zero alignment padding"):
            MODULE.validate(data)

    def test_rejects_unknown_command(self):
        data = container(struct.pack("<II", 99, 0))
        with self.assertRaisesRegex(ValueError, "unknown Z2FW command"):
            MODULE.validate(data)


if __name__ == "__main__":
    unittest.main()
