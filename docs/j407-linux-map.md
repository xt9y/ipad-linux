# J407 Apple-ADT -> Linux T8103 map

Target: iPad Air 5 Wi-Fi (`iPad13,16`, `J407AP`, M1/T8103).

This file separates reusable T8103 SoC support from iPad-specific board work. `verified` means the public J407 ADT and current Linux T8103 description independently agree closely enough to use the Linux node as the starting point. `likely` means the blocks clearly correspond but board wiring/runtime data still needs verification. `unknown` means we should not enable it yet.

## Key rule

Use upstream `t8103.dtsi` for SoC topology. Do **not** include `t8103-jxxx.dtsi`: that file explicitly describes M1 Macs (J274/J293/J313/J456/J457) and contains Mac-specific USB-C, PCIe Wi-Fi/Bluetooth and board wiring.

## Mapping

| Block | J407 public ADT evidence | Linux T8103 node/support | Confidence | Action |
|---|---|---|---|---|
| CPUs | 8 main CPUs; J407 `/cpus` data follows T8103 CPU topology | `t8103.dtsi` has 4 Icestorm + 4 Firestorm CPUs | verified | Reuse topology; loader must patch spin-table release addresses |
| Architected timer | J407 exposes AIC timebase/timer data | root `arm,armv8-timer` node | verified SoC | Ensure CNTFRQ/CNTVOFF contract before kernel entry |
| AIC2 | `/arm-io` child compatible `aic,1`, `aic-version = 2`, `#main-cpus = 8`; first child reg starts at `0x3b100000` | `aic@23b100000`, compatible `apple,t8103-aic`, IRQ controller | verified | Reuse Linux AIC node; do not invent IRQs outside DT/ADT |
| UART0 | `/arm-io/uart0`, Samsung-style UART, child reg `0x35200000`, IRQ 605 | `serial@235200000`, compatible `apple,s5l-uart`, IRQ 605 | verified | Good early console candidate; current loader already discovers it through ADT ranges |
| PMGR | `/arm-io/pmgr`; T8103 public map puts it at physical `0x23b700000` | `power-management@23b700000`, compatible `apple,t8103-pmgr` | verified SoC | Reuse Linux PMGR/power-domain description; board runtime state still matters |
| DART / SIO | J407 contains `dart-sio` and SIO/NVMe-related properties | `sio_dart: iommu@235004000`, `apple,t8103-dart` | likely/strong | Compare stream IDs and SIO wiring before enabling storage |
| NVMe / ANS2 | J407 public ADT contains `nvme-linear-sq`, `nvme-interrupt-idx` and adjacent SIO/DART data | `nvme@27bcc0000`, compatible `apple,t8103-nvme-ans2`, plus SART/mailbox | likely/strong | Storage is a high-value next mapping target; verify J407 mailbox/SART/power domains |
| USB controller 0 | J407 contains `dart-usb0`; T8103 USB/ATC blocks are present in ADT | `dwc3_0: usb@382280000` plus two DARTs and `atcphy0` | likely | J407 has one external USB-C port; determine which T8103 controller/PHY path is physically routed |
| USB controller 1 | T8103 provides a second DWC3/ATC path used on some Macs | `dwc3_1` + `atcphy1` | unknown for J407 | Keep disabled until J407 ADT proves the path is used |
| PCIe Wi-Fi/BT | iPad has Wi-Fi/BT, but Mac `t8103-jxxx.dtsi` hardcodes PCIe devices/board types for Macs | T8103 PCIe controller/DART support exists | unknown board wiring | Do not copy Mac Wi-Fi/BT nodes. Derive J407 transport/chip/firmware data independently |
| Display / DCP | J407 ADT contains `dcp0-expert`, DCP ASC data, display DART/scaler and `dispext0,t8103` data | no directly reusable J407 board description in current mainline T8103 DTS | unknown / major port | Keep framebuffer/simplefb as first display target; native DCP later |
| GPU | M1/T8103 GPU is supported by the Asahi stack at SoC level | Linux/Asahi AGX support exists for T8103 | SoC reusable, board integration unknown | Defer until memory/IOMMU/firmware handoff is stable |
| Watchdog | J407 ADT exposes watchdog state; T8103 map has WDT at `0x23d2b0000` | Linux Apple watchdog support can be evaluated | likely | Current payload only disables discovered watchdogs in a constrained MMU-off context |

## SMP is now a concrete loader requirement

Current upstream `t8103.dtsi` uses:

```text
enable-method = "spin-table"
cpu-release-addr = <0 0>   # loader fills this
```

for all eight CPUs.

m1n1 does not obtain those release addresses from a static board file. It starts secondary CPUs into its own holding loop, maintains a per-CPU spin table, and patches each Linux CPU node's `cpu-release-addr` with the address of that CPU's spin-table target slot.

Therefore our choices are:

1. reuse/adapt m1n1's T8103 SMP implementation, or
2. implement equivalent J407 secondary-CPU bring-up and holding pens ourselves.

Option 1 is preferred unless J407 boot state makes it impossible.

## Runtime DT properties we already know must be patched

The J407 DTB template now intentionally contains fixed-size placeholders for:

```text
/memory@800000000/reg
/chosen/linux,initrd-start
/chosen/linux,initrd-end
```

The payload only patches them when the entry loader sets `BOOT_INFO_DTB_MUTABLE`.

Next runtime properties to support once SMP is implemented:

```text
/cpus/cpu@0/cpu-release-addr
/cpus/cpu@1/cpu-release-addr
/cpus/cpu@2/cpu-release-addr
/cpus/cpu@3/cpu-release-addr
/cpus/cpu@10100/cpu-release-addr
/cpus/cpu@10101/cpu-release-addr
/cpus/cpu@10102/cpu-release-addr
/cpus/cpu@10103/cpu-release-addr
```

## Immediate bring-up order

1. Boot CPU entry contract: EL/MMU/DAIF/timer/cache state.
2. Writable Linux DTB with RAM/initrd runtime patches.
3. Secondary CPU holding pens + `cpu-release-addr` patching.
4. AIC and PMGR state required for Linux/SMP.
5. ANS2/NVMe + SIO DART.
6. One verified J407 USB-C controller/PHY path.
7. Simple framebuffer if firmware leaves a usable framebuffer.
8. Native DCP/display, GPU, Wi-Fi/BT, audio and remaining peripherals.

## Sources

- Public J407 Apple Device Tree template:
  - https://github.com/hack-different/apple-knowledge/blob/main/_data/devices/iPad13,16.yaml
- Linux T8103 device tree:
  - https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/apple/t8103.dtsi
- Linux M1 Mac common board data (reference only, not for inclusion on J407):
  - https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/apple/t8103-jxxx.dtsi
- Asahi T8103 memory map:
  - https://asahilinux.org/docs/hw/soc/memmap/
- m1n1 Linux DT patch/SMP implementation:
  - https://github.com/AsahiLinux/m1n1/blob/main/src/kboot.c
  - https://github.com/AsahiLinux/m1n1/blob/main/src/smp.c
