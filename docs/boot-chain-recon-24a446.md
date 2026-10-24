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
device ran iPadOS 27.0 beta 7 / `24A5424a`). The GA `24A446` inspection
therefore describes the bootloader generation the device is factually
running.

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

## Status

- [x] Components extracted (signed GA 27.0.1 / `24A446`)
- [x] Unpack to raw payloads
- [x] Component inventory + digest prefixes
- [x] On-device boot-chain observation cross-checked
- [x] DFU environment identification + SecureROM generation recorded
- [ ] Disassembly pass (iBoot/LLB) into a structured recon document
- [ ] USB/DFU attack-surface characterization + fuzz harness
