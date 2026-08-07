# J407 Apple-ADT -> Linux T8103 map

Target: iPad Air 5 Wi-Fi (`iPad13,16`, `J407AP`, M1/T8103).

This file separates reusable T8103 SoC support from iPad-specific board work. `verified` means the public J407 ADT and current Linux T8103 description independently agree closely enough to use the Linux node as the starting point. `likely` means the blocks clearly correspond but board wiring/runtime data still needs verification. `unknown` means we should not enable it yet.

## Key rule

Use upstream `t8103.dtsi` for SoC topology. Do **not** include `t8103-jxxx.dtsi`: that file explicitly describes M1 Macs (J274/J293/J313/J456/J457) and contains Mac-specific USB-C, PCIe Wi-Fi/Bluetooth and board wiring.

## Mapping

| Block | J407 public ADT evidence | Linux T8103 node/support | Confidence | Action |
|---|---|---|---|---|
| CPUs | 8 main CPUs; J407 `/cpus` data follows T8103 CPU topology | `t8103.dtsi` has 4 Icestorm + 4 Firestorm CPUs | verified | Reuse topology; m1n1 patches spin-table release addresses |
| Architected timer | J407 exposes AIC timebase/timer data | root `arm,armv8-timer` node | verified SoC | Ensure CNTFRQ/CNTVOFF contract before kernel entry |
| AIC2 | `/arm-io` child compatible `aic,1`, `aic-version = 2`, `#main-cpus = 8`; first child reg starts at `0x3b100000` | `aic@23b100000`, compatible `apple,t8103-aic`, IRQ controller | verified | Reuse Linux AIC node; do not invent IRQs outside DT/ADT |
| UART0 | `/arm-io/uart0`, Samsung-style UART, child reg `0x35200000`, IRQ 605 | `serial@235200000`, compatible `apple,s5l-uart`, IRQ 605 | verified | Enabled in J407 DTS as early console |
| PMGR | `/arm-io/pmgr`; T8103 public map puts it at physical `0x23b700000` | `power-management@23b700000`, compatible `apple,t8103-pmgr` | verified SoC | Reuse Linux PMGR/power-domain description; board runtime state still matters |
| DART / SIO | J407 contains `dart-sio` and SIO/NVMe-related properties | `sio_dart: iommu@235004000`, `apple,t8103-dart` | likely/strong | Compare stream IDs and SIO wiring before relying on SIO peripherals |
| ANS mailbox | J407 ANS register tuple 0 begins at child `0x77400000`; its interrupt list includes 583/584/585/586 | `ans_mbox: mbox@277408000` is inside the same translated ANS window and uses IRQs 583-586 | verified | Reuse T8103 mailbox/RTKit description |
| NVMe / ANS2 | J407 ANS tuple 3 is child `0x7bcc0000`, size `0x60000`; `nvme-interrupt-idx = 4` selects IRQ 590 | `nvme@27bcc0000`, size `0x40000`, IRQ 590, compatible `apple,t8103-nvme-ans2`; ANS reg `0x277400000` | verified addresses/IRQ | Reuse T8103 ANS2 node; mainline uses conservative subranges of Apple ADT windows |
| SART-ANS | J407 `sart-ans` is child `0x7bc50000`, size `0x10000`, `sart-version = 2` | `sart@27bc50000`, size `0x10000`, compatible `apple,t8103-sart` | verified | Reuse T8103 SART node |
| USB controller 0 | J407 contains `usb-drd0` and `dart-usb0`; T8103 USB/ATC blocks are present in ADT | `dwc3_0: usb@382280000` plus DARTs and `atcphy0` | likely | J407 has one external USB-C port; verify the exact controller/PHY and DART mapping before enabling board routing |
| USB controller 1 | T8103 provides a second DWC3/ATC path used on some Macs | `dwc3_1` + `atcphy1` | unknown for J407 | Keep board routing absent until J407 ADT proves the path is used |
| PCIe Wi-Fi/BT | iPad has Wi-Fi/BT, but Mac `t8103-jxxx.dtsi` hardcodes PCIe devices/board types for Macs | T8103 PCIe controller/DART support exists | unknown board wiring | Do not copy Mac Wi-Fi/BT nodes. Derive J407 transport/chip/firmware data independently |
| Display / DCP | J407 ADT contains `dcp0-expert`, DCP ASC data, display DART/scaler and `dispext0,t8103` data | no directly reusable J407 board description in current mainline T8103 DTS | unknown / major port | Use m1n1-patched firmware simple-framebuffer first; native DCP later |
| GPU | M1/T8103 GPU is supported by the Asahi stack at SoC level | Linux/Asahi AGX support exists for T8103 | SoC reusable, board integration unknown | Defer until memory/IOMMU/firmware handoff is stable |
| Watchdog | J407 ADT exposes watchdog state; T8103 map has WDT at `0x23d2b0000` | Linux Apple watchdog support can be evaluated | likely | Diagnostic Stage 2 only disables discovered watchdogs in a constrained MMU-off context |

