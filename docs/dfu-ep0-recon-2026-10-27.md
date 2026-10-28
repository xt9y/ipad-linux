# J407 DFU ep0 recon — candidates-only static audit (2026-10-27)

> **Status 2026-10-28 (overnight continuation): C1/C3/C4 closed, Phase B audit
> complete, svc census + gate templates recorded (§3–§6). The main remaining
> work is device-side and requires the iPad.**

Session continuation of `research/j407-entry-2026-10` at `c24d202`. **No device was
connected and none was used; every statement below is from static analysis of
`~/research/j407-bootchain/raw_iBoot.j407.RELEASE` (sha256 `dc3cb25f29f25645…`,
2,255,320 B) via the cached capstone instruction list and — newly this session —
Ghidra headless decompilation.** All addresses are raw file offsets (== prior doc
coordinates). For any *legacy REA/Hopper* addresses in older docs: REA = raw + 0xB8.

Compliance: no ECID/UDID/serial/nonces/USB strings in evidence; raw firmware, wrapper
artifacts and emulation logs stay outside Git; docs-only diff; class-level facts only.

## 1. Tooling hand-over: Hopper/REA decompiler → Ghidra 12.2 (headless)

The Hopper license is being dropped, so REA/Hopper is no longer the decompiler of
record. Replacement installed this session:

- **Ghidra 12.2** via `brew install ghidra` (formula; pulls `openjdk@25`).
  Headless entry: `/opt/homebrew/Cellar/ghidra/12.2/libexec/support/analyzeHeadless`.
- **Ghidra project**: `~/research/j407-bootchain/ghidra-proj` (inside the research
  dir, **outside Git**). Analysis of the 474,556-instruction image completed in 41 s.
- **Derived analysis copy** (never committed, lives in the research dir next to the
  raw file): `~/research/j407-bootchain/work_raw_nopac.bin`
  (sha256 `d190f4c72a9e5f81…`). It is a byte-for-byte copy of the raw file where the
  9,306 decoded PAC instructions are replaced one-for-one with register-flow-preserving
  plain forms (`pacibsp/autibsp/paciasp` → `nop`; `retab/retaa` → `ret`;
  `braaz+b xN` → `br xN`; `blraaz/b xN` → `blr xN`). Every substitution is
  interchangeable with the capstone ground truth in
  `/…/iboot-rea/insns.pkl` (474,556 insns) — the *original* raw file is never modified.
- **Addressing simplification**: Ghidra loads the copy with
  `-loader BinaryLoader -loader-baseAddr 0` / `AARCH64:LE:64:v8A`, so **Ghidra
  addresses == raw offsets** with no offset rule. The +0xB8 wrapper convention is
  retired with Hopper (old docs keep their recorded REA values).
- **Ghidra scripts** live in `/…/iboot-rea/scripts/` (cache dir, local only).
  First one: `DecompileAt.java` (decompile functions at raw addresses, write
  `<hex>.c` into `/…/iboot-rea/pc4/`). Cache convention continues: `pc3/` = REA
  pseudocode dumps (Hopper era), `pc4/` = Ghidra decompiles.
- REA remains installed solely as a *manual* curiosity channel; its Hopper provider
  crashed during this session and was not revived. Nothing in the record depends on it.

PAC caveat documented for future reads: the v8A `slaspec` has no PAC vocabulary, so
PAC-related instructions must go through the derived copy; instruction-level facts of
record stay capstone-based.

## 2. Phase C closure — DFU ep0 write path, byte-level

### 2.1 DFU state struct = one 0x120-byte object at `0x23b9a8`

The "individual globals" from the Phase C map (`0x23b9a8`, `0x23b9b0`, `0x23b9b8`,
`0x23b9bc`, `0x23b9c8`, `0x23b9e8`, …, up to but not including `0x23b9f8`) are fields
of **one 0x120-byte DFU state object `[0x23b9a8, 0x23b9ac8)`**:

| offset (from `0x23b9a8`) | size | field | evidence |
|---|---|---|---|
| +0x00 | u8 | state byte (DFU state machine) | `ldrb` @0x11cb74, writes @0x11cc74 etc. |
| +0x08 | u32 | "last block / fill" marker (zeroed on accept at 0x11cdf4) | `str wzr,[x21,#8]` |
| +0x0c | u16 | tail position in the staging buffer | `str w8,[x19,#0xc]` @0x11cc44 |
| +0x10 | u32 | cumulative bytes received (`0x23b9b8`) | `ldp w8,w9,[x3]` @0x11cd4c |
| +0x14 | u32 | expected total (`0x23b9bc`) — **same `ldp` pair** | @0x11cd4c |
| +0x18 | u32 | timeout value (`0x3200/0x3208/0x3209/0x320f…`) | `str w9,[x8,#0x18]` sites |
| +0x1c | u16 | phase halfword | `strh w9,[x8,#0x1c]` |
| +0x20..+0x38 | ptrs | staging-buffer descriptor card used by the copy calls | `ldp x9,x1,[x21,#0x20]` @0x11cdcc |
| +0x40 | desc pair | GETSTATE append ring / response desc base (`0x23b9e8`) | `ldp x9,x11,[x10,#0x40]` @0x11cb78 |
| +0x50 | desc pair | response desc high half (`0x23b9f8`) | @0x11cb7c |

