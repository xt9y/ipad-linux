# PHASE E PREP — instant-win closure, ROM/hardening re-verification, session plan (2026-11-04)

Class-level. Follows `phase-d-close-2026-11-04.md`; starts Phase E from its
coverage matrix. Nothing here was derived from a live device session; all
device-adjacent data is from the recorded 2026-10-24/27 baseline logs.

## 1. Instant-win branch — closed as a shortcut (verdict + one open read)

Kickoff §4 ordered this check FIRST: read the device's exact iPadOS version
and compare against public-chain windows. Public-chain landscape as of
2026-11-04 (all claims below are cited public sources):

**Boot-chain class (the only class that helps the Linux-boot goal):**

| Chain | Window | Silicon | J407 (T8103) relevance |
|---|---|---|---|
| checkm8 lineage (palera1n/pongoOS) | iOS/iPadOS 15–26 (tool) | arm64 only — **arm64e excluded** | No — T8103 is arm64e + post-A12 ROM fix |
| usbliter8 (DesignWare USB class) | published 2026, PoC public | demonstrated to A13-class silicon (iPhone 11 Linux boot via Hoolock Linux + m1n1) | Unknown **on T8103** — no public ROM image to compare against; exactly the class our kickoff §4 ordered studied first |
| Asahi/macOS boot-policy route | macOS only | — | No — Asahi FAQ explicitly: iPads "do not support running custom OS kernels"; even a userspace jailbreak would not help; "A boot ROM exploit might help, should one exist" |

**Kernel-level class (jailbreak windows — not Linux-boot-capable):**

| Window | M1 iPad status |
|---|---|
| iPadOS 16.6–17.3.1 | Dopamine 3.x "Titan" PPL/SPTM bypass; real-device support capped at 17.3.1 ("no SPTM bypass for iOS 17.4 or later") |
| iPadOS 16.0–16.6.1 | KFD-family kernel exploits (unofficial M1-targeting builds reported) |
| ≥ 17.4 | No public kernel window (Dopamine: SPTM-device support exists only on Corellium, up to 27 betas) |

One claim in the wild ("DSPloit", iOS 16–18.7.1 + 26.x on M1/M2) is recorded
as **unverified credibility** — unknown account, expansive claim; per the
Phase F standing rule it is treated as unestablished literature until it has
independent grounding. Not evidence.

**Open read (closed 2026-11-05):** the device's exact iPadOS `ProductVersion` is recorded
nowhere: the DFU census cannot observe it (DFU never loads iPadOS), and the
legacy recovery `getenv`/`version` reads returned nothing on this build
(`boot-entry-research.md`; recon §7.4 reconciliation). Read at E0 (normal
mode lockdown, read-only): **27.0.1 / 24A446** — recon doc §10; the verdict
paragraph below was written pre-read and stands unchanged.

