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
- Table B: 256 contiguous qword entries at `0x194da8`–`0x1955a8` directly adjacent; indices 0–254 are `{low32, 0x801023ca}` and index 255 (byte `0xff`) is the single re-signed record `{0x145b18, 0x807023ca}` — same kernel, different tag. The 256 lows resolve to 11 distinct code offsets `0x145adc..0x145c1c`.
- **Byte→kernel partition measured (2026-10-24 round)**: both tables map onto an *identical* 11-handler partition. Table A: 120 ordinary bytes (≡0–5 mod 8 and the rest of the residual class) → `0x140ca0`; the 32-byte block `0xa0–0xbf` → `0x140cd4`; bytes ≡7 mod 8 (7, 15, …, 159) → `0x140d08`; `0xf1–0xff` → `0x140dec`; `0xf0` → `0x140e10`; `0xe1–0xef` → `0x140e38`; `0xe0` → `0x140e50`; bytes 14/22 → `0x140f04`; the ≡6 mod 8 bytes split range-dependently between `0x140f2c` (30–62 plus an extended set) and `0x140f34` (70–110, 134–158, 198–206); byte 6 alone → `0x140f60`. Table B repeats the same partition with kernels `0x145adc..0x145c1c` and its own PAC context. Explicit single-byte tokens at `0xe0`/`0xf0`, a 32-byte block above `0xa0`, and the ≡6/≡7 mod 8 sub-classes are consistent with a literal-run/match control-byte taxonomy of an LZ-family decoder; bit-exact public-format equivalence is not claimed.
- Verify: bytes at the resolved targets decode as clean AArch64 bit-manipulation kernels (`lsr X, X, #6` / `add` / `cmp` / `b.hi` / `ubfx`) — the low32 halves are genuine image-relative code offsets, not coincidence.
- Interpretation (updated): the two 256-entry tables are byte-indexed dispatch into 11 handlers each (partition above; exact kernel semantics resolved 2026-10-26 in the dedicated section). *Correcting the earlier "no absolute pointers in the pool" reading*: the pool's `hi32=1` qwords (16,470) **are** absolute pointers — base **`0x1FC000000`** — but they target only the SMC-domain RAM (image-relative `[0x1a5b50..0x28a640]`), never iBoot's own code/data; "load-base independent" remains true for iBoot-internal addressing (see the address-space section below).

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

- **Driver A** (decoder entry `0x140b54..0x140c9c`; `0x140b44` is a separate 2-instruction predicate returning `1` iff `w0 ∈ {0x30000, 0x30001}`): forms table A base with `adrp x11, #0x194000; add x11, x11, #0x5a8`; maintains ring/window state at context offsets `+0x30/+0x38/+0x40/+0x48`; per-byte flow is `ldrb w16, [x12]` → `ldr x14, [x11, w16, lsl #3]` (full qword incl. cookie) → `mov x17, #0xb803` → **`braa x14, x17`** — an authenticated indirect branch (ARMv8.3 PAC, A-key) to the kernel. The block also contains LZ-style window copying: neg/offset pointer back-references, a bulk 8-byte copy loop plus `ldrb/strb` tail lanes, bounds `cmp x8/` and `cmp x10, #8`; returns codes `-1`/`-2`/`-3` (common stubs `0x140b74` returns `#-1`, `+0x140c94` sets `#-2`, `0x140f2c` sets `#-3`). Kernels `b` to the `-1` stub — earlier "kernels call a common helper" wording resolved: `0x140b74` is an error-return stub, not a shared decode helper.
- **Driver B** (`0x145a70..`, `pacibsp`-prologued real function): `adrp x25 + add #0xda8` → table B base; `ldrb w8, [x23]` (stream pointer carrying a length-prefixed chunk, bounds-checked against `[x0,#0x10]`) → `ldr x9, [x25, w8, lsl #3]` → `mov x17, #0x23ca` → `braa x9, x17`. First kernel at `0x145adc`: `lsr w21, w8, #6` = literal count (0..3); `add w9, w21, #2` = token+literal span check; `ubfx w9, w8, #3, #3; add w22, w9, #3` = match length 3..10; `ldrb w20, [x23, #1]; bfi w20, w8, #8, #3` = 11-bit distance.
- **Cookie semantics resolved structurally**: cookie `= (0x8010 << 16) | modifier`, with modifier `0xb803` (table A) / `0x23ca` (table B) matching each driver's `braa` modifier register exactly. The `braa` consumes the loaded qword (installing the top bits as the signed pointer) with x17 as the modifier — the high-32 is the per-table constant tag/code carried by the authenticated pointer. Key-material semantics (which PAC key/salt produces-consumes it at runtime) are not derivable statically; the image itself is compiled with `pacibsp` prologues throughout, confirming unconditional ARMv8.3 pointer-authentication in this iBoot build.
- **LZFSE-family engine context confirmed**: the twin-table neighborhood is a compression engine. Exact word scans find the full public LZFSE block-magic vocabulary as register-built constants: `bvx$` (end-of-stream) ×2 (`0x145a28`, `0x147314`), `bvx-` (uncompressed block) ×6, `bvxn` ×4, `bvx1` (compressed v1) ×7, `bvx2` (compressed v2) ×5; the public `bvxl` variant is absent, and non-public `avx1`/`avx2` constants (`movz #0x7661` builds) are present nearby. The table-B driver sits 0xe0 bytes after a `bvx$` compare feeding the same block-type dispatch.

### per-byte kernel tables: LZVN-family token grammar (resolved 2026-10-26)

The twin tables are now fully decoded (static, kernel-by-kernel). Both are 256-entry arrays of pre-signed pointer records `{tag|cookie, image-offset}`. The grammar below is the measured one; it matches the LZVN family (EOS `0x06`, reserved ranges `0x70-0x7f`/`0xd0-0xdf`), but bit-exact equivalence with the public lzfse/LZVN source is not asserted.

- **Table A** `0x1945a8`, record tag `0x8010b803` (driver `braa` modifier `0xb803`) → 11 kernels at `0x140ca0..0x140f60`.
- **Table B** `0x194da8`, record tag `0x801023ca` (modifier `0x23ca`) → the same 11 class kernels at `0x145adc..0x145c1c`. Byte `0xff` is the only entry with a different tag (`0x807023ca`) but resolves to the same kernel `0x145b18` — a deliberate per-entry re-sign, not a different action.

The byte-class partition is **identical** in both tables (11 classes, exact index sets):

