#!/usr/bin/env python3
"""LOCAL-ONLY J407 recovery consumer-trigger arc (2026-10-29).

Approved goal: observe the IMG4 consumer chain live — stage synthetic
payloads via the sanctioned recovery upload shape, then issue the sanctioned
execution verbs ('go'/'bootx' on bRequest=1) and read the console.

Contract:
  - execution verbs ONLY in the pmd3/libirecovery sanctioned form:
      ctrl 0x40/1 'go'    after send_buffer (iBEC-execute shape)
      ctrl 0x40/1 'bootx' after send_buffer (kernel-execute shape)
  - console nouns only via ctrl 0x40/0 ('getenv' baseline; no setenv/saveenv);
  - NO DETACH(0x00)/ABORT(0x06)/CLRSTATUS(0x04), NO DFU-class (0x21/0xA1);
  - payloads: synthetic, unsigned, deterministic, <= ~1 KiB; no Apple data;
  - after EVERY step: console health drain + personality re-check
    (enumeration is the authority); halt on wedge or personality flip;
  - log = class-level protocol bytes only (never ECID/UDID/serial/nonces).
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
        log_and_print(log, f"pid[{tag}]", "IN", "GONE (device left recovery or re-enum)")
        return False
    log_and_print(log, f"pid[{tag}]", "IN", f"05ac:{d.idProduct:04x}")
    return d.idProduct in PIDS


def drain(log, name):
    """Console ring replay; returns (alive, hex-preview)."""
    d = find_dev()
    if d is None:
        log_and_print(log, f"drain[{name}]", "IN", "no device")
        return False, ""
    try:
        data = bytes(d.ctrl_transfer(0xC0, 0, 0, 0, 0x200, timeout=T_HEALTH))
        dig = hashlib.sha256(data).hexdigest()[:16] if data else "-"
        log_and_print(log, f"drain[{name}]", "IN",
                      f"OK len={len(data)} hex={data[:48].hex()}", dig)
        return True, data.hex()
    except Exception as exc:
        log_and_print(log, f"drain[{name}]", "IN",
                      f"{type(exc).__name__} {str(exc)[:60]}")
        return False, ""


def send_cmd(d, cmd, b_request):
    d.ctrl_transfer(0x40, b_request, 0, 0, cmd.encode() + b"\0", timeout=T_CTRL)


def stage(d, log, name, payload):
    """Sanctioned upload shape: ctrl 0x41/0 opener + bulk 0x04 (+ZLP if 512-mult)."""
    try:
        d.ctrl_transfer(0x41, 0, 0, 0, b"", timeout=T_CTRL)
        log_and_print(log, f"stage[{name}]:opener", "OUT", "0x41/0 OK")
    except Exception as exc:
        log_and_print(log, f"stage[{name}]:opener", "OUT",
                      f"{type(exc).__name__} {str(exc)[:60]}")
        return False
    try:
        n = d.write(0x04, payload, timeout=T_CTRL)
        log_and_print(log, f"stage[{name}]:payload", "OUT",
                      f"bulk 0x04 wrote={n}/{len(payload)}",
                      hashlib.sha256(payload).hexdigest()[:16])
        ok = n == len(payload)
    except Exception as exc:
        log_and_print(log, f"stage[{name}]:payload", "OUT",
                      f"{type(exc).__name__} {str(exc)[:60]}")
        ok = False
    if len(payload) % 512 == 0 and payload:
        try:
            d.write(0x04, b"", timeout=T_CTRL)
            log_and_print(log, f"stage[{name}]:zlp", "OUT", "zero-length OK")
        except Exception as exc:
            log_and_print(log, f"stage[{name}]:zlp", "OUT",
                          f"{type(exc).__name__} {str(exc)[:60]}")
    return ok


def payload_vec_a():
    # weakest shape: magic only
    return b"IMG4" + struct.pack("<I", 16) + bytes(16)


def payload_vec_b():
    # structural IMG4 shell, fully synthetic, unsigned: IM4R + IM4M boxes with
    # DER-SEQ-like headers but zero bodies (invalid trust content)
    im4r_body = bytes(64)
    im4r = b"IM4R" + struct.pack(">I", len(im4r_body)) + im4r_body
    im4m_inner = b"\x30\x82" + struct.pack(">H", 320) + bytes(320)  # SEQ hdr + zeros
    im4m = b"IM4M" + struct.pack(">I", len(im4m_inner)) + im4m_inner
    body = im4r + im4m
    return b"IMG4" + struct.pack(">I", len(body)) + body


def main() -> int:
    log = open(f"{OUTDIR}/dfu-probe-log-{time.strftime('%Y%m%d')}-boot-trigger.tsv", "w")
    log.write("# LOCAL ONLY - never commit. class-level protocol bytes only\n")
    log.write("# columns: time,name,kind,detail,digest-prefix\n")

    d = find_dev()
    if d is None:
        print("no recovery personality present", file=sys.stderr)
        return 2
    log_and_print(log, "census:pid", "IN", f"05ac:{d.idProduct:04x}")
    try:
        dev_cfg = d.get_active_configuration()
        log_and_print(log, "census:cfg", "IN",
                      f"cfg={dev_cfg.bConfigurationValue} itfs={dev_cfg.bNumInterfaces}")
    except Exception as exc:
        log_and_print(log, "census:cfg", "IN", f"{type(exc).__name__} {str(exc)[:60]}")

    # Phase B: console baseline
    try:
        d2 = find_dev()
        d2.ctrl_transfer(0x40, 0, 0, 0, b"getenv build-style\0", timeout=T_CTRL)
        log_and_print(log, "baseline:getenv", "OUT", "bR=0 sent OK")
    except Exception as exc:
        log_and_print(log, "baseline:getenv", "OUT", f"{type(exc).__name__} {str(exc)[:60]}")
    ok, _ = drain(log, "baseline")
    if not ok:
        log_and_print(log, "ABORT", "-", "console dead at baseline")
        return 1

    wedge_guard = 0
    plan = [
        ("go-bare", None, "go", 1),
        ("go-vecA", payload_vec_a, "go", 1),
        ("go-vecB", payload_vec_b, "go", 1),
        ("bootx-vecC", payload_vec_b, "bootx", 1),
    ]
    for name, vec, verb, br in plan:
        if vec is not None:
            d3 = find_dev()
            if d3 is None:
                log_and_print(log, "STOP", "-", "device gone before stage")
                break
            if not stage(d3, log, name, vec()):
                log_and_print(log, "STOP", "-", "staging failed; halting")
                break
        try:
            d4 = find_dev()
            if d4 is None:
                log_and_print(log, "STOP", "-", "device gone before trigger")
                break
            d4.set_configuration()
            send_cmd(d4, verb, br)
            log_and_print(log, f"trigger[{name}]", "OUT", f"'{verb}' bR={br} sent")
        except Exception as exc:
            log_and_print(log, f"trigger[{name}]", "OUT",
                          f"{type(exc).__name__} {str(exc)[:60]}")
        time.sleep(1.5)
        ok, _ = drain(log, name)
        if not ok:
            # console pump may lag; one retry after a tick
            time.sleep(1.5)
            ok, _ = drain(log, name + "-retry")
            if not ok:
                wedge_guard += 1
                log_and_print(log, "STOP", "-",
                              f"console unresponsive after '{verb}' (wedge_guard={wedge_guard})")
                break
        else:
            wedge_guard = 0
        if not pid_check(log, name):
            log_and_print(log, "STOP", "-", "personality flipped/vanished; halting")
            break

    # final baseline
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
    print(f"log: {log.__dict__.get('name','tsv')} (LOCAL ONLY)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
