# J407 (iPad Air 5, M1/T8103) — Linux-boot feasibility research
## Final report — 2026-10-29 · branch `research/j407-entry-2026-10` (PR #4)

Research question: **can this iPad boot Linux?** Substance of the answer:
**not through any path that exists today, and here is the complete map of why** —
plus everything we learned about how this device's boot chain actually works,
statically and on real hardware.

This report is the index and conclusion. The evidence-of-record lives in
`docs/dfu-ep0-recon-2026-10-27.md` (device + runtime record), the older
`docs/boot-image-recon-24a446.md` (compression/selector groundwork), and
`docs/handoff-j407-2026-10-27.md` (ground rules, repo state, method log).

---

## 1. TL;DR

| Question | Answer |
|---|---|
| Does the boot chain accept unsigned/custom images through any documented path? | **No.** Every check runs before any use of uploaded bytes; all audited chains are fail-safe. |
| Did any device experiment show a crack? | **No.** Recovery uploads ACK everything silently; `go`/`bootx` accept-silent; console never printed anything but its baseline. |
| Is there a live exploitable bug in the audited iBoot code? | **No.** All audit candidates closed (`C1` latent-only/unreachable, `C3`/`C4` dead, `C5` stubs, Phase-B defensive). |
| Is there a public exploit for this SoC generation (A12+/M1-class, T8103)? | **No.** checkm8 = A5–A11; **usbliter8 (June 2026) = A12/A13 only**; the design that enabled those is stated as addressed on newer generations. T8103 = newer generation. |
| Would rule expansion change this? | No. Using an exploit requires the exploit to exist. A T8103-class BootROM bug would be original research of the rarest kind (and unpatchable-if-found, hence highest value). Not manufacturable on demand. |
| What is the realistic route to Linux on *an* iPad? | Older checkm8-era iPads (A7–A11): proven community chains (Hoolock Linux, Project Cascadia). The M1 iPad Air is research frontier, not a working path. |
| What does this repo deliver? | The complete map: static boot-chain audit, live protocol record for recovery mode, command-table reconstruction, tooling and claim disciplines, honest negative results. |

## 2. What we know, by domain (evidence pointers)

### 2.1 Secure-boot structure of this build (static)
- Load base derived base-free: `K = 0x1fc04c000` (§7.8 method); runtime VA = `K` + raw offset; Ghidra addresses == raw offsets.
- Recovery-mode session architecture: personality registration `0x11c684`, poll `0x11c818` → work `0x11c26c`; transfer service `0x893d4` endpoint-codes `0x80`(ep0-in)/`2`(ep2-out)/`0x81`(ep1-in)/`4`(ep4-out = the upload sink); byte-collect loop `0x11d9a0` sends on `0x81` (§7.8).
- Console ring: lock-protected masked circular buffer; append `0xc03e0` (pointer-registered), getc `0xc04d8`, four static read-callers; drain = flush `0x11d8c4`/commit `0x11dac4` or pump `0x11d9f8`; single-copy by construction (§7.10; echo/value duality closed as non-artifact).
- DFU (ep0) acceptance chain fully byte-mapped: state object
  `[0x23b9a8,+0x120)`; block-len/cum checks at `0x11cd34`/`0x11cd4c` BEFORE
  any write; write-grant gate `0x7e60c` with by-default-empty grant window
  and unset bypass bit → default-rejecting (§2.3/2.4; handoff item 1,
  status 2026-10-27).
- IMG4/Memz consumer cluster `0x81ca0`/`0x8205c`/`0x220a4`; measure layer `0x2030c`/`0x72be0`/`0x715a4` defensive by construction; validity_cb-NULL = fail-closed boot panic (handoff item 1, status 2026-10-28).
- Compression/decoding: LZFSE raw `0x144d5c` / container `0x144a0c`/`0x145e44`; VLC tables `img+0x207d88`/`0x207da8`; entrance budgets {20,20,64,256}, FSE state-sum checks ≤ {64,64,256,1024}; `0x891` = small-workspace variant (type word `0x3a98` bounds header field1 — the audited SMC stream fails it deterministically) (§2.12, Q4).
- Container/staging: NO `splt` staging exists on this build; validator `0xb5b68` is check-only and fails deterministically on the in-file `bvx2` stream; consumer `0xb58c0` never engaged; stream consumed in place via list-loader `0x125b6c` (§2.11, Q1/Q2).
- Boot-object identity: shared-base resolution `img+0x159bb8` == `0x1FC1A5BB8` portal root (§2.10); `0xd5960`(entry `0xd5600`) = pointer-registered reader of `boot-object-manifests`/`secure-boot-hashes` feeding `0xc2100`.
- Boot-context C2 (lower confidence; prior doc governs, unchanged) (§4/§8 item 4).

