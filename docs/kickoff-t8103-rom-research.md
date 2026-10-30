# KICKOFF — T8103 BootPath Research: "Pwn-to-Linux" program (J407 iPad Air 5)

> **Copy this entire file as the first message of a fresh session.** Work
> happens in `/Users/felixjaschul/ipad-linux` (origin:
> `https://github.com/xt9y/ipad-linux.git`, branch
> `research/j407-entry-2026-10`, pushed HEAD `d6661b7`).
> Read order at session start: `docs/final-report-j407-2026-10.md` → this
> file → `docs/dfu-ep0-recon-2026-10-27.md` (evidence of record) →
> `docs/handoff-j407-2026-10-27.md` (method log).

---

## 1. Mission

Research goal: **make custom code run on the J407 iPad Air 5 (Apple M1 /
T8103) early enough in the boot chain to boot Linux.** The prior phases of
this project (docs in-repo) mapped the entire recovery-side boot chain
statically and confirmed it live. The static+protocol answer was: fail-safe,
silent, no exploitable defect reachable from attacker bytes in the audited
iBoot image; no public BootROM exploit exists for this SoC generation
(checkm8 = A5–A11; **usbliter8 = A12/A13 only**, June 2026).

**Owner's rule change, 2026-10-29:** the owner of the device has EXPLICITLY
enabled the exploit-research scope for this program. Exploitation work on
this one device is now in-scope — Hunt bugs, develop proof-of-concepts,
fuzz, test, break. The prior "no exploit code targeting the device" rule is
historical context, superseded. Nothing here targets anyone else's devices,
accounts, or data.

## 2. Hard rails (not optional — they protect the mission itself)

1. **This iPad only.** All research output is owner-device-scoped. Any
   PoC/technique artifact gets written as class-level research documentation,
   never as tooling aimed at third parties, other people's devices, or
   systems the user does not own.
2. **Reversibility discipline.** BootROM/SecureROM-level bugs, if one is
   ever found, are permanent-by-silicon — that cuts both ways: an iPad
   bricked by a bad experiment is unrecoverable by us. Therefore:
   - SAFE tier (no approval needed beyond the standard announcement):
     census, DFU GETSTATUS/GETSTATE reads, recovery console reads,
     RAM-only `setenv`, upload+trigger sequences already run in §7.11/7.12,
     USB descriptors, purple-boot probing.
   - ELEVATED tier (announce; do; health-check; revert if possible):
     fuzzing campaigns against DFU/recovery, aggressive memory-shape
     sequences, custom staged payloads designed to wedge instead of
     persist. Reboot/DFU re-entry is the recovery plan.
   - PERSISTENT tier (needs one explicit user confirmation per action):
     `saveenv`/NVRAM writes, NOR writes, anything that touches the boot
     chain's on-disk state, SEP interactions beyond read-only. Before the
     first PERSISTENT-tier action ever: the user makes an iCloud/computer
     backup of the iPad.
   - FORBIDDEN tier (even with owner permission — pure damage, zero
     research value): irreversible fuse writes, NAND reformatting without a
     verified backup, SEP-relevant destruction, anything the device cannot
     come back from. A bricked device cannot boot Linux either.
3. **Announcement discipline** — unchanged: tell the user before any device
   connection/work, with the exact phrases: "IPAD REQUIRED IN DFU",
   "IPAD REQUIRED IN RECOVERY", "IPAD REQUIRED IN IOS", "IPAD NOT REQUIRED
   ANYMORE". Console-health check after every step; halt matrix on any
   wedge; re-verify the actual USB PID (enumeration is the authority:
   `05ac:12ab` normal iOS, `05ac:1281` recovery, `05ac:1227` expected DFU).
4. **Data hygiene** — unchanged: NEVER commit ECID/UDID/serial/Apple-ID
   values, nonces (NONC/SNON), USB serial strings, `UsbDeviceSignature`-class
   values, device-unique logs (`dfu-*-log-*.tsv` stay LOCAL, gitignored).
   Repo gets class-level knowledge only. The GitHub remote is public —
   treat every push as publication.
5. **New-artifact rule:** exploit PoCs developed during this program first
   live in a local-only directory (`research/poc-local/`, never pushed).
   Only after a finding is mature do we decide, with the user, what gets
   committed: method/write-up always; weapon-grade artifacts by default stay
   local (the user can relax case-by-case).

