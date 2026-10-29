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
3. **"Out-of-mapping" checks resolved:** the earlier `0x1b0030`
   flag was an arithmetic slip — `adrp(0x1b000)+add(0x30)` = **`0x1b030`**,
   which is inside `__DATA_CONST` (it is the `EVENT_BOOTSTRAP_TXM`
   slot of the state/event name arrays — see §6). True out-of-span
   targets like `0x130020` land in `__LINKEDIT`'s zeroed vmsize tail
   (`filesize 0x20` vs `vmsize 0x4000`) — a runtime patch area the
   loader fills; noted, not walked.

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
- **H5-M2 (done — see §6): per-domain handler binding + pointer
  format + per-board tables.**
- **H5-M3 (next): verb-dispatch entry points in the `0xe4000–0xe5f00`
  mass resolved to call sites, so the verb-fuzz harness can enumerate
  valid FUNCTIONIDs per domain from the name arrays.**

## 6. H5 milestone 2 — pointer format + dispatch binding (done)

Artifacts: `audit-sptm/ptr-tables.md`, `tags-classification.md`
(superseded — its "tag ≤ 0x40" filter mis-modeled meta; superseded by
the corrected meta analysis), scripts `sptm_ptr_tables.py`,
`sptm_tagged_classify.py` — all side-local.

### 6.1 Pointer-word format (calibrated)
Data-segment pointers are 8-byte words `{target32, meta32}`:
`target` = low32 (file offset; runtime VA adds the constant
`0xfffffff027000000` slide), `meta` = high32 metadata:
- `meta & 0x8000_0000` (bit63) ⇒ **PAC-authenticated code pointer**
  groups share diversity values (e.g. `0x8060d507`, `0x8010e833`,
  `0x80b0d507`, `0x8010c231`, `0x80200000`);
- bit63 = 0 ⇒ rebase/data pointer (`0x0010/0x0020/0x0040/0x0050/0x0080/
  0x00d0…0000` patterns).
The earlier "(tag32, ptr32) / tag 0x10 registry" framing was a
misread: the registry words are meta `0x00100000` data pointers to
name strings. Apple boot-image fixup metadata, not a custom tagging
scheme.

### 6.2 Enum-name arrays (the registry's true scope)
One contiguous name-table run in `__DATA_CONST`
(`0x1aeb0–0x1b090`, meta `0x00100000`, strings in `__LATE_CONST`
`0xf004–0xf582`):
1. `0x1aeb0–0x1af50` (21) — `SPTM_DOMAIN`, `SPTM_DISPATCH_TABLE_…`
   (`XNU_BOOTSTRAP, NVME, SART, UAT, HIB, GEN3_DART_XNU/SK,
   T6000/T8020_DART_XNU, RESERVED2`), terminator-ish last entry with
   meta `0x00500000`;
2. `0x1af78–0x1b028` (23) — `STATE_*` (SPTM/SK/TXM bootstrap,
   called-by chains, XNU panic, dispatch-panic-spin,
   re-entered-by-XNU…);
3. `0x1b030–0x1b0a0` (18) — `EVENT_*` (bootstrap, call/return,
   exception, context-saved, resume, panic-spin, guest enter/exit).

### 6.3 Per-state handler bindings (sparse PAC rows)
Right after the arrays, sparse `{index-or-aux, sigil fn}` blocks
(polarity discussed below):
- aux `2` @`0x1b0a8` → meta `0x8040d7e1` fn `0xe4b08`;
- aux `1` @`0x1b0c8` → meta `0x8200d7e1` fn `0xe4af4`;
- aux `0x13` @`0x1b1c8` → meta `0x8200d7e1` fn `0xa3430`
  (inside the cluster-hot fn `0xa2dac+0x684` — the panic path);
- aux `4` @`0x1b2c8` → meta `0x80c0d7e1` fn `0xa2270`, then aux `3`
  and aux `1` rows.
Index mapping against the `STATE_*` array *suggests* (adjacency-level,
not byte-polarity-proven): state `XNU_PANIC (19)` → `0xa3430`;
bootstrap-state rows → `0xe4af4`/`0xe4b08` (in the verb-plumbing
mass); `SPTM_CALLED_BY_SK (4)` → `0xa2270`. Zeros elsewhere =
unfilled/implicit slots.

