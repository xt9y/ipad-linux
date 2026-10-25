# J407 boot image recon — host-side first pass (24A446)

Source: raw `iBoot.j407.RELEASE` payload (the unified iBSS/iBEC/LLB/iBoot image, build tag `mBoot-20457.2.37`), analyzed offline outside the repository. This report contains only digest prefixes and content strings — no device-unique values exist in a bootloader image anyway.

```text
## header
size: 2255320 bytes
sha256: dc3cb25f29f25645 (prefix)
first-32-bytes: 1f211cd5df3f03d502113cd542005eb2420065b202111cd5df3f03d500000090
tail-16-bytes: 05000000000000000100000000000000

## strings
total printable tokens: 1953 (unique 1348)

## build identities
  mBoot-20457.2.37

## keyword corpus
  [  1] getenv: getenv
  [  1] setenv: setenv
  [ 10] usb: arm-io/usb-complex; arm-io/usb-complex/usb-device; force-usb-power; rsm-usb; usb-device; usb-drd0; usb-drd1; usb-hi-current; usb-otg0; usb-otg1
  [ 18] dart: arm-io/dart-; dart-acio0; dart-acio1; dart-ane; dart-aop; dart-apciec0; dart-apciec1; dart-ave; dart-dcp; dart-dcpext; dart-disp0; dart-dispext0; dart-id; dart-isp; dart-sio; dart-tunables-instance-; dart-usb0; dart-usb1
  [  2] pmgr: arm-io/pmgr; arm-io/pmgr-child
  [  2] secure: secure-boot; secure-boot-hashes
  [  2] aes: gid-aes-key; uid-aes-key
  [  1] malloc: malloc
  [ 54] boot: auto-boot; auto-boot-once; battery-force-boot; boot-adapter-id; boot-args; boot-battery-state; boot-breadcrumbs; boot-command; boot-device; boot-ios-diagnostics; boot-manifest-hash; boot-nonce; boot-nonce-hash-method; boot-object-manifests; boot-partition; boot-path; boot-ramdisk; boot-reason; boot-stage; boot-type; boot-voltage; boot/OS.dmg; boot/active; boot/applelogo
  [  7] debug: arm-io/cpu-debug-interface; debug-enabled; debug-soc; debug-uarts; debug-wait-start; dev-unset-debug-enabled; enable-auth-debug

## short identifiers (frequency >= 2, top 60)
   40x single
   22x struct
   15x failed
   14x calibration
   13x invalid
   10x called
    9x passed
    8x string
    8x sysconfig
    8x upgrade
    7x external
    7x parity
    7x terminated_by
    7x version
    6x manifest
    6x tunables
    6x uint32_t
    5x access
    5x cannot
    5x expected
    5x memory
    5x recover
    5x source
    5x synchronous
    4x channel
    4x command
    4x defined
    4x deleted
    4x firmware
    4x fsboot
    4x image_count
    4x image_offset
    4x interrupt
    4x length
    4x optmask
    4x provided
    4x reached
    4x section
    4x setpicture
    4x uint8_t
    4x unknown
    3x button
    3x common
    3x config
    3x counted_by
    3x decode
    3x exception
    3x failing
    3x flipbook
    3x offset
    3x repair
    3x unsupported
    2x abcdef
    2x aborting
    2x address
    2x apciec0
    2x apciec1
    2x battery
    2x bytemode
    2x chained

## entropy (48 KiB windows)
  windows: 46 high-entropy(>3.0): 41 low: 5
```

---

## capstone decode pass

Address-base-free structured decoder pass (same raw unified `mBoot-20457.2.37` payload), gap-skipping across literal pools. All offsets are image-relative; load-base resolution is a follow-on step. Data regions additionally decode as spurious instructions — coverage is an upper bound there. The literal-pool section extracts 8-byte-aligned constants from undecoded gap spans and long udf runs, keyed on the high 32 bits (all T8103 physical addresses are < 2^40, so the high word selects the region); packed dword-pair config tables and string data are filtered out, and DRAM-classified values must be 4 KiB page aligned (candidate values, not proven pointers).

