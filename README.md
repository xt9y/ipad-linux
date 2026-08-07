# ipad-linux

Research and bring-up project for Linux on the **iPad Air (5th generation) Wi-Fi**.

## Target

```text
ProductType: iPad13,16
BoardConfig: J407AP
Model:       A2588
SoC:         Apple M1 / T8103
CPID:        0x8103
BDID:        0x10
```

T8103 already has substantial upstream Linux/Asahi and m1n1 support. The project therefore reuses the SoC implementation and adds only J407-specific board data that can be independently verified.

## Boot architecture

The unresolved part is still the **initial iPad boot entry**. This repository does not assume that a public BootROM/iBoot bypass exists.

Once a legitimate research mechanism can execute m1n1, the preferred first-boot path is deliberately small:

```text
future J407 early-boot execution
        |
        v
upstream m1n1
        |
        | native concatenated payload scanner / kboot
        v
mainline Linux Image + t8103-j407.dtb + initramfs
        |
        v
PID 1 diagnostic userspace
```

The build produces a single payload-chain artifact:

```text
j407-m1n1-linux.bin =
    m1n1.bin
  + t8103-j407.dtb
  + initramfs.cpio.gz
  + Image
```

The uncompressed Linux `Image` is last, matching upstream m1n1's documented payload rules.

A separate freestanding `ipad-linux-stage2.bin` remains in the repository for diagnostics, alternative entry mechanisms and low-level experiments. It uses the versioned `boot_info v4` ABI and is **not required** for the preferred first Linux boot through m1n1 kboot.

## What is already implemented

- [x] Exact J407/T8103 target identity
- [x] Freestanding, relocation-free AArch64 diagnostic Stage 2
- [x] Bounded Apple Device Tree parser and `reg`/`ranges` translation
- [x] J407 live discovery for UART/AIC/PMGR/watchdog/storage/USB/display paths
- [x] EL1/EL2 exception vectors with ESR/ELR/FAR/SPSR diagnostics
- [x] ARM64 Linux Image/header and placement validation
- [x] FDT builder and fixed-size runtime patching
- [x] `boot_info v4` handoff ABI
- [x] Compile-checked m1n1 SMP/next-stage adapter
- [x] T8103 eight-core spin-table release mapping
- [x] J407 UART0 early console DTS
- [x] Mainline-kernel configuration for Apple mailbox/RTKit/SART/DART/ANS2 NVMe
- [x] Minimal static ARM64 initramfs with `/init`
- [x] Mainline `Image` + J407 DTB + initramfs cloud build
- [x] Self-contained m1n1/Linux payload-chain packer
- [x] Offline J407 ADT inspection tool
- [x] Verified J407 ANS2/NVMe/SART addresses and NVMe IRQ against mainline T8103
- [ ] Execute m1n1 on physical J407
- [ ] Observe UART0/earlycon and reach PID 1
- [ ] Verify SMP and ANS2/NVMe on physical hardware
- [ ] Verify the J407 USB-C controller/PHY route
- [ ] Bring up framebuffer/native display, then GPU
- [ ] Bring up Wi-Fi/BT, touch, audio and remaining board peripherals

## Repository layout

```text
.github/workflows/        cloud build/compatibility gates
docs/                     boot and J407 hardware research
dts/t8103-j407.dts        minimal J407 Linux board DTS
initramfs/init.c           first-boot PID 1
integration/m1n1/          compile-checked m1n1 adapter
kernel/                    J407 kernel config fragments
scripts/                   initramfs + payload-chain builders
src/
  adt/                     Apple Device Tree parser
  arch/aarch64/            exception/system helpers
  boot/                    Linux/FDT/handoff contracts
  debug/                   debug sink + UART
  memory/                  range helpers
  payload/                 diagnostic Stage 2
  platform/j407/           J407-specific discovery/contracts
tests/                     host-side parser/ABI/layout tests
tools/adt-inspect.c        offline raw ADT inspector
```

## Build the diagnostic Stage 2

Requirements: `clang`, `ld.lld`, `llvm-objcopy`, and `llvm-objdump`.

```sh
make
```

Outputs:

```text
build/payload.elf
build/payload.bin
build/payload.dis
```

The linker VMA is a build-time placeholder only. The payload is built position-independently and CI rejects runtime AArch64 relocations.

## Cloud first-boot image

The `j407-first-boot-image` GitHub Actions workflow checks out **current upstream m1n1** and **current mainline Linux**, then builds:

```text
Image
t8103-j407.dtb
initramfs.cpio.gz
m1n1.bin
ipad-linux-stage2.bin
j407-m1n1-linux.bin
SHA256SUMS
```

`j407-m1n1-linux.bin` is the preferred future physical-device bring-up artifact once a legitimate m1n1 execution path exists.

## Current hardware confidence

Already independently matched between the public J407 Apple Device Tree and Linux T8103 support:

```text
UART0       0x235200000, IRQ 605
AIC         0x23b100000
PMGR        0x23b700000
ANS window  0x277400000
ANS2 NVMe   0x27bcc0000, IRQ 590
SART-ANS    0x27bc50000
```

The live Apple Device Tree remains authoritative for runtime memory, firmware carveouts and board-specific routes.

## Project rules

1. Never invent MMIO addresses, IRQs, stream IDs, device-tree data or boot-policy behavior.
2. Reuse upstream T8103 support where J407 evidence matches it.
3. Do not import the M1-Mac-only `t8103-jxxx.dtsi` into J407.
4. Keep the unresolved initial secure-boot/entry problem separate from Linux bring-up.
5. Prefer fail-closed runtime validation over trusting loader metadata.
6. Add hardware writes only when the register block and required power/clock state are verified.

## Current blocker

The software side can now build a credible J407 m1n1/Linux first-boot image. The major unresolved gate is **getting sufficiently early, legitimate code execution on the physical iPad so m1n1 can run**. No public T8103/J407 BootROM or iBoot path is assumed by this project.
