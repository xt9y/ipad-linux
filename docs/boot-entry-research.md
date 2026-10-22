# Boot-entry research status

Target: iPad Air 5 Wi-Fi (`iPad13,16`, `J407AP`, M1/T8103, CPID `0x8103`, BDID `0x10`).

This document separates mechanisms that can actually hand control to a native Linux loader from mechanisms that merely provide code execution inside — or under — iPadOS.

Last full public survey: **2026-10-22**.

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

A normal application sandbox escape is not sufficient, and neither is a kernel exploit inside a running iPadOS: by the time the kernel (or anything above it) is compromised, SecureROM/iBoot have already booted a fully signed chain, and the pre-boot environment the loader needs has already been consumed. A conventional jailbreak is research infrastructure, not a Linux chainloader.

## Evidence collected

### Target identity — verified on physical hardware

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

Version drift note: the identity above was recorded on 2026-08-13. iPadOS 27.0.1 (`24A446`) has been signed since 2026-09-28, so the device may have auto-updated since the last physical contact — re-read `ProductVersion`/`BuildVersion` via `ideviceinfo` on the next connection before drawing build-specific conclusions.

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

For comparing later builds against `23F77` offline, `tools/j407-firmware-diff.py` now diffs two BuildManifests (identity fields, boot-chain components and digests, per-component restore policy, NeRD-type policy keys) with ECID/serial-class values always redacted.

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

## 2026 public boot-entry survey

The following public developments were reviewed against the required capability. None of them provides a boot-entry primitive for T8103.

### usbliter8 — SecureROM exploit, wrong SoC generation

- Published 2026-06-18 by the Paradigm Shift research group; immediate comparisons went to checkm8 because the flaw likewise cannot be patched — it is in immutable silicon.
- Mechanism (as described in public coverage): a DMA buffer underflow in the Synopsys DWC2 USB controller reachable in DFU's SecureROM, combined with the SecureROM's ISP (DART) configuration: on affected chips the SecureROM runs the DART in a mode that lets the underflowing DMA pointer reach (and rewrite) arbitrary SRAM. Post-exploitation, a custom USB request handler is injected and the device's USB serial string gets `PWND:[usbliter8]`; from there unsigned iBoot can be loaded, and production state can apparently be temporarily demoted. The Secure Enclave is reported unaffected.
- Affected silicon: **A12, A13, S4, S5** only (public exploit excludes A12X/A12Z; A11 is not affected; coverage states A14 and later — which includes every M1/T8103 device — appear out of reach because that DART-under-bypass configuration is what made the primitive exploitable there).
- Affected SecureROM versions: `3865.0.0.4.7` – `4479.0.0.100.4` (Per The Apple Wiki; newer SecureROM generations reflect the same hardware fix).
- Status: Paradigm Shift's writeup and source were pulled under a preliminary injunction dated 2026-07-21 (Magnet Forensics v. Del Gaudio); archived copies and independent implementations (e.g. ElcomSoft's hardware/RP2350 USB-hosted variant) circulate.
- **Conclusion for this project:** the exploit's reach ends at the A13/S5 generation. T8103 is two-plus generations past it and has a different USB controller generation and different SecureROM DART discipline. There is no evidence of an equivalent primitive for T8103, and nothing in this repository may assume one. This is a strong reminder that SecureROM USB-class research (the controller that both DFU and Recovery expose) remains the natural frontier for a future entry primitive.

### Project Cascadia — native Linux on iPad exists, but consumes an A5-bootROM-era primitive

- rzxvx's Project Cascadia (September 2026) boots a current Linux kernel (6.12) and Alpine Linux natively on the original iPad mini (Apple A5, S5L8942X), with touch, Wi-Fi and an XFCE desktop. Per its author it is the first step of an intended A5 → A6 → A12/A13 progression.
- The enabling tooling is the 32-bit A5–A11 boot-chain family: the device is checkm8-vulnerable (A5 is in the checkm8 set), and Cascadia is built on the earlier "iBSSloader"-style custom-iBSS booting work (see the curated index at `ipadlinux.org`, which also lists iBoot32Patcher and checkm8_bootkit as the relevant stack).
- **Conclusion for this project:** this is the first credible *native* Linux-on-iPad precedent the community has had in years — and it works precisely because the A5 BootROM has a public, unpatchable entry primitive. Every iPad-native Linux path known to date consumes a BootROM or patched-iBoot entry primitive from the A5–A11 era. That is the class of tool this project lacks for T8103, and the gap is a silicon-generation gap, not an engineering-effort gap.