### 6.4 Per-domain verb tables (name + handler pairs)
The `{name(meta 0x00100000), fn(meta 0x80xxxxxx)}` registration
row-pattern, resolved to containing pacibsp functions:
- **NVME endpoint table `0x18e38–0x18f28`** (10 rows, fn/name
  alternate at ~0x10–0x20 stride): names `SPTM_NVME_ENDPOINTID_{ENABLE_CG,
  MAP_PAGES, UNMAP_PAGES, INIT, ADMIN_QUEUE_REGS, IOQA_REG, IOSQ_REG…}`
  adjacent to fns `0xc4aa8, 0xc4348, 0xc3ce4, 0xc37f0, 0xc361c,
  0xc33b0…` — pairing polarity (name-before vs name-after-fn)
  deferred to M3; registration order = FUNCTIONID order.
- **HIB endpoint table `0x1edf0–0x1ee80`** (6 fn/name rows):
  `SPTM_HIB_ENDPOINTID_{HASH_HIBSEG_PAGE, HASH_PAGE, FINALIZE_HASH,
  FINALIZE_SK, FINALIZE_IMAGE, IOFILTER_PROTECTED_WRITE}` adjacent to
  fns `0xc11ec, 0xc18d8, 0xc1a70, 0xc1f00, 0xc2078, 0xc2670`.
- **SART op table `0x19438–0x19480`**: unnamed fn `0xc7820` first,
  then `SPTM_SART_SET_STATE → 0xc7270`, `SPTM_SART_MAP_REGION →
  0xc67bc`, plus SART violation-name array + fn `0xc7c00` at
  `0x1a810`
  (`SART` domain block `0x1a800–0x1a838`).
- **TXM permission/branch table `0x186d0–0x18750`**:
  `-shared-ro`, `-shared-rw` names + an 8-entry array (meta
  `0x80100a98`) of code addresses all inside fn `0xb3694`
  (`+0x1b8…+0x20c`, step 0xc) and `TXM-ro/rx/bx` — TXM region classes
  ↔ branch slots.
- **DART-policy helper chain `0x1add0–0x1ae58`** (12 entries, all
  meta `0x8xx0c231`): targets `0x0e5888–0x0e5cbc`, i.e. inside the
  verb/registration plumbing mass — the same functions the
  `0xe4000–0xe5f00` region references when registering domains.
- **Core handler column at `__DATA_CONST` start `0x18010+`**
  (meta `0x80200000`): 14 dense fn pointers (`0xb506c … 0xb650c`)
  = the default verb handlers (spaced 0x18–0x30 rows with aux data
  pointers into `__LATE_CONST` `0x139xx`).

### 6.5 Per-board config family + routing evidence
- **Triple-interleaved per-board tables `0x099e68–0x09c828`**
  (`__LATE_CONST`): three meta classes `0x8060d507` (68 fns),
  `0x8010e833` (68), `0x80b0d507` (67) interleaved on ~`0xd0` stride
  plus aux-int rows (`0x00030000`-class) — 60+ board/variant rows each
  binding three function groups. Preceded by `EXEC_MODE_*` enum names
  (`EXEC_MODE_{SPTM,SK,TXM,XNU,XNU_ROZONE_RW,XNU_USER_*}_DEFAULT`,
  stride `0x40`) and `IOMMU_ID_*` names at `0x1f3f0`
  (`SHART, SART, NVME, UAT, DART_T8020, DART_T8110, DART_T6000,
  CPUTRACE, DART_GEN3`).
- SoC-routing answer (class level): the t8103 build's dispatch tables
  are named by IOMMU *family*; `IOMMU_ID_DART_GEN3` and the
  `VIOLATION_T8020_DART_*` code list coexist in one build — family
  selection is a runtime/decomposition property, so "GEN3_DART_*"
  covers this SoC's IOMMUs while T8020/T8110/T6000 remain compiled in.
- Build tag found: **`SPTM-820.0.22|2026-08-08:13:06:06.975686|`**
  @`0x1f458`.

### 6.6 Remaining for M3
1. Verb-dispatch entry points: which `0xe4xxx`–`0xe5xxx` functions
   perform the table lookup (the `0x1aeb0` names + aux rows are
   already enumerated), i.e. the exact FUNCTIONID→handler resolution
   call site(s);
2. Complete per-domain row extraction (the DART-family tables'
   `(name, fn)` arrays — analogous to NVME/HIB/SART blocks — plus the
   remaining board-table columns) into a single machine-readable
   FID→fn map;
3. Then H5 verb-fuzz hook (harness H5) can be designed from the
   enumeration (class-level only; target = SPTM running in a research
   sandbox, not a user device).
