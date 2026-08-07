# Branch integration audit

This document records the branch decisions made while converging the project on
`ipad-air-5`. It exists to prevent old experimental branches from accidentally
reintroducing superseded boot ABIs or unverified J407 board assumptions.

## `ipad-air-5`

Canonical integration branch for the iPad Air 5 Wi-Fi (`iPad13,16`, J407,
T8103) port.

All production-facing bring-up work should eventually land here through a CI
gate. Hardware facts in this branch must be supported by the J407 Apple Device
Tree, current upstream Linux/m1n1 behavior, or measurements from the target.

## `main`

Status: **stale baseline; do not merge into `ipad-air-5`.**

`ipad-air-5` contains the large body of newer J407 work and is far ahead of
`main`. Merging `main` back would provide no useful forward work and would make
history harder to reason about.

The eventual direction, after physical J407 bring-up is stable, is the opposite:
promote the tested `ipad-air-5` result to the repository's default branch.

## `work/linux-entry-contract`

Status: **superseded; do not merge wholesale.**

This branch contains earlier revisions of the entry ABI, runtime FDT patching,
SMP contract, m1n1 handoff, J407 discovery and associated documentation/tests.
Those facilities already exist in newer form on `ipad-air-5`, including:

- versioned `boot_info` handoff data;
- Linux image/layout validation;
- runtime FDT patching;
- J407 SMP release-address validation;
- `integration/m1n1/ipad_linux_adapter.c`;
- m1n1 compile/API drift checks;
- J407 ADT discovery and host tests.

Re-merging this branch would risk downgrading those implementations. It remains
useful only as historical reference.

## `work/j407-entry-v2`

Status: **partially useful; selectively integrated.**

This branch was created later than the original entry-contract work and contains
several useful PCIe/USB/diagnostic changes, but it diverged before the newest
ADT function decoder and touch/audio research landed on `ipad-air-5`.

The following concepts have been selectively integrated on top of the current
branch rather than merging the branch as a unit:

- built-in DWC3/ATC/Type-C and SimpleDRM bring-up configuration;
- explicit enablement of the one J407-verified USB0 path;
- explicit disablement of the unsupported second T8103 USB path;
- explicit enablement of the J407 PCIe host for BCM4387;
- expanded initramfs PCI/USB/Type-C diagnostics;
- expanded serial-log analyzer coverage;
- PCIe/radio information in the host ADT inspector.

The full USB-C endpoint/mux graph from that work branch is intentionally **not**
copied wholesale. J407's CD3217 is currently represented conservatively as an
`apple,cd321x` I2C device at address `0x38`, without a guessed IRQ or connector
routing. The upstream driver can poll when no IRQ is provided. The graph can be
added later when its J407-specific lane/role routing is independently verified.

## `integration/j407-usb-radio`

Status: **active CI integration branch.**

This branch starts from the current `ipad-air-5` head and contains the selective
USB0, CD3217, framebuffer-console and radio/diagnostic integration. It is gated
by the draft pull request into `ipad-air-5` and should be merged only after all
current workflow runs pass.

## Merge policy

1. Never merge a divergent research branch simply because it is ahead by commit
   count.
2. Compare its changed files against current `ipad-air-5` first.
3. Port forward only the useful behavior, preserving newer ABI/hardware work.
4. Keep unverified board wiring disabled or absent.
5. Require the bare-metal, host-tool, mainline-Linux and first-boot-image CI
   gates before merging an integration branch.
