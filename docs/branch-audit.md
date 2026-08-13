# Branch integration audit

This document records branch decisions for the J407 project.

## Canonical policy

`main` is the canonical project branch.

The complete J407 development line was built and validated on `ipad-air-5` and
is being promoted forward to `main` on 2026-08-13. New canonical work should
target `main`.

`ipad-air-5` remains a historical integration branch so older build artifacts
and source revisions remain easy to reproduce.

## Target

```text
iPad Air 5 Wi-Fi
iPad13,16
J407AP
T8103 / Apple M1
CPID 0x8103
BDID 0x10
```

## `main`

Status: **canonical branch.**

It contains the current J407 bring-up implementation, tooling, documentation and
physical validation record.

## `ipad-air-5`

Status: **historical J407 integration branch.**

This was the canonical development line before promotion to `main`. It should
not receive independent divergent feature work after promotion.

## Superseded historical branches

The following branches contain older or already-integrated work and should not
be merged wholesale into `main`:

- `work/linux-entry-contract`
- `work/j407-entry-v2`
- `work/j407-integrated`
- `integration/j407-usb-radio`
- `integration/j407-touch`
- `integration/j407-live-discovery`
- `integration/j407-live-discovery-final`
- `integration/j407-physical-test-ready`
- `integration/j407-physical-test-ready-2`

Useful work from those branches has already been carried forward in newer form.

## Merge policy

1. Never whole-merge a divergent research branch based only on commit count.
2. Compare changes against current `main` first.
3. Port forward only genuinely newer behavior.
4. Keep unverified hardware assumptions disabled or absent.
5. Preserve exact source revisions for reproducible hardware-test artifacts.
