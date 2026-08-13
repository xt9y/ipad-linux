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

### Target identity — now verified on physical hardware

The target identity was first established from public firmware/device data and was then confirmed on the physical iPad on 2026-08-13:

```text
ProductType      iPad13,16
HardwareModel    J407AP
Model            A2588
SoC              Apple M1 / T8103
CPID             0x8103
BDID             0x10
CPUArchitecture  arm64e
iPadOS           26.5
Build            23F77
```

This is important: the iPad Air 5 is **M1**, not M2. T8103 is also used by first-generation M1 Macs, which gives us substantial reusable SoC support.

### Physical USB and Recovery validation

The real device was connected to an AArch64 Fedora Asahi Linux host with a normal USB-C data cable.

Normal iPadOS enumerated as:

```text
05ac:12ab Apple, Inc. iPad
```

Apple Recovery enumerated as:

```text
05ac:1281 Apple Mobile Device [Recovery Mode]
```

`irecovery` independently confirmed J407/CPID/BDID and reached the real Recovery command prompt. The observed Recovery firmware identified itself as:

```text
Microkernel iBoot for j407
Board 0x10 (j407ap) / Rev 0x5
BUILD_TAG:   mBoot-18000.120.36
BUILD_STYLE: RELEASE
```

Legacy `getenv` requests tested through libirecovery returned no values on this mBoot release. No write/upload/boot request was required for this validation.

The complete sanitized validation record is in `docs/physical-validation-2026-08-13.md`.

### Matching 26.5 J407 restore chain

The matching public `23F77` restore IPSW was inspected offline. Its BuildManifest contains J407 identities for erase, update and Recovery Customer Install flows.

The J407 boot/restore set includes:

```text
Firmware/dfu/iBSS.j407.RELEASE.im4p
Firmware/dfu/iBEC.j407.RELEASE.im4p
Firmware/all_flash/LLB.j407.RELEASE.im4p
Firmware/all_flash/iBoot.j407.RELEASE.im4p
Firmware/all_flash/DeviceTree.j407ap.im4p
kernelcache.release.ipad13b
```

The iBSS, iBEC, LLB and iBoot IM4P containers identify the same `mBoot-18000.120.36` build family observed on the physical device.

The BuildManifest marks the relevant boot/restore objects trusted. The Recovery Customer Install identity marks both `iBSS` and `iBEC` with `Personalize = True`, and their restore rules depend on Image4/security/production state.

### NeRD / RecoveryOTA evidence

The J407 Recovery Customer Install identity contains:

```text
AllowNeRDBoot = True
NeRDEpoch = 0
RestoreAttestationMode = 6
```

Many of its variant contents are labelled `RecoveryOTAProduction`.

No `PermitNeRDPivot` value was present in the J407 identity. This pass also found no Mac-style `LocalPolicy`, `CustomOS`, `coih`, `lpnh`, `smb0`, `smb1`, `smb2` or `nsih` fields.

Public TSS implementations model `NeRDEpoch` and optional `PermitNeRDPivot` as Apple TSS request fields together with an Image4 ticket request. Therefore `AllowNeRDBoot` is treated here as evidence of an Apple-authorized recovery/restore path, **not** as evidence that the device accepts arbitrary unsigned m1n1/Linux payloads.

### Linux support exists for the SoC, not this board

Current mainline Linux contains `arch/arm64/boot/dts/apple/t8103.dtsi` and board files for M1 Macs such as J274, J293, J313, J456 and J457. The common Mac board data cannot be blindly reused as J407 board data.

The project therefore reuses the T8103 SoC support and carries independently verified J407 board data in its own DTS/platform code.

### Mac-style CustomOS boot depends on LocalPolicy

Apple documents an owner-controlled LocalPolicy system specifically for **Mac with Apple silicon**. In permissive security, LocalPolicy fields allow a custom kernel collection to be authorized by the Secure Enclave owner key. Asahi uses that Mac-specific mechanism to place m1n1 in the boot chain.

No documented equivalent owner-configurable CustomOS/LocalPolicy workflow for iPad was found, and the physical J407/26.5 BuildManifest pass did not expose the corresponding LocalPolicy/CustomOS fields.

That remains the core architectural difference between the installable Asahi path on Macs and this project.

### Boot ROM status

No verified public M1/T8103 J407 BootROM entry primitive is assumed by this repository. Absence of a public method is not proof that no vulnerability can exist; it means the project currently has no reproducible immutable early-boot primitive to build on.

### Jailbreak status is a different capability class

Code execution inside a running iPadOS stack is not automatically equivalent to the pre-Linux EL1/EL2, MMU, cache, interrupt and DMA control required by this loader.

A jailbreak could still be useful for runtime observation, but the native boot-entry problem must be treated separately.

## What is already ready once entry is solved

The repository now has a clean target for any future legitimate entry mechanism:

1. Versioned `boot_info v4` handoff ABI.
2. Runtime EL/MMU validation instead of trusting loader metadata.
3. ARM64 `Image`, DTB and initrd placement validation.
4. Cache-maintenance and Linux handoff code.
5. Bounded live Apple Device Tree parsing and `ranges` translation.
6. J407-specific platform discovery isolated under `src/platform/j407/`.
7. J407 Linux FDT built from upstream T8103 support plus independently verified board data.
8. Eight-core SMP contract.
9. Mainline Linux + J407 DTB + static diagnostic initramfs cloud build.
10. m1n1 payload packer, live-ADT dumper, host preflight, first-boot analyzer and hardware-report builder.

## Current physical status

```text
J407 identity                       VERIFIED ON DEVICE
normal USB-C data link              VERIFIED ON DEVICE
Apple Recovery USB                  VERIFIED ON DEVICE
mBoot recovery prompt               VERIFIED ON DEVICE
mBoot build                         VERIFIED ON DEVICE
matching 26.5 IPSW/BuildManifest    VERIFIED OFFLINE
J407 iBSS/iBEC/iBoot identities     VERIFIED OFFLINE
Image4 trust/personalization        VERIFIED OFFLINE
m1n1 execution on J407              NOT ACHIEVED
Linux execution on J407             NOT ACHIEVED
```

## Current conclusion

The project still has two separate engineering problems:

```text
A. Obtain a legitimate/authorized execution path before XNU owns the machine.
B. Turn that execution environment into a correct T8103/J407 Linux boot environment.
```

Problem B is substantially prepared. Problem A remains the hard gate.

Nothing found in the physical validation invalidates the Linux design. Native Linux remains technically plausible because T8103 is already a Linux-capable SoC and the physical device exactly matches the J407 assumptions used by the software. But until m1n1 (or an equivalent loader) can actually be executed on J407, a physical Linux boot remains unproven.

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
