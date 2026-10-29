# Phase A — Technique-class literature study (T8103 boot-path program)

> Program: `docs/kickoff-t8103-rom-research.md` (§5) · branch
> `research/j407-entry-2026-10` · date 2026-10-29.
> Literature-only session work — no device connected, SAFE tier trivially
> satisfied. Every externally-sourced claim carries its source in §6.
> Class-level material only (device mode read this session: normal iOS,
> iPadOS 27.0.1 / build 24A446 / iPad13,16 — recorded in the device arcs
> doc lineage, no device-unique values in repo).

---

## 1. usbliter8 — what the June 2026 disclosure actually established

### 1.1 The event
- Published **18 June 2026** by Paradigm Shift (PoC + full writeup), with
  coordinated disclosure to Apple Product Security before publication;
  CERT/CC tracked as **VU#941987**.
- Vulnerable silicon: **A12, A13, S4, S5** (Watch/HomePod-class chips).
  A12X/A12Z are in the silicon set but the published PoC support excludes
  them (Elcomsoft).
- The Apple Wiki vulnerability table records a SecureROM version span
  (vulnerable `3865.0.0.4.7–4479.0.0.100.4`); the ROM itself is
  unpatchable — the range describes which silicon shipped which ROM.
- **Post-publication legal event:** *Magnet Forensics, LLC v. Del Gaudio*
  produced a preliminary injunction (2026-07-21) requiring removal of the
  public writeup, source code, and references; the PoC repository is
  archived. Sourcing consequences in §5.

### 1.2 The bug — a hardware/software *pair*, not a single bug
1. **Hardware half:** the Synopsys DesignWare USB controller's
   setup-packet storage holds three setup packets and resets its DMA
   pointer by a fixed stride when a fourth transaction arrives. Undersized
   setup packets are stored in 4-byte chunks; the mismatch lets the
   pointer walk *backward* — an underflow primitive whose DMA writes land
   in SecureROM SRAM (CWE-119/787-class OOB write).
2. **Software half (load-bearing):** the A12/A13 SecureROMs run the **USB
   DART in bypass mode**, so nothing intercepts the DMA pointer's reach —
   the underflow can overwrite arbitrary SRAM used by SecureROM.

### 1.3 Exploit arc (both routes end at EL1 inside SecureROM)
- **A12:** the DMA buffer sits heap-adjacent to the USB task's stack →
  overwrite a saved link register → program-counter control at the next
  context switch.
- **A13:** PAC protects stack-stored return addresses, so the route is
  multi-stage — corrupt DART-related heap structures for limited write
  primitives → overwrite the panic-depth counter (error-loop instead of
  reboot) → overwrite the USB interrupt handler pointer in BSS; the next
  USB interrupt executes attacker code.
- **Post-code-exec:** injected custom USB request handler, `PWND:` stamp
  in USB serial (checkm8 convention), temporary SoC demotion, and booting
  a raw unsigned iBoot image with no signature checks — i.e. at that
  point the signature wall is standing *behind* you. The Secure Enclave
  is not directly compromised (their own caveat: BootROM control opens
  *routes toward* attacking it).

### 1.4 Who is excluded, by the researchers' own boundary
- **A11 and earlier of the last-vulnerable generation:** the A11 USB
  driver manually resets the DMA address after every packet, so the
  mismatch never accumulates.
- **A14 and later (the “newer generation”):** DART is *correctly
  configured* in SecureROM — “making the same route unexploitable”.
  **T8103 (M1-class, in this iPad) belongs to that A14/M1 generation.**
  This is the precise technical boundary our program's Phase A exists to
  document: the class is a *pair* (controller-protocol flaw + ROM DART
  configuration), and T8103 only half-inherits it.

## 2. Transfer analysis: why the class reads as closed for J407 — and what
   would still need checking
- T8103 is on the “DART correctly configured” side of Paradigm Shift's
  stated boundary. For the class to apply, an M1-family SecureROM would
  have to deviate from that statement (e.g., iPad-silicon media deltas).
  Untestable until a T8103/M1-family ROM binary exists (Phase B §5).
- A **named audit check** is now pinned for any Phase B artifact that
  reaches ROM-family code: *"USB DART/LLB configuration in SecureROM —
  bypass or enforced?"* — the single binary question that reopens or
  closes the usbliter8 class here.
- **What our device record does and does not bear** (evidence of record:
  `docs/dfu-ep0-recon-2026-10-27.md`):
  - §7.2 ROM-DFU arcs (sticky bState 0x05, ABORT-detach ≈24.2 s
    re-enumeration) are *baseline behavior* of the ROM USB stack on this
    silicon — no anomaly class there matches the DesignWare mismatch
    signature (ours is a different controller generation; the mismatch
    behavior itself is unobservable without ROM bytes).
  - §7.7/§7.11/§7.12 are **recovery-side (iBEC-level)** arcs: class-DFU
    STALLs, uploads ACK-everything silently, verbs registration-keyed,
    consumer chain dark. These live *above* the class surface and are
    consistent with (not evidence about) the ROM boundary.

## 3. Technique-class matrix (Phase A deliverable)

