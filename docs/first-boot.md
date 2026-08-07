# J407 physical first-boot procedure

This is the complete test procedure for the **iPad Air 5 Wi-Fi** target:

```text
ProductType: iPad13,16
BoardConfig: J407AP
Model:       A2588
SoC:         T8103 / Apple M1
CPID:        0x8103
BDID:        0x10
```

The repository is prepared up to the point where a real device must be used.
It deliberately does **not** contain, assume or describe a Secure Boot,
BootROM or iBoot bypass. The first unresolved prerequisite is a legitimate
research mechanism that can already start m1n1 on J407.

Do not improvise DFU/recovery commands or try to send the final blob to normal
iPadOS/recovery as if it were a signed Apple image. The artifact is an m1n1
payload, not an IPSW component.

---

## 1. What hardware is required?

Required:

- the target iPad Air 5 Wi-Fi (`iPad13,16`, `J407AP`);
- a **Mac or native Linux computer**;
- one known-good USB-C data cable;
- enough free disk space for a Linux/m1n1 checkout and the Actions artifact;
- a backup of important iPad data before low-level experimentation.

Recommended:

- keep the iPad above 50% battery;
- use the Mac/Linux machine directly instead of a VM;
- install `picocom` for serial/CDC capture;
- keep the complete test artifact unchanged after downloading it.

### Can an iPhone be the host?

Not for this workflow. A USB-C iPhone can physically connect to an iPad, but
our bring-up host needs normal desktop Python tooling plus direct access to
m1n1's USB CDC serial interfaces. The supported practical setup is macOS or
Linux. Use an external Mac/Linux computer.

### Do I need a physical UART adapter?

**Not for the first test.**

The first hardware milestone is m1n1 proxy mode over USB. If J407's m1n1 USB
gadget path works, the host should see two CDC ACM serial devices. We can dump
the live Apple Device Tree and perform several checks using USB alone.

Linux earlycon is still configured for J407 UART0 (`ttySAC0`), but the project
does not currently publish a verified physical UART pad/pinout for this iPad.
Do **not** solder or probe guessed pads. For a direct Linux boot, the preserved
firmware framebuffer is the no-solder fallback: PID 1 mirrors a compact test
summary to `/dev/tty0` when SimpleDRM/fbcon is available.

---

## 2. Record the exact iPad identity before testing

On the iPad, open:

```text
Settings -> General -> About
```

Record locally:

- Model Name;
- iPadOS Version;
- the iPadOS build number (tap the version if needed).

For the public final iPadOS 26.5 release, the expected build is `23F77`.
However, record what the device itself shows and use that value in the final
report.

Do **not** include these in a public report:

- serial number;
- Apple ID;
- passwords/passcodes;
- trusted-device codes;
- private account identifiers.

---

## 3. Download the latest green hardware-test kit

Open the repository on GitHub and select:

```text
Actions -> j407-first-boot-image
```

Use the latest **successful** run on branch `ipad-air-5` and download the
artifact named:

```text
j407-first-boot-image
```

Unzip it into its own directory. The directory is expected to contain at least:

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

`j407-m1n1-linux.bin` is exactly:

```text
m1n1.bin
+ t8103-j407.dtb
+ initramfs.cpio.gz
+ Image
```

The uncompressed ARM64 `Image` is intentionally the final payload.

---

## 4. Verify the downloaded kit before touching the iPad

In a terminal, enter the artifact directory:

```sh
cd /path/to/j407-first-boot-image
```

Run the project verifier:

```sh
python3 verify-first-boot-kit.py .
```

It must end with:

```text
J407 first-boot kit: VERIFIED
```

Also verify the normal checksum manifest.

macOS:

```sh
shasum -a 256 -c SHA256SUMS
```

Linux:

```sh
sha256sum -c SHA256SUMS
```

Every listed file must report `OK`.

Finally inspect the identity/revisions:

```sh
cat TARGET
cat SOURCE_COMMITS
```

The target must contain:

```text
product_type=iPad13,16
board_config=J407AP
model=A2588
cpid=0x8103
bdid=0x10
```

If any of these checks fails, **stop** and download a fresh successful artifact.

---

## 5. Prepare a macOS host

A Mac is the simplest host option.

If Homebrew is installed:

```sh
brew install python git picocom
```

Clone upstream m1n1:

```sh
cd ~
git clone --recursive https://github.com/AsahiLinux/m1n1.git
cd m1n1
```

Create a Python environment for the proxy client:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install pyserial construct
```

Run the project host preflight from the downloaded artifact directory:

```sh
python3 /path/to/j407-first-boot-image/host-preflight.py \
  --artifact-dir /path/to/j407-first-boot-image \
  --m1n1 ~/m1n1
