# Physical J407 validation — 2026-08-13

This document records the first physical validation pass performed on the target
iPad Air 5 Wi-Fi. Device-unique identifiers are deliberately omitted.

## Target actually tested

```text
ProductType:      iPad13,16
HardwareModel:    J407AP
Model:            iPad Air (5th generation, Wi-Fi)
SoC:              Apple M1 / T8103
CPID:             0x8103
BDID:             0x10
CPUArchitecture:  arm64e
iPadOS:           26.5
Build:            23F77
```

The physical device therefore matches the repository target exactly.

## Host

The host was an Apple-silicon Mac running Fedora Asahi Linux:

```text
architecture: aarch64
kernel:       Asahi Linux, 16 KiB pages
Python:       3.14.6
```

The repository hardware-test kit verified successfully before any physical
probing. The host preflight reported the expected `m1n1_usb_devices=none` because
m1n1 had not been started on the iPad.

## Normal iPadOS USB enumeration

With iPadOS running normally, Linux enumerated:

```text
05ac:12ab Apple, Inc. iPad
```

This confirms the USB-C cable and host controller path are suitable for further
bring-up work.

## Apple Recovery enumeration

After entering Apple Recovery, Linux enumerated:

```text
05ac:1281 Apple Mobile Device [Recovery Mode]
```

`irecovery -q` independently confirmed:

```text
CPID:     0x8103
BDID:     0x10
MODE:     Recovery
PRODUCT:  iPad13,16
MODEL:    j407ap
```

No device-unique ECID, serial number or nonce is stored in this repository.

## Recovery boot firmware observed on the real device

The physical Recovery environment reported:

```text
Microkernel iBoot for j407
Board 0x10 (j407ap) / Rev 0x5
BUILD_TAG:   mBoot-18000.120.36
BUILD_STYLE: RELEASE
```

The interactive recovery command prompt was reachable over USB. Local
`libirecovery` commands worked, but legacy `getenv` requests such as
`getenv auto-boot` and `getenv boot-stage` returned no value on this mBoot
release. This is recorded as an observation only; it is not interpreted as a
boot-policy bypass.

## Matching 26.5 restore firmware

The matching `23F77` restore IPSW was inspected offline. Its BuildManifest has
three J407 identities relevant to this device family:

```text
Customer Erase Install (IPSW)
Customer Upgrade Install (IPSW)
Recovery Customer Install
```

For J407 the manifest identifies:

```text
ApBoardID:        0x10
ApChipID:         0x8103
ApSecurityDomain: 0x01
```

The matching boot components include:

```text
Firmware/dfu/iBSS.j407.RELEASE.im4p
Firmware/dfu/iBEC.j407.RELEASE.im4p
Firmware/all_flash/LLB.j407.RELEASE.im4p
Firmware/all_flash/iBoot.j407.RELEASE.im4p
Firmware/all_flash/DeviceTree.j407ap.im4p
kernelcache.release.ipad13b
```

The observed iBSS, iBEC, LLB and iBoot containers all identify the same
`mBoot-18000.120.36` build family as the physical Recovery environment.

## Trust and personalization findings

The BuildManifest marks the relevant boot and restore objects as trusted. In the
Recovery Customer Install identity, both iBSS and iBEC are explicitly marked:

```text
Personalize = True
```

Their restore rules depend on Image4/security/production-state inputs. This is
consistent with an Apple-personalized Image4 restore chain rather than a generic
unsigned-payload slot.

## NeRD / RecoveryOTA findings

The J407 Recovery Customer Install identity contains:

```text
AllowNeRDBoot = True
NeRDEpoch = 0
RestoreAttestationMode = 6
```

Its variant contents label many boot/firmware objects as
`RecoveryOTAProduction`.

The identity does **not** contain a `PermitNeRDPivot` value, nor did this pass
find Mac-style `LocalPolicy`, `CustomOS`, `coih`, `lpnh`, `smb0`, `smb1`,
`smb2` or `nsih` fields.

Public TSS implementations model `NeRDEpoch` and an optional
`PermitNeRDPivot` as Apple TSS request inputs alongside an Image4 ticket. The
physical/manifest evidence therefore supports treating NeRD as an
Apple-authorized restore/recovery mechanism, not as evidence that J407 accepts
arbitrary unsigned m1n1/Linux payloads.

## What is physically verified now

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

## Current hard gate

The remaining gate before the existing m1n1/Linux test kit can be exercised is
still:

```text
legitimate/authorized J407 early boot entry
        -> execute m1n1
        -> m1n1 USB proxy
        -> dump live ADT
        -> boot Linux Image + J407 DTB + initramfs
```

No public owner-configurable iPad equivalent of the Apple-silicon Mac
LocalPolicy/CustomOS mechanism was established by this validation pass.
Likewise, this document does not claim or depend on a BootROM/iBoot bypass.

## Theoretical feasibility

Nothing found in this physical pass invalidates the Linux side of the project.
T8103 already runs Linux on Apple-silicon Macs, the J407 board-specific software
stack is prepared, and the real device identity matches all assumptions used by
the build.

Therefore a native Linux boot remains technically plausible **if** a legitimate
mechanism can hand sufficiently early machine control to m1n1 (or an equivalent
loader). That condition is currently unresolved, so physical Linux boot remains
unproven.
