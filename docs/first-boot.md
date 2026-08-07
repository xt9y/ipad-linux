# J407 first-boot validation

This document starts **after** a legitimate research mechanism is already able to execute m1n1 on the iPad Air 5 (`J407AP`). It does not describe or assume a secure-boot bypass.

## Artifact

The preferred artifact is produced by the GitHub Actions workflow `j407-first-boot-image`:

```text
j407-m1n1-linux.bin
```

It is an upstream-native m1n1 concatenated payload chain:

```text
m1n1.bin
+ t8103-j407.dtb
+ initramfs.cpio.gz
+ Image
```

The same artifact directory also contains the unpacked pieces, the kernel `.config`, `SOURCE_COMMITS`, SHA-256 hashes and the diagnostic `ipad-linux-stage2.bin`.

`SOURCE_COMMITS` records the exact revisions of:

```text
ipad-linux
mainline Linux
upstream m1n1
```

so a physical result can always be tied back to source.

## Primary observation channel

The first boot is designed around J407 UART0:

```text
physical address: 0x235200000
AIC IRQ:          605
Linux device:     ttySAC0
```

The Linux DT sets:

```text
stdout-path = "serial0:115200n8"
bootargs = "earlycon console=ttySAC0,115200 loglevel=8"
```

A firmware simple-framebuffer is a secondary/fallback signal only. UART remains the authoritative bring-up channel.

## Expected stages

### Stage 1: m1n1 accepts the payload chain

Success means m1n1 executes normally on J407, recognizes the J407 FDT, finds the compressed CPIO initramfs and recognizes the final ARM64 Linux Image.

A failure here means the problem is still before Linux: initial entry, m1n1 platform handling, payload identification or FDT preparation.

### Stage 2: Linux early console

The first decisive Linux marker is similar to:

```text
Linux version ...
```

At this point:

- m1n1 successfully reached its Linux `next_stage`;
- the kernel Image was accepted;
- the J407 FDT was usable enough for very early boot;
- UART0 earlycon is functional if the message is visible there.

If output stops after this point, preserve the complete serial log. AIC, timers, memory description, SMP or another early driver is then a more likely problem than payload packing.

### Stage 3: PID 1

The initramfs prints:

```text
ipad-linux early userspace
target: iPad Air 5 Wi-Fi / J407 / T8103
If you can read this on ttySAC0, Linux reached PID 1.
```

Reaching this marker is the first major project milestone: the device has executed mainline Linux through to userspace without needing storage as the root filesystem.

### Stage 4: automatic hardware summary

PID 1 mounts devtmpfs, procfs and sysfs and prints a compact inventory.

Expected full-SMP result:

```text
cpu_nodes=8
SMP=PASS
```

Expected ANS2 success:

```text
nvme_controllers=1
ANS2/NVMe=DETECTED
```

A usable simple framebuffer or DRM device produces at least one entry in `/sys/class/graphics` and:

```text
framebuffer/DRM=ENUMERATED
```

The final marker is:

```text
ipad-linux: FIRST_BOOT_DIAGNOSTICS_COMPLETE
```

After that PID 1 deliberately stays alive so the system does not reboot immediately.

## Analyze a captured log

Save the serial capture as, for example, `boot.log` and run:

```sh
python3 tools/analyze-first-boot.py boot.log
```

Machine-readable output:

```sh
python3 tools/analyze-first-boot.py --json boot.log
```

The analyzer reports:

- last recognized boot stage;
- SMP result and detected CPU count;
- NVMe result and controller count;
- graphics result;
- whether the diagnostic Stage 2 logged an AArch64 exception;
- whether Linux emitted a kernel panic.

## Failure taxonomy

### No m1n1 output

The problem is before this repository's Linux path. Do not modify Linux drivers based on this symptom.

### m1n1 output, no `Linux version`

Inspect payload detection, J407 FDT preparation, memory placement and m1n1 kboot logs.

### `Linux version`, then silence

Focus on early Linux state:

- AIC/timer initialization;
- usable-memory range;
- CPU release state;
- UART handoff;
- very early exceptions/panics.

### PID 1 appears, but `cpu_nodes < 8`

Linux boot itself works. Focus specifically on m1n1 secondary-CPU startup, spin-table release addresses and coherency.

### PID 1 appears, NVMe absent

Focus on the already-verified T8103 ANS2 path:

```text
ANS/NVMe: 0x27bcc0000, IRQ 590
ANS mbox:  0x277408000, IRQs 583-586
SART-ANS: 0x27bc50000
```

Then inspect RTKit firmware startup, SART/DART state and Linux driver messages rather than changing the static addresses.

### PID 1 appears, no graphics

This is not a Linux-boot failure. Check whether Apple's boot environment supplied a framebuffer. Native J407 DCP support is a later milestone.

## Diagnostic Stage 2 fallback

`ipad-linux-stage2.bin` is included in the artifact directory for execution environments which want the repository's explicit `boot_info v4` ABI rather than m1n1 kboot.

Its EL1/EL2 vectors record fatal exception state including:

```text
vector
CurrentEL
ESR_ELx
ELR_ELx
FAR_ELx
SPSR_ELx
```

A captured line beginning with:

```text
ipad-linux: AArch64 exception
```

should therefore be accompanied by enough syndrome state to diagnose the failing access offline.
