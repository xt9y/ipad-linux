#!/usr/bin/env python3
"""LOCAL-ONLY J407 recovery upload-path reject-path probe (2026-10-28).

Approved arc: recovery personality (05ac:1281), upload opener + malformed /
unsigned payloads on the bulk upload endpoint, exercising REJECT paths only.

Contract (user-approved 2026-10-28):
  - no DETACH (0x00), no ABORT (0x06), no CLRSTATUS (0x04);
  - no DFU-class requests (they stall in recovery per recon §7.7);
  - no real images: synthetic malformed/unsigned payloads only;
  - nothing persistent: recovery mode, console health checked after each step;
  - payloads deterministic (fixed seed), small (<= 1 KiB);
  - log = class-level protocol bytes only, never ECID/UDID/serial/nonces.

Protocol shape (pmd3 irecv.send_buffer, recovery mode):
  ctrl 0x41/0 (vendor, interface recipient, no data)  -> opener
  bulk OUT 0x04 chunks                                 -> payload
  zero-length packet if total %% 512 == 0              -> terminator
Consumer per static model: IMG4 trust chain, validation precedes any
dereference (recon §7.9). Expect: clean rejects, console stays responsive.
"""

import hashlib
import struct
import sys
import time

import usb.core
import usb.util

OUTDIR = "/private/var/folders/b3/v6rf5zmn1cx3cyw0tvyp53nc0000gn/T/opencode"
VID = 0x05AC
PIDS = (0x1280, 0x1281, 0x1282, 0x1283)
T_CTRL = 2000
T_BULK = 2000
T_HEALTH = 1500

def prng(n, seed=0x407):
    out = bytearray()
    x = seed
    for _ in range(n):
        x = (1103515245 * x + 12345) & 0xFFFFFFFF
        out.append((x >> 16) & 0xFF)
    return bytes(out)

def payload_vectors():
    return [
        ("tiny4", b"AAAA", False),
        ("rnd64", prng(64), False),
        ("img4-magic-only", b"IMG4" + struct.pack("<I", 16) + bytes(16), False),
        ("img4-truncated-len", b"IMG4" + struct.pack("<I", 0x100) + b"AAAA", False),
        ("img4-oversize-len", b"IMG4" + struct.pack("<I", 0xFFFFFFF0) + b"AAAA", False),
        ("zlp-only", b"", True),
        ("blk512-invalid", b"A" * 512, True),
    ]

def log_and_print(log, name, kind, detail, digest="-"):
    stamp = time.strftime("%H:%M:%S")
    detail = str(detail).replace("\n", "; ").replace(",", ";")
    line = f"{stamp},{name},{kind},{detail},{digest}"
    print(line, flush=True)
    log.write(line + "\n")
    log.flush()

def health_check(dev, log, tag):
    """Console responsiveness: non-destructive 0xC0/0 drain; optional bulk-IN read."""
    try:
        data = bytes(dev.ctrl_transfer(0xC0, 0, 0, 0, 0x200, timeout=T_HEALTH))
        dig = hashlib.sha256(data).hexdigest()[:16] if data else "-"
        log_and_print(log, f"health[{tag}]:drain", "IN", f"OK len={len(data)} hex={data[:32].hex()}", dig)
        return True
    except Exception as exc:
        log_and_print(log, f"health[{tag}]:drain", "IN", f"{type(exc).__name__} {str(exc)[:60]}")
        return False

