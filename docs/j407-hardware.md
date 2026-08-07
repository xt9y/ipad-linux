# J407 / iPad Air 5 hardware notes

This file records board facts that have been verified against public J407 Apple Device Tree data and, where possible, cross-checked against Asahi/m1n1 T8103 knowledge.

## Identity

- Product: iPad Air (5th generation) Wi-Fi
- ProductType: `iPad13,16`
- Target/board: `J407` / `J407AP`
- Model: `A2588`
- SoC: Apple M1 / T8103
- CPID: `0x8103`
- BDID: `0x10`
- CPU count reported by J407 `arm-io` data: 8 main CPUs

## Public Apple Device Tree source

A public extracted J407 ADT template is available in the `hack-different/apple-knowledge` dataset. Its root identifies `J407DEV`, `iPad13,16`, and `AppleARM`, and exposes the board's `arm-io` hierarchy.

The template is useful for topology and mostly-static hardware data. It is **not** a substitute for the live boot ADT: properties such as the actual RAM `reg` value and runtime memory carveouts are filled or modified during boot.

## `arm-io` address translation

J407's `arm-io` node has a `ranges` table. The first range is:

```text
child bus:  0x000000000
parent:     0x200000000
size:       0x100000000
```

Therefore many child peripheral registers are bus-relative and require translation. For example:

```text
/arm-io/uart0 reg child address: 0x35200000
arm-io translation:            +0x200000000
physical address:               0x235200000
```

That result independently matches Asahi's published T8103 UART0 physical address.

`src/adt/adt_reg.c` implements bounded `reg`/`ranges` resolution so platform code should prefer the live ADT instead of hardcoded physical addresses.

## UART0

The J407 ADT identifies `/arm-io/uart0` as:

- compatible: `uart-1,samsung`
- `boot-console` present
- interrupt: 605
- bus-relative register address: `0x35200000`
- register size: `0x4000`
- translated physical address: `0x235200000`
- child node: `debug-console`

m1n1 uses the same Samsung-style UART block and discovers its base from the ADT. Its TX path waits for the transmit-buffer-empty bit in `UTRSTAT` and writes to `UTXH`.

The project implements the same conservative strategy in `src/debug/uart.c`: it reuses the ADT-discovered boot UART only when the caller reports physical-address execution with the MMU off. It does not reprogram clocks or power domains.

## Apple Interrupt Controller

The J407 ADT identifies an AIC v2 interrupt controller under `arm-io`, compatible with `aic,1`, with 8 main CPUs. The first register region has bus-relative base `0x3b100000` and size `0xc000`, which translates through the first `arm-io` range to physical `0x23b100000`. This agrees with published T8103 mappings.

The project currently discovers this address but does **not** initialize or mutate the AIC. Correct AIC2 initialization requires additional ADT properties and should follow the Linux/m1n1 implementation.

## Other SoC blocks

The live-discovery layer currently attempts to resolve these paths without touching the hardware:

```text
/arm-io/uart0
/arm-io/aic
/arm-io/pmgr
/arm-io/gpio
/arm-io/wdt
```

Missing paths are non-fatal. The live ADT remains authoritative.

## RAM

Do not hardcode the Mac M1 RAM map or assume the entire DRAM aperture is usable. The public J407 template intentionally has an unpopulated memory `reg` field. A real entry loader must provide the live physical RAM range and preserve/respect firmware carveouts.

## Linux device tree strategy

Upstream Linux already contains `t8103.dtsi` plus several M1 board DTS files. J407 should follow the same structure:

```text
t8103.dtsi            # reusable M1 SoC description
        +
t8103-j407.dts        # iPad Air 5 board description
        +
runtime patches       # RAM, carveouts, firmware-derived values
```

This is safer and more maintainable than attempting a blind one-to-one Apple-ADT-to-FDT conversion.
