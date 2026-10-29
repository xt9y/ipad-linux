#!/usr/bin/env python3
"""LOCAL-ONLY J407 recovery consumer-trigger arc, PART 3 (2026-10-29).

Residual: 'bootx' bR=1 against the vecB staging (part 2 left 412 B of the
synthetic unsigned IMG4 staged after go-vecB; staging state unknown).

Contract unchanged: sanctioned verbs only; no DETACH/ABORT/CLRSTATUS; no
DFU-class; no saveenv; personality re-checked every step; drains after all.

Claim lesson: the handle that performs the first successful bulk write stays
usable; FRESH handles get errno 13. This part therefore SKIPS bulk writes
and runs control-only triggers, first on the residual staging, then on a
re-stage via the same persistent handle consumed for everything.
"""

import hashlib
import struct
import sys
import time

import usb.core

OUTDIR = "/private/var/folders/b3/v6rf5zmn1cx3cyw0tvyp53nc0000gn/T/opencode"
VID = 0x05AC
PIDS = (0x1280, 0x1281, 0x1282, 0x1283)
T_CTRL = 2000
T_HEALTH = 1500


def log_and_print(log, name, kind, detail, digest="-"):
    stamp = time.strftime("%H:%M:%S")
    detail = str(detail).replace("\n", "; ").replace(",", ";")
    line = f"{stamp},{name},{kind},{detail},{digest}"
    print(line, flush=True)
    log.write(line + "\n")
    log.flush()


def find_dev():
    for pid in PIDS:
        d = usb.core.find(idVendor=VID, idProduct=pid)
        if d is not None:
            return d
    return None


def drain(log, name, dev=None):
    d = dev
    if d is None:
        d = find_dev()
    if d is None:
        log_and_print(log, f"drain[{name}]", "IN", "no device")
        return False
    try:
        data = bytes(d.ctrl_transfer(0xC0, 0, 0, 0, 0x200, timeout=T_HEALTH))
        dig = hashlib.sha256(data).hexdigest()[:16] if data else "-"
        hexp = data[:48].hex()
        log_and_print(log, f"drain[{name}]", "IN", f"OK len={len(data)} hex={hexp}", dig)
        return True
    except Exception as exc:
        log_and_print(log, f"drain[{name}]", "IN",
                      f"{type(exc).__name__} {str(exc)[:60]}")
        return False


def payload_vec_b():
    im4r_body = bytes(64)
    im4r = b"IM4R" + struct.pack(">I", len(im4r_body)) + im4r_body
    im4m_inner = b"\x30\x82" + struct.pack(">H", 320) + bytes(320)
    im4m = b"IM4M" + struct.pack(">I", len(im4m_inner)) + im4m_inner
    body = im4r + im4m
    return b"IMG4" + struct.pack(">I", len(body)) + body


def main() -> int:
    log = open(f"{OUTDIR}/dfu-probe-log-{time.strftime('%Y%m%d')}-boot-trigger3.tsv", "w")
    log.write("# LOCAL ONLY - never commit. class-level protocol bytes only\n")
    log.write("# prior: go-bare SILENT; go-vecA SILENT; go-vecB SILENT (412B staged)\n")
    log.write("# columns: time,name,kind,detail,digest-prefix\n")

    dev = find_dev()
    if dev is None:
        print("no recovery personality present", file=sys.stderr)
        return 2
    try:
        dev.set_configuration()
    except Exception as exc:
        log_and_print(log, "init", "OUT", f"{type(exc).__name__} {str(exc)[:60]}")
    log_and_print(log, "init", "IN", f"persistent handle 05ac:{dev.idProduct:04x}")

    steps = [
        ("bootx-residual", "bootx", None),
        ("go-fresh", "go", payload_vec_b()),
        ("bootx-fresh", "bootx", payload_vec_b()),
    ]
    for name, verb, payload in steps:
        if payload is not None:
            try:
                dev.ctrl_transfer(0x41, 0, 0, 0, b"", timeout=T_CTRL)
                n = dev.write(0x04, payload, timeout=T_CTRL)
                log_and_print(log, f"stage[{name}]", "OUT",
                              f"opener+bulk OK wrote={n}/{len(payload)} "
                              f"(persistent handle)",
                              hashlib.sha256(payload).hexdigest()[:16])
            except Exception as exc:
                log_and_print(log, f"stage[{name}]", "OUT",
                              f"{type(exc).__name__} {str(exc)[:60]} (staging skipped)")
        try:
            dev.ctrl_transfer(0x40, 1, 0, 0, verb.encode() + b"\0", timeout=T_CTRL)
            log_and_print(log, f"trigger[{name}]", "OUT", f"'{verb}' bR=1 sent")
        except Exception as exc:
            log_and_print(log, f"trigger[{name}]", "OUT",
                          f"{type(exc).__name__} {str(exc)[:60]}")
        time.sleep(1.5)
        if not drain(log, name, dev):
            time.sleep(1.5)
            if not drain(log, name + "-retry", dev):
                log_and_print(log, "STOP", "-", f"console dead after '{verb}'")
                break
        pd = find_dev()
        if pd is None or pd.idProduct not in PIDS:
            log_and_print(log, "STOP", "-", "personality flipped/vanished")
            break
        log_and_print(log, f"pid[{name}]", "IN", f"05ac:{pd.idProduct:04x}")

    try:
        dev.ctrl_transfer(0x40, 0, 0, 0, b"getenv build-style\0", timeout=T_CTRL)
        log_and_print(log, "final:getenv", "OUT", "bR=0 sent OK")
    except Exception as exc:
        log_and_print(log, "final:getenv", "OUT", f"{type(exc).__name__} {str(exc)[:60]}")
    drain(log, "final", dev)
    pd = find_dev()
    if pd is not None:
        log_and_print(log, "pid[final]", "IN", f"05ac:{pd.idProduct:04x}")
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