That resolves next-move item #1 from the handoff: there are **no per-field init
stores to `0x23b9bc`/`0x23b9c8` because the struct is initialized in bulk**.

### 2.2 The initializer: raw `0x11c294` (+ thunk `0x11c668`)

- Raw `0x11c294` (`pacibsp`) is the DFU state initializer: `x0` (param) decides
  init-vs-restore; both paths call the tiny **argument-materializing thunk at raw
  `0x11c668`** (`bl 0x11c668` returns with `x0 = x1 = 0x23b888`, `x2 = 0x23b9a8`,
  `x3 = 0x188b70` — Ghidra pseudocode `FUN_0011c294` / call sites `11c2c0`/`11c2cc`):
  - `param == 0` → `bl 0xd2ed0` with `w5 = 0x120` (bulk-init the full struct;
    second call-shape recorded at `0x11c2d0/0x11c2d4`).
  - `param != 0` → `bl 0xd2c84` (`0x11c2c4`).
- `x0 == x1 == 0x23b888`: the **18 × 16-byte service gate-slot array
  [0x23b888, 0x23b9a8)** (the `braaz *0x23b888..0x23b968` PATCH TABLE from the
  earlier audit) is initialized **as part of the same blob** — the gates live
  directly below the state object and travel through the same descriptor-based init.
- `x3 = 0x188b70` descriptor template (48 B; three `[ptr, ptr, u32, u32… ]`
  records, same shape family as the known descriptor templates `0x188728`,
  `0x188ee8`, `0x188ea0`).
- Callers of the initializer (capstone xref sweep): **only `0x86cb4` and `0x86d90`**,
  both inside the USB bring-up function (`0x85df0` cluster documented earlier).
- The bulk-copy helpers are used industry-wide in the image (call-graph noise);
  `0xd2c84`/`0xd2ed0` both funnel pointer-validation helpers (`0xd2de8`, `0xd2e5c`,
  security-mode gate via `0xd2e5c` returning `local != 1`).

### 2.3 Landing pad: the `svc #0xc5` gate and the two write arms

Acceptance chain raw `0x11cd18..0x11ce40` (context: DFU ep0 OUT data stage finish):

1. `0x11cd34` `ldr w8,[0x23b9b0]` (block length) `cmp w0, w8` — mismatch →
   timeout `0x3209`, state = `0xA` (`0x11cd68..0x11cd80`).
2. `0x11cd48..0x11cd58` `ldp w8,w9,[0x23b9b8]` = {cum Received, expected Total};
   `adds w8, w8, w0` (w0 = received) and `cmp w8, w9` — **cum+received > expected →
   timeout `0x3208`, state `0xA`** (`0x11cd5c..0x11cd80`).
3. `0x11cd94..0x11cdac`: `svc #0xc5` gate. `x0 != 0` → **secure arm**:
   `add x0, x9, x8; mov x4, x20; bl 0x119160` (raw `0x11cdb8`) then, on success,
   reload the full state card and `bl 0xd2c84` (`0x11cddc..0x11cde4`) — finalize:
   `cum += received`, `last-marker = 0`, timeout = `0x3200`, state = `5`
   (`0x11cde8..0x11ce0c`).
   `x0 == 0` → **alt arm**: `bl 0x8c3ac` (raw `0x11ce18`), success → same
   finalization (`0x11cdc0..`), failure → `0x11cedc` (error marker `−1` at
   `+0xaa`, flag `+0xa9 = 1`).
4. `0x11ce48..0x11ce74`: GETSTATUS-path epilogue: state == 8 → sets `+0xaa = 1`
   (`dfuCoreFlush` marker) and tail-branches `b 0xfaa28`.

### 2.4 Raw `0x119160` — the "append grant" check (resolves next-move #2, part 1)

- `0x119160` is literally `b 0x7e60c` (tail-jump shell; the branch-flush cluster
  0x119154–0x119170 is a set of neighbouring tail jumps).
- **`0x7e60c` = the shared write-grant check** (decompiled by Ghidra, verified
  against disasm):
  ```c
  bool FUN_0007e60c(ulong dst, ulong len /* in_x4 */) {
      if (*(u8*)0x230df2 & 1) return true;              // bypass flag: bit 16 of word 0x230df0
      // else
      end = dst + len;
      if (carry(dst, len)) return false;
      if (*(u64*)0x230e00 > dst) return false;          // base > dst  → no
      return end <= *(u64*)0x230e08;                    // end <= limit → yes
  }
  ```
