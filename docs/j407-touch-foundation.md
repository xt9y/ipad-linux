# J407 touch transport foundation

Target: iPad Air 5 Wi-Fi (`iPad13,16`, J407, T8103/M1).

This note separates facts that can already be encoded safely from parts of the
multitouch path which still require a Linux extension or device-specific
firmware/power data.

## Apple Device Tree transport

J407 exposes the touchscreen under:

```text
/arm-io/spi4/multi-touch
```

The touchscreen node reports:

```text
compatible = hid-transport,spi
bootloader-type = HBPP
```

HBPP is important because the current mainline `apple_z2` touchscreen driver
already implements Apple's HBPP/Z2 firmware upload and touch packet protocol.
This is strong protocol reuse evidence, but it is not permission to identify the
J407 touchscreen as one of the existing Mac Touch Bar compatibles.

## SPI4 controller

The J407 Apple Device Tree describes its `spi4` controller with:

```text
child address  0x35110000
physical       0x235110000
size           0x4000
AIC IRQ        618
clock-id       380
clock-gate     53
```

The low `arm-io` aperture maps this child address by adding `0x200000000`,
which gives the physical address above.

Current mainline T8103 has Apple SPI controller nodes at the neighboring
addresses but no node at `0x235110000`. The T8103 PMGR description already has
`ps_spi4`, so the missing controller does **not** require inventing a new power
domain.

The controller input clock is intentionally still unresolved. Existing T8103
SPI instances use different fixed input clocks, and Apple `clock-id` values are
not sufficient evidence to select 120 MHz vs 200 MHz for SPI4. No SPI4 DTS node
should be enabled until that rate is established from trustworthy data.

## Normal AP GPIO functions

The generic Apple ADT `function-*` decoder in this repository resolves the
following touchscreen functions through the normal J407 AP GPIO controller:

```text
chip select        GPIO 24
reset              GPIO 180
display-sync       GPIO 207
display-sync1      GPIO 208
```

These are board data and must not be replaced with the J293 Touch Bar pins.

## AOP GPIO interrupt controller

The touchscreen interrupt does not use the normal AP GPIO controller. Its
`interrupt-parent` is J407 ADT phandle 67 (`aop-gpio`).

That controller is another Apple `gpio,t8101` block:

```text
physical address       0x24a820000
size                   0x4000
pins                   42
AIC parent IRQs        268..274
supported irq groups   4, 5, 6
```

The touch node selects GPIO pin 20. Apple's second interrupt cell is an
Apple-specific value and must not be copied directly into Linux
`IRQ_TYPE_*` flags.

### Why vanilla mainline is not sufficient yet

Mainline's `pinctrl-apple-gpio` driver already supports the register layout,
multiple GPIO-controller instances and up to seven parent interrupts. However,
it currently assumes parent IRQ index `i` maps to hardware IRQ group `i`, and
new GPIO IRQs are initially assigned to hardware group 0.

J407's AOP GPIO advertises only groups 4, 5 and 6 as supported. Instantiating the
controller without addressing that mismatch would therefore program an invalid
interrupt group for the touchscreen.

The intended minimal Linux extension is an optional DT array mapping listed
parent IRQs to their actual hardware group numbers. Existing boards keep the
current 0..N-1 behavior when the property is absent.

For J407 the useful parent subset can then be represented as:

```text
AIC IRQs          272, 273, 274
hardware groups   4,   5,   6
```

No AOP MMIO implementation needs to be invented; the existing Apple GPIO driver
can remain the hardware driver once the group mapping is explicit.

## Secondary GPIO controller used by touch clock enable

`function-clock_24MHz_enable` references another `gpio,t8101` controller
(J407 ADT phandle 68):

```text
physical address       0x23d1f0000
size                   0x4000
pins                   23
AIC parent IRQs        330..336
supported irq groups   4, 5, 6
```

The touch function references pin 0 of this controller. This block can use the
same explicit IRQ-group mechanism if interrupt support is needed; for a simple
output GPIO only the ordinary pinctrl/GPIO functionality is required.

## Power sequencing remains unresolved

The touchscreen also exposes LDO, buck and analog power functions through a
J407 SMC/PMU node. Those functions are not yet mapped to Linux regulators.
Do not convert them into guessed GPIOs or fixed regulators.

A first physical boot may inherit enough display/touch power state from iBoot to
observe more behavior, but a final suspend/resume-safe driver must model the
power sequence explicitly.

## Linux Z2 driver compatibility

Current mainline `apple_z2` already understands the HBPP firmware command format
used by Apple's Z2 family. Its binding currently lists known Touch Bar devices,
including `apple,j293-touchbar`; J407 must receive its own compatible/board
profile after the protocol and firmware image are confirmed.

The upstream J293 DTS is a structural reference only. It shows the expected
shape of an Apple Z2 device:

```text
Apple SPI controller
manual CS GPIO
reset GPIO
GPIO interrupt
firmware-name
screen dimensions
```

Every J407 value in that shape must come from J407 evidence.

## Firmware path

Asahi's firmware tooling already parses Apple's `Multitouch.im4p` (`mtfw`) and
converts known HBPP/Z2 firmware descriptions into the `Z2FW` container consumed
by Linux.

The current extractor classifies known Mac trackpad/Touch Bar device keys. J407
may need an additional touchscreen device class once its actual
`Multitouch.im4p` is inspected. Proprietary firmware must be extracted locally
from a user-supplied Apple firmware source and is not committed to this
repository.

## Safe implementation order

1. Extend Apple GPIO DT/driver support for explicit hardware IRQ-group mapping.
2. Compile-test that patch against current mainline and preserve existing-board
   default behavior.
3. Add J407 AOP GPIO controller instances using only verified MMIO/IRQ/pin data.
4. Determine SPI4's real input clock.
5. Add the missing T8103 SPI4 controller node.
6. Determine the J407 touch interrupt trigger semantics.
7. Add a J407-specific `apple_z2` compatible/profile.
8. Extract/convert J407 multitouch firmware locally and determine panel size and
   calibration.
9. Model SMC/PMU power sequencing before claiming production suspend/resume.
