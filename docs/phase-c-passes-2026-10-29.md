# Phase C — first adversarial passes record (T8103 program)

> Program: `docs/kickoff-t8103-rom-research.md` (§7) · branch
> `research/j407-entry-2026-10` · date 2026-10-29 · host-side only (no
> device work in this phase step). Analysis state stays side-local
> (`~/research/j407-bootchain/audit-j408-delta/`, `audit-sptm/`);
> this file carries the class-level map. `make test` green at commit.

## 1. Delta audit — j407 vs j408 consolidated boot image (build 24A446)

**Method** (local scripts, side-local
`delta_audit_j407_j408.py` / `delta_code_diff.py` / `delta_tags_scan.py`):
full-file byte diff → runs merged at gap 256 → region census with
per-region decode-rate classification (Capstone ARM64 linear walk,
4-B-aligned instruction-start share), per-region nearest-earlier
`pacibsp` start, ±window string sweep; instruction-level alignment diff
for the code-encoding regions.

**Engine census (validation):** the linear decode of the j407 payload
reproduces **exactly 474,556 instructions** — the prior session's
`insns.pkl` count — on a fresh Capstone run (and the payload is
byte-identical to the published audit target: sha `dc3cb25f…`). The
prior project's instruction census is therefore reproduced, not
inherited, against the exact on-device image.

**Headline numbers:**

| Metric | Value |
|---|---|
| Payload sizes | 2,255,320 B both boards |
| Differing bytes | 465,949 of 2,255,320 = **20.660%** (board delta is large) |
| Merged regions (gap 256) | **51** |
| Decoded insns j407 / j408 | 474,556 / 474,521 |
| `pacibsp` function starts | **4,330 / 4,330 (identical)** |
| Keyword-tag hits near any region | only the boot banner (`iBoot for j407`) |

**Structure read-out:**
- Regions 1–47 decode ≈0% (pure data): the board delta mass is
  **per-board data, not code** — and 44 of the 51 regions end exactly at
  **64-KiB granules**, the signature of table islands laid on page
  granularity (literal pools / config tables); no string tags flank
  them, i.e. silent binary config, not XML-like structures.
- Truly code-interleaved changed slots exist in exactly two regions:
  - **Region 2 (`0x308d0–0x31000`)**: one 8-byte constant changes —
    the value pair `…00 00, 88 88 25 fc` vs `…18 89 25 fc`, i.e. a
    pointer that **moves by +0x90 between boards**; mapped via
    `VA − K(0x1fc04c000)` it targets `file-offset 0x20C888`,
    **inside diff-region 51** (`0x2015e0–0x20d000`, the VLC/noun-blob
    neighbourhood). Semantics: a data object near/inside region 51 has
    shifted by 0x90 in the j408 build — the "code" change is a
    **relocated pointer to shifted data**, not new code.
  - **Region 33 (`0xfc010–0xfd000`)**: a **16-byte board-specific blob**
    (`0xfc010–0xfc01f`) sits near a "uuid"-class label field; the rest
    of the region is alignment noise from the linear walker resyncing.
- Regions 48–51 (15–48 KB each, decode 41–78%) lie in the deep
  data band (>VLC-table offsets `0x207d88`); their partial decodes come
  from linear-walk misdecodes of high-entropy data, to be resolved when
  per-region structure framing lands (below).
- Region 1 = the boot banner string (`iBoot for j407 …` vs j408) — the
  sanity anchor proving these are genuinely the two board builds.

**Conclusions (write-up-able):**
1. **One code frame, per-board data.** Both boards share 4,330-citizen
   `pacibsp` function layout; the 20.66% byte delta is overwhelmingly
   per-board literal/config table islands (64-KiB-page granular,
   stringless). Apple derives the two boards from one binary template —
   the inverse mapping (code is common ⇄ deltas are board config) is a
   cheap board-coupling classifier for later parser-bug hunting.
2. **Data-layout shift, not code change.** The single documented
   pointer delta (+0x90) means board deltas can *move* per-board data
   within the blob band — offset-based analysis across boards must
   re-anchor per board, and any audit candidate anchored at an absolute
   offset in another board's build does not trivially transfer.
3. **Census reproduction** validates the whole host pipeline
   (capstone decode → counts) against the prior project record.

**Known gaps:** no Ghidra binary in the environment at present (the
12.2 project state survives, the tool is not installed); segment-level
decompile framing of the data band is therefore deferred; the decode%
heuristic is not a semantic classifier for high-entropy regions.

## 2. SPTM t8103 — structured pass v1 (the generation's monitor, in hand)

Artifacts (side-local `audit-sptm/`): recon, disasm, calls, xref,
identifier census. Fresh numbers recap (from the Phase B step): Mach-O
arm64, 1,228,832 B, 95.3% decode coverage, code head + data tail, 370
`pacibsp` starts, 3,386 `bl` edges, hottest routine `+0xf5a20` (873).

**The identifier census is the big find.** 138 unique `SPTM_*`
identifiers survive in the clear:

