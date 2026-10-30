#!/usr/bin/env python3
"""LOCAL-ONLY J407 recovery consumer-trigger arc, PART 2 (2026-10-29).

Residual ladder after part-1 (go-bare, go-vecA were SILENT; vecB staging
failed on a macOS claim race). Same contract as part 1:
  - verbs only in sanctioned form: ctrl 0x40/1 'go'/'bootx' after send_buffer;
  - console via 0x40/0; no DETACH/ABORT/CLRSTATUS, no DFU-class, no saveenv;
  - synthetic unsigned payloads only; personality re-checked every step;
  - claim race handled by retry loop (IOKit re-attach ~3 s lesson, §7.7).
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


def pid_check(log, tag):
    d = find_dev()
    if d is None:
        log_and_print(log, f"pid[{tag}]", "IN", "GONE")
        return False
    log_and_print(log, f"pid[{tag}]", "IN", f"05ac:{d.idProduct:04x}")
    return d.idProduct in PIDS


def drain(log, name):
    d = find_dev()
    if d is None:
        log_and_print(log, f"drain[{name}]", "IN", "no device")
        return False
    try:
        data = bytes(d.ctrl_transfer(0xC0, 0, 0, 0, 0x200, timeout=T_HEALTH))
        dig = hashlib.sha256(data).hexdigest()[:16] if data else "-"
        log_and_print(log, f"drain[{name}]", "IN",
                      f"OK len={len(data)} hex={data[:48].hex()}", dig)
        return True
    except Exception as exc:
        log_and_print(log, f"drain[{name}]", "IN",
                      f"{type(exc).__name__} {str(exc)[:60]}")
        return False


def stage(d, log, name, payload):
    """Sanctioned upload shape with claim-race retry."""
    for attempt in range(4):
        try:
            d.set_configuration()
            d.ctrl_transfer(0x41, 0, 0, 0, b"", timeout=T_CTRL)
            n = d.write(0x04, payload, timeout=T_CTRL)
            if n == len(payload):
                log_and_print(log, f"stage[{name}]",
                              "OUT", f"opener+bulk OK (attempt {attempt}) "
                              f"wrote={n}/{len(payload)}",
                              hashlib.sha256(payload).hexdigest()[:16])
                if len(payload) % 512 == 0 and payload:
                    d.write(0x04, b"", timeout=T_CTRL)
                    log_and_print(log, f"stage[{name}]:zlp", "OUT", "zero-length OK")
                return True
            log_and_print(log, f"stage[{name}]", "OUT",
                          f"attempt {attempt}: wrote {n}/{len(payload)}")
        except Exception as exc:
            log_and_print(log, f"stage[{name}]", "OUT",
                          f"attempt {attempt}: {type(exc).__name__} {str(exc)[:60]}")
        time.sleep(0.6)
    return False


def payload_vec_b():
    im4r_body = bytes(64)
    im4r = b"IM4R" + struct.pack(">I", len(im4r_body)) + im4r_body
    im4m_inner = b"\x30\x82" + struct.pack(">H", 320) + bytes(320)
    im4m = b"IM4M" + struct.pack(">I", len(im4m_inner)) + im4m_inner
    body = im4r + im4m
    return b"IMG4" + struct.pack(">I", len(body)) + body


def main() -> int:
    log = open(f"{OUTDIR}/dfu-probe-log-{time.strftime('%Y%m%d')}-boot-trigger2.tsv", "w")
    log.write("# LOCAL ONLY - never commit. class-level protocol bytes only\n")
    log.write("# part-1 already ran: go-bare SILENT, go-vecA SILENT, vecB claim-race abort\n")
    log.write("# columns: time,name,kind,detail,digest-prefix\n")

    plan = [
        ("go-vecB", payload_vec_b, "go", 1),
        ("bootx-vecC", payload_vec_b, "bootx", 1),
    ]
    for name, vec, verb, br in plan:
        d = find_dev()
        if d is None:
            log_and_print(log, "STOP", "-", "device gone")
            break
        if not stage(d, log, name, vec()):
            continue  # skip vector, keep ladder
        try:
            d2 = find_dev()
            if d2 is None:
                log_and_print(log, "STOP", "-", "device gone before trigger")
                break
            d2.set_configuration()
            d2.ctrl_transfer(0x40, br, 0, 0, verb.encode() + b"\0", timeout=T_CTRL)
            log_and_print(log, f"trigger[{name}]", "OUT", f"'{verb}' bR={br} sent")
        except Exception as exc:
            log_and_print(log, f"trigger[{name}]", "OUT",
                          f"{type(exc).__name__} {str(exc)[:60]}")
        time.sleep(1.5)
        if not drain(log, name):
            time.sleep(1.5)
            if not drain(log, name + "-retry"):
                log_and_print(log, "STOP", "-", f"console dead after '{verb}'")
                break
        if not pid_check(log, name):
            log_and_print(log, "STOP", "-", "personality flipped/vanished")
            break

    try:
        d5 = find_dev()
        if d5 is not None:
            d5.set_configuration()
            d5.ctrl_transfer(0x40, 0, 0, 0, b"getenv build-style\0", timeout=T_CTRL)
            log_and_print(log, "final:getenv", "OUT", "bR=0 sent OK")
    except Exception as exc:
        log_and_print(log, "final:getenv", "OUT", f"{type(exc).__name__} {str(exc)[:60]}")
    drain(log, "final")
    pid_check(log, "final")
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
