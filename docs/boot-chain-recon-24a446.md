# J407 boot-chain recon — iPadOS 27.0.1 (24A446)

Offline inspection of the boot-chain components of the currently signed
build for the target device. Raw firmware binaries are **not** committed
here (and never will be); they live outside the repository
(`~/research/j407-bootchain/`) and only facts, sizes and digest prefixes
are recorded. Extracted with `ipsw download --pattern` (remote partial
extraction, ~9.5 MB total) and `ipsw img4 im4p extract`.

## Component inventory

| Component       | Path                                            | Size    | SHA-256 prefix     |
| --------------- | ----------------------------------------------- | ------- | ------------------ |
| iBSS (DFU)      | `Firmware/dfu/iBSS.j407.RELEASE.im4p`           | 2.2 MB  | `dc3cb25f29f25645` |
| iBEC (DFU)      | `Firmware/dfu/iBEC.j407.RELEASE.im4p`           | 2.2 MB  | `dc3cb25f29f25645` |
| LLB             | `Firmware/all_flash/LLB.j407.RELEASE.im4p`      | 2.2 MB  | `dc3cb25f29f25645` |
| iBoot           | `Firmware/all_flash/iBoot.j407.RELEASE.im4p`    | 2.2 MB  | `dc3cb25f29f25645` |
| iBootData       | `Firmware/all_flash/iBootData.j407.RELEASE.im4p`| 98 KB   | `d08e11406f8107e8` |
| DeviceTree      | `Firmware/all_flash/DeviceTree.j407ap.im4p`     | 215 KB  | `fcc5798ea064dad8` |
| SEP Firmware    | `Firmware/all_flash/sep-firmware.j407.RELEASE.im4p` | 5.2 MB | `2edb3cff5c81818c` |

All four "stages" carry the same embedded build tag: `mBoot-20457.2.37`
(`BUILD_TAG: %s` string present), which **matches the boot chain
actually observed running on the physical device on 2026-10-22**
(`FirmwareVersion mBoot-20457.2.37`, verified via `ideviceinfo` while the
device ran iPadOS 27.0 beta 7 / `24A5424a`) and **re-verified on-screen
after the device was updated to the signed GA on 2026-10-24** (device now
runs `27.0.1 / 24A446`, same observed `mBoot-20457.2.37`). The GA
`24A446` inspection therefore describes the bootloader generation the
device is factually running, and the device environment is pinned to the
build documented here (automatic updates off; beta profile removed).

## Finding: unified multi-personality bootloader image

The four Deep four "stage" payloads are **byte-identical**
(SHA-256 prefix `dc3cb25f29f25645`):

```text
iBSS.j407 == iBEC.j407 == LLB.j407 == iBoot.j407
(verified: independent re-extract of iBEC hashes equal to the others)
```

Implications recorded for the research record:

- there is no separate per-stage binary on this silicon generation —
  the image is a single multi-personality bootloader whose stage
  behavior is decided by its invocation context (SecureROM as DFU/recovery
  loader vs. prior stage as flash loader);
- signing-wise the chain still verifies four named identities in the
  BuildManifest, but the executable payload subject to analysis (and,
  should one ever exist, to exploitation-class bug hunting) is this one
  image across the whole pre-OS chain;
- DFU and Recovery run the same code bytes as the regular boot loader —
  an attack-surface observation that also directly applies to things
  like `mBoot` environment interaction, USB protocol handling and
  heap-allocator behavior shared with the user-observable vectors.

## Other observations

- Payloads are position-independent AArch64 blobs (`file(1)` says
  "data"; no standard ELF/IM4P post-decompression headers).
- No secrets, no ECID data, and no device-unique material are involved
  in this reconnaissance; digests above are content hashes of
  publicizable images.

## DFU environment — observed on device (2026-10-24)

Probed once the physical device was placed in hardware DFU mode
(read-only `irecovery` identification only — no writes, no payload
uploads; device-unique values such as ECID/serial and the DFU nonces
are deliberately omitted from this record):