```text
## coverage
image words: 563830, decoded instructions: 474556
decode coverage: 84.2% (rest = literal pools/bounds data)
  undecoded gap spans: 41055, udf-run spans: 32901

## mnemonic histogram (top 24)
    83471 udf
    63088 mov
    50506 bl
    38813 add
    23202 stp
    21015 ldr
    19784 ldp
    17690 str
    14705 cmp
    11865 adrp
    10809 b
     7278 b.hs
     6906 sub
     6717 cbz
     6522 movk
     5895 ccmp
     4807 stur
     4662 ret
     4330 pacibsp
     3988 tbz
     3633 b.ne
     3388 csel
     3316 retab
     3176 eor

## system-register access surface (all)
      2 mrs actlr_el2
      1 mrs ccsidr_el1
      1 mrs clidr_el1
      1 mrs cntfrq_el0
      2 mrs cntkctl_el1
      1 mrs cntp_ctl_el0
      1 mrs cpacr_el1
      8 mrs elr_el1
      2 mrs esr_el1
      1 mrs far_el1
      2 mrs fpcr
      2 mrs fpsr
      1 mrs hcr_el2
      1 mrs id_aa64isar0_el1
      1 mrs id_aa64pfr0_el1
      1 mrs isr_el1
      3 mrs mpidr_el1
      1 mrs par_el1
      1 mrs s0_0_c11_c8_4
      1 mrs s0_2_c6_c13_6
      1 mrs s0_3_c3_c10_5
      1 mrs s0_4_c1_c9_0
      1 mrs s0_5_c14_c10_1
      1 mrs s0_5_c2_c6_7
      1 mrs s0_6_c0_c3_4
      1 mrs s2_0_c2_c0_3
      1 mrs s2_1_c4_c0_4
      1 mrs s2_2_c1_c9_6
      1 mrs s2_3_c0_c15_0
      1 mrs s2_7_c0_c6_0
      1 mrs s2_7_c2_c4_7
      1 mrs s3_1_c3_c14_2
      5 mrs s3_3_c15_c7_0
      1 mrs s3_3_c9_c0_2
      1 mrs s3_4_c15_c10_5
      2 mrs s3_4_c15_c2_5
      1 mrs s3_5_c14_c0_2
      1 mrs s3_5_c15_c0_6
      1 mrs s3_6_c14_c13_0
      2 mrs s3_6_c15_c14_6
      1 mrs s3_6_c7_c3_4
      1 mrs s3_7_c0_c7_7
      4 mrs sctlr_el1
      4 mrs sp_el0
      2 mrs spsr_el1
      2 mrs tcr_el1
      2 mrs tpidr_el0
      3 mrs tpidr_el1
      1 mrs tpidrro_el0
      4 mrs ttbr0_el1
      5 mrs ttbr1_el1
      1 msr #0
      2 msr #0xf
      2 msr #1
      1 msr #4
     35 msr x0
     20 msr x1
      3 msr x10
      2 msr x11
      1 msr x15
      2 msr x16
      2 msr x19
      6 msr x2
      1 msr x23

## call landscape
  bl/blr instructions: 50506 (direct bl: 50506, register-indirect: 0)
  distinct direct bl targets: 10120

## adrp/adr page-cluster histogram (top 16, page-relative buckets)
   1696 page+0x159
    713 page+0x23e
    596 page+0x197
    459 page+0x1e3
    388 page+0x15a
    326 page+0x199
    312 page+0x20c
    305 page+0x19a
    289 page+0x19c
    286 page+0x23b
    271 page+0x1e4
    219 page+0x19b
    216 page+0x236
    203 page+0x23d
    195 page+0x198
    186 page+0x224

## movk shift-histogram (top 16)
   1042 2
    257 0xbad0
    141 0x3d
    136 0x21
    130 0x35
    130 0x25
    129 0x2d
    128 0x31
    125 0x29
    116 0x39
     96 0x20
     74 0x200
     60 0x24
     57 0x3c
     52 0x7450
     52 0x4e6f

## literal-pool address-constant candidates (known families only)
  scan spans (gaps + udf runs): 73956, address-like pool constants: 264
    171 peripherals/MMIO (base 0x200000000)
     73 upper MMIO/PCIe window
     20 DRAM region (base 0x800000000)
    0x0000000200000000 @ +0x309b8  peripherals/MMIO (base 0x200000000)
    0x0000000200000004 @ +0x159b88  peripherals/MMIO (base 0x200000000)
    0x000000020000000c @ +0x15a210  peripherals/MMIO (base 0x200000000)
    0x0000000200000040 @ +0x15a640  peripherals/MMIO (base 0x200000000)
    0x00000002000000c8 @ +0x15a660  peripherals/MMIO (base 0x200000000)
    0x0000000200000118 @ +0x15b438  peripherals/MMIO (base 0x200000000)
    0x0000000200000014 @ +0x15c1e8  peripherals/MMIO (base 0x200000000)
    0x0000000200000070 @ +0x15c200  peripherals/MMIO (base 0x200000000)
    0x000000020000004c @ +0x15c268  peripherals/MMIO (base 0x200000000)
    0x0000000200000024 @ +0x15c2f8  peripherals/MMIO (base 0x200000000)
    0x0000000200000034 @ +0x15ddb0  peripherals/MMIO (base 0x200000000)
    0x000000020000002c @ +0x15ddc8  peripherals/MMIO (base 0x200000000)
    0x0000000200000048 @ +0x15ddf8  peripherals/MMIO (base 0x200000000)
    0x000000020000024c @ +0x15df08  peripherals/MMIO (base 0x200000000)
    0x0000000200002808 @ +0x15ec58  peripherals/MMIO (base 0x200000000)
    0x0000000200000090 @ +0x15f380  peripherals/MMIO (base 0x200000000)
    0x0000000200000028 @ +0x160ab8  peripherals/MMIO (base 0x200000000)
    0x0000000200000060 @ +0x188820  peripherals/MMIO (base 0x200000000)
    0x0000000200000140 @ +0x1888a8  peripherals/MMIO (base 0x200000000)
    0x00000002000000cc @ +0x188cd0  peripherals/MMIO (base 0x200000000)
    0x0000000200000400 @ +0x18e820  peripherals/MMIO (base 0x200000000)
    0x0000000200000008 @ +0x18f1e8  peripherals/MMIO (base 0x200000000)
    0x00000002000000f0 @ +0x18f538  peripherals/MMIO (base 0x200000000)
    0x0000000200000018 @ +0x18f858  peripherals/MMIO (base 0x200000000)
    0x00000002000000a0 @ +0x18fa68  peripherals/MMIO (base 0x200000000)
    0x0000000200000128 @ +0x18fa88  peripherals/MMIO (base 0x200000000)
    0x0000000200000030 @ +0x1906c8  peripherals/MMIO (base 0x200000000)
    0x00000002000000d8 @ +0x190708  peripherals/MMIO (base 0x200000000)
    0x00000002000002e8 @ +0x1907a8  peripherals/MMIO (base 0x200000000)
    0x0000000200000390 @ +0x1907e8  peripherals/MMIO (base 0x200000000)
    0x00000002000005a0 @ +0x190888  peripherals/MMIO (base 0x200000000)
    0x0000000200000648 @ +0x1908c8  peripherals/MMIO (base 0x200000000)
    ... (truncated at 32 unique values)```

## pc-relative data xref (load-base independent)

First code-to-data cross-reference pass (`tools/boot-image-xref.py`): ADRP(+immediate ADD) address formation is fully PC-relative, so target pages resolve in image coordinates without knowing the load base. Literal-pool LDRs (pointer traffic needing the base) are counted but not resolved.

```text
## pc-relative data-reference map
instructions decoded: 474556
adrp(+add) data references resolved: 9220 to 688 distinct target pages
literal-pool LDR instructions: 18459 (pointer traffic without resolved values — pool constants need the load base)

top referenced pages with resident strings (candidates for string/config tables and handler data):
  page+0x19c:   74 refs  "asc_data_isolation_handoff_telemetry_restricted"; "arm-io/smc/iop-smc-nub/smc-socd"; "s/usr/standalone/firmware/FUD/"
  page+0x1db:   70 refs  (no strings)
  page+0x1da:   62 refs  (no strings)
  page+0x1bd:   59 refs  "RDkA/1"
  page+0xd2:   59 refs  (no strings)
  page+0x2dc:   57 refs  (no strings)
  page+0x1be:   56 refs  (no strings)
  page+0x19b:   54 refs  "cacal_find_right_failing_point"; "cacal_find_right_passing_point"; "arm-io/aop/iop-aop-nub/compass"
  page+0x19d:   52 refs  "DERDecodeSysConfig3ParseAndPopulateMetadataSequence"; "single_allocSysConfig3PayloadEntryInternal"; "singlesysConfig3GetPayloadEntryForKey"
  page+0xd8:   52 refs  (no strings)
  page+0xdc:   51 refs  (no strings)
  page+0x24b:   50 refs  (no strings)
  page+0x1ad:   49 refs  (no strings)
  page+0x1d3:   47 refs  (no strings)
  page+0x245:   46 refs  (no strings)
  page+0x1dd:   43 refs  (no strings)
  page+0x277:   43 refs  (no strings)
  page+0x28a:   43 refs  (no strings)
  page+0x1a7:   42 refs  "cwFS6z"
  page+0x1de:   42 refs  (no strings)```

## literal-pool structure finding (two 256-class dispatch tables)

From the pool/udf-span qword scan plus follow-up verification (all offsets image-relative):