- **Dispatch-table namespace** (the monitor's verb router is keyed by
  named tables):
  `SPTM_DISPATCH_TABLE_{ CPUTRACE, GEN3_DART_SK, GEN3_DART_XNU, HIB,
  NVME, RESERVED2, SART, SHART, SK_BOOTSTRAP, T6000_DART_XNU,
  T8020_DART_XNU, T8110_DART_SK, T8110_DART_XNU, TXM_BOOTSTRAP, UAT,
  XNU_BOOTSTRAP }`
- **FUNCTIONID namespace** (mailbox verb set):
  `{CONFIGURE_ROOT, SWITCH_ROOT, SET_SHARED_REGION,
  CONFIGURE_SHAREDREGION, MAP_PAGE, MAP_TABLE, UNMAP_REGION,
  UNMAP_TABLE, UNMAP_DISJOINT, UPDATE_REGION, UPDATE_DISJOINT,
  UPDATE_DISJOINT_MULTIPAGE, NEST_REGION, UNNEST_REGION, RETYPE,
  CONDEMN_LEAF_TABLE, UNCONDEMN_LEAF_TABLE, SLIDE_REGION,
  SURT_ALLOC, SURT_FREE, GUEST_DISPATCH, GUEST_EXIT,
  GUEST_STAGE1_TLBOP, GUEST_STAGE2_TLBOP, GUEST_VA_TO_IPA, HIB_BEGIN,
  HIB_FINALIZE_NON_WIRED, HIB_VERIFY_HASH_NON_WIRED,
  SIGN_USER_POINTER, AUTH_USER_POINTER, BATCH_SIGN_USER_POINTER,
  IOFILTER_PROTECTED_WRITE, LOCKDOWN, REGISTER_CPU,
  REGISTER_EXC_RETURN, OUTPUT_AREA, FIXUPS_COMPLETE, CPU_ID,
  SPTM_SERIAL_DISABLE, SPTM_SERIAL_PUTC, CPUTRACE_ENDPOINTID_*}`
- **DART policy helpers** (policy lives *in the monitor*):
  `DART / dart / dart_register_iommu_restriction /
  dart_check_restrictions / dart_assert_prop_size /
  dart_compatible_to_iommu_id / dart_common / dart_id / dart-sep /
  dart-tunables-instance-`
- Sources-tree leakage still present: `Sources/SPTM/sptm/iommu/dart/…`,
  `…/boot/hib/…`, `SPTM_T8020_DART_{MAP,UNMAP}_TABLE`,
  `nvme-iboot-sptm-security`, `txm-secure-channel-base/size`.

**Interpretation (carefully scoped):**
- SPTM exposes a **SoC-keyed dispatch table family** for DART domains
  (`T8020`, `T6000`, `T8110`, `GEN3` × `XNU`/`SK`). Notably, a
  **t8103-named table is NOT present** in a t8103 build while
  T8020/T6000/T8110 names are — the plausible reading is that the
  t8103 DART routing lives under the family-generic key (`GEN3_DART_*`
  or an unnamed default path); this is a **named Phase D question**
  (resolve the dispatch keys → how a DART request is routed per domain).
- SART / SHART / UAT are sibling IOMMU classes (role naming follows
  the m1n1-community convention; flagged as such, not Apple-documented
  here) — the monitor manages *several* translation families, which is
  exactly the config architecture the usbliter8 class depended on
  being correct at ROM level. The **DART-config named check now has a
  monitor-level, off-device, fuzzable surface**: dispatch-table
  resolution + the `dart_*` restriction helpers + verb arguments
  (`CONFIGURE_ROOT`, `SET_SHARED_REGION`, `MAP/UNMAP`,
  `UPDATE_DISJOINT_MULTIPAGE` = length/finite-range-state minimal pair
  for the class).
- The GUEST_* set (stage-1/stage-2 TLB ops, `VA_TO_IPA`,
  `GUEST_DISPATCH/EXIT`) shows the HYP-domain boundary of the monitor
  — an attacker-relevant surface for any guest-threshold bugs, and
  exactly the architecture era's "smaller early-boot surface" design.

## 3. Framework impact on Phase D (harness backlog)

| Harness | Surface | Status / notes |
|---|---|---|
| H1 IMG4/Image4 parser cluster | consolidated iBoot (audited target) | unchanged (kickoff §8) |
| H2 LZFSE/deco chain | consolidated iBoot | unchanged; VLC-table delta region gives fresh corpus material |
| H3 registration/arg paths | consolidated iBoot verbs | unchanged (`go` key / `memboot` tag) |
| H4 iBSS USB (DFU mode) | consolidated image DFU personality | real bytes confirmed (consolidation finding) |
| **H5 (new)** | **SPTM dispatch verb router** | classify: enumerate pages of the tables via xref, replay FUNCTIONID verbs with argument shapes in emulation; the SoC-key table resolution question (§2) is the first static milestone of this harness |
| **H6 (new)** | **j407↔j408 delta-bounded copies** | use delta-region locations to pick paragraph-level corpora from the boards' differing data islands |

## 4. Standing open items (pre-H5)