```

Before m1n1 actually starts on the iPad, this line is normal:

```text
m1n1_usb_devices=none
```

---

## 6. Prepare a Linux host

Example for Debian/Ubuntu:

```sh
sudo apt update
sudo apt install -y python3 python3-venv git picocom
```

Then:

```sh
cd ~
git clone --recursive https://github.com/AsahiLinux/m1n1.git
cd m1n1
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install pyserial construct
```

Run:

```sh
python3 /path/to/j407-first-boot-image/host-preflight.py \
  --artifact-dir /path/to/j407-first-boot-image \
  --m1n1 ~/m1n1
```

Depending on the distribution, your user may need permission to access
`/dev/ttyACM*`. Follow your distribution's normal serial-device/udev procedure;
do not run the whole research stack as root just to avoid permissions.

---

## 7. Hard stop: the initial m1n1 entry is not supplied by this repository

At this exact point the host and Linux payload are ready, but there is still an
external prerequisite:

> J407 must already have a legitimate early-boot research mechanism capable of
> executing m1n1.

This repository does not currently provide that mechanism.

Important consequences:

- normal iPadOS cannot simply execute `j407-m1n1-linux.bin`;
- recovery/DFU does not imply arbitrary unsigned m1n1 execution;
- the Mac-specific Apple Silicon custom-OS boot policy path must not be assumed
  to exist on an iPad;
- do not substitute palera1n/checkm8 for this target: M1 is not in that device
  class;
- do not guess an exploit chain based on an unrelated Apple device.

If you do not independently have a legitimate way to start m1n1 on this exact
J407 device, **stop here**. Everything before this point can be prepared safely;
the next numbered step begins only after m1n1 actually runs.

---

## 8. First physical milestone: confirm m1n1 USB proxy mode

Once m1n1 is genuinely running on the iPad, connect the iPad directly to the
Mac/Linux host with the USB-C data cable.

On Linux, upstream m1n1 normally exposes two devices such as:

```text
/dev/ttyACM0
/dev/ttyACM1
```

On macOS, typical names are:

```text
/dev/cu.usbmodemP_01
/dev/cu.usbmodemP_03
```

List them.

macOS:

```sh
ls -l /dev/cu.usbmodem*
```

Linux:

```sh
ls -l /dev/ttyACM*
```

The first interface is normally the m1n1 proxy interface. Set it explicitly.

macOS example:

```sh
export M1N1DEVICE=/dev/cu.usbmodemP_01
```

Linux example:

```sh
export M1N1DEVICE=/dev/ttyACM0
```

Do not assume the suffix if your host shows different device names.

Run the preflight again:

```sh
python3 /path/to/j407-first-boot-image/host-preflight.py \
  --artifact-dir /path/to/j407-first-boot-image \
  --m1n1 ~/m1n1
```

Now at least one m1n1 USB device should be visible.

Test the proxy:

```sh
cd ~/m1n1
source .venv/bin/activate
python3 proxyclient/tools/shell.py
```

A successful proxy shell prints m1n1/ADT information and opens an interactive
Python prompt. Exit with `Ctrl-D` without changing hardware state.

### If no CDC/ACM devices appear

Stop before Linux boot. Save/report:

- output of `host-preflight.py --json`;
- the exact Mac/Linux version and architecture;
- the visible USB enumeration from the host;
- all m1n1 output available from the entry mechanism;
- whether the iPad screen changed.

Do not start changing Linux drivers yet; Linux has not been reached.

---

## 9. Dump the live J407 Apple Device Tree before booting Linux

This is a high-value, read-only measurement and should be performed before the
first Linux attempt.

With `M1N1DEVICE` set and m1n1 proxy mode alive:

```sh
PYTHONPATH=$HOME/m1n1/proxyclient \
python3 /path/to/j407-first-boot-image/dump_live_adt.py \
  j407-live-adt.bin
```

The helper uses upstream m1n1's existing `u.get_adt()` path and prints the ADT
size and SHA-256.

Now check out the exact `ipad-linux` revision from the artifact so the offline
inspector matches the boot image:

```sh
cd ~
git clone https://github.com/xt9y/ipad-linux.git ipad-linux-test
cd ipad-linux-test
IPAD_LINUX_SHA="$(awk -F= '$1 == "ipad-linux" {print $2}' \
  /path/to/j407-first-boot-image/SOURCE_COMMITS)"
git checkout "$IPAD_LINUX_SHA"
```

Build the inspector:

```sh
clang -std=c17 -O2 -Wall -Wextra \
  -Isrc/adt \
  tools/adt-inspect.c \
  src/adt/adt.c \
  src/adt/adt_reg.c \
  src/adt/adt_function.c \
  src/adt/adt_clock.c \
  -o adt-inspect