| # | Technique class | Required primitive | Silicon/OS applicability | Applicable to J407 (T8103, iPadOS 27.0.1)? | Basis |
|---|---|---|---|---|---|
| 1 | **checkm8** — ROM DFU image-loading heap UAF | heap grooming inside SecureROM DFU limb | A5–A11 (2019 research) | No known T8103 counterpart; the *style* remains the canonical first candidate for any ROM bug-hunt | Source A2, A4 |
| 2 | **usbliter8** — DesignWare setup-packet DMA-pointer underflow + DART-bypass pair | OOB DMA write into SRAM; ROM-side DART in bypass | A12/A13 (+S4/S5); **A14+/M1-class stated not exploitable** | **No** as stated — class pair closed unless iPad-silicon ROM config deviates (audit check pinned, §2) | Source A1, A3, A5–A7 |
| 3 | **CoreTrust-class trust-store bypass** | software trust-chain reuse on specific iPadOS builds | ≤16.6.x / 17-beta windows; revocable by update | **No** — device on 27.0.1, no signed downgrade path | Final report §5 (verified 2026-10-29) |
| 4 | **m1n1/Asahi boot-policy interposition** | SEP-signed per-OS Boot Policy (Permissive/Lowered), 1TR enrollment | **macOS only** — iPadOS has no boot-policy surface | **No** — structural absence, not a bug boundary; the design difference driving the whole feasibility answer | Source B1–B3 |
| 5 | **pongoOS/palera1n post-DFU chain-loading** | a working ROM pre-stage (checkm8) | A8–A11/T2; ecosystem active in 2026 (palera1n 3.0 beta Aug 2026) | Not for this silicon — but the *pipeline methodology* (pongoOS shell, KPF) is the reusable technique library for a hypothetical T8103 pwn | Source A4 |
| 6 | **iOS-version-restricted chains (2020-2026, newer silicon)** | version-specific app/kernel bugs | many windows, none public for iPadOS 27 + T8103 | **No public window** — quick-win check executed first thing this session (device at 27.0.1/24A446) | This session's device read + prior verified landscape |

Reading: **every class row is currently a "no" for this device.** That is
the expected Phase-A result (kickoff §13); the program's value rests on
Phases B–D producing evidence nobody else has for this silicon family.

## 4. What the sweep adds to the phase plan
- **Phase B (artifacts):** the usbliter8 PoC/writeup live only in
  archives — acquire the archived copies for mechanism cross-checks, keep
  them side-local. Mac-side power is higher than assumed: a structured
  M1-Mac boot-chain literature exists (Gallucci 4-part series: Boot ROM →
  LLB → iBoot), and macOS updater bundles remain the best public source
  for T8103-family iBoot/SPTM-era payloads. **T8103 SecureROM dump: no
  public artifact found in this sweep** — long-shot register stands.
- **Phase C (static audits):** priority #1 unchanged (iBSS.j407 USB stack
  = the usbliter8 analog at the software stage we *can* obtain); the
  DART-config question (§2) is added as a named check for any
  ROM-family artifact.
- **Phase D (emulated fuzz):** Harness 4 (iBSS USB descriptor/DFU replay)
  is now the closest emulation stand-in for the class-2 surface; nothing
  else changes.
- **New context, same conclusion:** even on Macs, the legitimate custom
  boot path is getting narrower at the edges (macOS 27 boot-picker
  metadata flag broke Asahi briefly; patched upstream within weeks) —
  reinforces that Apple's door is boot-policy-only and iPadOS simply has
  no such room, independent of bug classes.

- **Sourcing & legal caveat:** the usbliter8 writeup/PoC is
  injunction-affected. All citations in this doc go
	to independent secondary reporting, the CERT/CC note, and The Apple
	Wiki. If the program needs the primary text or PoC later, it comes from
	an archived copy, stays in the side-local research tree, and is treated
	as third-party published material for study — not redistribution.

## 6. Source ledger
- **A1** Infosecurity Magazine (2026-06): designware setup-packet storage
  (3 packets, fixed-stride DMA reset on 4th; undersized packets in
  4-byte chunks → backward pointer → SRAM overwrite); DART configured
  correctly on A14+.
- **A2** The Hacker News (2026-06): A12 saved-LR overwrite; A13 multi-step
  PAC route (DART-heap corruption → panic-depth counter → USB interrupt
  handler in BSS); demotion + unsigned raw iBoot capability; coordinated
  disclosure.
- **A3** Security Affairs (2026-06): DART-in-bypass on A12/A13 SecureROM
  as the enabling config; A11 per-packet manual DMA reset; post-exploit
  behavior incl. `PWND:[usbliter8]`.
- **A4** The Apple Wiki — palera1n page (2026 releases incl. 3.0 beta Aug
  2026, A8–A11/T2 support) and usbliter8 entry (silicon set, SROM version
  span, injunction 2026-07-21, Magnet Forensics v. Del Gaudio).
- **A5** SecurityWeek (2026-06): researcher framing — "even recent
  SecureROM generations remain susceptible to subtle hardware flaws";
  physical-access class; forensics-use note.
- **A6** Elcomsoft blog (2026-07): silicon support map incl. A12X/A12Z
  exclusion from published PoC support; Waveshare RP2350 flow.
- **A7** CERT/CC VU#941987 (SEI): unauthenticated local attacker, code
  execution at boot, unpatchable-by-design.
- **B1** Asahi Linux docs — Introduction to Apple Silicon: three-tier
  boot chain (SecureROM/iBoot1 NOR ↔ iBoot2 NVMe), Boot Policies signed
  by SEP-internal machine key, Full/Reduced/Permissive security states.
- **B2** Asahi distro:boot process guide: m1n1 stage 1 signed via Apple
  secure-boot policy at install, immutable; stage 2 from ESP.
- **B3** macOS 27 ("Golden Gate") boot-picker change vs Asahi (fosslinux +
  techtimes, 2026-07): container-metadata-flag visibility break, upstream
  patch — context only.
- **B4** U-Boot upstream Apple Silicon page: t8103 listed as supported
  SoC via m1n1 (same-chip public support exists — on Macs).
- **B5** O. Gallucci — "Boot ROM Security on Silicon Macs (M1/M2/M3)" +
  4-part boot-stage series: public structured reference for the M1-family
  boot chain (Phase B/C cross-reference).