- Table A: 256 contiguous qword entries at `0x1945a8`–`0x194da0`, each `{low32, 0x8010b803}`. The low32 values resolve to exactly **11 distinct code offsets** (e.g. `0x140ca0`, `0x140cd4`, `0x140d08`, …) inside a 0x2c0-wide window.
- Table B: 255 contiguous qword entries at `0x194da8`–`0x195598` directly adjacent, each `{low32, 0x801023ca}`, resolving to 11 distinct code offsets around `0x145adc`–`0x145b6c`.
- **Byte→kernel partition measured (2026-10-24 round)**: both tables map onto an *identical* 11-handler partition. Table A: 120 ordinary bytes (≡0–5 mod 8 and the rest of the residual class) → `0x140ca0`; the 32-byte block `0xa0–0xbf` → `0x140cd4`; bytes ≡7 mod 8 (7, 15, …, 159) → `0x140d08`; `0xf1–0xff` → `0x140dec`; `0xf0` → `0x140e10`; `0xe1–0xef` → `0x140e38`; `0xe0` → `0x140e50`; bytes 14/22 → `0x140f04`; the ≡6 mod 8 bytes split range-dependently between `0x140f2c` (30–62 plus an extended set) and `0x140f34` (70–110, 134–158, 198–206); byte 6 alone → `0x140f60`. Table B repeats the same partition with kernels `0x145adc..0x145c1c` and its own PAC context. Explicit single-byte tokens at `0xe0`/`0xf0`, a 32-byte block above `0xa0`, and the ≡6/≡7 mod 8 sub-classes are consistent with a literal-run/match control-byte taxonomy of an LZ-family decoder; bit-exact public-format equivalence is not claimed.
- Verify: bytes at the resolved targets decode as clean AArch64 bit-manipulation kernels (`lsr X, X, #6` / `add` / `cmp` / `b.hi` / `ubfx`) — the low32 halves are genuine image-relative code offsets, not coincidence.
- Interpretation (updated): the 256/255-entry tables are byte-indexed dispatch into 11 handlers each (partition above). *Correcting the earlier "no absolute pointers in the pool" reading*: the pool's `hi32=1` qwords (16,470) **are** absolute pointers — base **`0x1FC000000`** — but they target only the SMC-domain RAM (image-relative `[0x1a5b50..0x28a640]`), never iBoot's own code/data; "load-base independent" remains true for iBoot-internal addressing (see the address-space section below).

## string-anchored references pass

Reverse index over the ADRP(+ADD) graph (`tools/boot-image-xref.py` extension): which code pages form addresses into the string namespace. Page-level attribution (a formation pair targets one address; other strings sharing that page are listed). Highlights:

- `getenv`/`setenv`/`setenvnp` cluster: page 0x211, referenced from code at `+0x778ac`, `+0x89778`, `+0xb76dc`, `+0xb78cc`, `+0xb80d4`, `+0xb8174` and more — the environment variable machinery handler cluster.
- `boot-command`, `boot-args`, `iBootData`, `auto-boot-once`: page 0x210, referencing code pages ~`0x88-b4` (the boot-flow callout cluster).
- `com.apple.System.boot-nonce`: page 0x223 with 20 referencing sites in the `0x96-b4` region (platform nonce registry plumbing).
- Early-entry anchors: the image value at `+0x1c` already forms the address of the `mBoot-20457.2.37` string, and the `0xb24-0xf4c` range references the `recovery-boot-mode`/`boot-device`/`boot-path` namespace — first-boot property flows happen before much else.

Sample code windows at cluster sites (raw texture, decoded offline):

```text
--- at 0x778a8
    0x778a0  b.eq    #0x778c8
    0x778a4  and     w8, w1, #0xfffffffd
    0x778a8  cbnz    w8, #0x778c8
    0x778ac  adrp    x0, #0x19a000
    0x778b0  add     x0, x0, #0x33a
    0x778b4  adrp    x3, #0x159000
    0x778b8  add     x3, x3, #0xbb8
    0x778bc  add     x2, x0, #0xb
    0x778c0  mov     x1, x0
    0x778c4  b       #0xe174c
--- at 0x89778
    0x89770  add     x4, x4, #0x108
    0x89774  b       #0x136cf8
    0x89778  adrp    x4, #0x188000
    0x8977c  add     x4, x4, #0xa28
    0x89780  b       #0x136cf8
    0x89784  mov     x0, #0x72c3
    0x89788  movk    x0, #0x36c1, lsl #16
    0x8978c  movk    x0, #0xf5bc, lsl #32
    0x89790  movk    x0, #0xd25, lsl #48
    0x89794  ret     
--- at 0xb76dc
    0xb76d4  str     xzr, [sp, #0x28]
    0xb76d8  add     x8, sp, #0x28
    0xb76dc  adrp    x4, #0x15a000
    0xb76e0  add     x4, x4, #0x200
    0xb76e4  add     x1, sp, #0x28
    0xb76e8  add     x2, sp, #0x28
    0xb76ec  add     x3, x8, #0xc
    0xb76f0  mov     w0, #0x6f73
    0xb76f4  movk    w0, #0x4431, lsl #16
    0xb76f8  bl      #0xb71c4
```

```text
## string-anchored references
pages of interest that ADRP(+ADD) formation pairs target,
with the referencing code pages (page-level attribution: a
pair targets one address; residents of the same page are shown):
  page+0x19c:  74 refs from +0x5168; +0x517c; +0x51e0; +0x53d8; +0x549c; +0x54e4 (+68 more)  strings: ["iboot-data", "boot-object-manifests", "secure-boot-hashes", "VMiBoot", "iBootIm", "iboot-]
  page+0x19b:  54 refs from +0x4018; +0x4050; +0x4078; +0x40b0; +0x40e4; +0x40f8 (+48 more)  strings: ["disable-boot-wdt", "dev-unset-debug-enabled", "arm-io/dart-", "dart-tunables-instance-", ]
  page+0x19d:  52 refs from +0x6024; +0x6038; +0x6040; +0x6070; +0x6078; +0x60a4 (+46 more)  strings: ["DERDecodeSysConfig3ParseAndPopulateMetadataSequence", "DERDecodedInfo", "SysConfig3Payloa]
  page+0x19a:  40 refs from +0x32ec; +0x369c; +0x3a24; +0x3b60; +0x3cc8; +0x3e64 (+34 more)  strings: ["iboot-handoff", "dart-apciec0", "dart-usb0", "dart-acio0", "dart-apciec1", "dart-usb1", "]
  page+0x198:  34 refs from +0x1298; +0x12c8; +0x13c4; +0x148c; +0x14f4; +0x15c0 (+28 more)  strings: ["boot-args"]
  page+0x19e:  32 refs from +0x7068; +0x7078; +0x709c; +0x7138; +0x7394; +0x73bc (+26 more)  strings: ["SysConfig3", "SysConfigData", "SysConfig3", "SysConfigData"]
  page+0x199:  28 refs from +0x2288; +0x2294; +0x2620; +0x2660; +0x2720; +0x2810 (+22 more)  strings: ["boot-ios-diagnostics", "debug-enabled", "secure-boot", "boot-nonce", "boot-nonce-hash-met]
  page+0x200:  26 refs from +0x65c3c; +0x65c68; +0x65c9c; +0x65d00; +0x65d20; +0x65d44 (+20 more)  strings: ["mBoot-20457.2.37"]
  page+0x218:  25 refs from +0x39574; +0x3ba44; +0x7d0fc; +0x7d34c; +0x7d910; +0x7d97c (+19 more)  strings: ["dart-ane", "dart-aop", "dart-ave", "dart-isp", "dart-sio"]
  page+0x223:  20 refs from +0x9679c; +0x969b0; +0x96aac; +0x96b80; +0x96c30; +0x96c7c (+14 more)  strings: ["com.apple.System.boot-nonce"]
  page+0x210:  19 refs from +0x88bf0; +0x88e48; +0x88e7c; +0x88fe0; +0xb0500; +0xb4a3c (+13 more)  strings: ["iBootData", "iBootData", "boot-args", "auto-boot-once", "boot-command", "com.apple.System]
  page+0x211:  19 refs from +0x778ac; +0x89778; +0xb76dc; +0xb78cc; +0xb80d4; +0xb8174 (+13 more)  strings: ["getenv", "setenv", "setenvnp"]
  page+0x197:  17 refs from +0xb24; +0xb58; +0xcac; +0xdec; +0xe98; +0xf4c (+11 more)  strings: ["recovery-boot-mode", "boot-breadcrumbs", "boot-ramdisk", "boot-path", "boot-device", "boo]
  page+0x215:  16 refs from +0x7d1a0; +0x7d8cc; +0x7da5c; +0x7ea70; +0x889c8; +0xbc114 (+10 more)  strings: ["fsboot-safe", "dart-dcp", "dart-disp0", "dart-disp0", "dart-dcpext", "dart-dispext0", "da]
  page+0x0:   1 refs from +0x1c  strings: ["mBoot-20457.2.37"]```

