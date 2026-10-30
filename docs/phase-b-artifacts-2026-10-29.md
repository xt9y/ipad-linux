# Phase B — Artifact acquisition record & availability map (T8103 program)

> Program: `docs/kickoff-t8103-rom-research.md` (§6) · branch
> `research/j407-entry-2026-10` · date 2026-10-29. Class-level only; device
> observations referenced by pointer from
> `docs/dfu-ep0-recon-2026-10-27.md`. Full artifact ledger + hashes live
> side-local at `~/research/j407-bootchain/artifacts/inventory.md`
> (never committed).

## 1. Item acquired: device-exact second stages — verified from fresh source
The device's installed build (iPadOS 27.0.1, build **24A446**) was
confirmed on-device this session (normal iOS). The official IPSW segment
for that exact build was re-downloaded **fresh from the Apple CDN** on
2026-10-29 (`ipsw download ipsw --device iPad13,16 --build 24A446`
remote-pattern partial extraction; manifest reported `signed=true`, i.e.
Apple is still signing 24A446 today). The Oct-24 cached segment and the
fresh bytes are **byte-identical** for every checked file — cache
integrity proven, not assumed.

Extraction of the Image4 payloads (`pyimg4`) was method-validated by
byte-matching the known-good DeviceTree / iBootData / sep-firmware
`raw_` files before being trusted for the boot stages.

## 2. Findings (verified, class-level, reproducible by anyone)
### 2.1 The T8103-generation j407 ships a CONSOLIDATED boot image
Within the j407 IPSW for build 24A446, the four boot stages
`LLB (illb)`, `iBoot (ibot)`, `iBSS (ibss)`, `iBEC (ibec)` — each its own
Image4 container (distinct fourcc, iBEC manifest 30 B larger) — carry
**one and the same LZFSE payload**:

- sha256 `dc3cb25f29f25645fc1bb2b233476787160d0d9f1c22936cd4ee788c34e7fc15`
- size 2,255,320 B — **this is exactly the audited target
  `raw_iBoot.j407.RELEASE`** (prior-session static audit, load base
  `K = 0x1fc04c000`)
- every container versioned `Boot-20457.2.237`
- verified on BOTH the cached segment and the fresh Apple CDN download

Interpretation: on this platform family there is no separately-published
LLB / iBoot / iBSS / iBEC image set — the whole chain from the second
stage onward is **one binary** whose personality (DFU / recovery / boot)
is selected at runtime. The LLB-era multi-stage model is gone on this
silicon.

### 2.2 Cross-board family delta is free now
The same universal IPSW also carries **j408** (same-generation board),
whose four stages consolidate identically around a *different* payload
(sha256 `cd9d90b72a146ec270bff5943664f294a043357c61f11c3c5ae1f585ca2a81d4`).
A same-generation pair of whole-boot-image binaries is now in-house for
a cheap function-level delta audit (what changes per board, where the
USB/platform config deltas sit — the fastest way to localize the
hardware-coupled code, e.g. the USB stack routines playing into
technique-class 2 of the Phase A matrix).

