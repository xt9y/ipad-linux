# ipad-linux

Research and bring-up project for Linux on the **iPad Air (5th generation) Wi-Fi**.

## Target

```text
ProductType: iPad13,16
BoardConfig: J407AP
Model:       A2588
SoC:         Apple M1 / T8103
CPID:        0x8103
BDID:        0x10
```

T8103 already has substantial upstream Linux/Asahi and m1n1 support. The project therefore reuses the SoC implementation and adds only J407-specific board data that can be independently verified.

## Boot architecture

The unresolved part is still the **initial iPad boot entry**. This repository does not assume that a public BootROM/iBoot bypass exists.

Once a legitimate research mechanism can execute m1n1, the preferred first-boot path is deliberately small:

```text
future J407 early-boot execution
        |
        v
upstream m1n1
        |
        | native concatenated payload scanner / kboot
        v
mainline Linux Image + t8103-j407.dtb + initramfs
        |
        v
PID 1 diagnostic userspace
```

The build produces a single payload-chain artifact:

```text
j407-m1n1-linux.bin =
    m1n1.bin
  + t8103-j407.dtb
  + initramfs.cpio.gz
  + Image
```

The uncompressed Linux `Image` is last, matching upstream m1n1's payload rules.

A separate freestanding `ipad-linux-stage2.bin` remains in the repository for diagnostics, alternative entry mechanisms and low-level experiments. It uses the versioned `boot_info v4` ABI and is **not required** for the preferred first Linux boot through m1n1 kboot.

## What is already implemented

- [x] Exact J407/T8103 target identity
- [x] Freestanding, relocation-free AArch64 diagnostic Stage 2
- [x] Bounded Apple Device Tree parser and `reg`/`ranges` translation
- [x] J407 live discovery for UART/AIC/PMGR/watchdog/storage/USB/display paths
- [x] Live ADT clock resolver (`clock-id >= 256` -> `/arm-io/clock-frequencies`)
- [x] EL1/EL2 exception vectors with ESR/ELR/FAR/SPSR diagnostics
- [x] ARM64 Linux Image/header and placement validation
- [x] FDT builder and fixed-size runtime patching
- [x] `boot_info v4` handoff ABI
- [x] Compile-checked m1n1 SMP/next-stage adapter
- [x] T8103 eight-core spin-table release mapping
- [x] J407 UART0 early console DTS
- [x] Mainline-kernel configuration for Apple mailbox/RTKit/SART/DART/ANS2 NVMe
- [x] Verified J407 USB0/DART/ATC path
- [x] Conservative CD3217 USB-C/PD polling node
- [x] J407 PCIe port00 + BCM4387 Wi-Fi/BT PCI identities
- [x] J407 AOP/NUB GPIO foundation with compile-tested non-zero IRQ-group patch
- [x] Z2/HBPP touch firmware validator; proprietary firmware is not shipped
- [x] Minimal static ARM64 initramfs with `/init`
- [x] Automatic first-boot inventory for SMP/NVMe/USB/Type-C/PCIe/WLAN/BT/graphics/input/sound
- [x] PID-1 compact status page mirrored to `tty0` when firmware framebuffer works
- [x] Mainline `Image` + J407 DTB + initramfs cloud build
- [x] Self-contained m1n1/Linux payload-chain packer
- [x] Self-verifying physical hardware-test artifact
- [x] Mac/Linux host preflight, live ADT dumper, log analyzer and report builder
- [ ] Execute m1n1 on physical J407
- [ ] Perform the first physical proxy/ADT/Linux test below
- [ ] Use the resulting live ADT/logs to finish touch clock/IRQ/power details
- [ ] Bring up native display/DCP and GPU after first-boot validation
- [ ] Complete J407 audio endpoints and remaining device-specific peripherals

## Repository layout

```text
.github/workflows/        cloud build/compatibility gates
docs/                     boot and J407 hardware research
dts/t8103-j407.dts        J407 Linux board DTS
initramfs/init.c           first-boot PID 1 + hardware inventory
integration/m1n1/          m1n1 adapter + live ADT dump helper
kernel/                    J407 config and kernel patch series
scripts/                   initramfs + payload-chain builders
src/
  adt/                     Apple Device Tree parser/clock/function helpers
  arch/aarch64/            exception/system helpers
  boot/                    Linux/FDT/handoff contracts
  debug/                   debug sink + UART
  memory/                  range helpers
  payload/                 diagnostic Stage 2
  platform/j407/           J407-specific discovery/contracts
tests/                     host-side parser/ABI/layout/tool tests
tools/                     ADT inspector + hardware-test/report tooling
```

## Build the diagnostic Stage 2

Requirements: `clang`, `ld.lld`, `llvm-objcopy`, and `llvm-objdump`.