## dispatch-table semantics (structural characterization)

Follow-up on the two pool tables at `0x1945a8` / `0x194da8` — now end-to-end confirmed as indexed dispatch structures:

- **Ten accessor code sites** materialize addresses directly onto specific table entries (formation targets `0x194b78→A#186`, `0x194bb8→A#194`, `0x194be8→A#200`, `0x194d88→A#252`, `0x195190→B#125`, `0x195200→B#139`, `0x195218→B#142` (5 sites), `0x195378→B#186`); most sites are accessors whose next instruction is `ret` or a branch into a helper (`b #0x136cf8`, `b #0x3b704`) — they hand out pointers to entries. Others form pointers to neighboring flat structures on the same pages.
- **Every sampled entry contains a kernel target**: the low32 of each accessor-listed entry equals one of the 11 kernel code offsets of its table (verified both tables). So the full chain `code → accessor → entry[byte_idx] → {low32 = image-relative kernel offset, constant cookie}` is statically verified. The accessors never form addresses into the tables from the kernel clusters themselves (0 formation refs from regions 0x50/0x51) — consumers and kernels are separate.
- **The two tables are parallel twins**: the byte-index → kernel partition is identical in structure across A and B — same class sizes and index ranges (120 / 32 `[160..191]` contig / 20 / 15 `[241..254|255]` contig / 1 `[240]` / 15 `[225..239]` contig / 1 `[224]` / 2 / 37 / 12 / 1 `[6]`), each table dispatching into its own 11-kernel cluster (`0x140ca0..0x140f60` and `0x145adc..0x145c1c`).
- **Class-zone texture**: boundaries at `0xA0`-`0xBF`, `0xE0`, `0xE1`-`0xEF`, `0xF0`, `0xF1`-`0xFF`, singletons at `0x06` — Latin-range style character-class partitions. The kernels are compact bit-arithmetic routines (`lsr x?, x?, #6`, `ubfx ..,#3,#3`, `add #2`/`#3`, `cmp`, `b.hi`) consistent with small decoders/classifiers.
- **Kernel cluster texture (update)**: the big class (`0x140ca0`, 120 indices) covers bytes `≡0..5,6 mod 8`-style stride blocks (`0x00-0x05, 0x08-0x0d, ... 0x80-0x85, 0x88-0x8d, 0x90-0x95, 0x98-0x9d, 0xc0-0xc5, 0xc8-0xcd`); single-byte-index kernels own `0x06`, `0x0e`+`0x16`, `0xe0`, `0xf0`; the stride texture is `≡6/7 mod 8` exclusion bands plus magnitude splits — a protocol-shaped partition, not a text-class map (see driver findings below).

## dispatch drivers identified (braa + LZFSE engine context)

Both consumer loops are now located and the full semantic chain closes:

- **Driver A** (function block `0x140b80..0x140c9c`): forms table A base with `adrp x11, #0x194000; add x11, x11, #0x5a8`; maintains ring/window state at context offsets `+0x30/+0x38/+0x40/+0x48`; per-byte flow is `ldrb w16, [x12]` → `ldr x14, [x11, w16, lsl #3]` (full qword incl. cookie) → `mov x17, #0xb803` → **`braa x14, x17`** — an authenticated indirect branch (ARMv8.3 PAC, A-key) to the kernel. The block also contains LZ-style window copying: neg/offset pointer back-references, a bulk 8-byte copy loop plus `ldrb/strb` tail lanes, bounds `cmp x8/` and `cmp x10, #8`; returns codes `-1`/`-2` (common stubs `0x140b74` returns `#-1`, `+0x140c94` sets `#-2`). Kernels `bl` to the `-1` stub — earlier "kernels call a common helper" wording resolved: `0x140b74` is an error-return stub, not a shared decode helper.
- **Driver B** (`0x145a70..`, `pacibsp`-prologued real function): `adrp x25 + add #0xda8` → table B base; `ldrb w8, [x23]` (stream pointer carrying a length-prefixed chunk, bounds-checked against `[x0,#0x10]`) → `ldr x9, [x25, w8, lsl #3]` → `mov x17, #0x23ca` → `braa x9, x17`. First kernel at `0x145adc` opens with `lsr x21, x8, #6; add w9, w21, #2` — top-2-bits class + length arithmetic (2..5).
- **Cookie semantics resolved structurally**: cookie `= (0x8010 << 16) | modifier`, with modifier `0xb803` (table A) / `0x23ca` (table B) matching each driver's `braa` modifier register exactly. The `braa` consumes the loaded qword (installing the top bits as the signed pointer) with x17 as the modifier — the high-32 is the per-table constant tag/code carried by the authenticated pointer. Key-material semantics (which PAC key/salt produces-consumes it at runtime) are not derivable statically; the image itself is compiled with `pacibsp` prologues throughout, confirming unconditional ARMv8.3 pointer-authentication in this iBoot build.
- **LZFSE-family engine context confirmed**: the twin-table neighborhood is a compression engine. Exact word scans find the full public LZFSE block-magic vocabulary as register-built constants: `bvx$` (end-of-stream) ×2 (`0x145a28`, `0x147314`), `bvx-` (uncompressed block) ×6, `bvxn` ×4, `bvx1` (compressed v1) ×7, `bvx2` (compressed v2) ×5; the public `bvxl` variant is absent, and non-public `avx1`/`avx2` constants (`movz #0x7661` builds) are present nearby. The table-B driver sits 0xe0 bytes after a `bvx$` compare feeding the same block-type dispatch.

