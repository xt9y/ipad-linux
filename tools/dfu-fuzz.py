#!/usr/bin/env python3
"""Bounded, read-side DFU class-protocol harness for Apple DFU.

Modes:
  (default)          run the vector set against the offline state mirror
                     derived from the 2026-10-24 physical J407 capture.
                     No USB access happens in this mode.
  --device           issue the same read-side vectors against a real
                     05ac:1227 DFU device via pyusb. Per-session approval
                     is explicit: requires --allow-device as well.

Safety contract (enforced structurally, tested):
  - only class requests in READ_SIDE_REQUESTS are ever issued
    (UPLOAD=2, GETSTATUS=3, CLRSTATUS=4, GETSTATE=5, ABORT=6);
  - DNLOAD (0x01) and DETACH (0x00) are never constructed — adding them
    to any vector raises AssertionError in build_vectors();
  - logs never contain device-unique strings, only byte values and
    digest prefixes.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time

USB_VID = 0x05AC
USB_PID = 0x1227

READ_SIDE_REQUESTS = frozenset({0x02, 0x03, 0x04, 0x05, 0x06})

VN_FORBIDDEN = frozenset({0x00, 0x01})

CLASS_REQUEST_NAMES = {
    0x02: "UPLOAD",
    0x03: "GETSTATUS",
    0x04: "CLRSTATUS",
    0x05: "GETSTATE",
    0x06: "ABORT",
}

# Mirror of the read-side behavior recorded on the physical J407 in
# hardware DFU on 2026-10-24 (see docs/boot-chain-recon-24a446.md).
# Vectors absent from this mirror are UNKNOWN; the offline run reports
# them as UNRECORDED instead of inventing behavior.
MIRROR = {
    "GETSTATUS": {"bytes": [0x00, 0x32, 0x00, 0x00, 0x02, 0x00]},
    "GETSTATE": {"bytes": [0x02]},
    "UPLOAD": {"outcome": "TIMEOUT"},
}


class Vector:
    __slots__ = ("name", "bm_request_type", "b_request", "w_value", "w_index", "length")

    def __init__(self, name, b_request, data_len=0, w_value=0, w_index=0,
                 bm_request_type=0xA1):
        assert b_request in READ_SIDE_REQUESTS, (
            f"disallowed class request 0x{b_request:02x} for vector {name}"
        )
        assert b_request not in VN_FORBIDDEN, (
            f"write-side class request {b_request:#x} must never be issued"
        )
        self.name = name
        self.bm_request_type = bm_request_type
        self.b_request = b_request
        self.w_value = w_value
        self.w_index = w_index
        self.length = data_len


def build_vectors() -> list[Vector]:
    vectors: list[Vector] = []
    for _ in range(2):
        vectors.append(Vector("GETSTATUS", 0x03, data_len=6))
        vectors.append(Vector("GETSTATE", 0x05, data_len=1))
    vectors.append(Vector("ABORT", 0x06))
    vectors.append(Vector("CLRSTATUS", 0x04))
    for size in (8, 16, 256, 1024):
        vectors.append(Vector(f"UPLOAD({size})", 0x02, data_len=size))
    vectors.append(Vector("GETSTATUS(wrong-interface)", 0x03, data_len=6, w_index=1))
    return vectors


def mirror_lookup(vector: Vector):
    base = CLASS_REQUEST_NAMES[vector.b_request]
    entry = MIRROR.get(base)
    if entry is None:
        return "UNRECORDED", None
    if base == "GETSTATUS":
        if vector.w_index != 0:
            return "UNRECORDED", None
        return "OK", entry["bytes"]
    if base == "GETSTATE":
        return "OK", entry["bytes"]
    if base == "UPLOAD":
        return entry["outcome"], None
    return "UNRECORDED", None


def run_offline() -> int:
    print("offline mode: physical capture mirror (no USB)")
    print("vector,class-request,wValue,wIndex,mirror-outcome,detail")
    for vector in build_vectors():
        outcome, detail = mirror_lookup(vector)
        text = (",".join(str(x) for x in (
            vector.name, f"0x{vector.b_request:02x}", vector.w_value,
            vector.w_index, outcome, detail if detail else "-")))
        print(text)
    print("offline pass complete")
    return 0


def run_device() -> int:
    import usb.core
    import usb.util

    dev = usb.core.find(idVendor=USB_VID, idProduct=USB_PID)
    if dev is None:
        print("no 05ac:1227 device present", file=sys.stderr)
        return 2
    try:
        dev.set_configuration()
    except Exception:
        pass
    log = open(f"dfu-fuzz-log-{time.strftime('%Y%m%d-%H%M%S')}.tsv", "w")
    log.write("time,vector,request,wValue,wIndex,status,result,digest-prefix\n")

    for vector in build_vectors():
        stamp = time.strftime("%H:%M:%S")
        try:
            ret = dev.ctrl_transfer(
                vector.bm_request_type, vector.b_request,
                vector.w_value, vector.w_index,
                vector.length if vector.b_request not in (0x04, 0x06) else 0,
                timeout=2000,
            )
            data = bytes(ret)
            status = "OK"
            result = f"bytes={len(data)} head={data[:8].hex()}"
            digest = hashlib.sha256(data).hexdigest()[:16] if data else "-"
        except Exception as exc:
            status = type(exc).__name__
            result = str(exc)[:80]
            digest = "-"
        line = ",".join((
            stamp, vector.name, f"0x{vector.b_request:02x}",
            str(vector.w_value), str(vector.w_index), status, result, digest))
        print(line)
        log.write(line + "\n")

    log.close()
    print("device pass complete (read-side vectors only)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", action="store_true",
                        help="target real USB DFU device (requires --allow-device)")
    parser.add_argument("--allow-device", action="store_true",
                        help="explicit per-session approval to touch the device")
    args = parser.parse_args()
    if args.device and not args.allow_device:
        print("--device requires --allow-device (explicit per-session approval)",
              file=sys.stderr)
        return 2
    if args.device:
        return run_device()
    return run_offline()


if __name__ == "__main__":
    raise SystemExit(main())