## 3. Context digest (what the fresh session must not re-derive)

Already known and recorded in `docs/dfu-ep0-recon-2026-10-27.md` (§2 static,
§7.1–7.12 device) and `docs/handoff-j407-2026-10-27.md` (method):

- **Load base** for the j407 iBoot target: `K = 0x1fc04c000`; runtime VA =
  `K + raw offset`; Ghidra addresses == raw offsets. Target:
  `/Users/felixjaschul/research/j407-bootchain/raw_iBoot.j407.RELEASE`
  (2,255,320 B; sha-256 prefix `dc3cb25f29f25645`).
- **Recovery session architecture**: personality registration `0x11c684`,
  poll `0x11c818` → work `0x11c26c`, transfer service `0x893d4`
  (endpoint codes `0x80`=ep0-in / `2`=ep2-out / `0x81`=ep1-in / `4`=ep4-out
  = the upload sink); collect `0x11d984`/pump `0x11da84`, drain flush
  `0x11d8c4`/commit `0x11dac4`; console ring = masked circular buffer,
  append `0xc03e0` (pointer-registered) / getc `0xc04d8` (§7.10).
- **Complete console command surface** (§7.8 + §7.12 addendum): nouns at
  `img+0x211290..`; simple-unit table at `0x15c370` (stride 0x78); HIDDEN
  units: **`bootx` special `0x15b180`** (packed `0x40000001`-family words =
  vendor `0x40` bRequest **1** binding), **`memboot` `0x15b1f8` → handler
  `0x1164`** (4-char tag key `0x3c427478` via `0x12e518`), **`go`
  `0x15b270` → handler `0x183c`** (9-byte blob key at `img+0x1e31af` via
  `0xe6a0`; deeper BLs into the IMG4 band `0x82054`/`0x86390`); verbs are
  registration-keyed → they exit silent without a registered boot object.
- **pmd3 confirmed shapes**: console send `ctrl 0x40/0` (NUL-terminated),
  drain `ctrl 0xC0/0`, upload = `ctrl 0x41/0` opener + bulk `0x04` OUT +
  ZLP iff 512-multiple, execution = `ctrl 0x40/1` for `go`/`bootx`;
  class-DFU (0x21/0xA1) STALLs in recovery; unknown env names STALL at
  send (i.e., sends DO get parsed — silence on `go`/`bootx` = recognized).
- **Device-arcs results so far**: recovery uploads ACK everything, no
  STALL, no console reaction (7/7 reject-path vectors §7.11); `go` bR1 ×4
  and `bootx` bR1 ×2 all accepted-silent (§7.12). Consumer chain stays dark
  on sanctioned paths — prime hypothesis: registration-keyed verbs
  (`firmware`/`devicetree`/`ramdisk`/`rsepfirmware` = the registering
  nouns per §2.10).
- **Persistent-handle discipline (CRITICAL)**: ONE USB handle per device
  session. The handle that performs the first successful bulk write keeps
  working; any later-created handle fails bulk OUT with
  `USBError [Errno 13]` until the device re-enumerates.
- **Static audit verdicts**: audit candidates C1 (latent-only guard),
  C3 (dead), C4 (dead-by-environment), C5 (stubs) — all closed; IMG4/Memz
  consumers `0x81ca0`/`0x8205c`/`0x220a4`, measure layer `0x2030c`/
  `0x72be0`/`0x715a4` — defensive by construction; LZFSE raw `0x144d5c`,
  container `0x144a0c`/`0x145e44`, decode chain `0xdc808`→`0xdcc84`→
  `0xddb10`, VLC tables `img+0x207d88`/`0x207da8`; `splt` staging does NOT
  exist (validator `0xb5b68` check-only, fails deterministically on the
  in-file `bvx2`); boot-object reader `0xd5960` (entry `0xd5600`).
- **Environment**: macOS host; Python 3.14; pyusb; pymobiledevice3 11.45.1
  (user site-packages); Ghidra 12.2 headless project at
  `~/research/j407-bootchain/ghidra-proj`; Capstone `insns.pkl` (474,556
  insns, instruction-level evidence of record) in the research dir;
  `make test` = 15 suites, must stay green before every commit.

## 4. Reality check for the mission (so nobody wastes the session)