def main() -> int:
    dev = None
    for pid in PIDS:
        dev = usb.core.find(idVendor=VID, idProduct=pid)
        if dev is not None:
            break
    if dev is None:
        print("no recovery personality (05ac, 0x1280..0x1283) present", file=sys.stderr)
        return 2

    logpath = f"{OUTDIR}/dfu-probe-log-{time.strftime('%Y%m%d')}-upload-arc.tsv"
    log = open(logpath, "w")
    log.write("# LOCAL ONLY - never commit. class-level protocol bytes only\n")
    log.write("# columns: time,name,kind,detail,digest-prefix\n")

    log_and_print(log, "census:pid", "IN", f"05ac:{dev.idProduct:04x}")
    try:
        log_and_print(log, "census:product", "IN", repr(dev.getProduct() or "?"))
    except Exception as exc:
        log_and_print(log, "census:product", "IN", f"{type(exc).__name__}")
    try:
        cfg = dev.get_active_configuration()
        log_and_print(log, "census:cfg", "IN",
                      f"cfg={cfg.bConfigurationValue} itfs={cfg.bNumInterfaces}")
        for itf in cfg:
            eps = ",".join(
                f"{'IN' if usb.util.endpoint_direction(e.bEndpointAddress) else 'OUT'}"
                f"{e.bEndpointAddress:#04x}/{e.bmAttributes:#x}" for e in itf)
            log_and_print(log, f"census:itf{itf.bInterfaceNumber}/alt{itf.bAlternateSetting}",
                          "IN", f"class={itf.bInterfaceClass:#x} eps=[{eps}]")
    except Exception as exc:
        log_and_print(log, "census:cfg", "IN", f"{type(exc).__name__} {str(exc)[:60]}")

    try:
        dev.set_configuration()
    except Exception as exc:
        log_and_print(log, "census:set_cfg", "IN", f"{type(exc).__name__} {str(exc)[:60]}")

    # Phase B: console baseline (read-only identity, same as §7.7)
    try:
        dev.ctrl_transfer(0x40, 0, 0, 0, b"getenv build-style\0", timeout=T_CTRL)
        log_and_print(log, "baseline:getenv-build-style", "OUT", "send OK")
    except Exception as exc:
        log_and_print(log, "baseline:getenv-build-style", "OUT", f"{type(exc).__name__} {str(exc)[:60]}")
    if not health_check(dev, log, "baseline"):
        log_and_print(log, "ABORT", "-", "console unresponsive at baseline; stopping")
        log.close()
        return 1

    # Phase C/D: opener + malformed payload matrix
    bulk_ok = False
    try:
        cfg = dev.get_active_configuration()
        itf0 = list(cfg)[0]
        ep_out = usb.util.find_descriptor(itf0, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
        bulk_ok = ep_out is not None
    except Exception:
        pass
    log_and_print(log, "upload:ep", "IN", f"bulk-out ep found={bulk_ok}")

    for name, payload, zlp in payload_vectors():
        log_and_print(log, f"upload[{name}]", "-", f"begin payload={len(payload)}B zlp={zlp}")
        # opener (pmd3 form)
        try:
            dev.ctrl_transfer(0x41, 0, 0, 0, b"", timeout=T_CTRL)
            log_and_print(log, f"upload[{name}]:opener", "OUT", "0x41/0 OK")
        except Exception as exc:
            log_and_print(log, f"upload[{name}]:opener", "OUT", f"{type(exc).__name__} {str(exc)[:60]}")
        # payload via bulk
        if payload and bulk_ok:
            try:
                n = dev.write(0x04, payload, timeout=T_BULK)
                log_and_print(log, f"upload[{name}]:payload", "OUT",
                              f"bulk 0x04 wrote={n}/{len(payload)}",
                              hashlib.sha256(payload).hexdigest()[:16])
            except Exception as exc:
                log_and_print(log, f"upload[{name}]:payload", "OUT", f"{type(exc).__name__} {str(exc)[:60]}")
        # terminator
        if zlp and bulk_ok:
            try:
                dev.write(0x04, b"", timeout=T_BULK)
                log_and_print(log, f"upload[{name}]:zlp", "OUT", "zero-length OK")
            except Exception as exc:
                log_and_print(log, f"upload[{name}]:zlp", "OUT", f"{type(exc).__name__} {str(exc)[:60]}")
        # console health after each step
        if not health_check(dev, log, name):
            log_and_print(log, "STOP", "-", "console unresponsive after this vector; halting matrix")
            break

    # Phase E: final console identity
    try:
        dev.ctrl_transfer(0x40, 0, 0, 0, b"getenv build-style\0", timeout=T_CTRL)
        log_and_print(log, "final:getenv-build-style", "OUT", "send OK")
    except Exception as exc:
        log_and_print(log, "final:getenv-build-style", "OUT", f"{type(exc).__name__} {str(exc)[:60]}")
    health_check(dev, log, "final")

    log.close()
    print(f"log: {logpath} (LOCAL ONLY)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
