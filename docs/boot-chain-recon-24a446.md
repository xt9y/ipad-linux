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

The four "stage" payloads are **byte-identical**
(SHA-256 prefix `dc3cb25f29f25645`):

```text
iBSS.j407 == iBEC.j407 == LLB.j407 == iBoot.j407
(verified: independent re-extract of iBEC hashes equal to the others)
```

Container-level re-check (2026-10-26): the four `.im4p` files carry the
**same LZFSE stream** (`bvx2` at container offset `0x28`, stream length
`0x11142d`), byte-identical across iBSS/iBEC/LLB/iBoot; they differ only
in the IM4P 4CC/description (and 30 extra wrapper bytes in iBEC). The
on-disk containers are ~1.1 MB each; the 2.2 MB figure above is the
extracted (decompressed) payload.

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
- [x] String-anchored reverse mapping: `getenv`/`setenv`/`setenvnp` handler cluster (page 0x211), `boot-command`/`boot-args` boot-flow cluster (page 0x210), `com.apple.System.boot-nonce` registry plumbing (page 0x223), early-entry boot-property references
- [x] Dispatch-table semantics (structural): accessor sites → exact entries → kernel low32 verified end-to-end; parallel twin partitions (identical 11-class byte-index maps); Latin-zone class boundaries superseded by stride-8 protocol texture; kernel semantics resolved 2026-10-26 as an LZVN-family token grammar (11 classes, both drivers — see boot-image doc)
- [x] Dispatch drivers identified: both consumer loops located; per-byte `ldrb → qword load → braa` PAC branch chain confirmed in both; cookie = `(0x8010<<16)|modifier` where modifier matches each driver's `braa` x17 (0xb803 / 0x23ca); LZVN token state machine with `-1`/`-2`/`-3` error codes (Driver A raw stream resumable at `-2`; Driver B 12-byte-header block decoder with 4-byte word packer, unified `-1`); LZFSE-family engine context confirmed by full public block-magic vocabulary (`bvx$`/`bvx-`/`bvxn`/`bvx1`/`bvx2`, `bvxl` absent, Apple-internal `avx1`/`avx2` present)
- [x] Cross-band call topology: 184 bl edges bridge the 0x13c000 boundary in both directions; LZFSE engine band reachable only via 4 helper entries; both drivers single-caller (engine self-contained); density map is linear-decode measurement (bl-proved code exists in sparse back-half windows)
- [x] Embedded compressed payload decoded: single LZFSE stream 0x1a3768..0x1dd487 (5 `bvx2` blocks + `bvx$`), 0x39d23 B → 0x79760 B ARM64 module (sha256 prefix 7da684741cedf068); identity confirmed by embedded strings: **AppleSMCFirmware_H13-7372.2.11.ipad13b.REL on RTKit_release-3514.0.15.release** (charger/BMS/thermal/PMU/SPMI drivers, platform/t8103 shims, RTKSTACK guard pages ×1025); 16 early-code formation sites (0xc6xx-0xe7xx) target the stream page; the compressed blob, the decoding engine and the consumers are all statically linked in one chain
- [x] Address space & runtime layout resolved: pool census (30,719 qwords) splits into measured classes — **16,029 SMC-domain pointers (absolute base `0x1FC000000`)** mapping SMC RAM image-relative `[0x1a5bb8..0x28a640]`: staging zone with 12-byte-strided record tables, the **decoded SMC image at ≈`0x1f64a0` +0x79760 (645 pointers exactly on RTKSTACK guard starts + driver-string anchors, content-verified)**, beyond-file heap; ~1,944 `{tag,small}` records; 1,220 `{0x80XX0000|iBoot-code-offset}` pre-signed pointer records (94% into own code band); 511 braa-cookie dispatch entries; 7,521 plain ints. In-stream and beyond-file formation refs re-read as staged-zone/BSS targets — the file under-delivers ≈1.5 MB of zero-fill; per-segment δ-shift fit attempted and rejected; iBoot-internal addressing remains load-base independent (the one absolute base in the image belongs to the SMC domain)
- [x] FourCC tag scan: 414 distinct register-built word tags / 771 sites; IMG4 vocabulary cluster at 0x22508..0x22654 (IM4M/ECID/CHIP/BORD/DGST/SDOM/CSEC); bvxN/avxN codec-tag family co-located with the twin dispatch kernels (proximity, not linkage)
- [x] Decompress-call chain resolved: static bl/pacibsp callgraph (48,624 edges / 4,190 fns; `blr` ×0 — indirect flow authenticated: `blraaz` ×319, `paciza` ×566) resolves the full chain **`0x144a0c` (wrapper: PAC-signed context `{x2/x3 in-range, x0/x1 out-range}`, type word `0x3a98/0x9c40` at `+0x1c88`) → `0x145e44` (container: 12× `bl 0xd27f0` zero-fills) → `0x144d5c` (block-magic dispatcher: "bvx1"/"bvx2"/"bvxn" movz compares; unhandled → `bvx$` zone) → `bl 0x145a70` at site `0x144edc` (driver B) + kernels**; engine A chain `0xf5e94 → 0xf8cac → {0x13fea4, 0x14022c} → 0x1408bc` (falls through into the `[0x140b44..0x140fc0)` window-copy driver, per-byte `braa` cookie `0xb803` measured at all 4 sites; table A `0x1945a8` formed inline). The tail `bl 0x30444` = **ARM64 VM mapper** (3-level walk, TTBR roots `0x215700/0x215708`, KASLR slide) mapping the decode output beyond the file, with return-address chaining back into driver B. Pool `{0x80XX0000|low}` records structurally confirmed as **pre-signed pointer records** (same `{movk key | address}` shape as the wrapper's own `pacda` sites); concrete instance `pool[0x192078] = {0x8020|0xf5e94}` = per-SMC-object handler wiring (`{1|0xfc1dd7b8} ↔ {0x8020|0xf5e94}` alternating pattern). `0x144a0c` has no direct `bl` caller; its entry channel is the execute dispatcher `0x1473f0` tail branch at `0x147484` (types `0x801`/`0x802`/`0x891`), itself called by four protocol loaders
- [x] In-image decode chain proven end-to-end offline (Unicorn emulation): wrapper `0x144a0c` (selector 0, type word `0x9c40`) run on the real stream reproduces the `0x79760` B SMC image byte-exactly (sha256 prefix `7da684741cedf068`); measured 5 block headers, 5×360 VLC symbols, 5 decode loops, copy helpers `0x144330`/`0x144630` ×5 each, 0 error paths; this stream's path stays inside container `0x145e44` (`0x145ef8`/`0x146414`/`0x1471d8`/`0x14685c`) and does not execute `0x144d5c`/`0x145a70`/`0x145c3c`/`0x30444`
- [x] Message-type dispatch pair resolved: `0x147348` = size query keyed by `w0`, `0x1473f0` = execute keyed by `w5` (normalization `0x200-0x209`→`0x205`, `0x500-0x509`→`0x505`, `0xd00-0xdff`→`0xd05`; full type→target map in the boot-image doc); four protocol loaders (`0x20e0c`, `0xb58c0`, `0xddb10`, `0xea600`) follow `size → allocate → execute` with `{out,in,ctx,type}` arguments — two hard-code type `0x891`, two read `{len@+0x20, type@+0x24}` from a descriptor
- [x] `0x891` measured as a mode selector, not the SMC decode arm: the emulated chain parses block 0's header + all 360 VLC symbols, performs zero copy-helper calls, returns a mismatching output (digest `68d521d3fec67388` ≠ `7da684741cedf068`, wrapper `x0=0`); SMC decode is the non-`0x891` arm (`0x801`/`0x802`, type word `0x9c40`, zero-fill `0xb910`)
- [x] Per-byte kernel tables decoded kernel-by-kernel (static): identical 11-class byte partition in both tables; full LZVN-family token grammar (L/M/D formulas, 2/3/1-byte tokens, `e0`/`f0` long forms, `06` EOS, `0e`/`16` no-op, 37 invalid bytes); Driver A = raw-stream decoder with resumable `-2` state and `-3` distance underflow; Driver B = 12-byte-header block decoder writing through a 4-byte word packer, unified `-1`; `0x145c3c` relabeled as byte packer (not entropy); dispatcher arms `bvxn`→engine B, `bvx1`→0x304-byte header copy, `bvx2`→entropy setup, `bvx-`/`bvx$` zones; types `0x900/0x901` reach a third fast LZ decoder at `0x140fc0` (relative jump table `0x141300`); static-only — 0 emulation hits on the SMC path
- [x] Protocol loaders mapped to boot subsystems: `0x20e0c` = boot-file/IMG4 object cluster (`0x81ca0`; loader references `image4_callbacks.validity_cb is NULL`, cluster carries `image-version`, `boot-breadcrumbs`, upper chain `/boot`, `/boot/iBEC`, `boot-command`, `recovery-boot-mode`, `mount upgrade partition`), hard-codes `0x891`; `0xb58c0` = early boot flow (`0xb5c28`←`0x37440`←`0x37188`←`0x3724`), descriptor `+0x20`/`+0x24` = object `+0x48`/`+0x54` (length/type), payload header `+0x10` size and `+0x14` word index, compressed input at `base+0x18+4*index`; `0xddb10` = **"VMiBoot "/"LZFSE   " boot-object decoder** (caller `0xdcc84` walks 16-byte name/format entries; object `{len@+0x1c, data@+0x20}`), hard-codes `0x891`; `0xea600` = list loader (`0xe68c0` per-object iteration over flag `+0x21a`, u16 `+0x260`, fields `+0x40`/`+0x50`/`+0x60`; `0x125b6c`), descriptor type at `+0x24`; **only the descriptor-driven pair can carry the SMC `0x801/0x802` arm**
- [x] Boot-object registry tags: `img4` (`0x696d6734`) at object `+0x70` (constructor `0x20994` inside the linked-list allocator `0x207c8..0x20b00`, "linked list item %p corrupted"), `Memz` (`0x4d656d7a`) at `+0x08` (`0x8205c`); consumers `0x81ca0`/`0x220a4` admit the same pair
- [x] Object-field key setter `0x26d44` measured and shown statically unreachable: 18 keys `0x6b63_<low16>` (bytes `<2 chars>ck`, big-endian `kc<2 chars>`), writes fields `+0x08..+0xb0` and flags `+0/+1/+2`, minima `+0x10`/`+0x40`; outlined compare tail `0x2dcac` (`movk w9,#0x6b63,lsl#16; cmp w22,w9; ret`); **no `bl`, qword, 32-bit-relative or `adrp+add` reference anywhere in the image**, and no key bytes in iBoot/iBootData/DeviceTree/LLB/iBSS/iBEC/sep-firmware — negative result; `0xdcc84` (VMiBoot table walker) shares the property
- [x] Container-level re-check of the unified image: the four `.im4p` files carry the same LZFSE stream (`bvx2` at `0x28`, length `0x11142d`, byte-identical); they differ only in the IM4P 4CC/description (iBEC has 30 extra wrapper bytes) — the 2.2 MB extracted payload is one binary across iBSS/iBEC/LLB/iBoot
- [x] Boot-policy vocabulary resolved as iOS/cryptex1: `%s/%s/LocalPolicy.cryptex1.img4`, `%s/active`, `lp-nsih`, `lp-spih`, `chosen/asmb`, `asmb`, `/boot/active` at `0x19a074..0x19a0d0`; **no macOS permissive/custom-kernel vocabulary** (`fuOS`, `coih`, `smb0`-`smb4`, `lobo`, `love`, `hrlp`, `auxp`, `sip0`-`sip3`, `permissive`, `custom kernel`, `1TR`) as string/byte-reversed 4CC/movz-movk constant in iBoot, iBootData, DeviceTree or sep-firmware; DT has no security-mode-change/custom-kernel node — policy-based custom-kernel route absent in this build (static evidence; not a proof against an iBoot bug); policy strings are compact/indirect-table referenced (no adr/adrp±add/qword/movz-movk xref image-wide)
- [x] Pre-stream records measured: six complete 16-byte `{u32 0x76..0x7b, u32 0x25f..0x264, u32 0x3520c000+0x4000*n, u32 2}` entries end at `0x1a3760`; `{0x7c,0x265}` is cut off at the `bvx2` magic; no `{len@+0x10,type@+0x14}` boot-object header at any alignment — SMC blob descriptor origin still open
- [ ] Deep analysis (remaining): `0x891` message-mode purpose (tables-only parse measured; the `0x9c40`/selector-0 arm is the proven SMC-stream decode), payload meaning of protocol types `0x205/0x505/0x700-0x702/0x100/0x101` (engines located, payloads unidentified), and the VLC bitstream word-selection internals (container path proven byte-exact; the word-selection rule is not reduced to a standalone description)
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