- **Defaults**:
  - `0x230e00 = -1` and `0x230e08 = 0` set once at raw `0x7e25c..0x7e268`
    (`mov x9, #-1; stp x9, xzr, [x8]`) — an **empty interval**: by default *every*
    grant check fails and DFU-ep0 RAM appends are rejected gracefully (the
    accept path just marks the failure at `0x11ce20`).
  - The bypass bit (bit 16 → byte `0x230df2`) belongs to the 64-bit feature word
    at `0x230df0`. The word is aggregated by many tiny stub probes (bit 5 @`0x7e604`,
    bits 5/20 @`0x7e1f4`, bit 27 @`0x7e1fc`, bit 28 @`0x7e1d8`, bit 26 @`0x7e47c`,
    `0x8400000000` @`0x7e738`, `0x20000000000` @`0x7e83c`).
    **No write path that sets bit 16 was found in the 474,556-insn census**
    (only str-w/masked ORR candidates were excluded; a 32-bit `str w` covering
    exactly `0x230df0/0x230df4` does not occur).
- Grant-check call sites (capstone): `0x11c8, 0x18e0, 0x2210, 0x5124, 0x55c4,
  0xc4070, 0xe28d4, 0xef0bc, 0xef9c8, 0x118658` — a shared boot-arg/DFU-style
  helper, not DFU-specific.

### 2.5 Raw `0x8c3ac` — the alt (non-secure-monitor) writer arm — CLOSED (structural, 2026-10-28 night re-read)

- Full extent `0x8c3ac..0x8c494` (`retab` at `0x8c494`, next `pacibsp` at
  `0x8c49c`) — only **0xEB bytes**; the earlier "huge multi-call shell" reading
  came from listing its callees, not its body. Real disasm is the evidence;
  `pc4/8c3ac.c` still indicative.
- Structure: stack-staged continuation trampoline. Spills 4 args to x24–x27,
  zero-inits a 0x28-byte object at `sp+0x28` (`x28`), materialises call args via
  the `0x8fxxx` micro-thunk cluster (x3/x19-style argument shims — see C5),
  loads `*0x23e5f0` (`0x8f24c`) and saves it at `sp+0x58`, then calls the real
  workers `0xe3740` / `0xe399c` (×2) / `0xe3cd0`.
- Mid-body `svc #0xc2` with `w3 = 0x26` at `0x8c464` (family-0xc2 command 0x26).
- Tail: `ldrb w0,[x20,#0x20]` + `bl 0x8ee48` = flags-only compare of a saved
  value against `*0x23e5f0`. Mismatch → `bl 0x30444` (non-returning panic).
  Match → tail-call the shared epilogue trampoline `0x8fa94` with `x1 = LR`
  (the continuation address), then `retab`. `0x8fa94` confirms as pure
  callee-save restore of the `0x8fac4`-framed neighbour (ldp x19..x28; add sp).
- **All stores inside `0x8c3ac` go to its own frame** (`sp+0x00..0x58`); no
  global/heap stores at this layer.
- Worker `0xe3740` (read fully): region-claim — bulk-inits 0x4000 bytes from
  template `0x159bd0` via `0xd2ed0(dst,dst,dst+0x4000,&0x159bd0,0,0x4000)`,
  then writes a 0x28-byte descriptor card
  `{base, base, base+0x4000, &0x159bd0, 0, 0}` into the slot `[x20,x19)`.
  Panics on zero/misalign/OOB-slot: `0x3039c(0x90)`, `0x3039c(0x97)`,
  `0x13a40c`.
- **Flagged observation**: the alt arm is entered from `0x11cdac` (`cbz x0`
  after `svc #0xc5`) and *skips* the `0x119160` append-grant check entirely —
  that check only ran on the `x0 != 0` arm (`0x11cdb0..0x11cdbc`). On J407 the
  secure monitor is present, so the alt arm is dead-by-environment. Recorded as
  an environment-conditional hardening note, **not** an attacker-reachable path.

### 2.6 Service-patch table artifacts (context, hardening observation only)

- `0x11c668`/`0x7f02c..0x7f104` tiny argument-thunk/stub families are
  Hopper-"orphan"-shaped but are all reachable via `bl` (arg shuffle thunks —
  e.g. `0x7f094` = "move x0..x3 → x4..x7", `0x7f088` = load `0x159bb8`,
  `0x7f02c` = compare against `*0x23e5f0` context pointer).
### 2.7 Scrub/wipe loop (new structural note)

Raw `0x11cf84` = chunked wipe over `param_1` (buffer) with `x4` bytes, stepping
`0x2000` at a time through `0x11cf34(x0=…, x4=len, [0x159bb8])` which tail-branches
`b 0x11d5d8` or `b 0x93f60` conditioned on the `svc #0xc5` result; returns the
accumulated wipe count. `0x159bb8` holds a record template (`b9 5b 1a fc 01 00 00 00,
68 c0 25 fc 01 00 00 00, 01 …`): tagged 0x1fc-prefixed record-pointers chain (the
same template shape as the descriptor records passed to `0xd2c84`/`0xd2ed0`).

### 2.8 The `0x11d018` cluster — DFU-core session init semantics (2026-10-28)

- `0x11db00` = flags-getter thunk: `x19 = *0x20c868` (global DFU-core ctx),
  `w8 = *(x19+1)`; `0x11db10..` = arg-materializer thunks for the descriptor
  calls (`x27+0x98/0xc0` with `&0x188ee8`).