| bytes | kernel A / B | token semantics |
|---|---|---|
| `00-05 08-0d 10-15 18-1d 20-25 28-2d 30-35 38-3d 40-45 48-4d 50-55 58-5d 60-65 68-6d 80-85 88-8d 90-95 98-9d c0-c5 c8-cd` (120) | `0x140ca0` / `0x145adc` | 2-byte token; L=`b>>6` (0..3); M=`((b>>3)&7)+3` (3..10); D=`next_u8 | ((b&7)<<8)` (11-bit) |
| `a0-bf` (32) | `0x140cd4` / `0x145b7c` | 3-byte token; L=`(b>>3)&3` (0..3); M=`3+(((b&7)<<2)|(u16&3))` (3..34); D=`u16>>2` (14-bit) |
| `07 0f 17 1f 27 2f 37 3f 47 4f 57 5f 67 6f 87 8f 97 9f c7 cf` (20) | `0x140d08` / `0x145b24` | 3-byte token; L=`b>>6`; M=`((b>>3)&7)+3`; D=`u16` (16-bit) |
| `46 4e 56 5e 66 6e 86 8e 96 9e c6 ce` (12) | `0x140f34` / `0x145ba8` | 1-byte token; L=`b>>6`; M=`((b>>3)&7)+3`; D=inherited (previous distance) |
| `e0` (1) | `0x140e50` / `0x145b44` | 2-byte token; literal run L=`next_u8+0x10` (16..271); no match |
| `e1-ef` (15) | `0x140e38` / `0x145b6c` | 1-byte token; literal run L=`b&0xf` (1..15); no match |
| `f0` (1) | `0x140e10` / `0x145b00` | 2-byte token; match M=`next_u8+0x10` (16..271); D=inherited |
| `f1-ff` (15) | `0x140dec` / `0x145b18` | 1-byte token; match M=`b&0xf` (1..15); D=inherited |
| `06` (1) | `0x140f60` / `0x145c1c` | end-of-stream: requires ≥8 bytes; A consumes 8 and sets `[ctx+0x50]=1`; B advances the caller's input cursor by `0xc+payload` |
| `0e 16` (2) | `0x140f04` / `0x145bc0` | no-op (A skips the byte and re-dispatches; B emits nothing) |
| `1e 26 2e 36 3e 70-7f d0-df` (37) | `0x140f2c` / `0x145bfc` | invalid opcode: A returns −3; B returns −1 |

Kernel mechanics (from the disassembly of both clusters):

- Every kernel derives `{L, M, D, token}` from the opcode bits and operand bytes, then runs the shared tail: copy `L` literal bytes from the input to the output, copy `M` bytes from the **output at distance `D`** (overlap-capable), advance both pointers, and re-dispatch through the table. Driver A saves the live distance into `ctx+0x48` at kernel entry; Driver B keeps it in `w20`.
- Distance validation is against the bytes already produced: Driver A compares `D−1` with `out_cursor − out_window_base` and returns **−3** on underflow (`sub x16, x10, #1; cmp x16, x9; b.hs`); Driver B's match helper returns **−1** if the source falls outside the packed window. This is the origin of the −3 seen when the output buffer overlapped the frequency tables in emulation.
- **Driver A** (`0x140b54`, raw token stream) context: `+0x00` in-cur, `+0x08` in-end, `+0x10` out-cur, `+0x18` out-window base, `+0x20` out-end, `+0x30`/`+0x38` pending literal/match counts (resume), `+0x40` pending distance, `+0x48` live distance, `+0x50` EOS flag. Literal copies use 4-byte moves in the common tail and 8-byte chunks in the literal-run path; the match fast path is 8-byte `ldp/stp` when `D ≥ 8` and space allows (guarded by an `M+7` padding check), with byte loops otherwise. Returns `0` on EOS, **−1** on insufficient input / short EOS / exhausted stream, **−2** when output space runs out (saves resumable pending state), **−3** on invalid opcode or distance underflow.
- **Driver B** (`0x145a70`, block decoder) parses a **12-byte sub-block header** (magic at `+0`, payload length at `+8`) and runs the same token grammar over the `payload` bytes starting at `+0xc`, writing through a **4-byte word packer** (`0x145c3c` + leaf `0x145d30`): one byte per call is placed in byte lane `count` of a 32-bit accumulator (accumulator/count at `helper_ctx+0x18`/`+0x1c`; output cursor `+0x10`, limit `+0x08`, with `helper_ctx = ctx+0x18`), flushed word-by-word through the cursor. Match copies (`0x145d80`) feed the same packer and read source bytes back out of the packed window byte-exactly (logical position = flushed cursor + pending count − distance). On EOS it advances the caller's context input pointer past `0xc+payload` and returns `0`; every error returns **−1**.
- **Dispatch integration**: the block-magic dispatcher `0x144d5c` routes `bvx-` → `0x1454a4`, `bvx1` → the shared `0x144eec` setup (copies a 0x304-byte header), `bvx2` → the entropy-table init (`0x144f08`/`0x144f4c`, `bl 0x144ba0`), `bvxn` → `bl 0x145a70` (Driver B), and `bvx$` (plus the ≤`avx2` default) → `0x145a28` (end zone); unknown magics above `avx2` return 0. Driver A's decoder is called from the container at `0x14673c` (an arm the SMC stream does not take). Message types `0x900/0x901` route to `0x140fc0` — a **third, distinct fast LZ decoder** that uses a compiler-generated 256-entry **relative** halfword jump table at `0x141300` and a plain `br` (not a PAC `braa`).
- **Status**: these per-byte table semantics are static only. The selector-0 control run records 0 hits at `0x140b54`, `0x145a70`, `0x145c3c` and `0x145d30`. The `0x8a1` descriptor run does execute `0x145d80` (39,597 calls) but not the container, VM mapper, driver-B entry or packer; `0x145d80` is a **shared match-copy helper**, not exclusive to driver B. The table-A/B kernels remain statically characterized but not exercised by either measured SMC arm.

Correction to the earlier label above: `0x145c3c`/`0x145d30` are a **byte packer**, not an entropy bit-buffer (one byte per step, shifted by `count*8`; a 32-bit word flushes every 4 bytes).

### decompress-call chain (resolved 2026-10-24 round)

A bl/pacibsp callgraph pass (`tools/boot-image-calls.py`; code region `<0x14b000`: 48,624 `bl` edges, 4,190 `pacibsp` prologues, `blr` ×0 — indirect flow is authenticated: `blraaz` ×319, `blraa` ×11, computed targets pre-signed with `paciza` ×566, `braa` ×5, `braaz` ×65, `br` ×213) resolved the static chain into the engine:

- **`0x144a0c` (0x194 B) = the decode-call wrapper (top of the resolved chain).** Six caller args; message-type select `cmp w5, #0x891`; zero-fills the context region (`mov x0, x4; bl 0xd29c0`, length `0x5768`/`0xb910` by type); builds a **PAC-signed context**: `pacda` with per-field movk key constants (`0xb5f0`, `0x0b90`, `0x874b`, `0x9a95`, `0xfa25`, `0x3094`, each folded with the context base) stores `{ptr, ptr+len}` range pairs — args `x2`/`x3` into fields `+0x0..+0x10`, args `x0`/`x1` into `+0x18..+0x28` — writes the type word `0x3a98`/`0x9c40` at `+0x1c88`, then `bl 0x145e44(x0 = context)` (site `0x144b48`) and returns an authenticated-pointer delta (`autda` + `xpacd` sanity check + `sub x20, x16, x19` = bytes consumed/written). **It carries no direct `bl` caller** and no 4-byte literal or tagged pool record references it; the only static edge into it is the tail branch from the message-type execute dispatcher (`b 0x144a0c` at `0x147484`, types `0x801`/`0x802`/`0x891` — see the dispatch-pair section below). The earlier "zero static references" wording is corrected: the entry channel is the dispatcher, not a re-signed call.
- **`0x145e44` (0x16c0 B) = the container/decode driver.** Reads global `0x23e5f0` (`0x145e70`), zero-fills twelve buffers (`bl 0xd27f0` ×12), calls helper `0x144330` (`0x1461b8`), helper `0x144630` (`0x14709c`), engine A's window-copy/`−1` landing `0x140b54` (`0x14673c`; inside the driver-A zone `[0x140b44..0x140fc0)`, not a stub), calls the VM mapper `0x30444` (`0x147344`), and tail-branches `b 0x144d5c` (site `0x1474d0`) on one exit path. Sole `bl` caller: `0x144a0c`. **Measured (emulation, see below): the selector-0 control run decodes the all-`bvx2` SMC stream inside this container — per-block dispatch `0x145ef8`, header parse `0x146414`, VLC table parse `0x1471d8`, decode loops `0x14685c` — without executing `0x144d5c`, `0x145a70`, `0x145c3c` or `0x30444`. The descriptor-supported `0x8a1` arm takes the other, non-container route through `0x144d5c`; that sub-chain is therefore not unused by the SMC stream, only unused by the selector-0 control.**
- **`0x144d5c` (0xd14 B) = the raw block decoder.** movz/movk-built magic compares: `0x3178_7662` = "bvx1", `0x3278_7662` = "bvx2", `0x6e78_7662` = "bvxn"; unhandled magic → `b.ne 0x145a28` (the `bvx$` zone). For the `bvxn` route the decompress call is measured at **site `0x144edc`: `add x0, sp, #0x40; bl 0x145a70`** — driver B, per block, context in `x0`. Other calls: `0x144ba0` (`0x144f40`), bit-packer `0x145c3c` (`0x1454cc`), shared match-copy `0x145d80` (`0x1459d8`), and — as the function's very last word — `bl 0x30444` (`0x145a6c`) whose return address is exactly driver B's entry: **return-address chaining** into the next stage. The SMC stream takes the `bvx2` header/histogram path and reaches `0x145d80` directly; it does not take the `bvxn`/driver-B or VM-mapper routes (measured under the `0x8a1` run).
- **Engine A** (fn `0x1408bc`, 0x288 B, + the window-copy driver zone `[0x140b44..0x140fc0)` with no own prologue — `0x1408bc` falls through into it): static caller chain `0xf5e94 →(bl) 0xf8cac →(bl) {0x13fea4, 0x14022c} →(bl) 0x1408bc` (sites `0x14034c`, `0x13ffa0`). Harnesses: `0x13fea4` (0x144 B) additionally calls the `w0 == 0x300002` predicate `0x140b44` twice (`0x13fed0`, `0x13ff64`); `0x14022c` (0x1f0 B) gates on `[x0,#0x20]`/`[x0,#0x28]`. Driver A's per-byte dispatch is measured directly at all four of its `braa` sites (`0x140bd0`, `0x140c24`, `0x140f00`, `0x140f28`): `ldrb w16, [x12]; ldr x14, [x11, x16, lsl #3]; mov x17, #0xb803; braa x14, x17`, table A base formed inline (`adrp x11, #0x194000; add x11, #0x5a8` = `0x1945a8`) — the cookie/table relations confirmed structurally; error codes −1 (`0x140b74` family), −2 (`0x140c94`), −3 (`0x140f2c`); kernel `0x140f60` = end-of-stream (consumes 8 bytes, sets flag at `+0x50`, returns 0). Driver B's single `braa` sits at `0x145ad8`, matching the earlier identification.
- **`0x145c3c` + leaf `0x145d30` = 4-byte word packer (not an entropy coder):** one byte per call is inserted at byte lane `count` of a 32-bit accumulator (accumulator/count at `helper_ctx+0x18`/`+0x1c`, output cursor `+0x10`, limit `+0x08`, with `helper_ctx = ctx+0x18`); a word is flushed every 4 bytes. Called as `bl 0x145c3c(x0 = ctx+0x18, x1 = count, x2 = byte pointer)`; the match copier `0x145d80` reads source bytes back through the packed window.
- **`0x30444` = the ARM64 VM mapper — closes the beyond-file decode destination:** a three-level page-table walk (`ubfx` index bitfields, table descriptors `orr x7, #0x8000000000000003`, 4-KB granule stepping), allocator-cursor global `0x23e580`, TTBR roots at `0x215700`/`0x215708`, KASLR-slide-relative self-relocation (`... - x12`, `msr ttbr0_el1`/`ttbr1_el1`/`vbar_el1`, then `br x1` into the relocated continuation). The decode chain maps fresh pages into its output region as it advances — the mechanism behind the decoded SMC image living beyond the delivered file.