- **Stage-of-chain math:** even a full ROM/iBSS code-exec primitive does not
  boot Linux — it is ONE pierce in a ≥4-stage each-signed chain (ROM →
  iBSS/iBEC → iBoot(+SPTM/TXM era) → XNU). checkm8's power was that the ROM
  itself could be redirected pre-validation, collapsing the whole chain.
  Map every stage's boundary statically FIRST (Phase C) so we know exactly
  how many wins a candidate bug must produce.
- **Where bugs can actually matter here:**
  1. **SecureROM** — unpatchable if found (silicon). Not public for T8103.
     Getting a T8103/M1-family ROM binary is itself a research deliverable
     (Phase B). The class to study first: DesignWare USB-controller
     setup-packet/DMA-pointer underflow (usbliter8) and ROM DFU
     image-loading UAF (checkm8) — both documented publicly for earlier
     generations.
  2. **iBSS/iBEC (DFU second stage)** — public per-device artifacts we can
     obtain from the j407 IPSW immediately (Phase B). Software-patchable —
     BUT the owner allows staying on a vulnerable iPadOS version, which is
     reversible-by-choice and durable in practice. This is the most
     realistic bug-hunt surface that changes the Linux answer.
  3. **j407 iBoot recovery upload/registration chain** (we own this binary +
     harness already) — the "dark" ep4 consumer; a second adversarial pass
     plus emulated fuzzing is cheap for us and untouched territory.
  4. **SPTM/TXM/Exclave era hardening** — study target; the A15/M2+ design
     reportedly removed the classes behind checkm8/usbliter8 (Apple
     Platform Security guide). Verify on the Mac-side artifacts.
- **Instant-win branch to check FIRST (cheap):** read the device's exact
  iPadOS version (normal iOS, lockdown value or recovery
  `getenv`/`version`). If — unlikely but possible — it sits inside a window
  of any public chain (CoreTrust-era ≤16.6.x/17 beta, or anything new since
  mid-2026), the whole "find a bug" program collapses into "use the public
  chain". Check in ten minutes before investing months.
- **Honest success bar for Phase D/E:** even if no bug lands, the program
  yields: the T8103-era audit map, public-artifact corpus, fuzz harnesses,
  and class-level write-ups — real research results either way.

## 5. Phase A — Literature & technique study (session start, no device)

Read first, code after. Targets:

- **usbliter8**: Paradigm Shift's June 2026 writeup + published PoC — the
  DesignWare USB-controller setup-packet storage (3-packet FIFO, DMA reset
  by fixed stride on the 4th transaction; undersized packets stored in
  4-byte chunks → pointer walk-back underflow → SRAM overwrite over
  SecureROM); how A12/A13 (no PAC) vs newer generations differ; their
  Apple coordinated disclosure.
- **checkm8 lineage**: ipwndfu/gaster (bootrom dump, heap grooming, the
  checkm8 UAF lifecycle in DFU image loading), pongoOS, palera1n toolchain
  docs, checkra1n internals writeups.
- **Apple Silicon Mac (SAME SoC family = T8103)**: Asahi Linux + m1n1 —
  the M1 boot chain documentation, iBoot/SPTM/Exclave roles, how m1n1
  interposes, where macOS ships its iBoot artifacts (updates), the
  AppleMacBoot policy system (why Macs can and iPads cannot enroll
  custom boots). This is the closest public design reference for the
  exact silicon we target.
- **Apple Platform Security guide** (SPTM/TXM chapter) for the
  generation's design philosophy and what got hardened away.
- **USB DFU/iBoot protocol spec details** for the target's own behavior we
  already recorded (§7.2: sticky bState 0x05 arcs, ABORT detach timing).

Deliverable of Phase A: a technique-class matrix — for each known exploit
class: chip-generation applicability for T8103, required primitive, what
our recorded device behavior already contradicts/supports.

## 6. Phase B — Artifact acquisition (the missing binaries)

Order matters; verify every SHA; store under
`~/research/j407-bootchain/artifacts/` (side-local, never committed):

1. **j407 IPSW second stages**: `iBSS.j407.RELEASE.im4p` and
   `iBEC.j407.RELEASE.im4p` — fetch the current signed iPadOS IPSW for
   J407 (ipsw tool / idevicerestore fetch), extract + decrypt the im4p
   containers to raw (pymobiledevice3 or igetv; im4p → raw strip via the
   existing `tools/` pipeline used for `raw_iBoot.j407.RELEASE`). These
   are the DFU-door binaries for EXACTLY this device.