### VirtualMacOniPad — real work on our exact SoC, wrong capability class

- nfzerox's VirtualMacOniPad (2026) runs full macOS as a VM under iPadOS on M1/M2 iPad Pro **and M1 iPad Air (i.e. our exact J407 SoC)**, using the Apple Hypervisor framework plus paravirtualized graphics.
- To do this it jailbreaks (Dopamine/Taurine), extracts the Hypervisor/Virtualization/ParavirtualizedGraphics frameworks out of a macOS image with `uncache.py` (iPadOS ships without the shared-cache entries), emulates the USB devices needed for installation, and additionally **requires iPadOS ≤ 16.3.1**: iPadOS 16.4+ removed Hypervisor support from the XNU kernel.
- **Conclusion for this project:** impressive, but this is a VM *under* iPadOS. The guest macOS never touches SecureROM/LLB/iBoot, iPadOS itself owns the machine, and the tool needs (a) a jailbreak and (b) a firmware Apple stopped signing — 16.x has been unsigned for more than two years (27.0.1 being the currently signed J407 build). It is not a boot-entry mechanism and cannot be adapted into one without the very primitive this project is missing. It does, however, prove the J407 silicon is fully capable of workloads far heavier than our loader target.

### Jailbreak landscape 2026 — no M1-era channel, and jailbreaks are the wrong class anyway

- Dopamine 3.0 (August 2026) brought iOS 26 support — but only to **A12/A13 devices at 26.0–26.0.1** (via the momentarius PPL bypass by staturnzz and TheRealClarity). The A14–A17 Pro / **M1–M2** arm64e channel caps at iOS 15.0–17.3.1 (via the Titan PPL/SPTM bypass by alfiecg24).
- **Our device is on 26.5+ and unjailbroken.** There is no public jailbreak for iPadOS 26/27 on any M1-class iPad as of this survey; coverage reports nothing reliable above iOS 18.x for jailbreak-class access generally.
- Even a future M1-era PPL-era exploit (per the "kernel exploit ≠ boot entry" rule above): the moment it exists at all, it yields code execution under a fully approved iBoot-sealed chain — and it would be use-dependent for *observation* while remaining useless for pre-boot entry. This project treats both capabilities as strictly separate lanes.

### Signing state (as of 2026-10-22)

```text
iPadOS 27.0.1 (24A446)   SIGNED    <- only currently signed J407 build
iPadOS 27.0   (24A437)   unsigned
iPadOS 26.6.2 (23G90)    unsigned
iPadOS 26.6.1 (23G83)    unsigned
iPadOS 26.5   (23F77)    unsigned  <- firmware observed on the device 2026-08-13
```

Closing the 26.x signing window removed any restore-based research margin (an Error/Downgrade experiment that would have needed a device restore}) — any future restore-path research is now pinned to builds restoring as 27.0.1. This is purely informational for now: no signed-restore path provides boot entry by itself.

### Linux support exists for the SoC, not this board

Current mainline Linux contains `arch/arm64/boot/dts/apple/t8103.dtsi` and board files for M1 Macs such as J274, J293, J313, J456 and J457. The common Mac board data cannot be blindly reused as J407 board data.

The project therefore reuses the T8103 SoC support and carries independently verified J407 board data in its own DTS/platform code.

### Mac-style CustomOS boot depends on LocalPolicy

Apple documents an owner-controlled LocalPolicy system specifically for **Mac with Apple silicon**. In permissive security, LocalPolicy fields allow a custom kernel collection to be authorized by the Secure Enclave owner key. Asahi uses that Mac-specific mechanism to place m1n1 in the boot chain.

No documented equivalent owner-configurable CustomOS/LocalPolicy workflow for iPad was found, and the physical J407/26.5 BuildManifest pass did not expose the corresponding LocalPolicy/CustomOS fields.

That remains the core architectural difference between the installable Asahi path on Macs and this project.