```sh
make
```

Outputs:

```text
build/payload.elf
build/payload.bin
build/payload.dis
```

The payload is built position-independently, initializes BSS itself, includes its bootstrap stack in the raw image, and CI rejects runtime AArch64 relocations.

## Cloud first-boot image

The `j407-first-boot-image` GitHub Actions workflow checks out **current upstream m1n1** and **current mainline Linux**, applies the small J407 kernel patch series, then builds a self-verifying hardware-test kit containing:

```text
Image
t8103-j407.dtb
initramfs.cpio.gz
m1n1.bin
ipad-linux-stage2.bin
j407-m1n1-linux.bin
j407-m1n1-linux.manifest.txt
linux.config
TARGET
SOURCE_COMMITS
SHA256SUMS
HARDWARE_TEST.md
host-preflight.py
verify-first-boot-kit.py
analyze-first-boot.py
build-hardware-report.py
dump_live_adt.py
```

CI runs the same `verify-first-boot-kit.py` that the physical tester runs after downloading the artifact.

## Current hardware confidence

Independently matched between the public J407 Apple Device Tree and Linux T8103 support:

```text
UART0        0x235200000, IRQ 605
AIC          0x23b100000
PMGR         0x23b700000
ANS window   0x277400000
ANS2 NVMe    0x27bcc0000, IRQ 590
SART-ANS     0x27bc50000
USB0         0x382280000, IRQ 777
USB0 DARTs   0x382f00000 / 0x382f80000
BCM4387 WLAN PCI 14e4:4433
BCM4387 BT   PCI 14e4:5f71
AOP GPIO     0x24a820000, 42 pins, supported IRQ groups 4/5/6
NUB GPIO     0x23d1f0000, 23 pins, supported IRQ groups 4/5/6
SPI4         0x235110000, IRQ 618, clock-id 380
```

The **live** Apple Device Tree remains authoritative for runtime memory, firmware carveouts and runtime-filled clock values. In particular, SPI4 clock-id 380 maps to live `/arm-io/clock-frequencies[124]`; the public template contains a placeholder rather than a trustworthy runtime frequency.

## Project rules

1. Never invent MMIO addresses, IRQs, stream IDs, device-tree data or boot-policy behavior.
2. Reuse upstream T8103 support where J407 evidence matches it.
3. Do not import an M1-Mac board DTS as if it were J407.
4. Keep the unresolved initial secure-boot/entry problem separate from Linux bring-up.
5. Prefer fail-closed runtime validation over trusting loader metadata.
6. Add hardware writes only when the register block and required power/clock state are verified.

## Current blocker

The software side now builds a reproducible J407 m1n1/Linux hardware-test kit. The major unresolved gate is **getting sufficiently early, legitimate code execution on the physical iPad so m1n1 can run**. No public T8103/J407 BootROM or iBoot path is assumed by this project.

---

# Physical hardware test: exact step-by-step procedure

This section is the user procedure to follow next. A more detailed copy is also included in every Actions artifact as `HARDWARE_TEST.md`.

## Step 0 — understand the stopping point

You can do **Steps 1–5 immediately**. Step 6 is a hard gate.

This repository does **not** currently provide the mechanism that first executes unsigned m1n1 on J407. Do not invent a DFU/recovery command and do not treat `j407-m1n1-linux.bin` like an Apple-signed restore image.

If you do not independently have a legitimate J407 mechanism that already starts m1n1, stop at Step 6 and preserve the device/firmware for later research.

## Step 1 — hardware you need

Use:

- the iPad Air 5 Wi-Fi (`iPad13,16` / `J407AP`);
- an external **Mac or native Linux PC**;
- a known-good USB-C data cable;
- preferably >50% iPad battery and a current backup.

### Can I use iPhone -> iPad instead of a PC?

**No, not for this bring-up workflow.** The host must run the m1n1 Python proxyclient and access USB CDC serial devices directly. Use macOS or Linux.

### Do I need a UART adapter?

**Not for the first physical test.** First verify m1n1 USB proxy mode and dump the live ADT. For Linux, the firmware framebuffer/`tty0` can show a compact PID-1 status page if it survives. Do not solder/probe unknown UART pads; no verified J407 physical UART pinout is published by this project.

## Step 2 — record the iPad software identity

On the iPad:

```text
Settings -> General -> About
```

Record:

- Model Name;
- iPadOS Version;
- build number (tap the version if necessary).

If the device is on the public final **iPadOS 26.5**, the expected public build is `23F77`, but use the value the iPad itself displays.

Do **not** report serial number, Apple ID, passcode or trusted-device codes.

## Step 3 — download the latest successful test kit

On GitHub:

```text
Repository -> Actions -> j407-first-boot-image
```