- `0x11d018` (entry step): if the ctx+1 flag is clear, resolves descriptor
  `0x188ee8` via `0xd6590(ctx+0x98, ctx+0x98, ctx+0xc0, &0x188ee8, 0)` — a
  resolver consumer beyond `0xd2c84`/`0xd2ed0` — then gates on `0x100d14(4)`;
  on success issues `svc #0x50` with `w2 = 0xb`, stores the halfword result at
  `ctx+4`, sets `ctx+1 = 1`, returns 0; gate failure → `0x11daec` cleanup +
  `0x3039c(0x1a5)` panic.
- `0x11d0d0` (session init step): when `(*0x20c868)+1 == 1`, allocates two
  0x200-byte blocks (`0x870cc(3)` + `0x11daac`), zero-fills each via
  `0xd2ed0(…,0x200)`, stores into `ctx+0x18..0x48`; then loads the DFU-core
  descriptor cards at `ctx+0x140..0x270` — templates `0x203f80`, `0x203f92`,
  `0x160bb0`, `0x189108`, `0x225d10`, `0x15b538`, `0x159be8` — and paciza-signed
  function pointers for `0x11d29c`, `0x11d320`, `0x11d41c` stored at
  `ctx+0x210/0x260/0x250`: the DFU-core session object's own step-function
  table.

## 3. Candidate list status (crypto/DFU side)

- **C1 (LZFSE match-copy backward-OOB, raw `0x145d80`) — FINAL: latent-only,
  guard holds on genuine input.** The guard pair at `0x145de0..0x145df0` is
  *upper-bound-only* (`cmp x10,x11` against the cursor = `[hx+0x10]`;
  `ccmp w9,w8,#2,eq; b.hs 0x145e24`): there is **no `x10 >= [hx]` floor**, so an
  `x11 − (w22+x12)` underflow would land the source below the window base.
  Exactly two call sites confirmed: `0x1459d8` (`x0=x23+0x18`, `w1=w24+w8`,
  `x2=x19`) and `0x145be8` (`x0=x19+0x18`, `x1=x22`, `x2=x20`, preceded by the
  `0x145c3c` packer flush).
  Emulation proof (night session, instrumented `emu_c1.py` = local-only clone
  of the proven harness with per-call/per-guard telemetry): genuine SMC stream,
  entry `0x144d5c`, selector `0x8a1` — **39,597 calls, 346,415 guard
  evaluations, ZERO `src < base` events, ZERO `src > limit` events, 0 guard
  failures, ok = 39,586 (+11 no-loop early returns), output byte-exact matches
  the expected SMC image (exit 0)**. The `src − base` histogram spans 0..~0x1C0000
  in 64 KiB buckets (an LZ back-reference window into the already-decoded
  prefix); the 55,944 equality hits are the `src == cursor` lane that reads the
  packer accumulator (`x10` switched to `hx+0x18` on that edge).
  Classification stays honest: **"truncated-pointer wrap check missing"** — the
  wrap needs layout conditions not reachable from attacker-controlled bytes;
  driver-B's distance ledger keeps `dist ≤ produced` upstream, and the copy
  loop is bounded by `w1` regardless. Candidate closed as unreachable-on-real-
  input hardening gap.
  Configuration-independence addendum: the padded configuration (`STREAM_LEN`
  `0x39d30` = +0xD padding, selector `0x891`, same entry `0x144d5c`) engages the
  identical engine behavior — output `0x79760` B, sha `7da684741cedf068`
  (byte-exact expected SMC image, `match=True`), 39,597 calls / 346,415 guard
  evaluations / 0 backward / 0 above-limit — so the C1 result holds for every
  configuration that reaches the engine (selector lane does not alter it on
  this stream; only the container entry `0x144a0c` early-outs with 0 engine
  calls, which is not a C1 data point).
- **C2 (lower-confidence, per prior session)** — unchanged; not re-verified this
  session. See `docs/boot-image-recon-24a446.md` for the original *cv*; its status
  stays per that document until the dedicated re-run.
- **C3 (DFU ep0 RAM-append strictness) — FINAL: default-rejecting; no image-side
  writer of the bypass bit exists.** Full bit-level census of feature word
  `0x230df0` and window `0x230e00/0x230e08`:
  - init `*0x230df0 = 0x222c0000` (bits 29/25/21/19/18 — **no bit16**), written
    at `0x7e1b8` in the boot feature-probe function (pacibsp `0x7e17c`, called
    from `0x39b4/0x287e0/0x7dfc8`).
  - all other writers are constant ORRs (bits 28 / 5+20 / 27 / 26 via
    `0x7e1d8/0x7e1f4/0x7e1fc`; upper-half orrs `0x8400000000` @`0x7e738` and
    `0x20000000000` @`0x7e83c`, both through the `0x7f0dc` setter =
    `str x8,[x9,#0xdf0]`) — none touches bit16.
  - the masked writer at `0x7e5ec..0x7e608` (`(v & 0xDFF3FFDF) | 0x20`)
    *preserves* bit16 (sets bit5, clears bits 29/19/18).
  - **new call-graph edge (Phase B tie-in)**: the IMG4 parse fn `0x20e0c` calls
    `FUN_0007e5ec()` plus `0x7e984/0x7e66c/0x7e42c/0x7e6f8/0x7e458` — the
    feature word is mutated (bit5 set) as a side effect of an IMG4 decode, but
    no reachable path ever sets bit16 (whole-file qword scan).
  - three mini-setter hosts `0x7e464/0x7e71c/0x7e828` (`orr x8,x9,#const` then
    `bl 0x7f0dc`) have **no direct `b`/`bl` callers and no file records point
    at them** (§6) — presumed unreachable/dead in this build.
  - the grant window `0x230e00/0x230e08` is preset empty (`0x7e268`:
    `mov x9,#-1; stp x9,xzr,[x8]`); no second writer found.
  Conclusion: DFU RAM-append is default-rejecting in this build; the bypass
  byte `0x230df2` (bit16) has no image-side writer. Candidate closed with the
  presumed-dead mini-setters documented as the only theoretical residual.
