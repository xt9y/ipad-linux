#!/usr/bin/env python3
"""LOCAL-ONLY J407 DNLOAD-side acceptance probe (2026-10-28).

Validates the byte-mapped DFU acceptance chain from the static audit
(docs/dfu-ep0-recon-2026-10-27.md 2.3/2.4) against the live device:
  state object [0x23b9a8,+0x120): block_len @0x23b9b0, cum @0x23b9b8,
  expected @0x23b9bc; BUTT-len mismatch latch (fail -> state 0xA, code
  0x3209), cum/expected mismatch (code 0x3208), success arc -> state 5,
  timeout 0x3200 (12,800 ms).

Contract (host-side, tested style of tools/dfu-fuzz.py):
  - class requests only (bmRequestType 0x21/0xA1);
  - hardcoded single-pass vector list; no loops, no randomization;
  - no DETACH (0x00), no ABORT (0x06), no CLRSTATUS (0x04) — per the
    2026-10-24 mirror those flip the personality;
  - exactly three DNLOADs: 64 B, 64 B, 32 B (the 32 B one is a deliberate
    block_len mismatch, statically expected to fail BEFORE any memory
    write: the checks live at 0x11cd34/0x11cd4c, pre-dereference);
  - payload = zero bytes;
  - log lines carry timestamps, byte values, digest prefixes only —
    never ECID/UDID/serial/Apple-ID data.
"""

import hashlib
import sys
import time

import usb.core

USB_VID = 0x05AC
RECOVERY_PIDS = (0x1280, 0x1281, 0x1282, 0x1283)

def get(name, request, length, w_value=0, w_index=0):
    return ("IN", name, 0xA1, request, w_value, w_index, bytes(), length)

def dnload(name, payload, w_value=0):
    return ("OUT", name, 0x21, 0x01, w_value, 0, payload, 0)

BLOCK = 64
VECTORS = [
    get("GETSTATUS(baseline)", 0x03, 6),
    get("GETSTATE(baseline)", 0x05, 1),
    dnload("DNLOAD(first,64)", bytes(BLOCK)),
    get("GETSTATUS(after-dnload-1)", 0x03, 6),
    get("GETSTATE(after-dnload-1)", 0x05, 1),
    dnload("DNLOAD(second,64)", bytes(BLOCK)),
    get("GETSTATUS(after-dnload-2)", 0x03, 6),
    dnload("DNLOAD(mismatch,32)", bytes(32)),
    get("GETSTATUS(after-mismatch)", 0x03, 6),
    get("GETSTATE(final)", 0x05, 1),
]


def parse_status(data: bytes):
    if len(data) != 6:
        return None
    return {
        "bStatus": data[0],
        "bwPollTimeout_ms": data[1] | data[2] << 8 | data[3] << 16,
        "bState": data[4],
        "iString": data[5],
    }


def main() -> int:
    outdir = "/private/var/folders/b3/v6rf5zmn1cx3cyw0tvyp53nc0000gn/T/opencode"
    dev = usb.core.find(idVendor=USB_VID, idProduct=USB_PID)
    if dev is None:
        print("no recovery-personality (05ac, pid 0x1280..0x1283) present", file=sys.stderr)
        return 2
    try:
        dev.set_configuration()
    except Exception:
        pass

    log = open(f"{outdir}/dfu-probe-log-{time.strftime('%Y%m%d-%H%M%S')}.tsv", "w")
    log.write("time,vector,dir,request,wValue,wIndex,status,raw,parsed,digest-prefix\n")
    print("probe start: recovery-personality (05ac, pid 0x1280..0x1283), obstacles='none', vectors=%d" % len(VECTORS))

    for kind, name, bm, req, wv, wi, payload, rlen in VECTORS:
        stamp = time.strftime("%H:%M:%S")
        try:
            if kind == "IN":
                data = bytes(dev.ctrl_transfer(bm, req, wv, wi, rlen, timeout=2000))
                status, raw, dig = "OK", data.hex(), ("-")
                parsed = parse_status(data)
                parsed_s = ("{" + ",".join(f"{k}={v:#x}" if isinstance(v, int) and k != "bwPollTimeout_ms" else f"{k}={v}" for k, v in parsed.items()) + "}") if parsed else "-"
                digest = hashlib.sha256(data).hexdigest()[:16] if data else "-"
                result = f"raw={raw or '-'}"
            else:
                dev.ctrl_transfer(bm, req, wv, wi, payload, timeout=2000)
                status, parsed_s, digest = "OK", "zero-data-sent", "-"
                result = f"payload={len(payload)}B zeros"
        except Exception as exc:
            status, parsed_s, digest, result = type(exc).__name__, "-", "-", str(exc)[:80]
        line = ",".join((stamp, name, kind, f"0x{req:02x}", str(wv), str(wi),
                         status, result.replace(",", ";"), parsed_s, digest))
        print(line)
        log.write(line + "\n")

    log.close()
    print("probe complete: no DETACH/ABORT/CLRSTATUS issued; link left as-is")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
