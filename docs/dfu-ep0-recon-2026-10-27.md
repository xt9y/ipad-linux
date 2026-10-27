# J407 DFU ep0 recon — candidates-only static audit (2026-10-27)

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

### 2.5 Raw `0x8c3ac` — the alt (non-secure-monitor) writer arm (resolves next-move #2, part 2)

- Own `pacibsp` function (real entry `0x8c3ac`; NOT a fragment). Takes 4 args to
  x24–x27 plus the caller's x19 (`0x11cda4` path keeps caller's x19).
- Ghidra decompiles it, but the body is a huge multi-call shell
  (`0x8f24c/0x8f008/0xe3740/0x8f030/0xe399c/0x8f01c/0x8f828/0x8f6a4/0x8f8fc/0x8ed90/
   0x8f044/0x8f6b8/0xe3cd0/0x8ed58/CallSupervisor(0xc2)/0x8f6b8/0x8f520/0x8ee48/…`),
  with `svc #0xc2` inside (`0x8c368..0x8c36c` in the neighbouring same-shape
  function) — the arm family's own `CallSupervisor` usage. Reads
  `*(x20 + 0x20)` (`ldrb w0,[x20,#0x20]` @`0x8c37c`) for the conditional branch
  (`0x8ee48` result bit) — success sets the flag store `0x8fa94` path, failure
  goes to `0x30444` (the VM mapper / non-returning path).
- **Status**: structurally audited but NOT candidate-level resolved. Deliberately
  not decompiled into narrative here. Captured decompile in `pc4/8c3ac.c`
  (1479 chars) with the caveat that Ghidra lost some `unaff_x20/x30` provenance;
  treat `pc4/8c3ac.c` as *indicative*, instruction disasm of `0x8c2e0..0x8c420`
  remains the evidence of record.

### 2.6 Service-patch table artifacts (context, hardening observation only)

- `0x11c668`/`0x7f02c..0x7f104` tiny argument-thunk/stub families are
  Hopper-"orphan"-shaped but are all reachable via `bl` (arg shuffle thunks —
  e.g. `0x7f094` = "move x0..x3 → x4..x7", `0x7f088` = load `0x159bb8`,
  `0x7f02c` = compare against `*0x23e5f0` context pointer).
- The `0x11cf30` gateway (`b 0x93e9c` / `b 0x93f60`) and `0x11cf34`/`svc #0xc5`
  wipe loop (`0x11cf84`) from the earlier Phase C notes were re-confirmed:

### 2.7 Scrub/wipe loop (new structural note)

Raw `0x11cf84` = chunked wipe over `param_1` (buffer) with `x4` bytes, stepping
`0x2000` at a time through `0x11cf34(x0=…, x4=len, [0x159bb8])` which tail-branches
`b 0x11d5d8` or `b 0x93f60` conditioned on the `svc #0xc5` result; returns the
accumulated wipe count. `0x159bb8` holds a record template (`b9 5b 1a fc 01 00 00 00,
68 c0 25 fc 01 00 00 00, 01 …`): tagged 0x1fc-prefixed record-pointers chain (the
same template shape as the descriptor records passed to `0xd2c84`/`0xd2ed0`).

## 3. Candidate list status (crypto/DFU side)

- **C1 (LZFSE match-copy `source ≥ base` — raw `0x145d80`)** — **DOWNGRADED**.
  The previously reported *missing* bound check is present in the raw disasm at
  `0x145de0..0x145df4` (`cmp x10, x11; ccmp w9, w8, #2, eq; b.hs 0x145e24 → mov
  w8,#1` → `-1` via `sbfx` at `0x145e3c`). Consistent with the call-site at
  `0x1459d8` (`bl 0x145d80(x0 = helper ctx, w1 = n bytes, x2 = ptr)`; failure
  returns bit `0x1f` → branch `0x144e0c`). The earlier "missing" was an artifact
  of the REA/Hopper `procedure_pseudo_code` view only; with the Hopper pipeline
  retired, no REA-era claim stands without capstone or Ghidra crosscheck.
  **Remaining work** (next session): emulation spot-check *is still worth doing* to
  prove the wrap/fail path terminates (use the existing `emu_*.py` harness in the
  cache dir with the same mapping layout — no code needs to be invented).
- **C2 (lower-confidence, per prior session)** — unchanged; not re-verified this
  session. See `docs/boot-image-recon-24a446.md` for the original *cv*; its status
  stays per that document until the dedicated dedicated re-run.
- **C3 (THIS session, static)** — *DFU ep0 RAM-append strictness.* In the audited
  build the ep0 DFU data-stage write path is **default-rejecting**:
  the write-grant window `0x230e00/0x230e08` is preset to an empty interval and the
  bypass bit is not observed to be set anywhere. Both pre-checked invariants
  (`block_len` match and `cum+received ≤ expected`) live at `0x11cd34`/`0x11cd4c`,
  before any destination pointer is dereferenced. Structural candidates still open:
  (a) find *any* code path that flips the bypass bit 16 byte `0x230df2`;
  (b) confirm there is no second writer of `0x230e00/0x230e08` (census: none found).
- **C4 (THIS session, structural)** — *alt arm writer `0x8c3ac`*. Called only when
  `svc #0xc5` gate returns `x0 == 0`; un-nested, stack-heavy, multi-`svc` body;
  Ghidra decompile is indicative only (`pc4/8c3ac.c`) — needs its own dedicated
  read before any claim beyond "structure, not yet audited content".
- **C5 (THIS session, structural)** — *thunk/stub families pretending to be
  procedures.* Tiny arg-shuffle stubs (`0x11c668`, `0x7f02c..0x7f104`, `0x7f094`,
  `0x7f088`, `0x5ec/0x604 …`) are real reachable code that HA/Hopper-style orphans
  mis-cut into false "procedure starts". Any future cross-ref pass must treat
  these as in-body branches, not as procedure entries.

## 4. Phase B audit (IMG4 pipeline / Memz headers) — NOT started this session

Deliberately deferred to keep the diff to this turn small and focused. Keep pointer
from the handoff §7: doc `0x20994` `IMG4 pipeline` and `0x820c4` `Memz type headers`
remain the named targets; they are auto-analyzed in the new Ghidra project already,
so the next session should start there (Ghidra addressing = raw offsets, no +0xB8).

## 5. Evidence inventory (this session)

- `pc4/*.c` — 8 Ghidra functions: `119160.c, 8c3ac.c, 11c294.c, d2c84.c, d2ed0.c,
  11cf84.c, 11d018.c, 7e60c.c` (cache dir, not committed).
- `disasm_0x11cb00_11d100.txt` — re-dumped from the cached capstone list, fills
  the 0x11cb00–0x11cf00 gap from the previous session's stdout-only slice.
- `scripts/DecompileAt.java` — Ghidra headless script used for all extracts.
- `insns.pkl` — unchanged capstone census (474,556 insns), remains the
  instruction-level evidence of record.

## 6. Next session plan

1. Restore & run the emulator for the **C1 wrap/fail** proof (existing harness,
   mapping unchanged, no new code).
2. Phase B: audit doc `0x20994` (IMG4 pipeline) + `0x820c4` (Memz type headers),
   now in Ghidra terms.
3. C3 follow-up: re-run the 0x230df0/0x230e00 writer census with a bit-level
   taint of the whole feature word (the micro-thunk prologue interleaving means a
   fully manual read is possible but slow).
4. C4: disasm/`DecompileAt.java` the real `0x8c3ac` (full body) and either close it
   or properly document it as a candidate.
5. Rename the +0xB8 note to "legacy" everywhere; new docs record raw == Ghidra.