### 2.2 The complete console command surface (static — §7.8 + §7.12 addendum)
- Simple noun units stride `0x78` at `0x15c370`…: reboot (structurally special), reset `0x51c8`, bgcolor `0x51c8`, setpicture `0x5210`, **firmware `0x52ac`**, devicetree `0x50a0`, getenv `0x5698`, saveenv `0xc51ec`, setenv `0x51c4`, setenvnp `0xc52e4`, clearenvp `0xc550c`, ramdisk `0xc5574`, rsepfirmware `0x56f8`; tag-variant unit at `0x15c988`.
- Noun strings at `img+0x211290..`; hidden units BELOW the table: **`bootx` special unit `0x15b180`** (packed `0x40000001`-family = vendor `0x40` bRequest **1** binding — the headless-restore execution channel), **`memboot` `0x15b1f8` → handler `0x1164`** (4-char tag key `0x3c427478` via `0x12e518`; grant-band calls), **`go` `0x15b270` → handler `0x183c`** (9-byte blob key at `img+0x1e31af` via `0xe6a0`; deeper BLs `0x82054`/`0x86390` = IMG4 band).
- Boot verbs take **registered boot-object keys** — this is the load-bearing explanation of the on-device silences (below).
- Env registry stride `0x20` at `0x15bab8..`: `auto-boot`, `boot-args`, `debug-uarts`, `pwr-path`, `anid`, `apt-carveout-size-mb`, `auto-boot[-once]`, `audio-features`, `backlight-nits`, **`one-time-boot-command`**, `ramrod-kickstart-aces`, `device-material`, `dev-unset-debug-enabled`, `idle-off`, `force-upgrade-fail`, `security-mode-change-enable`, `com.apple.System.tz0-size`, `upgrade-retry`, `preserve-debuggability`, `panicmedic-panic-count/telemetry`…


### 2.3 USB protocol shapes (static + live-confirmed)
- Recovery upload: ctrl `0x41/0` opener (vendor, interface-recipient) + bulk EP `0x04` OUT chunks + ZLP iff total % 512 == 0 (pmd3 `irecv.send_buffer` shapes).
- Console: send = ctrl `0x40/0` + NUL-terminated text; drain = ctrl `0xC0/0`; execution verbs = ctrl `0x40/1` (`go`/`bootx`) — pmd3 `restore/recovery.py` sanctioned forms: upload iBEC → `go` bR1; upload RestoreKernelCache → (class `0x21/1`, suppressed) → `setenv boot-args …` → `bootx` bR1.
- Recovery composite geometry: cfg1 itf0/alt0 class `0xfe` `[OUT 0x04 bulk]`; itf1/alt0 none; itf1/alt1 `[IN 0x81, OUT 0x02]`.
- Personality census: `05ac:12ab` = NORMAL iOS composite (the earlier "recovery" label was wrong); `05ac:1281` = recovery iBoot. Enumeration is the authority — never trust the screen text over the PID.

## 3. Device arcs — what was tried and what happened (§7.1–7.12)

All arcs user-approved, all non-persistent, all stopped on console-wedge rule. Full protocol logs are LOCAL ONLY (never committed).

| Arc | What ran | Result |
|---|---|---|
| ROM DFU behavior (§7.2) | SecureROM DFU arcs, sticky bState 0x05, ABORT-detach timing 24.2 s re-enum | behaved per state machine; no error-latch anomaly |
| Normal-mode boundary (§7.4) | composite claims/PID | `12ab` = normal iOS; no DFU-class service |
| Recovery reach (§7.7) | entry via buttons; census; `getenv build-style` → `RELEASE`; env-lookup STALLs; class-DFU = STALL | console LIVE; audited chain NOT externally served |
| Upload reject-path (§7.11) | opener + 7 malformed/unsigned vectors (4B…512B+ZLP) | **all ACKed, no STALL, console unchanged (`RELEASE\0` 8-B replay), no wedge, nothing persistent** |
| Consumer-trigger (§7.12) | `go` bR1 ×4 (bare / 24-B / 412-B structural unsigned IMG4 ×2) + `bootx` bR1 ×2 | **six-for-six accepted-silent; console byte-identical every drain; personality stable; consumer chain never observable** |

Interpretation recorded in §7.12: the verbs are recognized (unknown envs STALL; these did not) and are registration-keyed — synthetic staging never produces a boot object, so `go`/`bootx` early-exit silently. The IMG4 consumer remains dark on every sanctioned path.

**Tooling lesson (mandatory for any future device work):** open ONE USB handle per recovery session and reuse it. The handle that performs the first successful bulk write keeps working; subsequently created handles fail bulk OUT with `Errno 13` until device re-enumeration.

## 4. Security-audit conclusion (the defensive reader's view)

- ep0 DFU acceptance chain: fail-safe by construction (checks precede dereference; default-rejecting write grants; bypass bit has no image-side writer).
- IMG4/Memz consumers: all length trust flows through validated readers with panics; no attacker-reachable desync found.
- Candidates C1 (upper-bound-only guard — latent-only; 346,415 guard evaluations, zero backward events on genuine stream), C3 (no reachable writer), C4 (dead-by-environment arm), C5 (micro-thunks) — all closed. svc census 373 sites with family counts; gate templates dumped; no mini-setter reachable.
- **Net: no exploitable defect reachable from attacker-supplied bytes was found in the audited iBoot image.**

## 5. Exploit landscape as of 2026-10-29 (web-verified)