```

Run it:

```sh
./adt-inspect /path/to/j407-live-adt.bin | tee j407-live-adt.txt
```

The especially important new value is:

```text
spi4 boot clock: clock-id=380 table-index=124 frequency=... Hz
```

That live value is required before the project enables the J407 touchscreen
SPI controller with a non-guessed input clock.

Keep both:

```text
j407-live-adt.bin
j407-live-adt.txt
```

---

## 10. Optional: open m1n1's secondary USB terminal

If m1n1 exposes the normal second CDC interface, you can open it before booting
anything further.

Linux example:

```sh
picocom --omap crlf --imap lfcrlf -b 500000 /dev/ttyACM1
```

macOS example:

```sh
picocom --omap crlf --imap lfcrlf -b 500000 /dev/cu.usbmodemP_03
```

Upstream m1n1 reserves this second interface for its virtual-UART/hypervisor
path. A **direct** Linux kboot does not magically turn J407's physical UART0
into USB earlycon, so do not interpret an empty second CDC terminal as proof
that Linux did not boot.

---

## 11. Preferred iterative Linux boot once m1n1 proxy works

For development, load the three components separately through upstream
`proxyclient/tools/linux.py`. This gives much faster iteration than rebuilding a
new initial-entry payload each time.

Our Actions artifact contains an **uncompressed** ARM64 `Image`. Current m1n1's
`linux.py` therefore requires `--compression none` explicitly.

Set the correct proxy device and run:

```sh
export M1N1DEVICE=/dev/ttyACM0        # Linux example
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

Before the final jump, m1n1 should print loader progress such as DTB/kernel
placement, secondary CPU startup and `Ready to boot`.

### About `j407-m1n1-linux.bin`

The combined blob is intended for an entry mechanism that natively launches a
raw m1n1 image with appended payloads. **There is intentionally no generic
`send this blob to DFU` command in this repository.** How that combined blob is
started depends on the legitimate J407 entry mechanism that becomes available.

For an already-running m1n1 proxy, use `linux.py` above instead.

---

## 12. What should appear on the iPad/display?

The DT asks m1n1 to preserve and patch Apple's firmware framebuffer when one is
available. Linux enables SimpleDRM + fbcon and includes `console=tty0`.

If the framebuffer survives, you may see Linux output on the iPad display.
When PID 1 completes its probes, it also writes a compact status page directly
to `/dev/tty0` with lines similar to:

```text
ipad-linux J407 FIRST BOOT
Linux reached PID 1.
CPUs:       8/8  PASS
NVMe:       DETECTED
USB:        ENUMERATED
Type-C:     REGISTERED
BCM4387:    Wi-Fi PCI OK / BT PCI OK
WLAN iface: PRESENT
BT class:   PRESENT
Graphics:   ENUMERATED
Input:      ENUMERATED
Sound:      ...
FIRST_BOOT_DIAGNOSTICS_COMPLETE
```

If you see this and no serial capture is available, take **clear photos of the
entire screen** before rebooting.

No visible framebuffer is not by itself proof of a kernel failure; native J407
DCP display support is not yet the first-boot dependency.

---

## 13. Serial/console expectations

J407 UART0 is described as:

```text
physical address: 0x235200000
AIC IRQ:          605
Linux device:     ttySAC0
configured rate:  115200
```

The DT bootargs are:

```text
earlycon console=tty0 console=ttySAC0,115200 loglevel=8
```

A physical UART capture would be the most complete direct-kboot log, but this
project does not currently identify a safe physical iPad UART connector/pad.
Do not solder unknown pads.

If a later verified UART adapter/pinout becomes available, capture the **whole**
boot from the first m1n1 line through PID 1. Until then, use:

- m1n1 proxy output;
- the live ADT dump;
- iPad framebuffer/tty0 output and photographs;
- any verified virtual-UART path available in the chosen m1n1 execution mode.

---

## 14. Expected first-boot stages

### Stage A: m1n1 proxy

Success:

- USB CDC devices enumerate;
- `proxyclient/tools/shell.py` connects;
- live ADT can be read.

If this fails, the problem is still m1n1/J407 USB/entry, not Linux.

### Stage B: m1n1 Linux preparation

Success markers include:

```text
Starting secondary CPUs...
Loading DTB...
Ready to boot
```

A failure here points to m1n1 platform handling, DT preparation or payload
placement.

### Stage C: Linux early boot

The decisive kernel marker is:

```text
Linux version ...
```

If this appears, m1n1 successfully transferred control to the kernel.

### Stage D: PID 1

The initramfs marker is:

```text
ipad-linux early userspace
target: iPad Air 5 Wi-Fi / J407 / T8103
```

Reaching this means mainline Linux reached userspace without relying on the
internal NVMe root filesystem.

### Stage E: automatic hardware inventory

The full log contains counts/states for:

```text
cpu_nodes
block_devices
nvme_controllers
graphics_entries
usb_entries
typec_entries
pci_functions
net_interfaces
wlan_interfaces
bluetooth_entries
input_entries
sound_entries

SMP
ANS2/NVMe
USB
TYPEC
BCM4387-WIFI
BCM4387-BT
WLAN-INTERFACE
BLUETOOTH-CLASS
INPUT
SOUND
framebuffer/DRM
```

The final success marker for the diagnostic image is:

```text
ipad-linux: FIRST_BOOT_DIAGNOSTICS_COMPLETE
```

PID 1 then stays alive instead of rebooting automatically.

---

## 15. Save and analyze the complete boot log

If you have a text capture, save it unedited as:

```text
boot.log
```

From the downloaded kit:

```sh
python3 analyze-first-boot.py boot.log
```

Machine-readable form:

```sh
python3 analyze-first-boot.py --json boot.log > boot-analysis.json
cat boot-analysis.json
```

Do not trim a failing log to only the final error. The lines immediately before
an exception/panic are often more useful than the last line.

---

## 16. Generate the report to send back

If you obtained the boot log **and** live ADT:

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

Replace `26.5 (23F77)` with the version/build actually shown on the iPad if it
differs.

This produces:

```text
j407-hardware-report.md
j407-hardware-report.json
```

If you did not get far enough for a live ADT, omit the two ADT arguments.

### Send back these files

Best report set:

1. `j407-hardware-report.md`
2. complete unedited `boot.log`
3. `j407-live-adt.bin` if proxy mode worked
4. `j407-live-adt.txt` if generated
5. any clear iPad screen photographs showing the PID-1 status page or failure
6. `boot-analysis.json`

You do **not** need to send:

- serial number;
- Apple ID information;
- passwords/passcodes;
- host username/hostname;
- unrelated personal files.

The report builder intentionally avoids embedding hostname/username.

---

## 17. If the test fails, report the earliest failed boundary

### No mechanism can start m1n1

This is the current external project boundary. Linux/m1n1 payload changes cannot
fix it. Preserve the device on a useful firmware version and continue only when
a legitimate J407 entry route exists.

### m1n1 starts, but no USB CDC interfaces appear

Report:

- host-preflight JSON;
- host USB enumeration;
- m1n1 revision;
- all visible m1n1 output;
- iPad screen state.

Focus next on J407 m1n1 USB gadget/controller handling.

### Proxy shell works, but live ADT dump fails

Report the full `dump_live_adt.py` error and proxy shell startup output. Do not
substitute addresses from a Mac ADT.

### Live ADT works, but Linux never prints/appears

Report:

- `j407-live-adt.bin` and inspector output;
- the complete `linux.py` output through `Ready to boot`/failure;
- iPad screen state.

The next focus is early Linux handoff/memory/AIC/timer/console.

### Linux starts, but PID 1 does not appear

Capture the kernel panic/exception and all earlier kernel lines. The initramfs
is self-contained, so this isolates a kernel/DT/handoff problem.

### PID 1 appears with fewer than 8 CPUs

Linux boot itself works. Focus on m1n1 secondary CPU start, spin-table release
addresses and coherency.

### PID 1 appears, NVMe is missing

Known static J407 values are already independently matched:

```text
ANS/NVMe: 0x27bcc0000, IRQ 590
ANS mbox:  0x277408000, IRQs 583-586
SART-ANS: 0x27bc50000
```

Do not randomly change those values. Inspect RTKit/SART/DART/ANS driver logs.

### BCM4387 PCI functions appear, but no WLAN/BT interface

PCIe/board topology is working. The likely next layer is firmware/calibration or
the device driver. Use the repository firmware checker on legitimately obtained
firmware; do not upload proprietary Apple firmware to the repository.

### Graphics is absent

This does not invalidate Linux boot. Check whether the firmware framebuffer was
preserved. Native DCP/display support is a later driver milestone.

### Input is absent

Touch is intentionally not enabled yet. The live ADT's SPI4 boot clock and J407
interrupt/power semantics are required before enabling the HBPP/Z2 path.

### Sound is absent

Expected for the first bring-up image. T8103 MCA transport exists, while J407's
MAX98709/ALC/AOP endpoint work is a later board/audio-driver milestone.

---

## 18. Diagnostic Stage 2 fallback

`ipad-linux-stage2.bin` is included for a future entry environment that wants
the repository's explicit `boot_info v4` ABI instead of m1n1 kboot.

Its EL1/EL2 exception vectors preserve:

```text
vector
CurrentEL
ESR_ELx
ELR_ELx
FAR_ELx
SPSR_ELx
```

A line beginning:

```text
ipad-linux: AArch64 exception
```

should therefore be reported with the complete surrounding output.

The diagnostic Stage 2 is not a substitute for the unresolved initial secure
boot/entry mechanism.
