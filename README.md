# ipad-linux

Experimental research project for booting Linux on Apple Silicon iPads.

## Current target

This branch targets the **iPad Air (5th generation) Wi-Fi** specifically:

```text
ProductType: iPad13,16
BoardConfig: J407AP
Model:       A2588
SoC:         Apple M1 / T8103
CPID:        0x8103
BDID:        0x10
```

The M1/T8103 SoC already has substantial Asahi Linux and m1n1 support on Macs. The iPad-specific boot chain and board peripherals remain the key unknowns.

## Goal

Long-term target:

```text
Apple BootROM
    -> iBoot / future execution mechanism
    -> custom AArch64 bootstrap
    -> m1n1-derived or compatible loader
    -> Linux kernel
    -> userspace
```

There is currently **no assumption that an exploitable boot path exists**. The repository is structured so SoC/board work can progress without pretending that the boot-entry problem has already been solved.

## Current milestones

- [x] Repository scaffold
- [x] Minimal freestanding AArch64 payload
- [x] LLVM/Clang build system
- [x] GitHub Actions build
- [x] Exact target identified: iPad13,16 / J407AP / T8103
- [x] J407 platform abstraction added
- [x] Initial boot-chain and hardware research documented
- [ ] Record installed iPadOS version/build
- [ ] Determine viable early-boot code-execution path for that build
- [ ] Establish safe USB/recovery probing workflow
- [ ] Obtain controlled early-boot code execution
- [ ] Bring up early debug output
- [ ] Extract/inspect the J407 Apple Device Tree
- [ ] Adapt or integrate m1n1
- [ ] Boot a Linux kernel
- [ ] Bring up platform devices and drivers

## Source layout

```text
src/
├── payload/
│   ├── start.S
│   ├── main.c
│   └── linker.ld
└── platform/
    └── j407/
        ├── platform.h
        └── platform.c
```

## Build

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

The current linker address is intentionally a placeholder. It is **not** an asserted RAM or MMIO address for the iPad Air 5.

## Project rules

1. Do not invent MMIO addresses, device-tree data, boot-policy behavior, or hardware identifiers.
2. Mark unknown platform details explicitly.
3. Prefer upstream Linux, Asahi Linux, m1n1, U-Boot, and primary Apple-platform research as references.
4. Keep J407-specific assumptions inside `src/platform/j407/`.
5. Treat the boot-entry problem separately from the Linux-porting problem.
6. Add real hardware initialization only after its addresses, clocks/power requirements, and execution context are verified.

## Status

The payload now builds as a J407/T8103-targeted freestanding ARM64 program, but it does **not** yet have a mechanism to execute on the iPad. That is the next major engineering gate.
