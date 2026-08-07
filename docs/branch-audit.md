# Branch integration audit

This document records the branch decisions made while converging the project on
`ipad-air-5`. It exists to prevent old experimental branches from accidentally
reintroducing superseded boot ABIs or unverified J407 board assumptions.

## Final policy

`ipad-air-5` is the **only canonical J407 integration branch**.

An old research branch is not merged merely because it contains commits that are
not ancestors of `ipad-air-5`. Divergent branches often contain older versions
of files which have already been ported forward and tested in newer form.

The physical-test-readiness work is developed temporarily on
`integration/j407-physical-test-ready` and is intended to be fast-forwarded to
`ipad-air-5` after its final gates pass. Once that happens, the integration
branch is historical only.

## `ipad-air-5`

Status: **canonical/final J407 branch.**

Target:

```text
iPad Air 5 Wi-Fi
iPad13,16
J407AP
T8103 / Apple M1
```

All physical-test artifacts should be built from this branch after integration.

## `main`

Status: **stale baseline; do not merge into `ipad-air-5`.**

`ipad-air-5` contains the complete newer J407 bring-up history. Merging `main`
back provides no forward work. If the project later wants `main` to become the
public default again, the correct direction is to promote the tested J407 work
forward into `main`, not merge the stale baseline backwards.

## `work/linux-entry-contract`

Status: **superseded historical branch; do not merge wholesale.**

It contains earlier versions of:

- `boot_info`;
- FDT patching;
- SMP contracts;
- m1n1 handoff;
- J407 discovery;
- associated tests/documentation.

All useful concepts are already present in newer, tested form on the canonical
line. A whole-branch merge would risk ABI and validation regressions.

## `work/j407-entry-v2`

Status: **selectively integrated; do not merge wholesale.**

Useful work was ported forward, including:

- J407 USB0/DART/ATC enablement;
- built-in DWC3/Type-C bring-up configuration;
- PCIe/BCM4387 diagnostics;
- first-boot USB/PCI inventory;
- conservative CD3217 discovery.

Its more speculative USB-C graph was deliberately not copied without independent
J407 evidence.

## `work/j407-integrated`

Status: **superseded divergent integration attempt; do not merge.**

This branch contains alternative/older versions of the first-boot DTS, packer,
initramfs and workflow files. The current canonical line has newer verified
implementations and stronger CI contracts.

## `integration/j407-usb-radio`

Status: **merged/superseded.**

This integration produced the USB/radio first-boot work that was merged into
`ipad-air-5` as the PR #2 integration. Do not merge it again.

## `integration/j407-touch`

Status: **merged/superseded.**

This integration produced the J407 touch foundation and Apple GPIO IRQ-group
kernel patch. It was merged into `ipad-air-5` as PR #3 after the build, tools,
kernel-patch, Linux-bundle and first-boot-image gates were all green. Do not
merge it again.

## `integration/j407-live-discovery`

Status: **superseded precursor to physical-test readiness.**

This was created after the touch merge for live ADT/clock/report tooling. Its
commits were carried forward into `integration/j407-physical-test-ready`.

## `integration/j407-live-discovery-final`

Status: **redundant historical ref; do not merge separately.**

It was accidentally created while reorganizing the final integration work and
does not represent an independent feature line.

## `integration/j407-physical-test-ready-2`

Status: **redundant historical ref; do not merge separately.**

It was accidentally created while checking the existing final branch. The
canonical temporary integration line is `integration/j407-physical-test-ready`.

## `integration/j407-physical-test-ready`

Status: **final temporary integration branch before real hardware testing.**

Scope:

- live ADT clock discovery;
- m1n1 live ADT dump helper;
- expanded PID-1 hardware inventory;
- on-display first-boot summary;
- self-verifying Actions hardware-test kit;
- Mac/Linux host preflight;
- boot-log analyzer;
- reproducible hardware-report builder;
- complete physical-test procedure in `docs/first-boot.md` and `README.md`.

This branch must remain a strict fast-forward of `ipad-air-5`. After final
validation, `ipad-air-5` should be moved forward to its exact head, preserving
all source SHAs used by hardware-test artifacts.

## Merge policy

1. Never whole-merge a divergent research branch based only on commit count.
2. Compare file changes against current `ipad-air-5` first.
3. Port forward only genuinely newer behavior.
4. Keep unverified hardware wiring disabled/absent.
5. Require fail-closed tests for parsers, payloads and artifact identity.
6. Require the bare-metal, host-tools, m1n1/kernel-patch, Linux-bundle and
   first-boot-image gates for canonical integration.
7. Prefer a fast-forward from a clean integration branch so artifact
   `SOURCE_COMMITS` remain directly reachable on the canonical branch.