### Boot ROM status

No verified public M1/T8103 J407 BootROM entry primitive is assumed by this repository. Absence of a public method is not proof that no vulnerability can exist; it means the project currently has no reproducible immutable early-boot primitive to build on.

Per the 2026 survey: the last public SecureROM-class primitive (usbliter8, June 2026) stops at the A13/S5 silicon generation; the last public patchable-iBoot generation tools are A5–A11-era; and the closest working iPad-native-Linux precedent (Project Cascadia, September 2026) depends on exactly those A5-era tools.

## What is already ready once entry is solved

The repository now has a clean target for any future legitimate entry mechanism:

1. Versioned `boot_info v4` handoff ABI.
2. Runtime EL/MMU validation instead of trusting loader metadata.
3. ARM64 `Image`, DTB and initrd placement validation.
4. Cache-maintenance and Linux handoff code.
5. Bounded live Apple Device Tree parsing and `ranges` translation.
6. J407-specific platform discovery isolated under `src/platform/j407/`.
7. J407 Linux FDT built from upstream T8103 support plus independently verified board data.
8. Eight-core SMP contract enforced on the payload side.
9. Mainline Linux + J407 DTB + static diagnostic initramfs cloud build.
10. m1n1 payload packer (fail-closed on FDT root compatible), live-ADT dumper, host preflight, first-boot analyzer, hardware-report builder and BuildManifest diff tool.
11. m1n1-side J407 adapter (`integration/m1n1/ipad_linux_adapter.c`): SMP collection, environment seeding, and RAM exclusion of the m1n1 image region so spin-table words and next-stage structures can never be advertised as allocatable to Linux.

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
firmware version on device as of today    UNKNOWN (device disconnected since 2026-08-13)
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

The 2026 survey sharpens problem A: no public entry primitive exists for T8103 silicon, the public SecureROM research frontier (USB DFU class) is the right axis but two generations shy of our chip, and every working native-Linux-on-iPad precedent is anchored in BootROM primitives from earlier silicon. Kernel-side exploits, as of the same survey, have not reached M1-era iPadOS 26/27 devices — and even when they eventually do, they remain in the wrong capability class for this loader.

Native Linux remains technically plausible: T8103 is already a Linux-capable SoC (mainline), and the physical device exactly matches the J407 assumptions used by the software. But until m1n1 (or an equivalent loader) actually executes on J407, a physical Linux boot remains unproven — and none of the mechanisms surveyed above claims to have done that.

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
- The Apple Wiki — usbliter8 exploit (affected SecureROM range, injunction)
  - https://theapplewiki.com/wiki/Usbliter8_Exploit
- The Hacker News — "Unpatchable usbliter8 Exploit Breaks Apple A12 and A13 SecureROM Boot Chain" (2026-06-19)
  - https://thehackernews.com/2026/06/unpatchable-usbliter8-exploit-breaks.html
- Security Affairs — "usbliter8 Brings Unpatchable BootROM Exploit to Apple A12 and A13 Devices"
  - https://securityaffairs.com/193965/hacking/usbliter8-brings-unpatchable-bootrom-exploit-to-apple-a12-and-a13-devices.html
- ElcomSoft blog — A12 usbliter8 BootROM sigpatches (hardware-hosted variant)
  - https://blog.elcomsoft.com/2026/07/a12-usbliter8-bootrom-sigpatches/
- GitHub — rzxvx/Project-Cascadia (native Linux on the A5 iPad mini)
  - https://github.com/rzxvx/Project-Cascadia
- iPad Linux — curated native-Linux-on-iPad project index (Cascadia/usbliter8 entries)
  - https://ipadlinux.org
- GitHub — nfzerox/VirtualMacOniPad (macOS VM under iPadOS, M1/M2 iPad, Hypervisor extraction)
  - https://github.com/nfzerox/VirtualMacOniPad
- The Apple Wiki — Dopamine (supported iOS ranges per chip generation)
  - https://theapplewiki.com/wiki/Dopamine
- securityonline.info — "Dopamine 3.0: First iOS 26 Jailbreak Is Here" (2026-08-08)
  - https://securityonline.info/dopamine-3-ios-26-jailbreak/