2. **Mac M1 (T8103-family) boot artifacts from a public macOS updater**:
   `iBoot-*.im4p`-equivalent payloads inside the updater bundle +
   SPTM/exclave resources if shipped. Same silicon family as the iPad —
   the community's best public reference for generation design, plus a
   delta-audit substrate against our j407 iBoot.
3. **T8103/M1 SecureROM** — long-shot inventory: community ROM dumps and
   research artifacts for desktop M1 (asahi/m1n1 ecosystem, boot research
   repos) and A13/usbliter8-era archives; document whatever can be
   verified public. If nothing exists (expected), record that fact — the
   dump problem becomes its own sub-project; the official-usable fallback
   is the Mac-side family code.
4. **Pad device-side reads we already trust**: while the device is out of
   the box, pull `version`/`security-mode`/`build-style` env read and the
   DFU census to freeze the exact baseline (LOCAL log, class-level in repo).

Exit criteria: checksummed artifact set + a `inventory.md` (side-local)
plus a class-level availability map committed to the repo.

## 7. Phase C — Static audit of the new surfaces

For each artifact (Ghidra headless + Capstone pass like the j407 run):

1. **iBSS.j407 (DFU door, device-exact)** — USB stack routines (the
   DesignWare-class setup/DMA handling is the usbliter8-analog target),
   image load path (length bookkeeping, buffer alloc/lifetime = checkm8-
   analog pointers), post-load validation ordering, and the handoff to
   persistent-image boot.
2. **Mac M1 iBoot/SPTM (family reference)** — diff-audit vs j407 iBoot:
   shared-mode code delta scan (function-level similarity), format-parser
   families (Image4/XML wire, compressed-image paths), the
   boot-object/manifest reader family; establish which functions are
   common vs divergent; hunt generation-shared bug classes fuzzer-friendly.
3. **j407 iBoot second adversarial pass** — prioritize: (a) the ep4 upload
   consumer chain from `0x893d4` (pointer-registered consumers —
   statically "dark", i.e. unreviewed because unreachable via static
   callers: `0xdc808` decode chain, boot-object registry `0xd5960`),
   (b) keyboard/IMG4 length fields vs allocation bookkeeping, (c) the
   three executing nouns' argument paths (`go` blob-key parse, `memboot`
   tag lookup), (d) the exact checks before each signature verify.
   Output = a triaged candidate list (path + one-paragraph rationale),
   same style as the archive's own audit work (§4/§5.1/§6 of the
   recon doc).

Exit: every extracted artifact has a Ghidra project + a written audit map;
candidates ranked by (primitive strength × stage-hit × reachability).

## 8. Phase D — Emulated structure-aware fuzzing (local, no device risk)

Build harnesses ≫ use them. Everything runs HOST-side (macOS/QEMU-less),
executable-unit fuzzing of the binary slices we own:

- **Harness 1 (Image4/IMG4 parser cluster)**: load the j407 iBoot slices
  at their VA (`K+offset`) in a userspace ARM64 emulator (Unicorn-class),
  stub the allocator/panics, drive the parser entry with our grammar of
  valid/malformed containers (magic, len fields, SEQ/property nesting,
  trust-cache paths). Corpus seeds from recon §2 + the §7.11 TSV payloads.
- **Harness 2 (compression chain)**: same treatment for the LZFSE/deco
  chain (`0xdc808` entry, `0xddb10` decoder, VLC tables) — invalid
  frame/bitstream shapes, length-field desyncs, the selector variants
  (`0x891` small-workspace path vs standard).
- **Harness 3 (registration/arg paths)**: the `go` 9-byte key + `memboot`
  4-char key lookups and their object-registration upstreams.
- **Harness 4 (iBSS USB descriptors, once extracted)**: static-shape
  replay of control/bulk requests against the extracted iBSS USB parsers
  in emulation — closest we'll get to ROM-DFU fuzzing without the ROM.
- Discipline: deterministic seeds, corpus versioning, crash triage logs,
  all findings doc-first (`crash→repro→minimal-case→verdict`), PoCs to
  `research/poc-local/`.

Exit: N harnesses with executed-coverage maps; zero/known crashes triaged.

## 9. Phase E — Device-side bounded campaigns (announce + approve rhythm)