Choose the latest **successful** run on `ipad-air-5`, download the artifact `j407-first-boot-image`, and unzip it.

Enter the directory:

```sh
cd /path/to/j407-first-boot-image
```

## Step 4 — verify every byte before hardware use

Run:

```sh
python3 verify-first-boot-kit.py .
```

Required final line:

```text
J407 first-boot kit: VERIFIED
```

Then verify SHA-256 separately.

macOS:

```sh
shasum -a 256 -c SHA256SUMS
```

Linux:

```sh
sha256sum -c SHA256SUMS
```

All entries must be `OK`.

Check target/revisions:

```sh
cat TARGET
cat SOURCE_COMMITS
```

Confirm at minimum:

```text
product_type=iPad13,16
board_config=J407AP
model=A2588
cpid=0x8103
bdid=0x10
```

If anything differs, **do not use the artifact**.

## Step 5 — prepare the Mac/Linux host

### macOS

```sh
brew install python git picocom
cd ~
git clone --recursive https://github.com/AsahiLinux/m1n1.git
cd m1n1
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install pyserial construct
```

### Debian/Ubuntu Linux

```sh
sudo apt update
sudo apt install -y python3 python3-venv git picocom
cd ~
git clone --recursive https://github.com/AsahiLinux/m1n1.git
cd m1n1
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install pyserial construct
```

Run the project preflight:

```sh
python3 /path/to/j407-first-boot-image/host-preflight.py \
  --artifact-dir /path/to/j407-first-boot-image \
  --m1n1 ~/m1n1
```

Before m1n1 is actually running, `m1n1_usb_devices=none` is expected.

## Step 6 — HARD STOP: obtain legitimate m1n1 execution on J407

The next requirement is external to this repository:

```text
J407 early boot -> execute m1n1
```

This repo does not currently provide that entry step.

Do not substitute an unrelated Mac custom-OS command or an A8–A11/checkm8 procedure. Continue only when you have a legitimate mechanism that actually runs m1n1 on this exact J407 device.

Once you can see m1n1 executing, continue below.

## Step 7 — connect m1n1 to the host over USB

Connect iPad -> Mac/Linux with the data cable.

macOS:

```sh
ls -l /dev/cu.usbmodem*
```

Typical m1n1 names:

```text
/dev/cu.usbmodemP_01
/dev/cu.usbmodemP_03
```

Linux:

```sh
ls -l /dev/ttyACM*
```

Typical names:

```text
/dev/ttyACM0
/dev/ttyACM1
```

The first interface is normally the proxy. Set the actual device you see:

```sh
# Linux example
export M1N1DEVICE=/dev/ttyACM0

# macOS example
# export M1N1DEVICE=/dev/cu.usbmodemP_01
```

Test it:

```sh
cd ~/m1n1
source .venv/bin/activate
python3 proxyclient/tools/shell.py
```

If the shell connects, exit with `Ctrl-D` without changing hardware state.

If no CDC device appears, **stop before Linux** and report host preflight + USB enumeration + m1n1 output.

## Step 8 — dump the live J407 ADT before Linux

With m1n1 proxy alive:

```sh
PYTHONPATH=$HOME/m1n1/proxyclient \
python3 /path/to/j407-first-boot-image/dump_live_adt.py \
  j407-live-adt.bin
```

Now clone the exact `ipad-linux` revision used by the artifact:

```sh
cd ~
git clone https://github.com/xt9y/ipad-linux.git ipad-linux-test
cd ipad-linux-test
IPAD_LINUX_SHA="$(awk -F= '$1 == "ipad-linux" {print $2}' \
  /path/to/j407-first-boot-image/SOURCE_COMMITS)"
git checkout "$IPAD_LINUX_SHA"
```

Build/run the ADT inspector:

```sh
clang -std=c17 -O2 -Wall -Wextra \
  -Isrc/adt \
  tools/adt-inspect.c \
  src/adt/adt.c src/adt/adt_reg.c \
  src/adt/adt_function.c src/adt/adt_clock.c \
  -o adt-inspect

./adt-inspect /path/to/j407-live-adt.bin | tee j407-live-adt.txt
```

**Important:** preserve the reported SPI4 line. Its `clock-id=380` uses live clock table index `124`. This is one of the measurements needed for the next touchscreen stage.

Keep:

```text
j407-live-adt.bin
j407-live-adt.txt
```

## Step 9 — optionally open the second m1n1 USB terminal

Linux example:

```sh
picocom --omap crlf --imap lfcrlf -b 500000 /dev/ttyACM1
```

macOS example:

```sh
picocom --omap crlf --imap lfcrlf -b 500000 /dev/cu.usbmodemP_03
```