**Hypothesis (explicitly labeled, unconfirmed):** the twin 256/255-entry tables are the per-byte interpreter engines inside the iBoot LZFSE-family decoder — byte-driven kernel dispatch with PAC-signed branches, window copying, and error-return codes. Identifying which LZFSE block/field the byte stream belongs to, and the exact kernel set semantics, is future work; device-side confirmation is not available from the DFU surface.

### decompress-call chain (resolved 2026-10-24 round)

A bl/pacibsp callgraph pass (`tools/boot-image-calls.py`; code region `<0x14b000`: 48,624 `bl` edges, 4,190 `pacibsp` prologues, `blr` ×0 — indirect flow is authenticated: `blraaz` ×319, `blraa` ×11, computed targets pre-signed with `paciza` ×566, `braa` ×5, `braaz` ×65, `br` ×213) resolved the static chain into the engine:

- **`0x144a0c` (0x194 B) = the decode-call wrapper (top of the resolved chain).** Six caller args; message-type select `cmp w5, #0x891`; zero-fills the context region (`mov x0, x4; bl 0xd29c0`, length `0x5768`/`0xb910` by type); builds a **PAC-signed context**: `pacda` with per-field movk key constants (`0xb5f0`, `0x0b90`, `0x874b`, `0x9a95`, `0xfa25`, `0x3094`, each folded with the context base) stores `{ptr, ptr+len}` range pairs — args `x2`/`x3` into fields `+0x0..+0x10`, args `x0`/`x1` into `+0x18..+0x28` — writes the type word `0x3a98`/`0x9c40` at `+0x1c88`, then `bl 0x145e44(x0 = context)` (site `0x144b48`) and returns an authenticated-pointer delta (`autda` + `xpacd` sanity check + `sub x20, x16, x19` = bytes consumed/written). **It carries zero static references** across every encoding channel (no `bl`/`b`/`b.cond`/`cbz`/`tbz` edge targets it, no 4-byte literal, no `adrp+add` formation, no tagged pool record): the entry path is purely via re-signed pointers (mechanism below).
- **`0x145e44` (0x16c0 B) = the container/decode driver.** Reads global `0x23e5f0` (`0x145e70`), zero-fills twelve buffers (`bl 0xd27f0` ×12), calls helper `0x144330` (`0x1461b8`), helper `0x144630` (`0x14709c`), engine A's window-copy/`−1` landing `0x140b54` (`0x14673c`; inside the driver-A zone `[0x140b44..0x140fc0)`, not a stub), calls the VM mapper `0x30444` (`0x147344`), and tail-branches `b 0x144d5c` (site `0x1474d0`) on one exit path. Sole `bl` caller: `0x144a0c`. **Measured (emulation, see below): the all-`bvx2` SMC stream decodes entirely inside this container — per-block dispatch `0x145ef8`, header parse `0x146414`, VLC table parse `0x1471d8`, decode loops `0x14685c` — without executing `0x144d5c`, `0x145a70`, `0x145c3c` or `0x30444`; that sub-chain is a separate arm not exercised by this stream.**
- **`0x144d5c` (0xd14 B) = the block-magic dispatcher.** movz/movk-built magic compares: `0x3178_7662` = "bvx1", `0x3278_7662` = "bvx2", `0x6e78_7662` = "bvxn"; unhandled magic → `b.ne 0x145a28` (the `bvx$` zone). The decompress call is measured at **site `0x144edc`: `add x0, sp, #0x40; bl 0x145a70`** — driver B, per block, context in `x0`. Other calls: `0x144ba0` (`0x144f40`), bit-packer `0x145c3c` (`0x1454cc`), `0x145d80` (`0x1459d8`), and — as the function's very last word — `bl 0x30444` (`0x145a6c`) whose return address is exactly driver B's entry: **return-address chaining** into the next stage.
- **Engine A** (fn `0x1408bc`, 0x288 B, + the window-copy driver zone `[0x140b44..0x140fc0)` with no own prologue — `0x1408bc` falls through into it): static caller chain `0xf5e94 →(bl) 0xf8cac →(bl) {0x13fea4, 0x14022c} →(bl) 0x1408bc` (sites `0x14034c`, `0x13ffa0`). Harnesses: `0x13fea4` (0x144 B) additionally calls the `w0 == 0x300002` predicate `0x140b44` twice (`0x13fed0`, `0x13ff64`); `0x14022c` (0x1f0 B) gates on `[x0,#0x20]`/`[x0,#0x28]`. Driver A's per-byte dispatch is measured directly at all four of its `braa` sites (`0x140bd0`, `0x140c24`, `0x140f00`, `0x140f28`): `ldrb w16, [x12]; ldr x14, [x11, x16, lsl #3]; mov x17, #0xb803; braa x14, x17`, table A base formed inline (`adrp x11, #0x194000; add x11, #0x5a8` = `0x1945a8`) — the cookie/table relations confirmed structurally; error codes −1 (`0x140b74` family), −2 (`0x140c94`), −3 (`0x140f2c`); kernel `0x140f60` = end-of-stream (consumes 8 bytes, sets flag at `+0x50`, returns 0). Driver B's single `braa` sits at `0x145ad8`, matching the earlier identification.
- **`0x145c3c` + leaf `0x145d30` = bit-packer pump:** per-byte emit into a 32-bit accumulator (bit-buffer/bit-count at `[ctx+0x18]`; full words flushed through the `[ctx+0x10]` cursor, called as `bl 0x145c3c(x2 = bytes, w1 = count)`) — the entropy-coder bitstream infrastructure.
- **`0x30444` = the ARM64 VM mapper — closes the beyond-file decode destination:** a three-level page-table walk (`ubfx` index bitfields, table descriptors `orr x7, #0x8000000000000003`, 4-KB granule stepping), allocator-cursor global `0x23e580`, TTBR roots at `0x215700`/`0x215708`, KASLR-slide-relative self-relocation (`... - x12`, `msr ttbr0_el1`/`ttbr1_el1`/`vbar_el1`, then `br x1` into the relocated continuation). The decode chain maps fresh pages into its output region as it advances — the mechanism behind the decoded SMC image living beyond the delivered file.