- **C4 (alt arm writer `0x8c3ac`) — FINAL: structurally closed** (§2.5).
  0xEB-byte stack-staged continuation trampoline; all stores to its own frame;
  workers panic-guarded (`0xe3740` region-claim); `svc #0xc2` w3=0x26;
  `0x8ee48` context-compare gates the continuation tail-call. Flagged
  observation: alt arm skips the `0x119160` grant check, but is
  dead-by-environment on J407 (secure monitor present). No attacker-reachable
  claim.
- **C5 (THIS session, structural) — FINAL** — *thunk/stub families pretending to
  be procedures.* Tiny arg-shuffle stubs (`0x11c668`, `0x7f02c..0x7f104`,
  `0x7f094`, `0x7f088`, `0x5ec/0x604 …`) are real reachable code that
  HA/Hopper-style orphans mis-cut into false "procedure starts". Any future
  cross-ref pass must treat these as in-body branches, not as procedure entries.
  Night-session extension: the whole `0x8f008..0x8fac4` C4-helper cluster is the
  same species — `0x8f24c` = load `*0x23e5f0`, `0x8ee48` = cmp flags only,
  `0x8f828/0x8ed90` = const-string loads, `0x8f6a4` = `x3=x19`-style arg shim,
  `0x8fa94` = shared callee-save epilogue. Ghidra decompiles several as `return;`
  yet they carry live register semantics — only disasm is authoritative for this
  cluster.

## 4. Phase B audit (IMG4 pipeline / Memz headers) — COMPLETE (2026-10-28 night session)

All six cluster functions plus the measure layer were decompiled (`pc4/*.c`) and
read end-to-end. Verdict: **defensive by construction; every length trust flows
through validated readers with panics; zero new attacker candidates.**

- `0x207c8` — bulk IMG4-card linked-list builder: ≤32 items per call
  (`0x20` cap); per-item span must be `0x1e` via `0x72be0` (twice) + `0x715a4`
  (`== 0x1e`) + measure `0x2030c(...,0x1e,…)`; card tag `img4` (`0x696d6734`)
  @+0x70, size @+0x74, links +0x20..+0x38; object writes bounded by the
  `0x23ce4` span check; list insert with triple-bounded cursor globals
  `0x2153a0..b0` / `0x2153c0..d0`; "linked list item %p corrupted" boot panic
  (`0x30378` + `s_…_0019954b`). Returns item count; any broken invariant →
  `0x30444`.
- `0x20994` — single-item linked-list append: same card layout, same 32-entry
  cap, same triple-bounded cursors and corrupted-panic, same `0x1e` measure
  gate (`0x715a4`/`0x72be0`).
- `0x2030c` — THE length-trust root, validated measure of a 0x1e-span header:
  requires `param_5 ≥ 0x1e` and `param_3 − derived == param_5`; two
  `0x2000000000000010` header compares (+ `0x16` sub-span + 4-byte tail
  check `local_78[3]==4`); secure 4-byte copy via `0xd2c84` + transform
  `0xcf50c`; bounded out-stores `*param_6` / `*param_10`; panics `0x13a40c` /
  `0x30444` on any mismatch. Callers compute nothing themselves.
- `0x72be0` — bounded slot read with `x21 ≤ x19 < x20` panics, returns
  `*(x19+0x20)`; `0x715a4` — svc `#0x62` measure with `param_14`-typed
  dispatch (1/2/3 → `0x115518/0x115a9c/0x1156e8`), else `0x3039c(0x195)`
  panic.
- `0x8205c` — "Memz" ctor (`0x4d656d7a` @+0x08): slot-region bounds
  `x20 ≤ x19 < x21` else `0x13a40c`; size computed by `0x2030c`, stored @+0x04;
  alloc id @+0x00; failure path releases the log context explicitly.
- `0x81ca0` — DFU flush consumer: tag-dispatch Memz/img4 → `FUN_00020e0c()`;
  error codes `0xcf/0xd5/0xdb/0xe1`, log codes `0x3000c/0x3000d/0x4003000x`.
- `0x220a4` — id-getter consumer: tag dispatch, `0x2030c` validate,
  `== *(obj+0x10)` compare; error codes `0x4004001d..22`.
