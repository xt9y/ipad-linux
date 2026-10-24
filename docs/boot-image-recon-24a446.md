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