```text
CPID:       0x8103          (T8103 / Apple M1 - matches all prior records)
CPRV:       0x11
BDID:       0x10            (J407AP - matches all prior records)
CPFM:       0x03            (production security policy)
SCEP:       0x01
IBFL:       0x3c
SRTG:       iBoot-5540.0.0.400.2   <- SecureROM generation tag
MODE:       DFU
PRODUCT:    iPad13,16  MODEL: j407ap
```

### Cross-check against the 2026 survey

The usbliter8 (June 2026) affected SecureROM range is documented as
`3865.0.0.4.7 – 4479.0.0.100.4`, with newer silicon carrying the fix
(`5281.0.0.100.45` as the listed "fixed-in" generation). This device's
SecureROM is tagged **`iBoot-5540.0.0.400.2`** — strictly *newer* than
the documented fix generation. First-hand confirmation of the survey
conclusion: the last public BootROM exploit class ends a full
SecureROM-generation window below this chip's ROM.

CPFM `0x03` also documents, first-hand, that this unit runs the
production (non-development) security policy — no dev-fused lever exists
here either.

## DFU USB-surface characterization (2026-10-24)

Raw session data archived **outside the repository** at
`~/research/j407-bootchain/dfu-2026-10-24/` (full `irecovery` output —
including device-unique ECID/nonces — USB descriptor strings, `ioreg`
USB tree and the probe script itself). Only device-class facts below
re-probed:

```text
usbmuxd sees 0 devices while in DFU (expected: no normal-mode services)
USB: idVendor 0x05ac  idProduct 0x1227  bcdDevice 0x0000
     product name: "Apple Mobile Device (DFU Mode)"
     configuration: bMaxPower 250, iConfiguration 5
     interface 0: class 0xfe subclass 0x01 protocol 0x00, 0 endpoints
```

DFU class-protocol behavior (read-side probes only, no dnload/erase):

```text
GETSTATUS -> bytes [0, 50, 0, 0, 2, 0]
              dfuState=2 (dfuIdle)  dfuStatusCode=0 (OK)  pollTimeout=50ms
GETSTATE  -> state=2 (dfuIdle)
UPLOAD(16)   -> silent timeout (no response)
UPLOAD(256)  -> silent timeout
UPLOAD(1024) -> silent timeout
GETSTATUS-after-attempts -> state=2 code=0 (clean, no error latch)
GETSTATE-after-attempts  -> 2 (clean re-entry into dfuIdle)
```

Interpretation recorded for the research record:

- the untouched (non-pwned) Apple DFU on this silicon answers the
  standard status/state queries immediately, but its UPLOAD readback is
  silently ignored at every size — consistent with the known
  checkm8/usbliter8-era observation that non-pwned Apple DFU has no
  functioning upload path, which is precisely why both public BootROM
  exploits begin by inducing a state the ROM trusts with readback;
- timed-out uploads do not latch the state machine into an error state
  (clean `dfuIdle` afterwards), so repeated read-side probing is safe
  and non-destructive as an ongoing characterization technique;
- DFU defines interface class 0xfe/0x01/0x00 with zero endpoints — an
  EP0-control-only surface, matching the SecureROM's trimmed-down USB
  handling that the post-A11 hardening moved out of the vulnerable
  generation's shape.

The saved `usb-descriptors-LOCAL-ONLY.txt` contains the device-unique
USB serial-string values; never copy them into the repo or any report.

## Status