**End-to-end offline proof (2026-10-25): the `0x144a0c` arm decodes the real SMC stream byte-exactly.** The chain was executed under Unicorn ARM64 emulation on the actual unified image — PAC neutralized in the mapped copy only (`retab`/`retaa` → `ret`; `autibsp`/`paciza`/`pacda`/`autda`/`xpacd` → NOP; `braa`/`blraa` → NOP with scoped hooks resolving the register's `{tag|low32}` record to `BASE+low32` and setting LR for calls; VM mapper `0x30444` skipped at entry, with page mapping for the output pre-arranged). Entry `0x144a0c`, `x0` = output buffer, `x1` = 1 MB, `x2` = stream VA (`0x1a3768`), `x3` = `0x39d23`, `x4` = zeroed context, `x5` = 0. Result: **`0x79760` B written, SHA-256 prefix `7da684741cedf068` — byte-identical to the liblzfse reference output** — with measured counts: container entry ×1, block headers ×5, frequency-table parses ×5, symbol decodes 1800 (= 5×360), decode-loop entries ×5, copy helpers `0x144330`/`0x144630` ×5 each, error paths ×0.

Facts confirmed by the run:

- Argument orientation: `x0`/`x1` = output `{ptr, len}`, `x2`/`x3` = input stream `{ptr, len}`, `x4` = context, `x5` = type selector; the wrapper returns the authenticated delta on success and `0` when the container reports a nonzero error.
- Context fields: `+0x0..+0x10` = input `{start, end}` (copy of `x2`, `x2+x3`), `+0x18..+0x28` = output `{start ×2, end}`, `+0x1c88` = type word (`0x9c40` unless `x5 == 0x891`, then `0x3a98`) with zero-fill length `0xb910`/`0x5768` respectively; helper `0x144630` receives `x2 = type−0x10` (`0x9c30` in selector 0).
- The in-image decoder re-reads its in-file frequency tables **before every block**: `0x207d88` = 32-byte type table (`02 03 02 05 02 03 02 08 02 03 02 05 02 03 02 0e` ×2; each byte = bits consumed), `0x207da8` = 32-byte signed table (`0 2 1 4 0 3 1 −1 0 2 1 5 0 3 1 −1 0 2 1 6 0 3 1 −1 0 2 1 7 0 3 1 −1`). Consequence for any emulation/decoder harness: the output buffer must not overlap the image (an overlap initially overwrote these tables mid-decode and produced a false `−3`).
- Per block, a VLC bitstream at `magic+0x20` yields **360 16-bit entries**: 5-bit index → type byte = bits consumed (`0xe` → +10 bits, value `+0x18`; `0x8` → +4 bits, value `+8`; otherwise the signed-table value); the table region ends at `magic+0xc9` (block 0) / `magic+0xcb` (blocks 1–2 measured); the block ends valid when residual bits ≥ 7 or the cursor exactly reaches the limit. An independent pure-Python simulation of this algorithm parses all five blocks cleanly — algorithm and data are consistent.

**Answer to "which arm drives the SMC-stream decode": the `0x144a0c` wrapper with selector 0 (type word `0x9c40`).** That arm reproduces the SMC image exactly; the `0x891`-selected variant (`0x3a98` type word, `0x5768` zero-fill) is a different mode not used by this stream's decode.

**The `0x891` type family (static scan).** The immediate appears at 19 sites across `0x20e0c`, `0x32ae4`, `0x79718`, `0x89150`, `0xddb10`, `0x1196c0`, `0x119960`, `0x144958`, `0x144a0c`, `0x145e44`, directly paired with the context-layout constants: `0x5768` (zero-fill, sites `0x144958`/`0x144a0c`), `0xb910` (selector-0 zero-fill, `0xba24`/`0x144958`/`0x144a0c`), `0x3a98` (`0x11d42c`/`0x144a0c`) and `0x9c40` (`0x7d04`/`0x9128`/`0x83860`/`0x144a0c`/`0x144d5c`/`0x145e44`). `0x20e0c` also does `mov w0, #0x891; bl 0x147348` — the container's cold tail entry immediately after the `bl 0x30444` at `0x147344` — so the `0x891` protocol selects the alternate context layout inside the same container code.

**Top-of-chain entries.** The pool's `{0x80XX0000 | low}` records are now structurally explained: the wrapper itself re-signs its pointers with `pacda` + per-field movk key constants — the same `{modifier | address}` shape as the pool records — and the runtime indirect-call machinery (`blraaz`/`braa`/`br` on targets pre-signed as `{tag|address}` records, `paciza`-signed) consumes them. One concrete instance: **`pool[0x192078] = {0x80200000 | 0xf5e94}`** — the entry record of the `0xf5e94` arm, in an alternating pattern with SMC-domain pointers (`{1|0xfc1a5bb8} ↔ {0x8020|0xf56e4}`, `{1|0xfc1dd7b8} ↔ {0x8020|0xf5e94}`, `{1|0xfc1dd7e0} ↔ {0x8020|0xf7078}`, `{1|0xfc1dc130} ↔ {0x80a0|0xf71fc}`, …) — **per-SMC-object handler wiring between iBoot and the SMC domain**, not ordinary callgraph material. The `0x144a0c` arm's caller is presumably reached through the same machinery; static search finds nothing for it.

Remaining opens, narrowed: the `0x891` message-type and `0x3a98` word semantics (`0x9c40`/selector 0 now proven to drive the SMC-stream decode) and the per-byte kernel-set mapping table (kernel semantics themselves).

## address space & runtime layout (resolved 2026-10-24 round)

The long-standing open questions — what the 18,459 literal-pool loads actually reference, why 54% of resolved formation targets fall beyond the file, and whether a per-segment VA↔file-offset model is needed — closed with a full value-class census of the pool region `0x15b000..0x196ff8` (30,719 qwords):

| pool class (hi32 \| low32) | n | reading |
|---|---|---|
| `{1 \| low ∈ [0xFC000000..0xFD000000)}` | 16,029 | **SMC-domain pointers** — absolute pointers `0x1FC000000 + image-relative offset`, every target in `[0x1a5b50..0x28a640]`, never touching iBoot's own code/rodata |
| `{1 \| small}` remainder | 441 | `{tag, count/size}` records |
| `{tag \| small}`, hi32 ∈ {2:479, 6:238, 0x10000001:211, 0x80000001:151, 0x40000001:143, 0xb:129, 0x13:83, 3:69} | 1,503 | tagged small-value records (counters/ids/attrs), not pointers |
| `{0x8010b803 \| kernel}` | 256 | dispatch table A (11 kernels `0x140ca0..0x140f60`) |
| `{0x801023ca \| kernel}` | 255 | dispatch table B (11 kernels `0x145adc..0x145c1c`) |
| `{0x80XX0000 \| low}` (top tags 0x8020×345, 0x8010×127, 0x8030×40, 0x8070×29, 0x8040×21, 0x80f0×15, …) | 1,220 | class-tagged pointer records; **94% of lows are offsets into iBoot's own code band** (`0x1316d8`, `0x1351d4`, `0x133cfc`, `0x157f6c`, …; remainder in the `0x151000..0x158000` service band) |
| `{0 \| small}` | 7,521 | plain integers (7,415 below `0x10000`) |

The `{0x80XX0000 \| offset}` records share the pointer shape of the dispatch entries (`{signed-pointer-tag, target}`); the per-class hi32 codes act as pre-signed-pointer context tags. Which key/material actually signs them at runtime is not derivable statically and is not asserted.

### The SMC RAM map (built from the pointer family)

The 16,029 domain pointers describe one contiguous region, image-relative **`[0x1a5bb8..0x28a640]`**, addressed at **SMC-VA base `0x1FC000000`**:

- **Staging/service zone** `[0x1a5bb8..0x1f64a0)`: 10,405 pointers. The file stores the compressed SMC stream at part of this span (`0x1a3768..0x1dd48b`) — transient packaging bytes; at runtime the space holds staged objects. Measured structure: 607 consecutive 12-byte-strided record pointers at pool `[0x17fd60..0x181058)` (consecutive deltas `0xc` ×517) targeting `[0x1c74d0..0x1ca734]` inside the zone.
- **Decoded SMC image** at **`≈0x1f64a0` (±0x180 anchor-match plateau) + `0x79760` B**: 645 pool pointers land **exactly on RTKSTACK guard-page starts** of the decoded payload and 13 land on payload string starts — content-verified against driver strings `drv_apc_simetra.cpp`, `ADC_GAIN/ADC_OFST: %04X, %04X, %04X`. The destination overlaps the file's `blob_post` band and extends `0x49000` B past the file end.
- **Beyond-file tail** `[0x2269d8..0x28a640]`: 649 pointers — SMC heap/stack living in zero-fill beyond the delivered file; 171 further in-file pointers sit just below the zone base.
- The **fixed shared base `0x1a5bb8` → SMC-VA `0x1FC1A5BB8`** repeats at a strict rhythm in every `0x194000..0x1945a8` descriptor group.

### Reference anomalies closed

- **Inside-stream / blob_post formations** (1,187 + 1,071 of the 9,220 resolved pairs) are **staged-region references**, not reads of compressed bytes: the file's content there is transient packaging, replaced at runtime by the staged zone above. The "16 early-code sites target the stream page" reading becomes "16 early-code sites target staged-zone addresses" (the fixed zone base sits `0x2450` into the file's stream span).
- **Beyond-file formations** (4,995 refs, `0x2269d8..0x3975f0`) are BSS/runtime-object references — e.g. `pc 0x5a8: adrp x8, #0x23e000; add x8, x8, #0x5f0; ldr x8, [x8]` loads a global from beyond the file end. Intra-page offset concentrations `0x5f0` ×631 and `0xbb8` ×338 across hundreds of pages; source PCs concentrate in `0xc0000..0x130000` (303–528 per 64-KiB band). The runtime image therefore under-delivers ≈1.5 MB of zero-fill/BSS relative to the 2,255,320-B file.
- A per-segment VA↔file-offset (δ-shift) model was fitted and **rejected**: string-zone hit counts form a plateau without a spike (≤193/1187); the uniform load model plus a zero-fill tail explains every population.
- iBoot's own addressing stays **load-base independent** (adrp-relative, plain-integer pool constants) — the one absolute base inside the image is `0x1FC000000` (SMC-domain). Consistently, the decoded SMC firmware itself contains **zero** base-coded pointers: it links position-independently, and the base is applied by this image's descriptor constants, not by SMC-side relocations.
- The `0x194000..0x1945a8` descriptor table reads in these terms: `{fourcc+version}` section words (`'MgrC'` v0x0401, `'MitC'` v0x0100, `'aehC'` v0x0100), task rows as 4-tuples of `{class-tag \| iBoot-fn-offset}` (2–3 entries sharing one hi32 class, then a class switch), the fixed `0x1FC1A5BB8` base, and length/id small-ints — the SMC↔iBoot section/task wiring.

