# J407 touch and audio bring-up

Target: iPad Air 5 Wi-Fi (`iPad13,16`, `J407AP`, T8103/M1).

This document records what can be reused from current Linux and what still needs an iPad-specific driver or binding. Nothing here enables a node merely because a similar Mac device exists.

## Touch: strong Apple Z2/HBPP relationship, but not drop-in

The public J407 Apple Device Tree exposes the internal touch controller as `multi-touch` below the SPI4 path.

Important J407 properties include:

```text
name: multi-touch
bootloader-type: HBPP
fdr-classes: GpC2 / multitouch-cal-container
interrupt-parent: aop-gpio
```

The GPIO function blobs decode to useful board facts:

```text
chip-select/enable GPIO: 24
interrupt configuration GPIO: 20
reset GPIO: 180
display-sync GPIOs: 207, 208
```

The interrupt parent is the J407 AOP GPIO controller (`AAPL,phandle = 67`, `name = aop-gpio`, compatible `gpio,t8101`), not the normal AP GPIO controller.

### Existing Linux code

Mainline Linux now has:

```text
drivers/input/touchscreen/apple_z2.c
Documentation/devicetree/bindings/input/touchscreen/apple,z2-multitouch.yaml
```

The driver is SPI-based and implements Apple's HBPP firmware command format. That is a strong protocol-level match with J407's `bootloader-type: HBPP`.

However, the current OF match table only accepts:

```text
apple,j293-touchbar
apple,j493-touchbar
```

and the binding is explicitly written around those Touch Bar devices.

### Why we do not enable it yet

Declaring the iPad panel as `apple,j293-touchbar` would make the DT compile, but it would encode a false hardware identity and hide real J407 differences.

At minimum J407 needs these questions answered first:

1. Does the SPI message/report layout match the existing Z2 driver after HBPP firmware boot?
2. How is the `aop-gpio` interrupt surfaced to Linux?
3. Is the reset GPIO controlled directly from AP GPIO or proxied through another firmware function?
4. Which calibration payload from `multitouch-cal-container` must be supplied before normal reports are valid?
5. Which X/Y ranges and orientation are reported by the firmware versus supplied by board data?
6. Does display synchronization on GPIOs 207/208 matter for ordinary touch reporting or only latency/power features?

### Current touch plan

The clean path is:

```text
J407 ADT / live measurements
        |
        +--> SPI4 controller description
        +--> AOP GPIO / interrupt support
        +--> J407-specific Z2/HBPP compatible/profile
        +--> calibration firmware handoff
        |
        v
Linux input subsystem
```

The likely kernel work is therefore an extension of the existing Apple Z2 driver/binding plus AOP interrupt support, not a touchscreen driver written from zero.

Touch should be attempted after UART/SMP/storage are stable, but it no longer needs to wait for native DCP/GPU support.

## Audio: T8103 transport exists, J407 endpoints are different

The J407 ADT contains a substantial Apple audio graph including:

```text
mcaCluster,t8103
alc,t8103
AOP PDM / low-power microphone paths
MAX98709 speaker/control nodes
speaker protection/calibration data
```

Examples visible in the public J407 tree include:

```text
compatible = "audio-control,max98709"
name = "audio-speaker-fh-left"
name = "audio-speaker-cn-right"
compatible = "alc,t8103"
compatible = "audio-aop-pdm2"
```

### Existing Linux code

Mainline already has the Apple Multi-Channel Audio controller infrastructure:

```text
sound/soc/apple/mca.c
Documentation/devicetree/bindings/sound/apple,mca.yaml
```

and T8103 contains the SoC-side MCA description. This means DMA/serial-audio transport does not need to be reverse engineered from scratch.

### Current endpoint gap

The J407 speaker chain is not the same endpoint setup used by the already-supported M1 Macs. In particular, J407 identifies `MAX98709` audio-control/speaker devices, and no current mainline `MAX98709` codec driver was found during this audit.

J407 also has ALC/AOP microphone paths which require more than simply enabling the MCA node.

So the split is:

```text
T8103 MCA transport          -> reusable
J407 MAX98709 speaker codec  -> missing / needs driver research
J407 speaker calibration     -> board-specific
J407 ALC/AOP microphones     -> board-specific / firmware-coupled
```

### Current audio plan

1. Keep audio disabled during first Linux boot.
2. Verify MCA/ADMAC/DART discovery from the live J407 ADT.
3. Map the exact speaker I2C/control transport and MAX98709 register protocol.
4. Determine whether an existing upstream Maxim codec is register-compatible; do not assume compatibility from the vendor/name alone.
5. Implement/bind the J407 speaker endpoints and calibration only after the codec path is understood.
6. Treat microphones/AOP low-power audio as a separate later milestone.

## Bring-up priority after first Linux boot

Current expected order:

```text
1. UART / earlycon / PID 1
2. SMP + AIC + timers
3. ANS2/NVMe
4. BCM4387 PCIe enumeration
5. USB0 core path
6. firmware framebuffer
7. touch SPI/AOP-GPIO/Z2-HBPP
8. native DCP/display + GPU
9. speaker audio / MAX98709
10. microphones / advanced AOP audio
```

Touch is placed ahead of native display because input reporting can in principle be validated from UART/sysfs/event data without a working native display stack.

## References

- Public J407 Apple Device Tree:
  - https://github.com/hack-different/apple-knowledge/blob/main/_data/devices/iPad13,16.yaml
- Mainline Apple Z2 touchscreen driver:
  - https://github.com/torvalds/linux/blob/master/drivers/input/touchscreen/apple_z2.c
- Mainline Apple Z2 binding:
  - https://github.com/torvalds/linux/blob/master/Documentation/devicetree/bindings/input/touchscreen/apple,z2-multitouch.yaml
- Mainline Apple MCA driver:
  - https://github.com/torvalds/linux/blob/master/sound/soc/apple/mca.c
- Mainline Apple MCA binding:
  - https://github.com/torvalds/linux/blob/master/Documentation/devicetree/bindings/sound/apple,mca.yaml