1. Full decompile frame for SPTM + consolidated iBoot (Ghidra binary
   currently absent on this host; Java is present). Governs how far
   Phase D static milestones can be pushed per session.
2. ROM-level DART-config check stays gated on the Phase B long-shot
   (no public T8103 SecureROM bytes known).
3. Inventory sync for newly written analysis
   state (`audit-j408-delta/`, `audit-sptm/`, scripts) is done in the
   side-local ledger (never committed).

## 5. H5 milestone 1 — SPTM dispatch/verb plumbing located (partial)

Artifacts: `audit-sptm/xref-sptm-t8103.md`, `xrefs-dispatch-ids.md`,
`delta-t8103-vs-t8112-report.md`, `identifiers-sptm-t8103.md`
(all side-local; script `sptm_dispatch_analysis.py`).

### 5.1 SPTM-as-Mach-O segment map (t8103 payload)
| Segment | vmaddr (base `0xfffffff027000000` +) | fileoff | filesize |
|---|---|---|---|
| `__TEXT` | +0x0000 | 0x00000 | 0x18000 |
| `__DATA_CONST` | +0x18000 | 0x18000 | 0x8000 |
| `__LATE_CONST` | +0x24000 | 0x20000 | 0x80000 |
| `__TEXT_EXEC` | +0xa4000 | 0xa0000 | 0x5c000 |
| `__LAST` | +0x100000 | 0xfc000 | 0x4000 |
| `__DATA` | +0x104000 | 0x100000 | 0x14000 |
| `__BOOTDATA` | +0x118000 | 0x114000 | 0x18000 |
| `__LINKEDIT` | +0x130000 | 0x12c000 | 0x20 (vmsize 0x4000) |

`VA − 0xfffffff027000000 = file offset` is a single constant slide, so
the flat Capstone walk maps directly onto the t8103 SPTM layout. The
"second code mass" (`0xa0000–0xfc000`, the 99.9%-decode delta band) is
**`__TEXT_EXEC`** — the SoC-varying code; `__LATE_CONST`
(`0x20000–0xa0000`) holds the string/formats blobs; `__DATA_CONST`
(`0x18000–0x20000`) holds the pointer registries.

### 5.2 Located structures
1. **Domain-name registry at `0x1aeb0`** (`__DATA_CONST`): 21
   consecutive tagged pointers of the form `0x001000000000xxxx` whose
   low bits are exactly the string addresses of
   `SPTM_DOMAIN`, `SPTM_DISPATCH_TABLE_{XNU_BOOTSTRAP, NVME, SART,
   UAT, HIB, GEN3_DART_XNU, GEN3_DART_SK, …}` (string cluster
   `0xf004–0xf225` in `__LATE_CONST`). The registry is an ordered name
   table for the domain classes — a stable, parseable dispatch
   skeleton.
2. **Verb/registration plumbing** around `0xe4000–0xe5f00`
   (`__TEXT_EXEC`): extensive `SPTM_DOMAIN` name-string flows
   (dozens of references) + the two hot routines `0xf5a20`/`0xf5a60`
   (in-edges 873/476) recurring as assert/abort/log funnel with
   stack-built records and small verb-id immediates (`w0 = 0x2f/0x4f/
   0x61/0x62/0x70/0x2b/…`). This code mass is the natural
   SPTM-verb-fuzz entry area once decompile framing exists.
3. **Out-of-mapping resyncs flagged:** a few `adrp+add` targets
   (`0x1b0030`) lie beyond the mapped span; linear-walk artifacts, not
   tables — decompile-framed scanning will drop these false leads.

### 5.3 t8103 vs t8112 SPTM delta (methodology transferred)
1,228,832 vs 1,245,216 B (t8112 is 16,384 B larger), **41.74%** in 10
regions, `pacibsp` 370→385. Unlike the iPad pair (identical code
frame, config-only deltas), **the SPTM SoCs differ in real code mass**
(`__TEXT_EXEC` band and `__DATA_CONST`) — per-SoC monitor builds.
Region inventory (side-local report):
- R2 `0x41e6–0x17000` (0% decode): `__LATE_CONST`-band data incl. the
  memory-registration assert strings ("Attempted to register a managed
  memory reg…", "…unaligned IO r…", "length is greater than the
  maximum", `rc32_dec`, `hib_init_sha_context`) — ready fingerprint
  vocabulary for the IOMMU/registration fuzzing family.
- R3 `0x18010–0x20000` (`__DATA_CONST`), R6 `0xab0d4–0xfb000`
  (`__TEXT_EXEC`, 327 KB!), R10 `0x12c000–0x130020` (the SoC-size
  tail) = genuine code-level SoC divergence.

### 5.4 Milestone status
- **H5-M1 (this record): tables located; verb plumbing located;
  dictionary ready.**
- **H5-M2 (next):** per-domain handler binding (which function
  pointer pairs with which domain name — needs the registry entry
  *buddy* structure followed) + the SoC-routing question (why no
  t8103-named dispatch table). Requires decompile-frame tooling —
  Ghidra binary is not installed on this host right now (Java 26 is
  present); re-install is queued as a next-step unit of work.
