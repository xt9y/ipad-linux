# Boot-entry research status

Target: iPad Air 5 Wi-Fi (`iPad13,16`, `J407AP`, M1/T8103, CPID `0x8103`, BDID `0x10`).

This document separates mechanisms that can actually hand control to a native Linux loader from mechanisms that merely provide code execution inside iPadOS.

## Required capability

The project ultimately needs an execution environment that can hand the machine to Linux with enough control to:

- execute our AArch64 payload at EL1 or EL2;
- supply or recover the live Apple Device Tree and RAM layout;
- stop or quiesce DMA-capable devices;
- mask interrupts;
- perform required data/instruction-cache maintenance;
- enter Linux with the MMU off;
- place a Linux `Image`, DTB and optional initrd in valid physical RAM;
- branch to the Linux entry point with `x0 = dtb` and `x1..x3 = 0`.

A normal application sandbox escape is not sufficient. A conventional jailbreak may be useful research infrastructure, but it is not automatically equivalent to a Linux chainloader.

## Evidence collected

### Target identity

Multiple public firmware/device databases agree on the target identity:

```text
ProductType  iPad13,16
Model        A2588
BoardConfig  J407AP
SoC          Apple M1 / T8103
CPID         0x8103
BDID         0x10
```

This is important: the iPad Air 5 is **M1**, not M2. T8103 is also used by first-generation M1 Macs, which gives us substantial reusable SoC support.

### Linux support exists for the SoC, not this board

Current mainline Linux contains `arch/arm64/boot/dts/apple/t8103.dtsi` and board files for M1 Macs such as J274, J293, J313, J456 and J457. The common `t8103-jxxx.dtsi` sets up Mac-specific pieces such as two USB-C paths, PCIe Wi-Fi/Bluetooth and loader-filled memory/framebuffer data.

No `J407` board file was found in the current mainline Linux or m1n1 trees during this research pass. We should therefore reuse `t8103.dtsi` but must **not** blindly include the Mac-only `t8103-jxxx.dtsi` on the iPad.

### Mac-style CustomOS boot depends on LocalPolicy

Apple documents an owner-controlled LocalPolicy system specifically for **Mac with Apple silicon**. In permissive security, LocalPolicy fields such as `smb1` allow a custom kernel collection to be signed by the Secure Enclave owner key; the `coih` field records the CustomOS Image4 manifest hash. These settings are changed from paired One True Recovery (1TR).

Asahi relies on that mechanism: iBoot2 loads m1n1 as the configured custom kernel, then m1n1 converts the Apple/XNU-style boot environment into an ARM64 Linux/FDT environment.

There is no documented equivalent owner-configurable CustomOS/LocalPolicy workflow for iPad. That is the core architectural difference between the easy-to-install Asahi path on Macs and this project.

### Boot ROM status

The public Apple-device research databases checked for T8103 currently list no known Boot ROM vulnerability for M1/T8103. This is not proof that none exists; it means this project has no verified public immutable early-boot primitive to build on.

### Jailbreak status is a different capability class

Public compatibility databases list jailbreaks for `iPad13,16` on older iPadOS 15.x/16.x releases. Those techniques execute within or against the running iPadOS software stack. They do not by themselves establish the EL1/EL2, MMU-off, DMA-quiesced pre-Linux environment required by this loader.

A jailbreak can still be useful for collecting runtime information, studying the live ADT or testing hardware assumptions, but the native boot-entry problem must be treated separately.

## What we can build before entry is solved

The loader should continue to become a clean target for any future authorized/research entry mechanism. The entry adapter only needs to populate the stable `boot_info` ABI and transfer control.

Current loader-side work can proceed independently:

1. Validate the real runtime exception level and MMU state rather than trusting loader metadata.
2. Validate ARM64 `Image` placement, DTB alignment/size and initrd placement.
3. Perform required cache maintenance before Linux entry.
4. Parse the live Apple Device Tree and derive physical addresses through `ranges` rather than hardcoding Mac addresses.
5. Keep J407-specific hardware initialization isolated under `src/platform/j407/`.
6. Build a J407 Linux FDT from upstream `t8103.dtsi` plus verified board data and runtime patches.
7. Define explicit CPU/timer/coherency requirements for the handoff contract.

## Next research targets

### 1. Pin the physical device's installed build

Record only the non-secret fields needed for research:

```text
iPadOS version
build number
ProductType
```

Do not record serial number, ECID or other device-unique identifiers in this public repository.

### 2. Map the matching public firmware

For the installed build, record from public IPSW metadata:

- restore IPSW filename/build;
- iBoot/iBEC version where publicly exposed;
- DeviceTree image name for J407;
- kernelcache naming;
- BuildManifest identity for `iPad13,16`.

This gives us reproducible firmware-version context without modifying the device.

### 3. Compare J407 ADT topology with T8103 Linux nodes

Build a table mapping live/public ADT paths to Linux DT nodes for at least:

```text
AIC
PMGR
UART
DART/IOMMU
NVMe
USB/DWC3
ATC/USB-C PHY
GPIO
watchdog
DCP/display
Wi-Fi/Bluetooth
```

### 4. Keep the entry mechanism replaceable

Do not couple generic Linux bring-up code to a specific jailbreak, exploit, restore tool or firmware vulnerability. Any future entry path should terminate at the same `boot_info` boundary.

## Current conclusion

The project has two separate engineering problems:

```text
A. Obtain a legitimate/research execution path before XNU owns the machine.
B. Turn that execution environment into a correct T8103/J407 Linux boot environment.
```

Problem B can make substantial progress today. Problem A remains unresolved: no public M1/T8103 Boot ROM path or owner-authorized iPad CustomOS mechanism was verified in this research pass.

## Public references

- Apple Platform Security — Contents of a LocalPolicy file for a Mac with Apple silicon
  - https://support.apple.com/guide/security/secc745a0845/web
- Asahi Linux — Open OS Platform Interoperability
  - https://asahilinux.org/docs/platform/open-os-interop/
- Asahi Linux — Apple Silicon Boot Flow
  - https://asahilinux.org/docs/fw/boot/
- Linux kernel — Booting AArch64 Linux
  - https://www.kernel.org/doc/html/latest/arch/arm64/booting.html
- Linux mainline — Apple T8103 device trees
  - https://github.com/torvalds/linux/tree/master/arch/arm64/boot/dts/apple
- IPSW device metadata for `iPad13,16`
  - https://ipsw.me/iPad13,16/info/
- AppleDB device metadata for `iPad13,16`
  - https://appledb.dev/device/identifier/iPad13,16.html
- The Apple Wiki — T8103
  - https://theapplewiki.com/wiki/T8103