**End-to-end offline proof (2026-10-25): the selector-0 `0x144a0c` control arm decodes the real SMC stream byte-exactly.** The chain was executed under Unicorn ARM64 emulation on the actual unified image — PAC neutralized in the mapped copy only (`retab`/`retaa` → `ret`; `autibsp`/`paciza`/`pacda`/`autda`/`xpacd` → NOP; `braa`/`blraa` → NOP with scoped hooks resolving the register's `{tag|low32}` record to `BASE+low32` and setting LR for calls; VM mapper `0x30444` skipped at entry, with page mapping for the output pre-arranged). Entry `0x144a0c`, `x0` = output buffer, `x1` = 1 MB, `x2` = stream VA (`0x1a3768`), `x3` = `0x39d23`, `x4` = zeroed context, `x5` = 0. Result: **`0x79760` B written, SHA-256 prefix `7da684741cedf068` — byte-identical to the liblzfse reference output** — with measured counts: container entry ×1, block headers ×5, frequency-table parses ×5, symbol decodes 1800 (= 5×360), decode-loop entries ×5, copy helpers `0x144330`/`0x144630` ×5 each, error paths ×0. This was a control entry, not the descriptor's runtime selector; the descriptor-supported `0x8a1` arm is documented in the next section.

Facts confirmed by the run:

- Argument orientation: `x0`/`x1` = output `{ptr, len}`, `x2`/`x3` = input stream `{ptr, len}`, `x4` = context, `x5` = type selector; the wrapper returns the authenticated delta on success and `0` when the container reports a nonzero error.
- Context fields: `+0x0..+0x10` = input `{start, end}` (copy of `x2`, `x2+x3`), `+0x18..+0x28` = output `{start ×2, end}`, `+0x1c88` = type word (`0x9c40` unless `x5 == 0x891`, then `0x3a98`) with zero-fill length `0xb910`/`0x5768` respectively; helper `0x144630` receives `x2 = type−0x10` (`0x9c30` in selector 0).
- The in-image decoder re-reads its in-file frequency tables **before every block**: `0x207d88` = 32-byte type table (`02 03 02 05 02 03 02 08 02 03 02 05 02 03 02 0e` ×2; each byte = bits consumed), `0x207da8` = 32-byte signed table (`0 2 1 4 0 3 1 −1 0 2 1 5 0 3 1 −1 0 2 1 6 0 3 1 −1 0 2 1 7 0 3 1 −1`). Consequence for any emulation/decoder harness: the output buffer must not overlap the image (an overlap initially overwrote these tables mid-decode and produced a false `−3`).
- Per block, a VLC bitstream at `magic+0x20` yields **360 16-bit entries**: 5-bit index → type byte = bits consumed (`0xe` → +10 bits, value `+0x18`; `0x8` → +4 bits, value `+8`; otherwise the signed-table value); the table region ends at `magic+0xc9` (block 0) / `magic+0xcb` (blocks 1–2 measured); the block ends valid when residual bits ≥ 7 or the cursor exactly reaches the limit. An independent pure-Python simulation of this algorithm parses all five blocks cleanly — algorithm and data are consistent.

**Which arm drives the SMC-stream decode.** The earlier control experiment ran the `0x144a0c` wrapper with selector 0 (type word `0x9c40`) and reproduced the SMC image exactly; that is a valid emulation of the default LZFSE arm. The descriptor found since then carries `0x8a1`, and the `0x8a1` execute arm (`0x144d5c`, block-level decoder) also reproduces the image byte-exactly. The runtime descriptor is therefore best supported as the `0x8a1` arm, with the selector-0 wrapper/container path retained as an independent control. The `0x891` variant (`0x3a98`, zero-fill `0x5768`) is not this stream's mode.

**Message-type dispatch pair (`0x147348` size / `0x1473f0` execute) — the entry channel.** Two leaf thunks (no prologue, tail branches) normalize the type and route it. `0x147348` reads the type in `w0` and returns the required context size; `0x1473f0` reads it in `w5` and executes. Normalization folds `0x200-0x209`→`0x205`, `0x500-0x509`→`0x505`, `0xd00-0xdff`→`0xd05` (the `w5` thunk additionally folds `0xa00-0xaff`→`0xa18`, `0xb00-0xb0a`→`0xb02`). Full mapping:

| type | size query (`0x147348` →) | execute (`0x1473f0` →) |
|---|---|---|
| `0x100` | — (returns 0) | `0x1415c4` |
| `0x101` | — (returns 0) | `0x144958` |
| `0x205` | `0x1425c4` = `0x20000` | `0x1425cc` with `w5 := 0` |
| `0x505` | `0x1425c4` = `0x20000` | `0x1425cc` with `w5 := 1` |
| `0x700-0x702` | `0x144620` = `mov w0,#0x2080` | `0x1445ec` (32-bit-length guard → `0x141d04`) |
| `0x801`, `0x802` | `0x1449f8` = `0xb910` | **`0x144a0c`** (decode wrapper, default layout) |
| `0x891` | `0x1449f8` = `0x5768` | **`0x144a0c`** (decode wrapper, alternate layout) |
| `0x8a1` | `0x144d54` = `mov w0,#0x1f08` | `0x144d5c` (raw block decoder; block-magic dispatch plus its own decode loops) |
| `0x900`, `0x901` | `0x141500` = `mov x0,#0` | `0x140fc0` (fast LZ decoder) |

Each thunk has exactly four static `bl` callers — the protocol loaders `0x20e0c`, `0xb58c0`, `0xddb10`, `0xea600` (size-query sites `0x21d3c`, `0xb5964`, `0xdde90`, `0xea728`; execute sites `0x21fa0`, `0xb5a10`, `0xdded4`, `0xea768`). All four follow the same pattern: `size = query(type)` → allocate → `execute(type)` with `x0`/`x1` = output `{ptr,len}`, `x2`/`x3` = input `{ptr,len}`, `x4` = allocated context, `x5` = type; success is checked as “returned delta == requested output length” (`cmp x0, x21` at `0x21fa4`). Two loaders hard-code type `0x891` (`0x20e0c` sites `0x21d38`/`0x21f9c`; `0xddb10` sites `0x0dde8c`/`0x0dded0`); two take the pair from a caller descriptor — `ldr w0,[x23,#0x24]` / `ldp w3,w5,[x23,#0x20]` (type at `+0x24`, length at `+0x20`) in `0xb58c0` and `0xea600`. **This resolves the runtime entry channel: loader → `bl 0x1473f0` → tail branch `0x144a0c` with `x5` = type; no direct `bl` targets the wrapper.**

**Compression-ID vocabulary correction (2026-10-26).** The type words are Apple compression selectors, not SMC-specific opcodes. The public Apple-compression mapping used by `blacktop/ipsw` and `m1stadev/apple-compress` gives `0x100` LZ4, `0x101` LZ4_RAW, `0x205` ZLIB, `0x306` LZMA, `0x702` LZBITMAP, `0x801` LZFSE, `0x891` LZFSE_IBOOT, `0xb02` BROTLI, `0xd05` LZRAVEN and `0xe05` LZMESH. In this image `0x801`, `0x802` and `0x891` share the `0x144a0c` route; `0x802`'s public name is not established. The earlier "SMC-specific `0x801`/`0x802` opcode" wording is withdrawn. `0x8a1` is not in that public list; it is an Apple selector used by this build for the block-level raw LZFSE stream and is referred to here as the `0x8a1` block mode, not as LZFSE_IBOOT.

**`0x891` is a message mode, not the SMC descriptor type (measured).** Both the wrapper and the size helper branch on `w5 == 0x891` (`0x5768`/`0x3a98` vs `0xb910`/`0x9c40`), and `0x20e0c`/`0xddb10` use `0x891` for their descriptor-driven loads. Running the emulated chain with selector `0x891` on the real SMC stream, however, only parses block 0's header and its 360 VLC symbols and exits without a single copy-helper call (0 hits at `0x144330`/`0x144630`; output digest `68d521d3fec67388` ≠ `7da684741cedf068`; wrapper returns 0). The SMC stream is not `0x891`. The boot-object descriptor at `0x215ed8` carries `0x8a1`; its execute arm `0x144d5c` decodes the real stream byte-exactly (next section). The selector-0 wrapper/container run remains a valid byte-exact **emulation** of the default LZFSE arm, but selector 0 was an artificial entry argument, not evidence that the runtime descriptor uses `0x801`/`0x802`.

**Top-of-chain entries.** The pool's `{0x80XX0000 | low}` records are now structurally explained: the wrapper itself re-signs its pointers with `pacda` + per-field movk key constants — the same `{modifier | address}` shape as the pool records — and the runtime indirect-call machinery (`blraaz`/`braa`/`br` on targets pre-signed as `{tag|address}` records, `paciza`-signed) consumes them. One concrete instance: **`pool[0x192078] = {0x80200000 | 0xf5e94}`** — the entry record of the `0xf5e94` arm, in an alternating pattern with SMC-domain pointers (`{1|0xfc1a5bb8} ↔ {0x8020|0xf56e4}`, `{1|0xfc1dd7b8} ↔ {0x8020|0xf5e94}`, `{1|0xfc1dd7e0} ↔ {0x8020|0xf7078}`, `{1|0xfc1dc130} ↔ {0x80a0|0xf71fc}`, …) — **per-SMC-object handler wiring between iBoot and the SMC domain**, not ordinary callgraph material. The wrapper's own entry is static: `0x1473f0` tail-branches to it (`0x147484`), and that dispatcher is called by the four protocol loaders (see the dispatch-pair section above).

Remaining opens, narrowed: the purpose of the `0x891` message mode (its container path parses block-0 tables but performs no copies); the public name of the `0x8a1` block mode; runtime reachability of the `0x37440` early-flow block and the staging step that makes the descriptor's `+0x00` SMC pointer contain the compressed stream; and the runtime meaning of the `0x205/0x505/0x700-0x702/0x100/0x101` protocol types (their engines are located; the payloads they carry are not yet identified).

## protocol loaders → boot subsystems (resolved 2026-10-26 round)

Each of the four dispatch-pair loaders was traced through its static callers and the string anchors inside its caller cluster (callgraph via the committed `tools/boot-image-calls.py`; strings resolved from ADRP+ADD sites per function):

| loader | type source | static caller chain | subsystem evidence |
|---|---|---|---|
| `0x20e0c` | hard-coded `0x891` (`0x21d38`/`0x21f9c`) | `0x81ca0` (one `bl` site `0x81ef8`) → L2 `0x81f18`/`0x82424`/`0x8296c`/`0x82be8` → L3/L4 `0x272bc`, `0x34a68`, `0xcab6c`, `0xdb68c`, `0xef044`, `0x121bb8` and the early boot flow | boot-file / IMG4 object cluster: the loader itself references `image4_callbacks.validity_cb is NULL` (`0x21fc4`); `0x81b40` carries `image-version`/`te_ca`, `0x82f58` carries `boot-breadcrumbs`; the upper chain contains `/boot`, `/boot/iBEC`, `boot-command`, `recovery-boot-mode`, `mount upgrade partition` |
| `0xb58c0` | descriptor `[+0x24]` (`0xb5960`) | `0xb5c28` (site `0xb5d40`) ← `0x37440` ← `0x37188` ← `0x3724` | early boot flow; single caller at every level |
| `0xddb10` | hard-coded `0x891` (`0xdde8c`/`0xdded0`) | `0xdcc84` (site `0xdce34`); no static callers | **"VMiBoot "/"LZFSE   " boot-object decoder**: both 8-byte names are referenced inside the loader (`0xddcf4`, `0xdde28`); `0xdcc84` walks 16-byte table entries (8-byte name / 8-byte format-or-size) and matches the name/format pair before calling the loader |
| `0xea600` | descriptor `[+0x24]` (`0xea724`/`0xea758`) | `0xe68c0` (site `0xe69a8`) and `0x125b6c` (site `0x125c58`) | list-driven: `0xe68c0` iterates objects (flag `+0x21a`, u16 `+0x260`, fields `+0x40`/`+0x50`/`+0x60`) and calls the loader per entry; the chain reaches the shared node `0xb5c28` and the early flow `0x3724` |

The loader→dispatcher mechanics are shared: `size = 0x147348(type)` → allocate via `0x13822c`/`0x1381d8` → `0x1473f0({out,out_len},{in,in_len},ctx,type)`. Return checks differ: `0x20e0c` requires equality with the requested output length (`0x21fa4`), while `0xb58c0` only requires a non-zero, 4-byte-aligned return (`0xb5a14..0xb5a20`). The two descriptor-driven loaders use `{ptr@+0x00, len@+0x20, type@+0x24}`; `0xddb10` uses an in-object layout `{len@+0x1c, data@+0x20}` and wraps the call with constructor `0xdf0c4` and release `0x1009bc`. `0x20e0c` is multi-mode: its `w23 == 1` arm runs the `0x891` thunk (size `0x5768`), while `w23 == 0` / other arms call `0xd2c84`/`0xd2f64`/`0xd3c04` instead.

**`0xb58c0` descriptor origin (resolved).** `0xb5c28` builds the descriptor at caller `sp+0x48` (`0xb5cb0..0xb5d40`): `+0x00..+0x18` copy the boot-object `[+0x00..+0x18]`, `+0x20` = u32 `[obj+0x48]` (input length), `+0x24` = u32 `[obj+0x54]` (protocol type; this supersedes the earlier “count” label). The payload header is separate: `[base+0x10]` is a size word (`w21` at `0xb5900`, fed to `0x1381d8` and to `0xf0a04`), `[base+0x14]` is a 4-byte word index (`w27` at `0xb5994`), and the compressed input cursor is `base + 0x18 + 4*index` (`0xb5998`). Type `0` (or a failed `0xb5b68` verification) takes the `0xb6984` + `0x125b6c` fallback.

**`0xea600` is the alternate loader, not the normal SMC entry.** Its descriptor has the same `{base@+0x00, len@+0x20, type@+0x24}` layout, but the decode input is `base` itself (`0xea754..0xea768`) — it does not apply the `+0x18 + 4*index` cursor used by `0xb58c0`. Its normal caller `0xe68c0` is gated by `0xe7400` → `0x10f3c0`; in the shipped image `0x10f3c0` is a one-instruction stub (`mov w0,#1; ret`), `0xe7400` maps a non-zero return to 4, and `0xe68c0` skips the object on 4 (`0xe6958..0xe695c`), so every object is skipped on that path. No static qword or `adrp`+`add` reference to `0x10f3c0` was found (runtime patching not observed). The only other caller, `0x125b6c`, is reached from `0xb58c0`'s type-0/verification-failure fallback (`0xb5d48..0xb5d60`) and passes the same descriptor; `0xea600` is therefore a fallback/alternate handler, not the normal `0x8a1` SMC decode entry.

**Consequence for the SMC payload**: among the four loaders, only the descriptor-driven pair (`0xb58c0`, `0xea600`) can pass a type other than `0x891`. The `0xb58c0` chain is the only one with a single static path into the early boot object (`0xb5c28` ← `0x37440` ← `0x37188` ← `0x3724`), and the object at `0x215ed8`, which `0xb5c28` receives, carries type `0x8a1` and length `0x39d30`. This ties the SMC firmware load to the boot-object/descriptor pipeline; the hard-coded `0x891` loaders remain boot-file/VMiBoot paths. The `0xea600` fallback is not used on its normal path (gated off at `0x10f3c0`).

### SMC boot-object descriptor and the `0x8a1` decode arm (static identity resolved, 2026-10-26 round)

The early-flow call chain `0x37440` passes a static data object to `0xb5834` and then, after a successful return, to `0xb5c28`:

- `0x37440` sets `x19 = 0x215ed8`, calls `0x3ba10` (sets `x3 = 0x160950`), sets `x2 = x19 + 0x68 = 0x215f40`, calls `0x3b8a0` (sets `x0 = x1 = x19`), then `bl 0xb5834` (site `0x37618`). `0xb5834` stores this `[0x215ed8, 0x215f40)` range plus `0x160950` at global `0x235b28..0x235b40`, then works on the adjacent descriptor block at `0x235b48` via `0xb6948`/`0x1253ac`.
- After `0xb5834` returns 0, `0x37440` repeats the setup: `bl 0x3ba10` sets `x3 = 0x160950`; `add x2, x19, #0x68` sets `x2 = 0x215f40`; `bl 0x3b8a0` sets `x0 = x1 = 0x215ed8`; then `bl 0xb5c28` (site `0x3762c`).
- `0xb5c28` calls `0xb695c` at `0xb5c48`. That stub is `mov x19,x3; mov x20,x2; mov x21,x1; mov x22,x0; ret`; it therefore sets `x22 = 0x215ed8`, `x21 = 0x215ed8`, `x20 = 0x215f40`, `x19 = 0x160950`. The guard `x21 <= x22 < x20` passes with `x22` exactly at the start of the static object. **The object identity is resolved statically**; what remains is runtime reachability of `0x37440` and the staging of the input pointer at `+0x00`.
- `0xb5c28` copies `[x22+0x00..0x18]` into the caller descriptor, takes `w23 = [x22+0x48]` as the input length and `w24 = [x22+0x54]` as the type, clears/resets secondary fields `+0x28/+0x30/+0x38`, and uses `+0x40/+0x62`. It calls `0xb58c0` (site `0xb5d40`) with descriptor `+0x20 = 0x39d30` and `+0x24 = 0x8a1`; `0xb58c0` passes type `0x8a1` to `0x1473f0`, whose tail branch enters `0x144d5c`.

**Call-site wiring into `0xb58c0` (static; resolved 2026-10-26 round).** With type `w24 ≠ 0`, `0xb5c28` clears/pokes the secondary object fields (`+0x30` zeroed if nonzero, the word at `*+0x28` ANDed with `~3`, `+0x38` zeroed if nonzero), then builds the local descriptor at `sp+0x48` — `+0x00/+0x08` = `0x1FC1EF768`, `+0x10/+0x18` = object `+0x10/+0x18`, `+0x20 = 0x39D30` (length), `+0x24 = 0x8A1` (type) — and calls the container validator `0xb5b68` as `(x0 = 0x1FC1EF768, x1 = 0x1FC1EF768, x2 = 0x1FC229498, x4 = 0x39d30)` (`x3` is unset at this site and keeps the incoming `0x160950`). A failed validator result or `type == 0` branches to the fallback at `0xb5d48`. On success it computes `end = 0x1FC1EF768 + 0x39D30 = 0x1FC229498` — object `+0x10` exactly — and `input = container + 0x18 = 0x1FC1EF780`, pushes the runtime container words read at `0x1FC1EF778/0x1FC1EF77C` (container `+0x10/+0x14`: the `+0x10` word feeds the early prepare call inside `0xb58c0`, the `+0x14` word is the input word-index — 0 in emulation), the interface markers `0x222ad8`/`0x222d40`, and `{input, end}` as stack args, then calls `0xb58c0` with `x0..x3` = the four pointers of global `0x235b48` (the endpoint block filled during `0xb5834` via `0xb6948`/`0x1253ac`), `x4/x5` = the descriptor copy, `x6` = descriptor copy `+0x28`. The two words the loader consumes at `container+0x10/+0x14` come from the **container header**, not from the static object — the object's `+0x10` is the independent end-pointer field above — and this matches `0xb5b68`'s checks (`splt` magic at container `+0x00`, fields at `+0x10/+0x14`, hash via `0xb690c`/`0xc098c`).

Inside `0xb58c0` the picture is symmetric: descriptor type → `0x147348` (per-type object) plus the early prepare pair `0x13822c`/`0x1381d8`; decode input computed as `[descriptor+0x00] + 0x18 + 4·(index word)`, i.e. `0x1FC1EF780` for index 0; decode entry `0x1473f0` called as `(x2 = input, w3 = 0x39D30, w5 = 0x8A1)` with tail branch into `0x144d5c`; a 4-aligned success result is then installed through `0xcf5a0` with seven arguments, several fed from virtual calls dispatched via `0xb6814`/`0x136cf8` on interface object `0x222ad8` (dispatch tables at `+0xa0/+0xb0`) and the `0x235b48` channel pair. Who stages the stream bytes and container-header words into SMC VA space upstream of `0xb5c28` remains open statically.

The object at `0x215ed8` is therefore the descriptor `b5c28` consumes, with this field map:

| offset | value | reading |
|---|---|---|
| `+0x00` | `0x1FC1EF768` | container pointer (runtime SMC VA; the decode input actually consumed starts at `+0x18` = `0x1FC1EF780`, so the container carries an 0x18-byte header followed by the staged stream — see the call-site wiring below) |
| `+0x08` | `0x1FC1EF768` | duplicate input pointer |
| `+0x10` | `0x1FC229498` | **input end pointer**: `+0x00 + length` exactly (`0x1FC1EF768 + 0x39D30`), computed and self-consistent at `0xb5d00` |
| `+0x18` | `0x1FC1A5BB8` | third runtime pointer; forwarded into `0xb58c0` as arg3, not consumed on the traced `0x8a1` path before the decode call (the register gets reused for the decode return) |
| `+0x20` | `0x23FE00000` | tagged pointer (not consumed by `b5c28`); registration adds `+0x50` to it and registers the range via `0xb68c0` from `0xb5834` |
| `+0x28` | `0x23D2B800C` | secondary state pointer; `b5c28` clears the low two flag bits at `*+0x28` |
| `+0x48` | `0x39D30` | input length, 13 bytes more than the exact `bvx$`-bounded stream length `0x39D23` (16-byte padding) |
| `+0x4c` | `0x55000` | secondary size, not consumed by `b5c28` |
| `+0x50` | `0x100000` | 1 MiB span consumed by registration (`0xb5834` at `0xb5860..0xb5874`): `x9 = [x0+0x20] + w9` then `bl 0xb68c0` with marker `0x222b78`; not consumed by `b5c28` |
| `+0x54` | `0x8A1` | compression/protocol type |
| `+0x60` | `0xF6` | u16 scalar read by the `b68c0` metadata builder; `+0x62` is the bit index used by `b5c28` (zero here) |

`0x39D30` is the exact padded length used in the `0x8a1` emulation: output remains `0x79760` B and digest `7da684741cedf068` matches the expected SMC image. The decoder stops at `bvx$` and ignores the 13 trailing bytes.

**Emulation result (local, offline).** Entry `0x144d5c` (not the wrapper), `x0/x1` = 1 MiB output, `x2/x3` = `0x1a3768`/`0x39d30`, `x4` = zeroed `0x1f08` context, `x5` = `0x8a1`. It returns `0x79760` and produces the byte-exact SMC image. Recorded counts: dispatcher entry ×1, `bvx` block-zone helper ×5, shared match-copy helper `0x145d80` ×39,597; **0** container entries (`0x145e44`), **0** VM-mapper calls (`0x30444`), **0** hits at `0x145a70`/`0x145c3c`. This is an emulation result, not device boot evidence. The emulation used the in-file stream bytes; the descriptor's `+0x00` runtime pointer has not been shown to contain those same bytes.

**Interpretation.** `0x144d5c` is a full six-argument raw-block decoder, not just a dispatch tail: it checks the input/output 4-byte alignment (`0x144e00`), zero-fills its own `0x1f08` context (`0x144dd8`), stores `{out, out+len, in, in+len}`, and loops over block magics. It handles the `bvx2` header and histogram path at `0x144eec..`, then decodes via its own loops (`0x145800..`) and the shared `0x145d80` match-copy helper. The `0x144a0c` wrapper/container path is a separate, VM-aware decoder; both reproduce the same output in emulation. Public Apple names for `0x8a1` are not established; it is not `0x891` (LZFSE_IBOOT) and not `0x801` (plain LZFSE).

**Boot-object registry tags**: `0x207c8..0x20b00` allocates linked-list objects (string `linked list item %p corrupted`); its `img4` constructor (`0x20994`) writes `0x696d6734` at object `+0x70` and a size at `+0x74`, with list links `+0x40..+0x60` and ranges at `+0x78`/`+0x88`. `0x8205c` constructs the other type, `0x4d656d7a` ("Memz" when read big-endian), at `+0x08`, with `+0x04` (u32), `+0x0c` (u32) and five pointers at `+0x10..+0x2f`. Consumers: `0x81ca0` admits only the `Memz`/`img4` type word at `+0x08` before entering the boot-file decode path; `0x220a4` dispatches on the same pair.

**Negative result — object-field key setter `0x26d44`.** The routine compares its first argument against 18 keys of the form `0x6b63_<low16>` (memory bytes `<two chars>ck`, big-endian `kc<two chars>`: `fb,zb,pe,ve,fl,xz,zl,fm,zm,fr,zr,fs,zs,uu,fw,zw,fx,ol`; e.g. `0x6b636c6f` renders `olck`), and writes the associated value into object `+0x08..+0xb0` with flags at `+0`/`+1`/`+2` and minima at `+0x10`/`+0x40`. The compare tail `0x2dcac` is an outlined helper: the caller presets the key's low half, the helper runs `movk w9,#0x6b63,lsl#16; cmp w22,w9; ret`, and the caller branches on the returned flags. **No static reference to `0x26d44` exists** — no `bl`, no qword with either half matching, no 32-bit relative entry, no `adrp`+`add` formation — and none of the 18 key byte sequences occurs in iBoot, iBootData, the DeviceTree, LLB, iBSS, iBEC or sep-firmware. The routine is therefore statically unreachable in this build (dead or runtime-registered through a table absent from the image); recorded as a negative, not as a decoded feature. `0xdcc84` (the VMiBoot table walker) shares this property: it too has no `bl`, pointer, relative or formation reference anywhere in the image.

### boot-object-manifest consumer chain (static, resolved 2026-10-26 round)

Static wiring between the manifest property, the record walker and the SMC chain, end to end:

- **DT property reads.** The name `boot-object-manifests` at `0x19c419` is referenced only from `0xd59ec`/`0xd5bb0`, inside a DT-walker function at `0xd5960..`: it reads the property into a local buffer via helper `0xd5d10` (stack args `[buf, buf, buf+0x20, 0x15a998]`), processes the result through `0xc2100`, then performs a second read with the adjacent property name `secure-boot-hashes` at `0x19c42f`. The `0xd5bb0` reference is the second format/log site of the same walker. In the image's name list, `boot-object-manifests` and `secure-boot-hashes` sit adjacent, followed by `nvram-bank-size`/`nvram-bank-count` and other DT names.
- **Early-band region reader.** Sites `0x3a344`/`0x3a364` (inside the large early function `0x37188`'s body) read `smc-shared-region-base`/`smc-shared-region-size` from the DeviceTree: name span passed as `x4` with an end marker derived in `x6`, the values `0x24AE4E000` and `0x2000` pushed at `[sp]`, through the `0x3b70c`/`0x3b750`/`0x3b744`/`0x3b858` constant-stub family into registry portal `0xc2934` (same portal as the `0xc2100` manifest processing above).
- **Record walker `0xbb930` — sole caller `0x37218`**, inside `0x37188`. Incoming four pointers are registered at global `0x235c00..0x235c1f` (same registered-block shape as `0xb5834`'s `0x235b28`). The loop reads a u16 record bitmask at `[x19]`, a u8 record count at `[x19,#2]`, and an s8 tag at `[x19,#5]`; helper `0xbc374` returns a record-slot base and the walker addresses `base + index*0x20` (error on a negative byte tag or index mismatch), caps at `index < 9`, and links 0x20-byte nodes into global `0x235ce0` (`0x235c20 + 0xc0`) with a member function table pointer `0x18f840` at node `+0x18`. The **≤9 record cap matches the nine `{u32 addr, type=2, id, id2}` pre-stream records at `0x1a36d8`** counted one-to-one.
  The earlier idea of a `0x1253ac`/`0x3b5dc` staging line *inside* this walker is corrected: `0x1253ac`'s only bl callers are `0xa1ac`, `0xa1d4`, `0xa230`, `0xbe68`, `0xb0fac`, `0xb589c` — none in `0xbb930..0xbbf40`; the `0x3b5dc` stub family serves `0x37188`'s body (`0x373e4..0x3b378`).
- **Parallel registration site `0xbe68`.** Mirrors `0xb5834`'s `0x1253ac` registration shape but registers a different block (`0x226cd0`, with `x2 = 0x226cf0`) and a different tag package (`x4 = 0x15dc98`, `x3 = 0x15d5a0`, `x7 = 0x15d640`, `x5/x6 = 0x15dc98/0x15dd88`), then continues into `0x12694c` with `w4 = 2`.
- **arg3 table at `0x160950`.** The table handed as `x3` to `0xb5834`/`0xb5c28` is a 0x28-stride record table: each record ends in the fixed shared base pointer `0x1FC1A5BB8` (observed at table `+0x20` and `+0x48`, predicted to repeat; never missing so far), preceded in each record by beyond-file SMC heap/stack pointers (`0x1FC261B3C`, `0x1FC26E7B0`, `0x1FC261B80`), staging-zone pointers (`0x1FC1AC951`/`0x1FC1AC979`/`0x1FC1AC9B1`, separations `0x28`/`0x38`), tagged `{size, tag}` qwords (`{0x68,0xb}`, `{0x50,0x13}`, `{0x20,1}`) and `{0,1}` markers — the same tagged record family as the DeviceTree `RAUS`/`clock-gates` payload records and the `0x1a36d8` pre-stream records (a tail byte-set check on record 3 is outstanding but the shared-base repetition carries the pattern).
- **Naming strings.** The static descriptor object `0x215ed8` sits inline inside iBoot's peripheral-name string pool: `arm-io/i2c0..i2c4` end just before it, and `nub`, `nub_spmi`, `smc_out`, `smc_in`, `ans`, `dart-dcp`, `dart-disp0`, …, `aop`, `pmp`, `sep`, `sio`, `ane`, `disp0`, `dcp-ext`, `dcp`, `dispdfr`, `scaler`, `jpeg` begin exactly at the object end `0x215f40`. `smc_out`/`smc_in` have **no code references** — RTKit channel-name strings pooled with the descriptor, not descriptor content.

Static conclusion: `0xd5960` (property read) and `0xbb930` (record walker) join `0x37188`'s registry-portal work (`0xc2100`/`0xc2934`) into one manifest-processing pipeline with the SMC descriptor chain; the ninth-record cap, the fixed shared base `0x1FC1A5BB8` and the `{addr,type,id,id2}`/`{ptr,ptr,{size,tag},{0,1},base}` rhythms tie `0x1a36d8`, the DT `RAUS`/`clock-gates` payloads, and the `0x160950` records into one record family. The runtime staging step (filling container `0x1FC1EF768..0x1FC229498` upstream of `0xb5c28`) is still untraced statically; nothing here is on-device evidence.

## boot-policy vocabulary of the unified iBoot (resolved 2026-10-26 round)

The unified payload contains one local-policy vocabulary, and it is the iOS/cryptex1 form, in a contiguous string block at `0x19a074..0x19a0d0`:

| site | string |
|---|---|
| `0x19a074` | `%s/%s/LocalPolicy.cryptex1.img4` |
| `0x19a094` | `%s/active` |
| `0x19a09e` | `lp-nsih` |
| `0x19a0a6` | `lp-spih` |
| `0x19a0ae` | `chosen/asmb` |
| `0x19a0ba` | `asmb` |
| `0x19a0bf` | `/boot/active` |

Read as a boot policy, this pins the next-stage image with `lp-nsih` (plus a second policy hash `lp-spih`), selects the active assembly via `/boot/active`/`chosen/asmb`, and names the policy file `LocalPolicy.cryptex1.img4`. It is the iOS mechanism, not the macOS owner-controlled security-mode/LocalPolicy flow.

**Negative — no macOS permissive/custom-kernel vocabulary.** Image-wide scans find none of `fuOS`, `coih`, `smb0`–`smb4`, `lobo`, `love`, `hrlp`, `auxp`, `sip0`–`sip3`, and no `permissive` / `custom kernel` / `One True` / `1TR` string — neither as ASCII, nor as a byte-reversed 4CC, nor as a `movz`/`movk`-resolved 32-bit constant (the resolver was run over the whole image, including the `0x151000..0x158000` service band). The same scan over `iBootData`, the J407 DeviceTree and `sep-firmware` is empty (the lone `1TR` hit is a single triplet inside the 5.4 MB SEP blob, consistent with chance). The DeviceTree exposes only certificate/security-status fields (`effective-security-mode-ap`, `certificate-security-mode`, `effective-production-status-ap`, `cryptex1-key-scheme`, `amfi-allows-trust-cache-load`) and no `security-mode-change`/custom-kernel node.

**Caveat.** The policy strings have no simple static xref: no `adr`, `adrp`+`add`/`sub` (including negative page offsets), 8-byte literal pointer, or `movz`/`movk`-resolved address over the whole image lands in `0x19a040..0x19a0d0`; like the VMiBoot loader strings, they are reached through a compact/indirect table. The result is a statement about the vocabulary present in this build — it rules out the macOS policy-based custom-kernel route for this image, but not an implementation bug in iBoot. It cross-checks the earlier BuildManifest pass, which had already found no Mac-style LocalPolicy/CustomOS fields (`docs/boot-entry-research.md`).

## address space & runtime layout (resolved 2026-10-24 round)

The long-standing open questions — what the 18,459 literal-pool loads actually reference, why 54% of resolved formation targets fall beyond the file, and whether a per-segment VA↔file-offset model is needed — closed with a full value-class census of the pool region `0x15b000..0x196ff8` (30,719 qwords):

| pool class (hi32 \| low32) | n | reading |
|---|---|---|
| `{1 \| low ∈ [0xFC000000..0xFD000000)}` | 16,029 | **SMC-domain pointers** — absolute pointers `0x1FC000000 + image-relative offset`, every target in `[0x1a5b50..0x28a640]`, never touching iBoot's own code/rodata |
| `{1 \| small}` remainder | 441 | `{tag, count/size}` records |
| `{tag \| small}`, hi32 ∈ {2:479, 6:238, 0x10000001:211, 0x80000001:151, 0x40000001:143, 0xb:129, 0x13:83, 3:69} | 1,503 | tagged small-value records (counters/ids/attrs), not pointers |
| `{0x8010b803 \| kernel}` | 256 | dispatch table A (11 kernels `0x140ca0..0x140f60`) |
| `{0x801023ca \| kernel}` | 255 | dispatch table B entries 0–254 (11 kernels `0x145adc..0x145c1c`); index 255 (`0xff`) is the re-signed `{0x807023ca \| 0x145b18}` record |
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
- **Pre-stream records**: nine complete 16-byte entries occupy `0x1a36d8..0x1a3768`: `{u32 addr, u32 type = 2, u32 id, u32 id2}`, with `addr = 0x35200000 + 0x4000*n`, `id = 0x74 + n`, `id2 = 0x25d + n` for n = 0..8. The first `bvx2` block begins immediately after the last entry at `0x1a3768` (the table is not truncated). The `0x352xxxxx` sequence is a candidate destination/segment map (SMC address space), not yet proven. There is no inline `{len@+0x10, type@+0x14}` header at the stream itself. The external descriptor is at `0x215ed8` (`+0x48 = 0x39d30`, `+0x54 = 0x8a1`), documented in the SMC boot-object section above. `b5c28` receives it through `0xb695c` from `x0 = 0x215ed8`; the static object identity is resolved. The remaining gap is runtime staging: the descriptor's `+0x00` input pointer is an SMC VA, while the stream bytes in the file are at `0x1a3768`.
- **Decoded with the public liblzfse reference decoder**: input `0x39d23` B → output **`0x79760` B** (497,504 bytes); the decoder consumed the stream up to exactly the `'bvx$'` marker. Decompressed SHA-256 prefix `7da684741cedf068` (unified image prefix `dc3cb25f29f25645` for cross-reference). The same stream was later decoded by the **in-image engine itself** under emulation to the identical digest (see the emulation proof in the decompress-call-chain section).
- **Handler-verified structure of the output**: 67.7% non-zero; **0.84% `ret` word density across 0x1e5d8 words** with zero `pacibsp` words — a real (PAC-less, pre-PAC-style) ARM64 module; the dominant record stride is 8 bytes (78.3% of non-zero u32 blocks) with 16-byte nesting.
- **Identity markers**: 1025 eight-byte records spelling **`rtkstack`-style markers as `"RTKSTACK"`** (low32 `0x534b5452 'RTKS'`, high32 `0x4b434154 'TACK'`), plus embedded file-path strings reconstructing to `platform/t8103/...` (e.g. `.../drivers/power/drv_therma...`). The payload head is `b +0x204` followed by zero-fill, and the branch target opens with `mrs x1, currentel; ubfx x1, x1, #2, #2; cmp x1, #3` — an EL3 validation guard.
- **Persistent reading**: the payload is an **Apple coprocessor firmware image built for the `ipad13b` platform group**, embedded LZFSE-compressed inside iBoot's data region.
- **Identity — confirmed by embedded strings**: the payload self-identifies as **`AppleSMCFirmware_H13-7372.2.11.ipad13b.REL`** (at +0x6b878) on top of **`RTKit_release-3514.0.15.release`** (at +0x52dbc). Source-path strings confirm the SMC role: charger (`drivers/charger/v1/potomac/drv_potomac_charger.cpp`), battery management (`smc/bms/v1/batterySocFilter/batterySocFilter.cpp`, `charge_control.cpp`), thermal (`smc/thermal/componentController/basebandCC.cpp`), power/PMU (`drivers/power/drv_pmu_interface.cpp`, `drv_pmu_events.cpp`, `drv_apc_sera.cpp`, `drv_apc_simetra.cpp`), and T8103 platform shim files (`platform/t8103/device_{gpio,pmgr,spmi,watchdog,dockchannel,iop_ans,forcewakeup}.cpp`, `platform/common/platform_{power,mem}.cpp`). The 4096-byte-aligned `RTKSTACK` guard runs (`x1025`) are RTKit stack guard pages. `ipad13b` matches the same platform tag as the J407 `kernelcache.release.ipad13b` in the restore manifest.
- **Consumer chain (resolved)**: the early-code formation sites that appeared to point into the compressed blob (`0xc6c4`, `0xc6f4`, `0xc718`, `0xc738`, `0xc75c`, `0xc77c`, … targeting page `0x1a3`) are **staged-region references** — in the runtime layout that file area is SMC staging/service RAM (see the address-space section above), so no static reference reads compressed bytes. The measured chain is: **embedded compressed firmware (transient file content) → in-image LZFSE-family engine (twin PAC-dispatch tables, 11 kernels each) decodes to image-relative `≈0x1f64a0` → iBoot's pool carries the SMC's runtime object map (16k domain pointers at base `0x1FC000000`: staging records, RTKSTACK guard pages, the image itself, and a beyond-file heap)**.

What the payload does at runtime: it is the **SMC (System Management Controller) firmware** — `AppleSMCFirmware_H13-7372.2.11.ipad13b.REL` on `RTKit_release-3514.0.15.release`, managing charger/BMS/thermal/PMU/SPMI — embedded compressed and decoded by the in-image engine into image-relative `≈0x1f64a0` (SMC-VA `0x1FC1F64A0`). The stream is byte-exact under two independent in-image decode paths: (a) the earlier selector-0 control, wrapper `0x144a0c` → container `0x145e44` (per-block dispatch `0x145ef8`, header parse `0x146414`, VLC table parse `0x1471d8`, decode loops `0x14685c`, copy helpers `0x144330`/`0x144630`); and (b) the descriptor-supported `0x8a1` path, raw block decoder `0x144d5c` → `bvx2` table setup `0x144eec` / shared match-copy `0x145d80`, with no container or VM-mapper call. Both reproduce the digest `7da684741cedf068`. The runtime entry channel is resolved (execute dispatcher `0x1473f0` tail branch; four protocol loaders mapped to boot subsystems in the loader-map section above); the boot-object descriptor consumed by `b5c28` is `0x215ed8` with `+0x48 = 0x39d30` and `+0x54 = 0x8a1`. Still open: runtime reachability of the `0x37440` block and the staging step that populates the descriptor's SMC input pointer, the public name of `0x8a1`, the mailbox semantics of the shared `0x1FC1A5BB8` base, and the `0x891` message-type / bitstream-word selection semantics.

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