### 2.3 Consequence for Phase C / D (sharpened, not changed)
- The kickoff planned "audit iBSS.j407 (DFU door)" and "audit j407
  iBoot" as separate items. **They are one binary now.** In particular:
  the ep0 DFU acceptance chain already audited in the prior
  session (`state object `[0x23b9a8,+0x120)`, block-len checks at
  `0x11cd34`/`0x11cd4c` before any write, write-grant gate `0x7e60c`)
  *is* the DFU-mode personality surface of this same image — the DFU
  "door" audit priority #1 becomes a deeper, second adversarial pass on
  code we already have mapped (cheap and high-value).
- Phase D Harness 4 (iBSS USB emulation) now has **real DFU-protocol
  bytes of the exact image the device runs**, not an assumed stand-in.
- The recovery §7 arcs (§7.7/§7.11/§7.12 record) were conducted against
  the same image's recovery personality — the audit story closes
  cleanly: one mapped image enforces everything we observed on both
  personalities.
- New delta-question added: invert the j407-vs-j408 diff to locate
  board-config regions (helps separate hardware-coupled code from
  generic parser code when hunting input-driven bugs).

## 3. Item acquired: Mac M1/T8103-family firmware set from macOS 27.0.1
Source: `UniversalMac_27.0.1_26A434_Restore.ipsw` (Apple CDN, manifest
`signed=true`). Remote pattern-pull obtained the **T8103 + T8112
(SoC-direct) firmware set IN THE CLEAR** — the im4p containers carry
unencrypted LZFSE payloads (payload extraction verified for sptm/ansf):

| Artifact (Firmware/) | Container size | Note |
|---|---|---|
| `sptm.t8103.release.im4p` | 186,687 B | **Secure Page Table Monitor of the J407 SoC family — publicly shipped**; payload 1,228,832 B raw, sha256 `c59c6c8a…` (full in inventory) |
| `sptm.t8112.release.im4p` | 199,175 B | host Mac M2 (t8112) family twin — same SPTM generation delta pair |
| `ansf.t8103/.t8112`, `rans.t8103/.t8112` | ~0.97 MB each | Apple NVMe-storage firmware + recovery variant (role per m1n1-community naming; flagged as such) |
| `pmp/t8103pmp`, `scodec/t8112scodec` | — | power-management / audio-security coprocessors |
| `t8103ciofw`, `t8103tmufw`, `t8112…` | 0.17 MB / 11 KB | composite-I/O and thermal-unit firmware |
| `dfu/iBSS.j715,…,j873s,vma2` (12 files) | — | **T2/bridgeOS-era Mac DFU loaders only** (older Mac boards) |

Published-vs-kept map (what Apple redistributes for this generation's
boot):
- **Shipped:** SPTM per SoC; coprocessor firmware suite per SoC; T2-era
  DFU loaders (for older Macs inside the same universal bundle).
- **Not shipped:** any T8103 boot-CPU stage image (iBoot/LLB/iBSS/iBEC
  class) — confirmed with a SoC-targeted pattern pass plus a
  boot-stage-naming probe across the whole bundle. Same design as the
  SEP: the pieces that enforce the chain on Macs are *not* in the
  restore bundle.

This gives the program a real SPTM/TXM-era study target (kickoff §4.4)
in clear text, including the SoC-family delta pair (t8103 vs t8112) —
the monitor side complements the already-owned iBoot side (consolidated
image).

## 4. Long-shot register: T8103/M1-family SecureROM dump
- Web sweep (Phase A session): no public dump known. The SROM version
  *span* is public metadata (A12/A13 `3865…4479`; per Paradigm Shift,
  A14-class correctly configures DART), but no T8103 ROM bytes are
  public. Stays registered; treat as its own research sub-problem.
- No device-side action planned (SAFE-tier device reads for env census
  remain available whenever the device is out of the box).

## 5. Phase C opened — first-pass recon record on SPTM (t8103)
Host-side only (repo tooling `boot-image-{recon,disasm,calls}.py` on the
extracted payload; reports side-local
`~/research/j407-bootchain/audit-sptm/`):
- **Shape:** Mach-O arm64, 1,228,832 B; decode coverage 95.3%; code
  concentrated in the head (~0x0–0x13FFF mixed windows at 31–38%) with
  a large data tail (functions still present up to ≥`0xf5a20`).
- **Symbols survive:** source-tree strings
  (`Sources/SPTM/sptm/iommu/dart/…`, `…/boot/hib/…` = DART IOMMU +
  hibernation modules) and structured identifier sets
  (`root_pt_fte`/`page_fte`/`prev_pte`, `sanitize_integer`, `refcnt`,
  `caller_domain`, `endpoint_id`, `txm-secure-channel-base/size`,
  `dart-tunables-*`, `nvme-secure-bar`, `bypass`, `carveout`).
- **Control flow:** 370 `pacibsp` function starts (the monitor is
  PAC-instrumented), 3,386 `bl` edges, hottest routine `+0xf5a20`
  (873 in-calls).
- Named audit question this immediately feeds (Phase A §2): the
  DART-bypass question now has two levels — **ROM-level DART mode**
  (needs a dump; Phase B long-shot) and **SPTM-level DART policy**
  (startable now with these bytes). The usbliter8 class taught us which
  config made the difference on A12/A13; SPTM is where the A14-class
  "correct configuration" plausibly lives at the higher stage.

## 6. Ground rules honored
- No device connection in this phase (normal-iOS read earlier used
  usbmuxd; announced; no writes; nothing persistent).
- No device-unique values (ECID/UDID/serial), no NONC/SNON, no USB
  serial strings in this document. All artifact bytes stay side-local.
- `make test` green before this commit (repo tooling untouched).
