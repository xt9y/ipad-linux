# Phase D — H1 IMG4-parser grammar & first mutation campaign (T8103 program)

> Program: `docs/kickoff-t8103-rom-research.md` (§7 passes) · branch
> `research/j407-entry-2026-10` · dates 2026-10-30/31 · host-side only
> (device not involved). All harness code, corpora and ledgers stay
> side-local (`~/research/j407-bootchain/`); this file carries the
> class-level map only: grammar structure, fault classes, guard
> placement, reject behavior, robustness verdicts. No injection
> chains, no ready-to-run corpora. `make test` green at commit.

Analysis state (side-local): audit of the **iBoot payload** of the
on-device image (sha `dc3cb25f…`, iPadOS 27.0.1 24A446), emulated under
a fault-recording substrate; every structural claim below comes from
real instructions of that payload or from recorded emulation runs, not
from memory. Evidence: `h1_*` driver ledgers + the grammar report
(side-local `harness/reports/h1-grammar-2026-10-30.md`).

## 1. What H1 is

The stage that parses the launch-dictionary container family built from
DER/ASN.1-style TLV nodes: the outer container holds a 0x16-tagged
magic node (`IMG4`), a nested `{payload, manifest?, recovery?}` region
whose payload is headed `IM4P`, and the post-stage checks pair the
manifest (`IM4M`) or recovery (`IM4R`) variants. The parser is shared
by boot-path image handling on this build; the objective was a
**completeness read of its input grammar** and a **robustness verdict
of its validation order** for the Phase E rebase-table work.

## 2. Grammar structure (decoded end-to-end)

**Pipeline.** One wrapper fn parses the outer container and writes a
child-descriptor array (0x10-stride `{ptr,len}` pairs) onto its stack
frame; four post-stages then re-parse each region into the output
struct, each guarded by a schema **island** — a static table of
0x18-stride entries `{store_offset, expected_form, flags}` with:

| flag | bit | semantics (all from instruction decode) |
|---|---|---|
| optional | 1<<0 | entry may be skipped; mismatch advances instead of failing |
| wildcard | 1<<1 | any child form accepted |
| no-store | 1<<2 | child consumed without writing to the out array |
| rebase | 1<<3 | child stored as `{TLV_head, full_TLV_size}` (copied/deferred) |

Stage tables and their child slots (census, side-local ledger):

- top capture, cap 4: magic node, payload region (rebase), manifest
  slot (optional), recovery slot (optional)
- payload stage, cap 4–6: magic-bearing headers up to two optional
  trailing blob/sequence slots
- manifest stage, cap 5: `IM4M` header node, 0x02 integer, rebase slot
  for the hash-set, blob slot, trailing sequence
- recovery stage, cap 2, via the second capture fn: header node +
  rebase slot.

**Fourcc whitelist** closed by movz/movk census: `IMG4` (wrapper),
`IM4P` (two sites), `IM4M` (manifest stage), `IM4R` (recovery stage).

**Leaf classifier** fn (per-child TLV walker): two modes — strict
(rejects a declared length exceeding remaining with err 3) and
clamping (min(remaining, declared) + writes the form to the caller).
Canonical-integer reader (strict): leading-zero or empty integer
values reject with err 3.

## 3. Guard census (fault sites)

| Guard | Site (relative to payload base) | Tripped when |
|---|---|---|
| BRK 0x5519 | wrapper tail, +0x132954 | outermost input node's value: `value_len==0 && value_ptr!=0` |
| BRK 0x5500 | capture head, +0x136864 | `{ptr,len}`-span carry overflow (`cmn` over-range) |
| BRK 0x5519/3/5 | walker, +0x1360f0/f4/f8 | block invariant asserts on node extents |

Emulation lesson (class-level): BRK faults surface only via the
faulted PC after an exception stop — memory-hook telemetry alone is
silent for these sites.

## 4. Reject classes (clean x0 returns)

| x0 | Meaning |
|---|---|
| 0 | accept |
| 2 | form/schema mismatch (incl. fourcc pairs failing the stage assert) |
| 3 | walker/canonical reject: declared > remaining, non-canonical or empty integers, malformed tag encodings |
| 5 | required slot unfilled |
| 6 | appended-descriptor head integer value > 1 (`csel`-hi path) |
| 7 | overflow / end mismatch at container extent |

**Shared stage-worker shape** (recovered from the two post-stage
bodies): head-gate `{len==0 || ptr==0}` → skip-and-accept; → child
capture; → fourcc/length assertion on the region's head slot: value
shorter than the tag → −1, longer → +1, exact length → strict reader +
memcmp; any nonzero is surfaced as x0=2.

## 5. Mutation campaign v1 — verdict distribution