- `0x20e0c` — the deep IMG4/boot-file parse (32 args), full read:
  - **validity check is fail-closed**: item requires validity
    (`(*0x227ef0)(tag) != 0`) with `*(code**)(param_31+0xf30) == NULL` → boot
    panic with `s_image4_callbacks_validity_cb_is_N_001993ff`
    ("image4_callbacks.validity_cb is NULL", non-returning `0x30378`). Success
    further *requires* the validity callback to have run (flag byte
    `*(param_32+0x1dd) == 1`, else final `0x30444` panic). This resolves the
    earlier "validity_cb" side-thread: fail-closed, not exploitable.
  - every error path logs a distinct `0x4004xxxx` code
    (`0x4004000a..0x40040057`, plus `0xd9a/0x4b0/0x382/0x40040204`), zeroizes
    the local flag words, and the final exit **scrubs the whole parse
    workspace** via `0xd2ed0(param_14…, 0, param_18)` zero-fill.
  - **decoder tie-in (Phase B ↔ Phase C/C1)**: the packed-payload path arms the
    LZ engine with `FUN_00147348(0x891)` and decodes via
    `FUN_001473f0(param_14, …, 0x891)`, both behind overflow-guarded extent
    checks (`CARRY8` chains) against `param_18`; reservations `0x2000` (type 0)
    / `0xa400` (type 1, else `0x40040025`). Same engine whose C1 guard was
    proven to hold on genuine streams.
  - crypto payload path: `0x2000000000000010`-header shell parsed via
    `0x13633c/0x136424/0x1363f8/0x136238`; key sizes restricted to
    0x80/0x100/0xc0 bits (else `0x4004000e`), mapped to flags
    `0 / 0x20000000 / 0x10000000`; key material copied via `0xd2c84` bounded
    slices; operations via `0x80fd4(0x11, …)` ×2 + post-transform `0xcf528`;
    16-byte alignment enforced (`uVar16 & 0xf` → `0xd9a`).
  - calls `FUN_0007e5ec()` (C3 masked feature-word writer) — bit5-set side
    effect on this path; bit16 untouched.

## 5. Evidence inventory (this session)

- `pc4/*.c` — Ghidra decompiles (cache dir, not committed). Session 1 (Phase C):
  `119160.c, 8c3ac.c, 11c294.c, d2c84.c, d2ed0.c, 11cf84.c, 11d018.c, 7e60c.c`.
  Night session (C4 helpers + Phase B): `8fac4, 8f24c, 8f008, 8f828, 8f6a4,
  8fa94, 8ee48, 8ed90, 8ed58, 8f030, 8f01c, 8f39c, 8f044, 8f520, 8f6b8, 8f8fc,
  e3740, e399c, e3cd0` + `207c8, 20994, 8205c, 81ca0, 220a4, 20e0c, 2030c,
  23ce4, 72be0, 715a4, 23d4c, 23d18, 30378` + `d2de8, d2e5c, 145c3c, 145d30`.
- `emu_c1.py` / `emu_c1_891.py` / `emu_c1_padded.py` + `emu_c1.log` /
  `emu_c1_891.log` / `emu_c1_padded.log` (LOCAL ONLY, never committed):
  instrumented C1 telemetry harness clones — per-call arg sampling, guard-phase
  `src/base/limit` classification, 64 KiB distance histogram, ok/fail/eq-edge
  tallies. `emu_c1.log` + `emu_c1_padded.log` = the C1 emulation proofs of
  record (identical statistics, two streamlength/selector configurations).
- `disasm_0x11cb00_11d100.txt` — re-dumped from the cached capstone list, fills
  the 0x11cb00–0x11cf00 gap from the previous session's stdout-only slice.
- `scripts/DecompileAt.java` — Ghidra headless script used for all extracts.
- `insns.pkl` — unchanged capstone census (474,556 insns), remains the
  instruction-level evidence of record.

### 5.1 svc instruction census (completed night session)

373 real `svc #imm` sites across the image (disasm-resync census against
`insns.pkl`); top families: `0xc2` ×134, `0xc5` ×73, `0x62` ×24, `0x38` ×10,
`0x50` ×10, `0x71` ×8, remainder single-digit families. Three census hits
(`0xb03c`, `0xcfb0`, `0xd07e`) sit in the data region above the code bounds and
are recorded as false positives — they are data words, not code. Family usage
corroborates Phase C: `0xc5` = config/bulk service (state init, wipe loop), 
`0xc2` = per-command work service (e.g. command `0x26` inside `0x8c3ac`),
`0x62` = the measure service consumed by the Phase B measure layer.

## 6. Gate slots (patch table) — enumerated level recorded (2026-10-28)

The four descriptor templates are dumped (raw offsets; whole-file qword scan at
4-byte step). **No record anywhere in the file points at
`0x7e464/0x7e71c/0x7e828/0x7dff4/0x7f0dc/0x7e60c/0x11c668/0x11db00`** — the
slots resolve to other handlers, which also closes the C3 mini-setter
reachability question.