## embedded compressed payload (decoded)

The data region contains a real LZFSE-compressed payload, located and decoded **statically**:

- **Stream bounds**: five `'bvx2'` block magics at `0x1a3768`, `0x1b09c2` (+0xd25a), `0x1bf3eb` (+0x1bc83), `0x1cd8b0` (+0x2a148), `0x1db5c8` (+0x37e60), plus end-of-stream `'bvx$'` at `0x1dd487`. The headers are **not 4-byte aligned** (two sit at mod-4 offsets 2 and 3), which is why a 4-byte-grid magic scan finds only three of them. Each header carries its uncompressed size at `magic+4`: `0x14d10 + 0x17286 + 0x17235 + 0x2e3d1 + 0x81c4 = 0x79760` — exactly the decoded output size (independent structural confirmation of the 5-block chain; the in-image decoder's output cursor also advances by exactly each block's `n_raw`, measured).
- **Decoded with the public liblzfse reference decoder**: input `0x39d23` B → output **`0x79760` B** (497,504 bytes); the decoder consumed the stream up to exactly the `'bvx$'` marker. Decompressed SHA-256 prefix `7da684741cedf068` (unified image prefix `dc3cb25f29f25645` for cross-reference). The same stream was later decoded by the **in-image engine itself** under emulation to the identical digest (see the emulation proof in the decompress-call-chain section).
- **Handler-verified structure of the output**: 67.7% non-zero; **0.84% `ret` word density across 0x1e5d8 words** with zero `pacibsp` words — a real (PAC-less, pre-PAC-style) ARM64 module; the dominant record stride is 8 bytes (78.3% of non-zero u32 blocks) with 16-byte nesting.
- **Identity markers**: 1025 eight-byte records spelling **`rtkstack`-style markers as `"RTKSTACK"`** (low32 `0x534b5452 'RTKS'`, high32 `0x4b434154 'TACK'`), plus embedded file-path strings reconstructing to `platform/t8103/...` (e.g. `.../drivers/power/drv_therma...`). The payload head is `b +0x204` followed by zero-fill, and the branch target opens with `mrs x1, currentel; ubfx x1, x1, #2, #2; cmp x1, #3` — an EL3 validation guard.
- **Persistent reading**: the payload is an **Apple coprocessor firmware image built for the `ipad13b` platform group**, embedded LZFSE-compressed inside iBoot's data region.
- **Identity — confirmed by embedded strings**: the payload self-identifies as **`AppleSMCFirmware_H13-7372.2.11.ipad13b.REL`** (at +0x6b878) on top of **`RTKit_release-3514.0.15.release`** (at +0x52dbc). Source-path strings confirm the SMC role: charger (`drivers/charger/v1/potomac/drv_potomac_charger.cpp`), battery management (`smc/bms/v1/batterySocFilter/batterySocFilter.cpp`, `charge_control.cpp`), thermal (`smc/thermal/componentController/basebandCC.cpp`), power/PMU (`drivers/power/drv_pmu_interface.cpp`, `drv_pmu_events.cpp`, `drv_apc_sera.cpp`, `drv_apc_simetra.cpp`), and T8103 platform shim files (`platform/t8103/device_{gpio,pmgr,spmi,watchdog,dockchannel,iop_ans,forcewakeup}.cpp`, `platform/common/platform_{power,mem}.cpp`). The 4096-byte-aligned `RTKSTACK` guard runs (`x1025`) are RTKit stack guard pages. `ipad13b` matches the same platform tag as the J407 `kernelcache.release.ipad13b` in the restore manifest.
- **Consumer chain (resolved)**: the early-code formation sites that appeared to point into the compressed blob (`0xc6c4`, `0xc6f4`, `0xc718`, `0xc738`, `0xc75c`, `0xc77c`, … targeting page `0x1a3`) are **staged-region references** — in the runtime layout that file area is SMC staging/service RAM (see the address-space section above), so no static reference reads compressed bytes. The measured chain is: **embedded compressed firmware (transient file content) → in-image LZFSE-family engine (twin PAC-dispatch tables, 11 kernels each) decodes to image-relative `≈0x1f64a0` → iBoot's pool carries the SMC's runtime object map (16k domain pointers at base `0x1FC000000`: staging records, RTKSTACK guard pages, the image itself, and a beyond-file heap)**.

