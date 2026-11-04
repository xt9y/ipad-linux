# Phase D close-out — emulated harness series (class-level) — 2026-11-04

Exit criterion (kickoff §8): "N harnesses with executed-coverage maps;
crash ledger triaged (zero or known-crash items with verdicts). Only
then Phase E device sessions re-open, announcement-first."

## Coverage matrix — 6 harnesses, all closed

| harness | repo doc(s) | executed inputs (ledgered) | crash-verdict status |
|---|---|---|---|
| H1 IMG4 parser | `phase-d-h1-grammar-2026-10-30.md`, campaign-v2 closure (`a8d7cca`) | 741 runs (smoke, tag sweep, chains, mutate v1+v2) | 0 unattributed; faults = 5 BRK-guard sites + schema/walker rejects, all class-mapped |
| H2 LZFSE chain | `phase-d-h2-2026-11-04.md` + erratum (`637d934`) | 398 runs (4 byte-exact anchors, 96+183-splice mutations, full-budget re-eval) | 0 faults, 0 hangs; budget artifacts erratum'd; byte-exact vs public reference on every reference-decodable row |
| H3 recorder | `phase-d-h3-2026-10-31.md` | 24 unit runs + 366 H6 interleave rows | 0 unattributed; all faults = labeled walls (sysreg MRS wall, panic-mediator), class-mapped |
| H4 ep0/DFU decoder | `phase-d-h4-2026-11-01.md` | 38 runs | 0 unattributed; class map from the decode |
| H5 SPTM verb router | `phase-d-h5-2026-11-01.md` | 88 runs (22-run tier-wave, thrice) + sysreg-hatch modeling | 0 unattributed; uniform gate/tier discipline, 22/22 expected classes |
| H6 delta-bounded interleave | `phase-d-h6-2026-11-04.md` | 1,101 runs (1,098 ledger rows + 3 preflight controls) | 0 new-class rows; no unattributed faults |

Grand total across the series: **2,313 ledgered runs**, every outcome
either a mapped class or a labeled wall. The phase-D suite (`make
test`, 15 suites) is green at close.

## Discipline trail

- Every harness committed class-level only; runtime sig-checks on
  entry anchors; byte-verification of corpora and deltas before use
  (H6 refused on drift by construction).
- Inventory (`artifacts/inventory.md`, side-local) holds hashes for
  every corpus and result file, including today's additions.
- Triage rule §5 exercised once for real: the H2 "stop extents"
  re-read revealed budget artifacts; that finding was re-measured
  (46 + 49 runs at 200M/75 s) before rewriting the class story —
  measurement first, labels second.
- Phase F standing rule respected: no claim in this series rested on
  prior-session text alone; all anchors were re-established from
  bytes.

## Substrate changes during the phase (recorded for reproducibility)

- emu.py: the SPTM tag-band mirror mapping became opt-in
  (`Emu(..., tag_bands=True)`); the iBoot image runs band-free, which
  is exactly the recorded H1–H4 record semantics. The wholesale
  neutralization (pac/ret/authbr/VM-extent/ldapr) is unchanged apart
  from the already-recorded H5 additions (ldapr verified a no-op on
  the iBoot image: 0 sites).
- The behavior-preservation proof: the new H6 preflight regression
  gate reproduces H1/H2/H3 canonical classes on the current substrate
  (passing), and H5 re-verified green post-change (22/22,
  `expectation_failures=[]`, 2026-11-04 ledger).
- Harness-side instruments added during H6/H2-close:
  `harnesses/h6_deltas.py` (verify/preflight/corpus/waves),
  `harnesses/h2_caprecheck.py` + `harnesses/h2_crosseval.py`
  (full-budget re-measurement pattern: wall-vs-budget as the
  natural-termination discriminator).

## Known-crash ledger summary (verdicts)

- All fault classes across H1–H5 sit at mapped guard/wall sites
  (container guards, the recorder's unmodeled-sysreg wall, panic
  mediator, anti-tamper brk) — emulated-environment labels, not
  device reachability claims.
- H6 added the interleave no-data point: real sibling-board
  divergence bytes do not produce any class outside the maps.
- No new crash classes; nothing beyond class-level description was
  produced (§5).

## What re-opens next

Phase E device sessions re-open per the standing rule: coordinated-
disclosure conversation and announcement first, device sessions after
— elevator: the harness series is the emulated half of the evidence
base; device-side probes remain un-run and out of scope until that
conversation.