- Record shape per template: header pair `{0xfc1dxxxx, 0xfc26xxxx}` (code-page
  + BSS-object pointer), then `{len, count, flags}`, then per-slot records
  `{handler-tag 0xfc1axxxx, slot-index, mode-flag}`.
- `0x188b70` (96 B) — the ep0 write-gate descriptor: header
  `{0xfc1d4b71, 0xfc26e0a0}`, `{0x120, 0x8b, 0}`, four per-slot records
  `{0xfc1a7538, 0x10/0x20/0x30/0x40, 0x10000010}` (slot indices 0x10..0x40).
- `0x188728` (96 B): header `{0xfc1d4729, 0xfc26e088}`; records
  `{0x1a5b50,0x40,0xb}`, `{0x1d4751, …}`, `{0x26c718, 0xd0,0x13,0x10000080}`,
  `{0x1a6930, 0x20, 0x10000080}`, `0xfc1a5b50`.
- `0x188ea0` (72 B): header `{0xfc1d4ea1, 0xfc26ef60}`; records
  `{0x1a5bb8, 0x20, 1}`, `{0x1a6218, 0x60, 0x10000002}`, `{0x1a7538, …}`,
  `0xfc1d4ee9`.
- `0x188ee8` (64 B): header `{0xfc1d4ee9, 0xfc26cbb8}`; records
  `{0x1ac3f8, 0x28, 0xb}` and `{0xfc1d4f11, 0xfc26cbcc, 0x60, 0xb}`.
- `0x159bb8` (svc-c5 wipe template, §2.7): `{0xfc1a5bb9, 0xfc25c068, 1, …}`.

Full slot↔handler resolution requires walking the `0xd2c84` resolver over the
`0xfc1axxxx` handler-tag pages — future work, low priority now that the C4 alt
arm is structurally closed and the grant check itself (`0x119160`) is already
read.

## 7. Device validation record — 2026-10-28 (live session)

First on-device session. Every vector set was explicitly user-approved before
issue (connection was user-initiated in DFU; the DFU→recovery flip was
individually approved via question). Raw logs stay LOCAL ONLY:
`dfu-probe-log-20261028-*.tsv` in the session tmp dir (never committed;
contains byte values, errnos, digest prefixes only — no ECID/serial data).
Commit here: class-level facts only.

### 7.1 Personality map (corrected same session — 12AB is NORMAL iOS)

- `05ac:1227` = **SecureROM (BootROM) DFU** and NOT the audited iBoot code.
  Everything recorded against 1227 describes ROM-side code; architectural
  cousins of the audited chain at best. Do not attribute 1227 observations to
  the iBoot image without iBoot-runtime evidence.

- `05ac:12ab` composite (product string "iPad", 5 configurations,
  `SupportsIPhoneOS` = Yes) = **NORMAL iOS MODE**, not recovery. VALIDATED in
  the same session after the correction: Apple's usbmuxd lists the device and
  a lockdown `QueryType` over the mux answers
  `Type = com.apple.mobile.lockdown` — recovery iBSS/iBoot cannot run
  lockdownd, so this is ordinary iPadOS enumeration. Earlier text in this
  session (and the 2026-10-24 mirror notes) had labeled 12ab as "recovery":
  mislabel corrected retroactively; keep table-level artifacts (cfg census,
  errnos) anyway — they now describe NORMAL-mode runtime and remain
  class-level facts.

- Consequence: the `0x11c***`/`0x23b9a8` acceptance chain lives in the audited
  iBoot image, whose USB console actually lives on the yet-unseen RECOVERY
  personality (expected pid family 0x1280..0x1283, the range libirecovery/
  pmd3 DO match). Tonight's 12ab tests therefore say "normal iOS mode does
  not service DFU-class ep0" — expected behavior, not a chain boundary.

- The `irecovery`/`pymobiledevice3` structural note stands as written for
  12ab (not a recovery pid — normal-mode devices are driven through usbmuxd,
  where it appeared), and additionally: both tools DO match 0x1227 as DFU.

### 7.2 SecureROM DFU observations (05ac:1227)

- Fresh-link baseline (2026-10-24 mirror, class-level): GETSTATUS =
  `{bStatus=0x00, poll=50 ms (bytes 32 00 00), bState=0x02, iString=0}`,
  GETSTATE=0x02. Host-visible poll unit = 50 ms; the static constant
  `0x3200` is a state-object field — different layer, keep interpretations
  separated.
- After zero-byte DNLOADs (64 B / 64 B / 32 B — the last one being a
  block_len-mismatch shape per the static model): bState=0x05 sticky across
  ≥6 s and repeated GETSTATUS; bStatus stays 0x00; **no error latch is
  visible at bStatus**; GETSTATUS does not reset to dfuIDLE. This is
  Apple-nonstandard vs. the DFU spec's error-clearing expectation, but it
  describes the ROM's own state machine, not the audited chain.
- Stable fingerprint of record (ROM runtime, state 5): GETSTATUS body
  `0032000005 00` (digest `f8494b2e4891f7c3`); GETSTATE `05`
  (digest `e77b9a9ae9e30b0d`).

### 7.3 Personality flip: DFU → recovery via ABORT