What the payload does at runtime: it is the **SMC (System Management Controller) firmware** — `AppleSMCFirmware_H13-7372.2.11.ipad13b.REL` on `RTKit_release-3514.0.15.release`, managing charger/BMS/thermal/PMU/SPMI — embedded compressed and decoded by the in-image engine into image-relative `≈0x1f64a0` (SMC-VA `0x1FC1F64A0`). The decompress call chain is resolved and **proven end-to-end offline** (see "decompress-call chain" above): wrapper `0x144a0c` (selector 0, type word `0x9c40`) → container `0x145e44` (per-block dispatch `0x145ef8`, header parse `0x146414`, VLC table parse `0x1471d8`, decode loops `0x14685c`, copy helpers `0x144330`/`0x144630`); under emulation this chain reproduces the decoded SMC image byte-exactly (SHA-256 prefix `7da684741cedf068`). What remains open is the runtime entry channel into `0x144a0c` (static search is empty — pointers into this subsystem are re-signed, see the `0x192078` callback-record instance), the mailbox semantics of the shared `0x1FC1A5BB8` base in the descriptor groups, and the `0x891` message-type / bitstream-word selection semantics.

## measured image layout (decode-density)

`tools/boot-image-disasm.py` now emits a 16 KiB decode-density map (share of words decoding to non-`udf` instructions). Measured on the 24A446 image:

- **code** (≥90% density) `0x0..0x14b000` — the main module collection; the LZFSE-family engine and its twin per-byte dispatch tables both live here (`0x140xxxxxxxx`-adjacent region and `0x144xxx..0x146xxx`).
- **mixed/partial** `0x14b000..0x15b000` decays to mixed (`0x153000..`), then **data** `0x15b000..0x197000` (near 0% density) — the pointer-table/pool region hosting the `0x1fc…`-tagged pointer blocks, the dispatch tables (`0x1945a8`/`0x194da8`), and pool constants into image code offsets (tagged pointers seen: `0x8010_0000_0015_7f6c`, `0x80c0_0000_0013_16d8`).
- **string table** `0x197000..0x19e000` (28 KiB dense printable, incl. `iBoot`/`iBEC`/`IMG4`/`IM4P` text and the build strings).
- **data blobs** `0x19e000..0x20f000` (sparse decode residue only), partial `0x20f000..0x213000` (26%), sparse remainder to `0x226000`, and a 2 KiB printable tail `0x226000..0x2269d8`.
- **Density caveat (bl-proved)**: the density map is a linear-decode measurement, not ground truth for the back half — direct `bl` instructions at `0x21d3c`, `0x21fa0`, `0x22074`, `0x223bc`, `0x22400`, `0x228b0`, `0x229d0` call into band helpers (`0x147348`, `0x1473f0`, `0x151d88`, `0x157xxx`), proving real code lives inside sparse windows there.
- **Cross-band call topology**: 184 `bl` edges cross the `0x13c000` boundary — callers in low code (`0x66d0`, `0x7848`, `0x1a328..0x1a814` — tight stride patterns like `0x1557c4/0x1557d0/0x1557d8` consecutive) and in the back half all reach a service-hub band around `0x153000..0x157c00`; conversely the LZFSE-family engine band (`0x144xxx..0x147xxx`) is reachable only through ~4 helper entries (`0x147348`/`0x1473f0` ×4 calls each). The image is interwoven zones, not a strictly sequential code-then-data layout.
- No second mach-o/sub-image header found (no `feedfac*`/`fat` magic anywhere).

Note: the fourcc tag-builder clusters previously described (IMG4 vocabulary at `0x22508..0x22654`, `bvxN` at `0x144xxx`) sit **inside the code region** — verified by instruction-level disassembly at each site (`cmp`/`movk`/`b` sequences, not data tables).

## fourcc-style word tags (movz+movk scan)

New pass in `tools/boot-image-disasm.py` (`fourcc_tags`): scans aligned words for `movz w?, #imm16` + `movk w?, #imm16, lsl #16` pairs on the same register, keeps pairs whose 32-bit concatenation is printable ASCII (0x20–0x7E) in little-endian memory order. Encoding-based matching on raw instruction words (`movz` hw=0 = `0x52800000` mask, `movk` hw=1 = `0x72A00000` mask, same Rd in bits 0–4) — capstone 5 renders `movz` as `mov`, so mnemonic matching is not reliable. Data-as-code regions decode spuriously; tags are candidates. Covered by a unit test with hand-encoded fixtures (`movz w0, #0x6f73` = `0x528DEE60`; `movk w0, #0x4431, lsl #16` = `0x72A88620`; tag `"so1D"`; a non-printable pair excluded).

Result on the 24A446 image: **414 distinct tags over 771 build sites**. Two readable structures:

- **IMG4/IM4P vocabulary cluster at `0x22508..0x22654`**: tightly packed sites (4–6 occurrences each) building constants whose little-endian renderings byte-reverse to canonical image4 manifest tags — `M4MI`→IM4M, `DICE`→ECID, `TSGD`→DGST, `DROB`→BORD, `PIHC`→CHIP, `MODS`→SDOM, `CESC`→CSEC. This pins an image4 manifest builder/parser cluster inside iBoot — a first-hand anchor for the boot-object machinery (`iboot-data`/`boot-object-manifests` strings live 10 pages away, page 0x19c).
- **`bvxN`/`avxN` codec-tag family co-located with the twin dispatch kernels**: `bvx1` (+0x144bcc), `bvx-` (+0x144e74), `bvx2` (+0x144eb8), `bvxn` (+0x144ec8), `avx1` (+0x145ecc), `avx2` — all in the same 0x144000–0x146000 neighborhood as the twin 11-kernel clusters (table A `0x140ca0..0x140f60`, table B `0x145adc..0x145c1c`). Site context is genuine code: the built words are **compared against values loaded from structures** (`cmp w8, w9` right after the build at +0x144eb8) and stored — a tag/variant-driven switch inside the same neighborhood as the byte-class dispatch tables. Whether these fourcc-tag comparisons and the byte-class tables belong to the same subsystem is **not confirmed** — proximity only.
- **Reversed-readable tags elsewhere**: `lnrk`→krnl (+0xdbc), `ogol`→logo (+0x4628), `tsni`→inst (+0xf64b0), and direct-order `root` (+0x72dfc) — both tag conventions (byte-reversed canonical vs memory-order) co-exist in the image, matching the observed `DICE`/`bvx1` split.
