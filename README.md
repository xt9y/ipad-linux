# ipad-linux

Experimental research project for booting Linux on Apple Silicon iPads, initially targeting M2 iPad hardware.

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

There is currently **no assumption that an exploitable boot path exists**. The first stage of this repository is limited to reproducible research, freestanding ARM64 payload development, and tooling that can be built without physical access to the iPad.

## Current milestones

- [x] Repository scaffold
- [x] Minimal freestanding AArch64 payload
- [x] LLVM/Clang build system
- [x] GitHub Actions build
- [ ] Identify exact target iPad board/model/SoC configuration
- [ ] Document iPad boot chain and execution constraints
- [ ] Establish a safe device-probing workflow
- [ ] Obtain controlled early-boot code execution
- [ ] Bring up serial/USB debugging output
- [ ] Adapt or integrate m1n1
- [ ] Boot a Linux kernel
- [ ] Bring up platform devices and drivers

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

The linker address is intentionally a placeholder. It is **not** an asserted RAM or MMIO address for any iPad model.

## Project rules

1. Do not invent MMIO addresses, device-tree data, boot-policy behavior, or hardware identifiers.
2. Mark unknown platform details explicitly.
3. Prefer upstream Linux, Asahi Linux, m1n1, U-Boot, and primary Apple-platform research as references.
4. Keep platform-specific assumptions out of generic bootstrap code where possible.
5. Treat the boot-entry problem separately from the Linux-porting problem.

## Status

This project does not currently boot on an iPad. The initial code is a buildable development scaffold for future platform work.