- DFU ABORT (`0x21/0x06`, zero data) on 1227 → immediate detach (USBError
  Errno 5 at t+1 ms; I/O error on control transfer is the detach signature,
  same as the 10-24 mirror).
- 05ac:12ab composite enumerated at t≈24.2 s (~15 s was seen after CLRSTATUS
  in prior sessions — same order of magnitude).

### 7.4 12ab boundary facts (NORMAL iOS runtime — first-read 'recovery' label superseded)

- Interface census (class-level): cfg1 = PTP only; cfg2 = audio + HID;
  cfg3 = PTP + itf1 `0xff` (bulk 0x02/0x83); cfg4 = PTP + two `0xff`
  interfaces (itf2 = multi-alt classic console geometry); cfg5 = full
  composite (PTP + `0xff` + CDC-ACM ×2 + NCM-style data). macOS auto-selects
  cfg5 on enumeration.
- Kernel claims are per-config (normal iOS composites attach NCM/PTP drivers) and re-attach within ~3 s after each config
  switch (claim race): cfg3/cfg4 itf1 are claimable immediately;
  cfg5 itf1 stays Errno-13 (kernel driver holds it; not releasable without
  sudo, no passwordless sudo on this host, no `/dev/tty.usbmodem*` exposed).
- Class-DFU ep0 on the 12ab (normal-iOS) runtime: GETSTATUS/GETSTATE at
  wIndex=0 → **timeout (Errno 60), not stall**; wIndex=1 → host-side claim
  rejection (Errno 13). INTERPRETATION (corrected): NORMAL iOS does not service DFU-class ep0
  requests — expected, since the audited iBoot code is not what runs in
  normal mode. The chain's live validation still needs a DFU-family runtime:
  ROM DFU (done, ROM-side results only) or the yet-unreached recovery
  personality.
- ep0 vendor surface attempts (pmd3/irecovery shapes included): all
  `0x40/0` command-text forms STALL (Errno 32); `0x41/0` opener (pmd3
  recovery-upload init) times out; `0xC0/0` returns a byte-stable 6-byte
  blob (semantics unknown; value stays in the local TSV) — re-read as
  NORMAL-iOS ep0 vendor stub behavior, not console traffic. All `0x40`-text
  and bulk-console experiments on 12ab are WITHDRAWN as recovery-console
  probes; ep0 stayed healthy throughout
- Tooling state: pymobiledevice3 11.45.1 installed to user site (pip); its
  irecv clone matches 0x1227 DFU but no normal-iOS pids (by design:
  normal mode routes through usbmuxd, not direct irecovery); its
  doctor/usbmux plumbing may matter for future host-side routes.

### 7.5 Where the acceptance-chain validation stands

- The DNLOAD-arc validation vector (block_len check `0x23b9b0` →
  `0x3209`/state 0xA; cum/expected `0x23b9b8`/`0x23b9bc` → `0x3208`;
  success → state 5, timeout `0x3200`) remains **static-model only**.
- Live corroboration options, in increasing cost:
  1. SecureROM runtime arc (exists today; but it validates the ROM's own
     state machine, not the audited iBoot chain);
  2. recovery personality (unseen; likely 0x1280..0x1283 pid family, which
     irecovery/pmd3 match natively). User asks at the button-dance level:
     from normal iOS — VOLUME-UP, VOLUME-DOWN, then hold TOP until the
     recovery picture appears. Rebooting out = TOP held ~10 s.
  3. loader-stage personality via a controlled restore-prefix flow
     (heaviest; requires explicit user approval in a planned session).

## 8. Next session plan (updated 2026-10-28)

1. **Device-side work needs the iPad. Do nothing on-device without alerting
   the user first.**
2. **Recovery personality arc (the unlock; device in NORMAL iOS since the
   12ab correction).** Ask the user: "IPAD REQUIRED IN RECOVERY" (from normal
   iOS: VOLUME-UP, VOLUME-DOWN, then hold TOP until the recovery picture
   appears). Expected 0x1280..0x1283 pid family (irecovery/pmd3-native).
   Arc order: (a) personality census (product/pid/cfgs); (b) read-only
   `getenv build-style` / `getenv version` — confirms the audited build;
   (c) class-DFU GETSTATUS/GETSTATE — tests whether the recovery composite
   services the audited ep0 chain; (d) only on positive (c) the DNLOAD arc
   per the static model (mismatch-shaped probes are fail-safe: checks
   precede any dereference).
3. Optional static leftovers (all low priority, none gate any candidate):
   - ~~padded `0x891` probe~~ — DONE (see C1 addendum in §3): identical
     engine statistics and byte-exact expected output.
   - ~~`0x11d018` cluster extension~~ — DONE (§2.8); the `0x37188`
     boot-object manager note ("what NEW info the `0x11cd18` acceptance chain
     changes") remains open.
   - walk the `0xd2c84`/`0xd6590` resolver for the full slot↔handler map (§6).
4. C2 stays unchanged (lower confidence; prior doc governs).
5. Housekeeping: `make test` green before every commit; TSVs and DFU fuzz
   session logs stay untracked; wrapper artifacts and `pc4/` cache never
   committed.