- **checkm8** (2019): BootROM use-after-free, **A5–A11** — permanent, public.
- **usbliter8** (Paradigm Shift, 2026-06-19): BootROM code-exec for **A12/A13** (incl. iPad 9th gen) via the Synopsys DesignWare USB controller setup-packet/DMA-pointer underflow + SecureROM config flaw; unpatchable; PoC published; coordinated disclosure with Apple. **Per the researchers: newer generations "have addressed the underlying issue."**
- **This device (iPad Air 5, M1/T8103)**: newer generation ⇒ **no public BootROM exploit**. Also no downgrade path (Apple stopped signing older iPadOS), so software-only trust-store bypasses that reached A12…M1 kernels on *specific iOS versions* (CoreTrust class, revocable by update) are unusable on an already-updated device.
- Forensic vendors list M1-iPad extraction using closed/commercial chains — irrelevant to a public, self-serve Linux route.
- The boot chain additionally hardened on this generation by SPTM/TXM replacing PPL from A15/M2-class silicon — smaller early-boot surface by design (Apple Platform Security guide).

**Consequence for rule expansion:** making `go`/`bootx` speak, or forging a boot object, does not run custom code — the signature wall sits above all of it. The only class of finding that changes this device's answer is a T8103 SecureROM/early-boot bug — and none is public. That is a research frontier measured in person-years, not something any tool — us included — can produce on demand; and the community evidence says Apple's newer-generation redesign specifically removed the bug-classes that produced checkm8/usbliter8.

## 6. Booting Linux on *an* iPad — the proven routes (community state, 2026)

- **A7–A11 / T2 era** (`checkm8`-vulnerable): active ecosystem — **Hoolock Linux** (iPhone/iPad/iPod/Apple TV), **Project Cascadia** (iPad mini 1, current kernel + Alpine, Sept 2026), iBSSloader lineage, postmarketOS-on-iPad demos. Works, documented, self-serve.
- **Apple-Silicon Macs** (same M1 silicon as this iPad): Asahi Linux — because Apple deliberately exposes custom-boot enrollment there. **That switch does not exist on iPadOS.** This single design difference is why "same chip, different answer."
- **M1 iPad Air**: research frontier only. No public chain. What exists publicly for Macs (m1n1, Asahi tooling) cannot be applied because the entry door (macOS boot policy) doesn't exist on iPadOS.

## 7. Data and ground rules honored throughout

- Never committed: ECID/UDID/serial/Apple-ID values, nonces (NONC/SNON), USB serial strings, `UsbDeviceSignature`-class values; all device TSVs (`dfu-*-log-*.tsv`) are LOCAL ONLY and `.gitignore`d.
- Never issued DETACH (0x00)/ABORT (0x06)/CLRSTATUS (0x04) without explicit approval; no DFU-class requests in recovery (they stall, §7.7).
- No exploit code was produced targeting the device; audit + mapping only.
- All device work announced first; console-health check after every step; halt-on-wedge rule; nothing persistent was ever left on the device.

## 8. Repo inventory (everything we hold)

```
docs/
  final-report-j407-2026-10.md   ← THIS report (entry point)
  dfu-ep0-recon-2026-10-27.md    ← record of record: §2 static sections, §7.1–7.12 device record, §8 plan
  handoff-j407-2026-10-27.md     ← ground rules, method/tooling log, repo state, status timeline
  boot-image-recon-24a446.md     ← prior-generation compression/selector groundwork (context)
tools/                            ← flat layout, same style as the rest of the repo
  recovery-probes-README.md       ← probe ground rules + the persistent-handle discipline
  dfu_probe_recovery.py           ← §7.7-era acceptance probe driver
  upload_probe_recovery.py        ← §7.11 reject-path matrix driver
  boot_trigger_recovery*.py       ← §7.12 consumer-trigger ladder (parts 1–3)
  (+ analysis tooling with PYTHON_TESTS wiring: boot-image-*, dfu-fuzz, host-preflight …)
tests/                            ← make test = green
research side-local (NOT in repo): raw_iBoot.j407.RELEASE target image, Capstone insns.pkl,
  Ghidra 12.2 project, pc4/ decompile cache, wrapper artifacts, all device TSVs — paths and
  method in the handoff.
```

## 9. Open items (all optional, none blocking the conclusion)

1. Naming-only polish of resolved clusters (`0xb6814`/`0x136cf8`, ring ops) — cosmetic.
2. Device arc (needs approval, WOULD complete observability): `firmware`/`devicetree` registration nouns with staged synthetic bytes — expected to make the registration layer visible; per §5 it will not change the Linux answer.
3. T8103 SecureROM: no public dump is known; obtaining one is itself research. Out of scope of this project.

## 10. Closing statement

The static audit, the live-protocol record, and the exploit-landscape survey
converge on one answer: **this iPad's boot chain is intact, fail-safe, and
publicly unbroken for its chip generation; booting Linux on J407 requires a
security discovery that does not exist publicly as of October 2026.** What we
have built instead is the complete, verified map of the boot machinery that
enforces that answer — reusable for anyone studying Apple 2022-era recovery
boot behavior.