- [x] Components extracted (signed GA 27.0.1 / `24A446`)
- [x] Unpack to raw payloads
- [x] Component inventory + digest prefixes
- [x] On-device boot-chain observation cross-checked
- [x] DFU environment identification + SecureROM generation recorded
- [x] DFU USB-surface/protocol characterization (state machine, upload policy, interface shape)
- [x] Raw session data archived locally (`~/research/j407-bootchain/dfu-2026-10-24/`)
- [x] Host-side first pass on the unified image (strings / keyword / identifier corpus — see `docs/boot-image-recon-24a446.md`)
- [x] Read-side DFU harness (`tools/dfu-fuzz.py`, offline mirror + `--allow-device` gated mode)
- [x] Structured decode pass (Capstone, 84.2% coverage, PAC prologues found — see `docs/boot-image-recon-24a446.md`)
- [x] Literal-pool address-constant scan (264 known-family constants: 171 peripheral/MMIO, 73 upper MMIO/PCIe, 20 page-aligned DRAM — incl. the `0x200000000` region base itself)
- [x] Load-base-independent code-to-data xref (`tools/boot-image-xref.py`): 9220 ADRP(+ADD) refs → 688 data pages, top pages identified as SysConfig3/DER parsing machinery
- [ ] Deep analysis: load-base resolution + literal-pointer resolution (18459 pool LDRs pending) → full handler-cluster enumeration
- [ ] Extended DFU fuzz campaign with per-session device approval

## DFU session 2 (2026-10-24 afternoon, fresh DFU entries)

Repeatable causality established on fresh DFU entries (device re-entered by user after the first flip):

- **IN-class requests are all nondisruptive on a fresh device**: GETSTATUS/GETSTATE reproduce session-1 bytes byte-for-byte (`00 32 00 00 02 00` / `02`, stable digests) and remain clean after the whole read battery. UPLOAD is a genuine 2 s timeout with no error latch (steady state — earlier mid-flip errors were not upload semantics). Wrong-interface targeting (wIndex=1) returns an immediate `[Errno 2] Entity not found` — a distinct, instant rejection, not a timeout.
- **Both OUT-class requests are state-changing**: ABORT (`0x21/0x06`) and CLRSTATUS (`0x21/0x04`), n=2 each-pass, on separately entered DFU states: the request itself returns `[Errno 5] Input/Output Error`, the device leaves the USB bus within 250 ms, and ~16–34 s later **re-enumerates as `05ac:12ab`** — deviceClass 0x00 with 5 configurations exposing PTP imaging (3 endpoints), audio class, HID, CDC-NCM and vendor interfaces — the normal iPadOS boot USB personality, not a DFU variant. The `12ab` window then leaves the bus again after tens of seconds.
- **Interpretation (bounded)**: on this BootROM DFU build, host-to-device class requests trigger a ROM USB-stack teardown from which the device boots onward into the normal OS. Whether that is a deliberate reset handler or a crash path is indistinguishable from the host side; both are consistent with the data. DFU idle is therefore only stable under IN-only traffic.
- Good practice recorded for future sessions: run all IN-side probes first; treat ABORT/CLRSTATUS as the terminal step of any session; after an OUT request, do not reuse the old handle (the device re-appears under a different PID and needs re-entry via the physical buttons).
- Session logs archived locally (`dfu-fuzz-run.log`, `phaseA-reads.log`, `phaseB-clrstatus.log`).

### Control follow-up (same afternoon, third fresh DFU entry)

An 8-minute idle control window (`15:03:39`–`15:11:40`, zero transfers sent, pure enumeration watch) showed **no flip: `1227` stayed present the entire time**. The flip therefore is not an idle timeout within this window; the un-provoked drop observed once earlier this afternoon had not reproduced under zero-traffic conditions (host-side actors such as `irecovery`/`usbmuxd` remain environmental variables; if `irecovery` participates in a session, treat that as a possible confounder).

A single CLRSTATUS after the control window reproduced the flip deterministically (now **n=3 across three independently entered DFU states**): I/O error on the request, detachment in the same second, `05ac:12ab` 15 s later — composite normal-OS personality (PTP/audio/HID/NCM/vendor interfaces, no DFU class surface). Unlike the first two flips, this `12ab` window was observed for over two minutes *while untouched* (descriptor reads only) — the earlier rapid disappearances correlated with issuing control transfers at its interfaces, not with the personality itself.

Un-bounded statement of the operational rule that follows from this: on this BootROM build, **ABORT and CLRSTATUS terminate the DFU link** (device boots onward into the normal OS). DFU longevity requires IN-only traffic. The generic-DFU assumption "ABORT is always harmless" is not valid here.