## First-boot path

The preferred first-boot path uses upstream m1n1's native payload scanner/kboot implementation rather than forcing the diagnostic Stage 2 into the critical path.

The packed image is ordinary upstream-supported concatenation:

```text
m1n1.bin
  + t8103-j407.dtb
  + initramfs.cpio.gz
  + Linux Image
```

The DTB is directly recognized as FDT. The gzip initramfs is decompressed by m1n1 and then recognized as CPIO. The final uncompressed ARM64 `Image` is deliberately last because m1n1 can recognize it but cannot infer the end of a size-less inline kernel in order to continue scanning beyond it.

m1n1 then starts secondary CPUs, prepares the Linux FDT and schedules the kernel through its normal kboot/`next_stage` path. `scripts/pack-m1n1-j407.py` validates and creates this exact chain, and `.github/workflows/j407-image.yml` builds the complete artifact.

The custom `ipad-linux-stage2.bin` remains useful for controlled diagnostics and for future entry mechanisms that want a versioned `boot_info` ABI rather than invoking m1n1 kboot directly.

## Firmware framebuffer

The J407 board DTS provides a disabled `simple-framebuffer` placeholder under `/chosen`, following the same shape expected by m1n1 kboot. If Apple's boot arguments contain a valid framebuffer, m1n1 patches its physical range, width, height, stride and format before Linux entry. If no framebuffer is available, it stays disabled and UART remains the primary bring-up console.

This gives us a low-risk visual fallback without claiming native J407 DCP support.

## SMP

Current upstream `t8103.dtsi` uses:

```text
enable-method = "spin-table"
cpu-release-addr = <0 0>   # loader fills this
```

for all eight CPUs.

m1n1 starts secondary CPUs into its own holding loop, maintains a per-CPU spin table, and patches each Linux CPU node's `cpu-release-addr` with the address of that CPU's spin-table target slot. The repository also has a compile-checked m1n1 adapter implementing the equivalent `boot_info v4` contract for the diagnostic Stage 2 path.

## Runtime DT properties in the diagnostic Stage 2 path

The J407 DTB template contains fixed-size placeholders for:

```text
/memory@800000000/reg
/chosen/linux,initrd-start
/chosen/linux,initrd-end
```

and mainline `t8103.dtsi` contains the eight `cpu-release-addr` placeholders. The Stage 2 payload patches these only when the entry loader explicitly marks the DTB mutable and provides validated runtime data.

For the native m1n1 first-boot path, upstream `kboot_prepare_dt()` performs the corresponding Linux FDT runtime preparation.

## Immediate bring-up order

1. Produce a reproducible `j407-m1n1-linux.bin` from current upstream m1n1 + mainline Linux.
2. UART0 earlycon and PID1 initramfs output.
3. SMP/AIC/timer stability through m1n1 kboot.
4. Firmware simple-framebuffer if iBoot leaves a usable video buffer.
5. ANS2/NVMe using the verified T8103 addresses/IRQ/SART path.
6. Verify the single J407 USB-C controller/PHY/DART route.
7. Native DCP/display, then GPU.
8. J407-specific Wi-Fi/BT, touch, audio and remaining peripherals.

## Sources

- Public J407 Apple Device Tree template:
  - https://github.com/hack-different/apple-knowledge/blob/main/_data/devices/iPad13,16.yaml
- Linux T8103 device tree:
  - https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/apple/t8103.dtsi
- Linux M1 Mac common board data (reference only, not for inclusion on J407):
  - https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/apple/t8103-jxxx.dtsi
- Asahi T8103 memory map:
  - https://asahilinux.org/docs/hw/soc/memmap/
- m1n1 payload/kboot/SMP implementation:
  - https://github.com/AsahiLinux/m1n1/blob/main/src/payload.c
  - https://github.com/AsahiLinux/m1n1/blob/main/src/kboot.c
  - https://github.com/AsahiLinux/m1n1/blob/main/src/smp.c