This is m1n1's secondary/virtual-UART interface. A direct Linux kboot does **not** guarantee that physical `ttySAC0` earlycon will be visible on this USB port, so an empty secondary terminal is not by itself proof of a failed kernel boot.

## Step 10 — first iterative Linux boot through the already-running m1n1 proxy

The Actions kit uses an **uncompressed** `Image`, therefore current upstream m1n1 `linux.py` needs `--compression none`:

```sh
export M1N1DEVICE=/dev/ttyACM0   # Linux example; use your actual device
# export M1N1DEVICE=/dev/cu.usbmodemP_01  # macOS example

cd ~/m1n1
source .venv/bin/activate

python3 proxyclient/tools/linux.py \
  --compression none \
  /path/to/j407-first-boot-image/Image \
  /path/to/j407-first-boot-image/t8103-j407.dtb \
  /path/to/j407-first-boot-image/initramfs.cpio.gz \
  -b "earlycon console=tty0 console=ttySAC0,115200 loglevel=8"
```

Save all m1n1 output. Important pre-jump markers include secondary CPU startup and:

```text
Ready to boot
```

`j407-m1n1-linux.bin` is for an entry mechanism that can directly launch raw m1n1 plus appended payloads. There is intentionally **no generic DFU/recovery injection command** here. When m1n1 proxy is already available, use `linux.py` above.

## Step 11 — observe the iPad

If iBoot's framebuffer survives and SimpleDRM/fbcon initializes, kernel text can appear on the display.

If Linux reaches PID 1, the iPad should eventually show a compact page similar to:

```text
ipad-linux J407 FIRST BOOT
Linux reached PID 1.
CPUs:       8/8 PASS
NVMe:       DETECTED
USB:        ENUMERATED
Type-C:     REGISTERED
BCM4387:    Wi-Fi PCI OK / BT PCI OK
WLAN iface: PRESENT
BT class:   PRESENT
Graphics:   ENUMERATED
Input:      ...
Sound:      ...
FIRST_BOOT_DIAGNOSTICS_COMPLETE
```

**Take clear photos of the full screen** if this appears, especially if no serial log is available.

No display output does not automatically mean Linux failed; native J407 DCP support is not required for the first kernel milestone.

## Step 12 — save/analyze the boot log

If you have a text capture, keep the complete unedited output as:

```text
boot.log
```

Run:

```sh
cd /path/to/j407-first-boot-image
python3 analyze-first-boot.py boot.log
python3 analyze-first-boot.py --json boot.log > boot-analysis.json
```

The analyzer reports the furthest stage plus SMP, NVMe, USB, Type-C, BCM4387, WLAN, Bluetooth, graphics, input, sound, panic and Stage-2 exception status.

## Step 13 — generate exactly what you should send back

From the artifact directory:

```sh
python3 build-hardware-report.py \
  --boot-log boot.log \
  --adt-bin /path/to/j407-live-adt.bin \
  --adt-report /path/to/j407-live-adt.txt \
  --source-commits SOURCE_COMMITS \
  --checksums SHA256SUMS \
  --ipad-os "26.5 (23F77)" \
  --output-prefix j407-hardware-report
```

Replace the iPadOS string with the version/build your device actually showed.

Send back:

1. `j407-hardware-report.md`
2. complete unedited `boot.log`
3. `boot-analysis.json`
4. `j407-live-adt.bin` if m1n1 proxy worked
5. `j407-live-adt.txt`
6. clear iPad screen photo(s) if any output appeared

Do **not** send serial number, Apple ID, passwords/passcode, trusted-device codes or unrelated personal files.

## Step 14 — what each failure means

| Earliest failed point | What it means / next target |
| --- | --- |
| Cannot execute m1n1 | Initial J407 boot-entry research; Linux code is not involved yet |
| m1n1 runs, no CDC devices | m1n1 J407 USB gadget/controller path |
| Proxy works, ADT dump fails | m1n1 proxy/boot-args/ADT handling |
| ADT works, `linux.py` fails before jump | m1n1 DT preparation or payload placement |
| `Linux version` appears then hangs | early Linux memory/AIC/timer/console/exception path |
| PID 1 appears, CPUs < 8 | SMP release/coherency |
| PID 1 appears, no NVMe | RTKit/SART/DART/ANS runtime state; do not change verified static addresses blindly |
| BCM4387 PCI IDs appear, no WLAN/BT class | firmware/calibration/driver layer |
| No graphics | framebuffer preservation/native DCP later; not a boot failure by itself |
| No input | expected until live SPI4 clock + J407 touch IRQ/power details are finished |
| No sound | expected first-boot state; J407 audio endpoint work remains |

The project should be continued from the **first failed boundary**, not by randomly changing unrelated hardware definitions.