Only after Phase D gives candidate shapes. All device sessions follow the
announcement rule; SAFE tier freely, PERSISTENT tier with a per-action
user confirmation and a prior verified backup.

1. **DFU-door shape probing (ELEVATED)**: from the §7.2 baseline (sticky
   bState 0x05 behavior), replay controlled control-transfer sequences
   keyed to candidate classes from the audit/fuzz; health-check after
   each; halt-on-wedge rule; DFU re-entry is the recovery plan.
2. **Upload-chain live probes**: the never-yet-run registration nouns
   (`firmware` / `devicetree` / `ramdisk`) with staged synthetic bytes —
   expected to make the registration layer observable (§7.12 next-arc
   item); if any console output ever appears, capture it as class-level
   evidence in the recon doc.
3. **Custom-payload boundary test (PERSISTENT, per-step approval)**: the
   moment a Phase-D/E candidate looks executable, the plan flips to a
   two-hop test: non-persistent code-exec PoC in the affected stage →
   then (and only then, separately approved) a persistent-hold stage.
   Every first-execution event gets logged with full byte-level evidence.

Exit: a matrix of probing results per candidate; bug-claims always
verified by a second independent reproduction.

## 10. Phase F — Triage, write-up, disclosure

- Doc-first: every finding written as class-level research in the recon
  doc as a new §7.13+ / new §2.13+ section (event → evidence → verdict).
- If anything exploitable-class lands on the J407: coordinate with the
  user on whether/how to disclose upstream (Apple Product Security) —
  the project's precedent is coordinated disclosure (usbliter8 did the
  same); decide BEFORE any PoC artifact leaves the local machine.
- LLM-output hygiene: an artifact/name/claim that resurfaces from an
  earlier LLM pass (ours or an adviser's) is treated as **reused
  hallucination, not new evidence** until it is independently grounded
  in repo evidence or a cited public source. Program step 1 already
  discarded several such fabricated names; this makes the discipline
  standing policy for Phase F triage and any future write-up.
- Repo hygiene unchanged; `make test` before every commit; pushed branch
  stays public — treat push = publication.

## 11. Reading list (public sources, titles first)

- "Unpatchable 'usbliter8' Exploit Breaks Apple A12 and A13 SecureROM Boot
  Chain" (The Hacker News / The Register / SecurityAffairs, June 2026);
  Paradigm Shift publication & PoC (ps.tc).
- checkm8 research corpus: axi0mX ipwndfu; gaster (verygenericname);
  palera1n / pongoOS documentation; Zimperium checkm8 analysis; Elcomsoft
  device-support note (M1-pads listing — treat as commercial-chain
  indicator, not a public tool).
- Asahi Linux / m1n1 documentation + Apple Silicon macOS updates;
  Apple Platform Security guide (SPTM/TXM chapter);
  iPhone-dev-wiki/iphonedevwiki iBoot/DFU notes.
- Existing repo docs (final report, recon record, handoff).

## 12. Quick reference

- Repo: `/Users/felixjaschul/ipad-linux` (branch `research/j407-entry-2026-10`, pushed `d6661b7`).
- Target + analysis: `/Users/felixjaschul/research/j407-bootchain/` (raw
  image, `insns.pkl`, Ghidra project, pc4/ decompile cache).
- Probes: `tools/upload_probe_recovery.py`, `tools/boot_trigger_recovery*.py`
  (+ `tools/recovery-probes-README.md` — the persistent-handle discipline
  lives there; local TSVs `dfu-probe-log-*` are gitignored).
- Tests: `make test` (must stay green).
- pmd3: `~/Library/Python/3.14/lib/python/site-packages/pymobiledevice3/`
  (`irecv.py` = upload/command shapes; `restore/recovery.py` = sanctioned
  boot flows).

## 13. Expectation management (read once, honestly)

- Probability of a NEW exploitable T8103 BootROM/early-boot bug emerging
  from this program: low; the technique-class study says later-generation
  silicon removed the known bug families, and professional teams just
  landed the A12/A13 generation breakthrough in 2026.
- Probability the program still produces real research value: high —
  device-exact second-stage audit map, family delta knowledge, emulated
  harnesses, corpus, and honest records.
- If ANY bug lands, even at "crash instead of exploit" strength: that is a
  class-level discovery for this generation — publish trail, coordinated
  disclosure decision, and the Linux-boot chain-extension path is then
  re-evaluated with the user on live evidence.