Ledger (side-local): 3 canonical accept seeds re-anchored byte-exact
against recorded chains evidence, then 273 single-point mutations
(truncation, length ±1/0/longform, tag orbit, fourcc write, integer
value/canonicality, opaque-value writes, byte delete, rng flips).

| Verdict class | Count of 273 |
|---|---|
| silent accept | 30 |
| walker/canonical reject (3) | 156 |
| schema/fourcc reject (2) | 79 |
| end-mismatch (7) | 6 |
| appended-int-value reject (6) | 1 |
| **fault: guard-top-zero-len-value (BRK 0x5519)** | **1** |

**Sole fault:** lengthening→zeroing the outermost container's value
byte hits the wrapper-tail guard at 0x132954 — i.e. the zero-value
invariant is reachable from a canonical seed by **one byte**. No
walker-range or overflow-guard fault is reachable through short-form
length encodings (they cap at 255); those require the long-form
length encodings queued as campaign v2.

## 6. Robustness verdict classes (the 30 silent accepts)

| Class | Verdict |
|---|---|
| S1 | label/fourcc children other than the whitelisted heads carry **no validation** at this layer |
| S2 | opaque byte values (blobs, set members, certificate data) are unvalidated — expected for opaque fields |
| S3 | the manifest version integer's **value** is unconstrained (only DER canonicality applies) |
| S4 | the appended-descriptor second integer is value-unconstrained |
| S5 | the ≤1 value rule binds **only** the appended descriptor's first integer (0 accept / 2 reject-6) |
| S6 | zero-length values are structurally accepted **inside** nested regions (guard is outermost-only) |
| S7 | hash-set internals have **no schema island**: any child encodings absorb without parse effect |
| S8 | nested length drift absorbed by declared-size consumption + clamp semantics |
| S9 | the appended-slot value rules are **keyed on the container's own tag form**: re-typing the container demotes it to an unchecked blob slot |

Context: none of these are authority-relevant fields on this layer
(no trust-anchor data at this parse depth); they quantify how much of
the grammar is decoration vs enforced, which is the input the rebase
work (Phase E) must respect.

## 7. Boundary probe round

| Probe shape | x0 | Verdict |
|---|---|---|
| zero-length value on the magic child | 3 | walker-cascade reject — guard NOT reached |
| zero-length value on the payload child | 2 | schema reject at capture — guard NOT reached |
| empty set inside the manifest region | 2 | REJECTED at the manifest stage's assert |
| empty set inside the recovery region | 0 | accepted (head-gate skip) |

Acceptance asymmetry: the recovery stage tolerates any
`{len==0 || ptr==0}` region, the manifest stage does not — the gate
difference is now pinned in the instruction sequence, not inferred.

## 8. Campaigns v2 — longform / capacity closure (2026-10-31)

Second campaign (111 anchored seeds, same substrate): long-form length
encodings and duplicate/capacity classes, targeting the four
non-reachable guard sites from §3.

**Long-form canonicality gate.** Every long-form length encoding —
including two- and three-octet encodings whose declared value exactly
matches the actual content (`81 3e` for 62) — rejects with err 3 at
every walk position: the walker enforces DER **minimal-length**
canonicality. Poisoned-descriptor shapes (rebase slots declared ≈ 2⁶⁴
across the `cmn`-carry region) therefore never reach the stage-feed
capture heads.

**Guard-reachability closure.** With minimal-length enforced and all
over-declared short-form lengths extent-checked (or absorbed only
inside island-less set bodies), the rebase-overflow guard
(0x136864) and walker-range asserts (0x1360f0/f4/f8) are **not
reachable from the input grammar**; output-plane writes stayed flat
across all 114 runs. The only input-reachable fault class in the whole
campaign set remains the outermost zero-value guard (§5).

**Duplicate / capacity verdicts** (new grammar facts):

| Shape | Verdict |
|---|---|
| both optional top slots filled (manifest + recovery regions) | accepted |
| any additional head child beyond the schema slots |reject (err 2) |
| container with children beyond its capture capacity | reject (err 3) |
| appended descriptor with more integer children than its table | reject (err 3) |
| hash-set bodies with multiple arbitrary children | accepted (island-less internals) |
| short-form length maxima (0x7e/0x7f over-declares) | reject via extent checks, never via the range asserts |

The post2/post3 assert-ordering asymmetry (§7) stands as phase-local
evidence that stage invariants differ per slot kind — carried into the
Phase E rebase-table requirements.

## 9. Hygiene

Harness drivers, corpora, and every mutation ledger remain side-local.
This repo change adds documentation only. Commit contains no seed
bytes, no device identifiers, and no exploit-capable artifacts —
analogy note: the S-class table is an audit of validation coverage
(ordering/shape), not a bypass procedure.
