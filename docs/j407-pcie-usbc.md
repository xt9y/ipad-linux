# J407 PCIe and USB-C topology

Target: iPad Air 5 Wi-Fi (`iPad13,16`, `J407AP`, T8103/M1).

This note records mappings that have survived a J407 ADT -> current mainline
Linux cross-check. Unresolved board wiring stays out of the DTS.

## APCIE / BCM4387

### J407 evidence

The public J407 Apple Device Tree contains:

- `/arm-io/apcie` and `/arm-io/dart-apcie0`;
- `pci-bridge0`;
- WLAN PCI function 0 (`AAPL,unit-string = 00000000`);
- Bluetooth PCIe function 1 (`AAPL,unit-string = 00000001`);
- BCM4387 identification for the combo module.

`pci-bridge0/function-perst` is an Apple function descriptor whose GPIO
argument decodes to **152**.

The J407 `/arm-io/wlan` `module-instance` value decodes from its little-endian
64-bit representation to:

```text
lycheea
```

Linux Broadcom firmware selection calls this module-instance codename the board
type, so the J407 nodes use:

```text
brcm,board-type = "apple,lycheea"
```

### Mainline T8103 match

Current mainline `t8103.dtsi` describes APCIE at `0x690000000`; port 0 uses
GPIO 152 as its active-low reset. That independently matches J407's
`function-perst` descriptor.

Current mainline Broadcom drivers define the BCM4387 PCI IDs used by the J407
combo module:

```text
Wi-Fi:     14e4:4433
Bluetooth: 14e4:5f71
```

These are not the BCM4378 endpoints used by the M1 Mac common board DTS, so the
Mac board nodes are not inherited.

### DTS policy

`dts/t8103-j407.dts` enables the T8103 PCIe host and describes the two devices
under `port00`:

```text
wifi@0,0       pci14e4,4433
bluetooth@0,1  pci14e4,5f71
```

The `wifi0` and `bluetooth0` aliases allow upstream m1n1 kboot to copy
runtime/device-specific data from the live Apple Device Tree, including radio
addresses and calibration data. Proprietary radio firmware is not redistributed
by this repository; `tools/check-j407-firmware.py` only inspects a local
user-supplied firmware tree for filenames current Linux may request.

## USB controller path

J407's public ADT contains exactly one USB DRD path:

```text
usb-drd0
dart-usb0
atc-phy0
```

Its controller, DART and IRQ values independently match the first T8103 USB path
in mainline (`0x382...`). The public J407 ADT does not contain the second
`usb-drd1` path used by some other T8103 products.

The board DTS therefore explicitly enables:

```text
dwc3_0
dwc3_0_dart_0
dwc3_0_dart_1
atcphy0
```

and explicitly disables the second `0x502...` T8103 USB path.

## CD3217 USB-C / Power Delivery controller

J407 places one USB-C/PD controller directly below Apple I2C0. Its public ADT
properties include:

```text
compatible: usbc,cd3217
I2C address: 0x38
port-number: 1
hpm-class-type: 10
usbc-fw-personality: HPM,42_R
```

Mainline T8103 already describes the parent Apple I2C0 controller at
`0x235010000`, and the mainline TPS6598x driver supports Apple's CD321x family
with:

```text
compatible = "apple,cd321x"
```

The conservative J407 board node is therefore:

```text
/soc/i2c@235010000/usb-pd@38
```

### IRQ policy

J407's Apple interrupt descriptor for this controller is not yet translated far
enough to emit a trustworthy Linux GPIO/IRQ specifier. The board DTS therefore
contains **no CD3217 interrupt property**.

This is intentional and testable: the upstream TPS6598x/CD321x driver has a
polling fallback when no IRQ is supplied. `scripts/check-j407-dtb.sh` fails if
an `interrupts` or `interrupt-parent` property appears before that mapping is
verified.

### Connector/mux graph policy

A complete USB-C graph would connect the CD3217 role/orientation state, the ATC
PHY Type-C lanes and DWC3 USB2/USB3 endpoints. A divergent research branch
contains such a graph, but it is **not part of the canonical J407 DTS yet**.

The SoC endpoint interfaces are known; the missing proof is the exact
J407-specific connector/lane/role routing. Until that survives an independent
ADT/live-hardware cross-check, the project keeps the minimal CD3217 node and
controller path instead of copying a Mac-style graph.

## Bring-up kernel

The first-boot kernel builds the relevant transport stack in:

```text
CONFIG_USB=y
CONFIG_USB_DWC3=y
CONFIG_USB_DWC3_DUAL_ROLE=y
CONFIG_USB_ROLE_SWITCH=y
CONFIG_TYPEC=y
CONFIG_PHY_APPLE_ATC=y
CONFIG_I2C=y
CONFIG_I2C_APPLE=y
CONFIG_TYPEC_TPS6598X=y
```

It also builds the verified BCM4387 PCIe Wi-Fi/Bluetooth drivers and SimpleDRM
into the image so early enumeration never depends on the storage device or a
module filesystem already working.

## First-boot observability

The static initramfs reports CPU, NVMe, USB, Type-C, PCI and framebuffer state.
It also scans PCI vendor/device IDs and explicitly distinguishes BCM4387 Wi-Fi
`14e4:4433` and Bluetooth `14e4:5f71`.

This lets a single serial capture distinguish:

- PCIe host failure;
- successful BCM4387 enumeration but missing radio firmware;
- USB controller enumeration;
- CD3217/Type-C registration;
- framebuffer availability;
- unrelated SMP/NVMe failures.