**Verdict (class-level):** at every observable version, the public landscape
offers **no Linux-boot path**: the boot-chain class does not reach T8103
publicly (no public ROM image/exploit), and the kernel class by construction
cannot substitute a kernel (Asahi's own FAQ). The instant-win branch is
therefore closed *as a shortcut*; the version read stays on the plan because
it selects the research-platform branch: if the device is ≤ 17.3.1 a
published kernel window (Dopamine) exists and would give an instrumented
PPL/SPTM-bypass platform for runtime study — that is PERSISTENT-tier
jailbreak territory, requires explicit user approval, and is deferred until
the Phase E boot-chain sessions are done, if ever.

## 2. SecureROM T8103/M1 acquisition — recorded absence re-verified

Kickoff §6.3 ordered the long-shot documented. Re-verified 2026-11-04:

- No public T8103/M1 SecureROM dump surfaced in the m1n1/Asahi ecosystem
  (m1n1 documents ROM-tag presence only; Asahi doc set treats the ROM as
  on-chip, never dumps it, and the hypervisor stack starts at iBoot).
- Public 2026-08 security literature records: "no Boot ROM exploits have
  been publicly disclosed for M-series chips", and that all A12-and-later
  (thus all M1/M2/M3) are not vulnerable to the checkm8 class.
- Our only ROM-adjacent observable remains the device-reported silicon build
  tag from the recorded DFU census: SRTG `iBoot-5540.0.0.400.2` (T8103
  generation tag; class-level).

Recorded verdict: **absence stands.** The dump problem remains its own
sub-project. Program consequence (unchanged from kickoff §4): the reachable
surfaces for T8103 are iBSS/iBEC/iBoot/SPTM public images (we own them) plus
the *device-side* DFU door — the Working plan Phase E probes.

## 3. SPTM/TXM hardening verification vs Apple Platform Security

Verification of kickoff §4.4 against published sources, cross-checked with
our t8103 SPTM binary maps from Phase C/H5:

**Apple's published matrix:** SPTM (with TXM) is supported in "the A15 or
later and M2 or later SoCs" and replaces Page Protection Layer on supported
platforms; "PPL and SPTM enforce the execution of signed and trusted code on
all platforms with the exception of macOS". So the M1/T8103
*iPadOS-runtime* reading of the guide is PPL-era hardware.

**Class-level consistency of our maps:** the t8103 SPTM *image* we audited is
real public-artifact material (H5 campaign ran on it), and the behaviors we
recorded — tier/gate discipline in the verb router, anti-tamper `BRK`
classes, the SoC-token MRS wall in the recorder — are consistent with the
published RE picture of the SPTM/TXM architecture (frame types owned
exclusively by SPTM; retyping rule sets; TXM operating in GL0 behind ~40
selectors; GENTER/SVC/HVC entry discipline; domains SPTM/XNU/TXM/SK). The
public analyses (2025–2026 RE series and the 2025 arXiv Exclaves paper)
validate our mapped surfaces rather than contradicting them.

**Reconciliation note:** the m1n1 hypervisor docs describe SPTM as required
to boot XNU on M1–M3 *macOS* targets, while Apple's matrix lists M1 as
outside the SPTM columns. These are not contradictory artifacts — macOS and
iPadOS ship different policy matrices on the same silicon — but the
device-side question ("what monitor actually runs when J407 boots XNU")
stays a device-side observation, deferred; it does not affect any Phase E
session plan below, none of which touches the XNU runtime.

**Frontier note:** the public jailbreak series records that for ≥ iPadOS
17.4 no real-device SPTM bypass exists (virtualization-only). If the device
turns out to be ≥ 17.4, both the kernel-class escape margins *and* our
SPTM/TXM image study sit on open public frontier — strengthens the research
value, does not change the Phase E plan.

## 4. Phase E session plan (announcement-first; SAFE → PERSISTENT)

Per kickoff §9 and the phase-D close-out, each session below is announced
before the device is connected: title, tier, traffic description, halt
rules, recovery, expected duration, and what gets logged. All logs stay
side-local (`~/research/j407-bootchain/`); identifiers (ECID/UDID/serial,
nonces) never leave the side logs — no exceptions.

### E0 — census + version read (SAFE, normal mode, ~10 min)

- Device connected in **normal mode (iPadOS on, unlocked)**.
- Read-only lockdown census (`pymobiledevice3 lockdown info` field set):
  `ProductVersion`, `ProductType`, platform/arch class; compare identity
  class against the recorded baseline census.
- Also: clarify nothing is installed, opened, or written; no pairing
  prompts beyond the host's existing pairing state.
- Output (recorded 2026-11-05): read `27.0.1` / `24A446` /
  `mBoot-20457.2.37`, identity class matching the DFU baseline; verdict
  finalized in `dfu-ep0-recon-2026-10-27.md` §10 — device is outside every
  public window, so the program itself is the frontier and the session
  plan below proceeds unchanged.
- **User instruction: plug the iPad in normally when announced.** The DFU
  switch happens separately afterwards; do not pre-enter DFU.

### E1 — DFU baseline re-freeze (SAFE/READ-equivalent, DFU mode, ~15 min)

- Enter DFU following the recorded recon §7.2 procedure (DFU re-entry is
  also the standing recovery rule for every session).
- Replay exactly the recorded-safe traffic classes from the 2026-10-24b
  baseline: GETSTATUS (bR0)/GETSTATE reads, `getenv build-style`
  send+drain, the class-matrix sends already exercised; every request
  keyed to an H4 class map entry; NO uploads, NO new request shapes.
- Success criterion: baseline census reproduced (sticky bState 0x05
  included); deltas recorded as class-level.
- Halt-on-wedge: any GETSTATUS non-recovery hang → stop session, DFU
  re-entry recovery, display failure class in recon doc.

### E2 — registration-noun staged-synthetic probes (ELEVATED, per-item approval)

- The never-run nouns `firmware` / `devicetree` / `ramdisk` receive staged
  synthetic bytes (shapes pre-derived from the H3/H4 emulated record:
  expected instant-reject/wall classes; JSON-controlled error behavior).
  Each probe is announced individually before it is sent.
- DFU-door shape probing (kickoff §9.1 ELEVATED): controlled
  control-transfer replay from the §7.2 baseline keyed to the H4 class
  map; health-check after each probe; DFU re-entry as recovery.
- Success criterion: class-level observable events recorded
  (accept/reject/drain behavior), matching or diverging from emulated
  predictions; every divergence gets its own §7.x recon entry per Phase F
  doc-first rule.

### E3 — custom-payload boundary test (PERSISTENT, per-step approval) — not planned

Only if a Phase-D/E candidate looks executable (kickoff §9.3): two-hop
non-persistent PoC → separately-approved persistent-hold stage. Standing
precondition: backup verified, per-action confirmation, halt-on-wedge,
log everything byte-level. Nothing currently activates this tier.

## 5. Announcement template (used verbatim before each session)

```
[Phase E announcement] Session EX — title | tier: SAFE/ELEVATED/PERSISTENT
Traffic: <one sentence: what leaves and enters the device>
Recovery: <halt-on-wedge rule + DFU re-entry>
Fallback: if anything wedges: disconnect, reconnect, re-run recovery steps
Duration: ~N min
Approval: user connects device = approval for SAFEs; ELEVATED/PERSISTENT
  need a per-item "go" in chat before each probe.
```

## Sources (public, cited)

- Asahi Linux FAQ and m1n1 docs (iPad/kernel restrictions; hypervisor targets).
- Paradigm Shift usbliter8 writeup thread; ipadlinux.org community index
  (iPhone 11 Linux boot built on Hoolock Linux + m1n1; checkm8-era iPads).
- palera1n docs (arm64-only, arm64e excluded) and select-iPad-Air page.
- Dopamine 3.0–3.0.7 coverage notes (window table; Titan PPL/SPTM bypass;
  17.4 cutoff; Corellium-only above).
- Apple Platform Security guide, "Operating system integrity" / SoC
  security tables (SPTM/TXM, PPL, KIP, SPRR, EMTE).
- Public RE series on SPTM/TXM (frame types, domains, selectors) and the
  2025 SPTM/Exclaves academic paper; 2026-08 public summary "Boot ROM
  Security on Silicon Macs" (no public M-series ROM exploits/dumps).
