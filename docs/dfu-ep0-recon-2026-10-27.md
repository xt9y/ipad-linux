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

### 2.9 The `0xd2***`/`0xd65***` family classification (2026-10-28, static)

The earlier "resolver" framing is corrected — the family is **checked memory
and task services**, not a resolver:

- `0xd2c84`/`0xd2ed0` = bounds-checked copy/write wrappers: pointer-kind tags
  (`*p & 7 ∈ {1, 6}`, pointer body masked `& ~7`), high-bit VA checks
  (`param[2] >> 0x23 == 0`), violation → `0x13a40c` panic (fail-safe style,
  checks precede every dereference). `0xd2ed0` is the length-carrying variant
  (observed lengths: `0x800` DFU status init, `0x200` wipe blocks, `0x140`
  DFU-core step cards, `0x28` work descriptors).
- `0xd6590` = **deferred-work queue**: validates a 0x28-byte work descriptor
  via `0xd2ed0`, stores a busy flag (`+0x26`), schedules with a callback
  argument (`0x11d018` queues it with callback `LAB_00188ee8` and the DFU-core
  ctx buffers `+0x98/+0xc0`).
- The full slot↔handler map question dissolves: the handler slots
  (`0x23b888..0x23b998`) are runtime-registered by the supervisor-mediated
  event layer (no static writer — §7.8); static reach ends at the slot table.

### 2.10 The `0x37188` boot-object-manager note — what the acceptance chain changes (2026-10-28)

Resolving the leftover note ("what NEW info does the `0x11cd18` acceptance
chain change") with the §7.8 map in hand:

- **The shared-base identity**: the per-command/env registry object
  `img+0x159bb8` decodes (VA = base + offset) to exactly
  **`0x1FC1A5BB8` — the fixed shared base the earlier SMC/manifest analysis
  already tied to the registry portal** (`0xc2100`/`0xc2934`). The console
  command units, the env registry units, the personality registrations, and
  the DFU state init all reference this same root — the DFU, recovery-console,
  and env infrastructures are ONE registry family rooted at `0x1FC1A5BB8`.
- **The acceptance chain's data path stays inside its own state object**: the
  `0x11cd18` accept path writes DNLOAD chunks into the DFU state object's own
  buffer (`0x23b9c8`-region), allocated/flushed through `svc #0xc5(w0=4)`
  (`0x11cd94`), via the checked writers `0x119160`/`0x8c3ac` and the
  checked-copy finalizer `0xd2c84` — it does NOT write the
  `0x1FC1EF768..0x1FC229498` staging container directly. The chain→container
  link remains the untraced consumption step (Open Q1): the boot flow
  (`0x3724`→`0x37188`→`0x37440`→`0xb5c28`) consumes the DFU-staged image
  later, through the same portal family.
- **What the chain therefore changes for the `0x37188` picture**: (a) the
  supervisor svc layer participates in the DFU data path (alloc at
  `0x11cd94`, event svc in the session stubs); (b) all writes are checked
  (kind-tagged pointers, panic-on-anomaly); (c) the fill is tracked by the
  state latches (`0x3200`/`0x3208`/`0x3209`/`0xb800`/`0xb`, states
  2/5/7/8/0xa) — the fill-tracking vocabulary the boot-object manager can
  observe; (d) the DFU state init (`0x11c9dc`) registers its callbacks into
  the same PAC-signed slot discipline (`0x23b9a8` object, `paciza`) as the
  session event slots.

### 2.11 Open Q1/Q2 resolved — no `splt` staging on this build; the `bvx2` stream is consumed in place (2026-10-28)

**Container identity (corrects the earlier "needs runtime staging" hypothesis).**
With the load base `0x1fc04c000` established (§7.8), the container VA in the
static descriptor object `0x215ed8` (+0x00/+0x08 = `0x1FC1EF768`) decodes to
`img+0x1a3768` — **verified in-file: the bytes at `0x1a3768` are the `bvx2`
magic**, the start of the embedded compressed stream, and `container +
0x39D30 = 0x1FC229498` = `img+0x1dd498` (still inside the 0x2262c8 file) — the
object length is exactly the stream region. The container is the image's own
data region seen through the same flat `K + offset` VA space as every other
pool pointer (all checked pool VAs decode consistently).

**The validator `0xb5b68` is check-only and the `splt` path is dead on this
build.** Full decode:

- `null container || zero length` → panic (line 0x14c); container must lie in
  `[x1, x2)` (else `0x13a40c`).
- `[container]` must equal `0x746c7073` (`splt`) — the compare constant is
  formed at `0xb5b9c`; **it is the only `splt` formation in the entire image**
  (no literal `splt` bytes anywhere, no other `movk #0x746c`) → there is no
  splt-header builder, statically or otherwise.
- On magic match: `[+0x10]` and `[+0x14]` must be non-zero,
  `([+0x14] << 2) + 0x18 < length`, then `0xc098c` is run over the span
  `container+8 .. container+8+(([+0x14] << 2) + 0x10)` and **must equal
  `[container+4]`** — a checksum of the input stream stored in the header.
- Return value = (`[container] == 'splt'`).

On this image the container holds `bvx2`, so the validator returns 0
deterministically and the loader branches to the skip path — **no runtime
staging of the container ever happens**: the header is never built and the
stream bytes are never copied anywhere.

**The loader flow `0xb5c28` (called from `0x37440` ← `0x37188` ← `0x3724`)**:

1. `0xb5c48: bl 0xb695c` — a marshaling fragment (the `0xb6800..0xb6984`
   cluster is a pool of such fragments, each a few instructions + `ret`),
   reversing the incoming `x0..x3` into `x19..x22`; `x22` = incoming arg0 =
   the descriptor object (`0x215ed8`, passed down the boot flow).
2. `bl 0xb6818` — typed-span dispatch with the kind-4 context `img+0x191488`
   → `0x136cf8` (below); result checked non-null (else panic line 0x167).
3. The object must lie in `[in-x1, in-x2)`; fields poked: `*+0x28 &= ~3`,
   `+0x30` zeroed, `+0x38` zeroed.
4. Local descriptor built at `sp+0x48`: `{container, container, obj+0x10,
   obj+0x18, len=[obj+0x48]=0x39D30, type=[obj+0x54]=0x8A1}`.
5. `type != 0` → validator → **fails** → skip path.
6. Skip path: the `0xb6984` fragment (`x7 = img+0x159c60`, stack byte set)
   then **the list loader `0x125b6c`** with the `0x235b48` endpoint-block
   pointers. (The dead splt path would instead have pushed the interface
   markers `0x222ad8`/`0x222d40` and `{input = container+0x18, end}` and
   called the consumer `0xb58c0`.)
7. Both paths join: log tag, flag-set (`[obj+0x40]`, bit `[obj+0x62]`), then
   the status service `0x125cb0` (six callers) whose result becomes the
   return value.

**Interface markers decoded.** `0x222ad8`'s pointer fields target
`img+0x222ac0/0x222ac4`, which hold the ASCII strings **"SMC", "smc/",
"ips-smc-", "nub"** — it is the SMC nub name bundle (IORegistry-style),
rooted at the portal `img+0x159bb8`. `0x222d40` (`0x222ad8 + 0x268`) is the
near-empty second marker (`{0, 0x0001000100000000, 0…}`).

**Q2 — the `0xb6814`/`0x136cf8` cluster classified.** It is not a staging
builder: `0xb6814` = a jump-table/fragment cluster whose tails form `x4` kind
contexts (`img+0x191488` kind 4 — a real pointer descriptor; `img+0x159bb8`,
`0x159c88`, `0x159b78` kind 1 — self-referential marker objects, first word
pointing at themselves+1, tag = `w0 & 7`) and branch into `0x136cf8`, the
typed-span driver: load `*x4`, strip the 3-bit tag, read the pointee's first
word `& 7` as its kind, dispatch via the PC-relative jump table at
`0x137040`; per-kind span transforms (element size from `0x137068`, stride/
alignment arithmetic `udiv/msub`, singleton check against `img+0x159b50`,
`>> 0x23` VA-validity gates, a reserve call `0x1386e8`, conversion
`0x137520`), fallback copy worker `0x1368b8`; returns the (adjusted) span
tuple in `x0..x3`. The same `& 7` tag scheme as the checked-copy family
(§2.9) — one pointer-tagging discipline across the image.

**Consequence for the staging thread.** The `splt`-container path
(consumer `0xb58c0` + markers) is the alternative layout for a different
build/config. On this build the embedded `bvx2` stream is consumed **in
place** through the descriptor/list-driven path (`0x125b6c` family — the
pair the prior analysis already tied to the SMC `0x801/0x802` arm). The
decode chain end `0xdcc84` → `0xddb10` (`VMiBoot `/`LZFSE`) is entered via
`0xdc808`, which has **no static callers** (pointer-registered, matching the
image's registration style) — the one remaining dynamic entry in this thread.

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

### 7.6 Recovery-personality plan-of-record (protocol shapes + static corroboration)

Classical recovery shapes, transcribed from the on-disk libirecovery/pmd3
sources for validation at device time (never trusted blind):

- Config dance: `set_configuration(1)` (classic recovery composite), interface
  0 alt-setting 0; for mode value > RECOVERY_MODE_2 add
  `set_interface_altsetting(1, 1)`. Composite geometry on USB-C iPads may
  shift interface numbers (12ab showed cfg4-itf2 multi-alt) — enumerate, do
  not assume.
- Console command: ctrl `0x40`, bRequest 0, wValue 0, wIndex 0, payload =
  `command + "\0"`. Response: ctrl `0xC0` read (255 B). Text-only commands
  are the identity arc: `getenv build-style`, `getenv version`.
- Image upload session: ctrl `0x41/0` as the initiator; data via BULK OUT
  (pmd3 hard-codes endpoint 0x04 for Lightning-era interfaces) with a
  terminating ZLP at a 512-byte boundary.
- DFU-mode runtime machinery per pmd3: GETSTATUS `0xA1/3` body
  `{bStatus, poll24, bState, iString}`; DNLOAD `0x21/1` with
  wValue=packet_index; final chunk extended by `dfu_xbuf` =
  `{ff ff ff ff ac 05 00 01 55 46 44 10}` + crc32(all data, salted); then
  USB reset.

Static corroboration (strings scan of the audited image, local file —
class-level facts): recovery console command nouns `bootx`, `dev`, `getenv`,
`reboot`, `root`, `saveenv`, `setenv`, `usb` all present in-image; identity
banner `iBoot for j407 Copyright 2007-2026, Apple Inc.`; `RELEASE` and
BUILDSTYLE vocabulary present. The console dispatch really is the audited
code. At device time, `getenv version` is expected to answer in the banner
or an `iBoot-<build>` family — record the exact string it returns.

### 7.7 Recovery-arc results (05ac:1281 — the unlock session)

- Personality: `05ac:1281` "Apple Mobile Device (Recovery Mode)" — matched by
  libirecovery AND pmd3 (RECOVERY_MODE_2) — one configuration: itf0 class
  `0xfe` with a single bulk OUT `0x04` (the pmd3 recovery-upload endpoint
  shape, confirmed), itf1 class `0xff` alt0 empty / alt1 = bulk IN `0x81` +
  OUT `0x02` (console). Classical geometry confirmed end-to-end.
- Class identifiers (USB serial string, filtered to class-level): CPID
  `0x8103` (T8103/M1 class — J407 ✓), CPRV `0x11`, BDID `0x10`, CPFM `0x03`,
  SCEP `0x01`, IBFL `0x3d`, **SRTG = "N/A"** (the recovery runtime does not
  carry the ROM tag in the serial string — that field is ROM-DFU-stage).
- Console LIVE on the classical protocol: pmd3 IRecv `getenv build-style` →
  `RELEASE` (first identity answer from the audited runtime; matches the
  in-image `RELEASE`/BUILDSTYLE vocabulary).
- **ep0 vendor-write does env-lookup at send time** (behavior of record):
  accepted = known env names (`build-style` → `RELEASE`, `auto-boot` →
  `true`); unknown names (`version`, `platform`, `config`, `build-id`,
  `buildid`, `build-timestamp`, `build`, `security-domain`, `secure-epoch`,
  `boot-delay`, `SERIALNUM`) STALL the send (Errno 32) — reject at the ep0
  layer, never queued. This is why libirecovery's own `-q` shows no
  `Version:` line on this device: `version` is not an env var on this build.
- Console output read-back: `0xC0/0` reads REPLAY a bounded window of the
  last console output (non-destructive; content follows the most recent
  successful sends: `RELEASE\0`×N then `true\0`×N). Each successful send
  appears to append the value twice — echo/value duality unresolved, low
  priority.
- **Class-DFU on the recovery runtime = STALL (Errno 32) at GETSTATUS/
  GETSTATE, wIndex 0 and 1.** Bounded conclusion: the audited ep0 DFU
  acceptance chain is NOT externally serviced via class requests in the
  recovery runtime either — the chain's live validation requires the
  DFU-family runtime arc (ROM DFU behaves, ROM-side; audited-chain arc
  remains static-model), OR the recovery upload path (`0x41` + bulk) which
  exercises the IMG4 consumer chain with REAL file semantics — that arc is
  invasive (image upload + trust validation) and stays reserved for an
  explicitly-approved planned session.

### 7.8 Static wiring of the recovery console (device-independent, same session)

Method note (reusable): raw file offsets == Ghidra addresses for this image;
runtime VA = `0x1fc04c000` + offset. Load base derived base-free: (1) histogram
of 8-aligned qwords whose low-12 bits match a known string offset's low-12 bits
(top candidate `0x1fc04c000`, 8 hits), then (2) delta-consistency pairs of
adjacent qwords differing by known string deltas (`reboot`→`getenv` = 0x34;
`getenv`→`setenv` = 0x7) — confirmed by exact matches `0x15c3e0`→`reboot`,
`0x15c6b0`→`getenv`, `0x15c7a0`→`setenv`. Pool qwords store full VAs; exact
pointer decode = VA − base.

- **Command noun table** (units stride 0x78, from `0x15c370`): reboot (first,
  structurally special), reset, bgcolor, setpicture, firmware, devicetree,
  getenv, saveenv, setenv, setenvnp, clearenvp, ramdisk, rsepfirmware, plus one
  more unit at `0x15c988` (tag variant). Unit shape: `{name-ptr, obj img+0x159bb8,
  packed {tag 0x80f0 << 48 | code-offset}, obj img+0x15a9d8, 3×BSS byte-ptrs
  (0x272bb8+i region, two aliasing the same byte; bgcolor shares reset's slot),
  obj img+0x159bb8, zeros, optional 0x2, name-ptr, name-ptr}`.
  All packed low-32 code offsets disassemble as valid `pacibsp`-functions:
  getenv→`0x5698`, reset+bgcolor→`0x51c8`, setpicture→`0x5210`, firmware→
  `0x52ac`, devicetree→`0x50a0`, rsepfirmware→`0x56f8`, saveenv→`0xc51ec`,
  setenv→`0x51c4`, setenvnp→`0xc52e4`, clearenvp→`0xc550c`, ramdisk→`0xc5574`.
  Noun strings are referenced ONLY via these table slots (no adrp+add
  formations, no direct BL — pointer-table design; the earlier zero-hit scan
  was a base-blindness artifact, now corrected).
- **Parallel table** at `0x19e1c0` (stride 0x20, rows `{name, obj img+0x15aa00,
  name, name}`) mirrors the command sequence.
- **Env registry**: 0x20-stride units at `0x15bab8..` (auto-boot, boot-args,
  debug-uarts, pwr-path, anid, apt-carveout-size-mb, auto-boot [2nd], auto-boot-
  once, audio-features …; name blob at `0x210a20..`); a separate name/defaults
  blob at `0x197***` (auto-boot `0x1974be`, build-style `0x197887`, version
  `0x197899`, security-domain `0x199983`) has no pool refs. Two early walkers:
  `0x3a7c` (from `0x15bab8`, ≤5 units: loads the 4 unit qwords into x4–x7 and
  calls `0x4f40`, continue-check `0xd2054`, index from `0x4fbc`) and `0x3afc`
  (from `0x15bb58`, ≤39 units, then resolver-band calls `0xd233c`/`0xd23a4`
  with the `0x1972ef` string) = early env/registry init. `0xd233c` itself is a
  bounds-check helper (panic `0x1f`/`0x28` on violation) — the band-wide
  fail-safe style again.
- **Recovery USB session architecture**:
  - setup `0x86514`: poll flag via `0xfad74`, mark session active, `0x86430`
    (usb setup), register personality via `0x11c684` (names "Apple Mobile
    Device (Recovery Mode)" `0x19a15b` / "(DFU Mode)" `0x19a17f`, registry
    object `img+0x159bb8`), fill descriptor record via `0x11c7f8`
    (`{session, session, session+0x40, record img+0x188728}`), then the poll
    loop `0x11c818` → work `0x11c26c`.
  - `0x11c684` allocates via `svc #0xc5` (w0=4 — the supervisor event/alloc
    svc) and registers through `0x124a74` with record `img+0x188728`.
  - **Event-slot dispatch**: stubs at `0x11c244+` — `svc #0xc5(4)` →
    load PAC-signed slot `0x23b888..0x23b998` (17 slots, 0x10 apart) →
    `braaz` call; empty slot = panic (line numbers 0x27..0x87; panic-tag
    magics formed at `0x11c654`/`0x11c998`). **No static writer exists for
    these slots — they are runtime-registered by the supervisor-mediated
    event layer; static reach ends at the slot table.**
  - transfer service `0x893d4(ep, buf, ...)`: endpoint-coded args observed:
    `0x80` = ep0-in (DFU GETSTATUS response), `2` = ep2-out, `0x81` = ep1-in,
    `4` = ep4-out (the pmd3 upload endpoint). A byte-collect loop at
    `0x11d9a0` (`ldrb [sp,#0xf]` → `strb [x8+x21]`, ring bounds
    `[x22+0x38..0x48]`, then `0x893d4(0x81, count)`) = console output
    collection onto the bulk-IN stream — matching the census geometry
    (itf1 alt1 IN `0x81`/OUT `0x02`), so the session serves a classical
    control console AND a bulk console pair.
- Reconciliation with the live device (§7.7): the env-lookup-at-send runs in
  the ep0 control-write path whose handler is one of the runtime-registered
  slots — the unknown-env→STALL decision sits above static reach, consistent
  with the band's design (bounds-checked, panic-on-anomaly, no error leaks).
  Class-level reconciliation: `auto-boot` and `build-style` are registry names
  (tables above), `version`/`platform`/`config` are not.

### 7.9 Recovery upload path — protocol notes (docs-only, no device)

Cross-reference to §7.6 (pmd3 protocol shapes) with today's static service map:

- Classical control console: send = `0x40/0` (text command, NUL-terminated),
  drain = `0xC0/0` (bounded replay of last console output; §7.7 semantics).
- File upload: init `0x41/0` then bulk on the itf0 endpoint (EP `0x04` OUT) —
  statically corroborated by the transfer service `0x893d4` endpoint-coding
  (`4` = ep4-out enqueue; §7.8) and by the pmd3 hardcoded EP choice.
- Bulk console pair: EP `0x02` OUT (command stream) / EP `0x81` IN (output
  stream) — statically corroborated by the byte-collect loop at `0x11d9a0`
  sending on `0x81` (§7.8).
- Upload finisher per §7.6: final chunk + `dfu_xbuf` tail + crc32 salted, then
  USB reset. The consumer = the IMG4 trust chain (validation precedes any
  dereference per the audited style).
- Arc status: reserved for an explicitly-approved planned session (§7.7). When
  run, malformed/unsigned IMG4 payloads first (reject-path exercise), real
  images only if separately approved.

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
   - ~~`0x11d018` cluster extension~~ — DONE (§2.8).
   - ~~`0x37188` boot-object manager note~~ — DONE (§2.10): shared-base
     identity resolved (`img+0x159bb8` == `0x1FC1A5BB8` portal root); the
     acceptance chain stays inside its state object, container consumption
     remains Open Q1.
   - ~~`0xd2c84`/`0xd6590` resolver walk~~ — DONE (§2.9 + §7.8): family =
     checked-copy + deferred-work services; the slot↔handler map's static half
     is complete (event slots runtime-registered, no static writer).
   - ~~Open Q1 (runtime staging)~~ — RESOLVED (§2.11): no `splt` staging on
     this build; validator is check-only and fails deterministically on the
     in-file `bvx2` stream, which is consumed in place via the list-loader
     path; only `0xdc808` (decode-chain entry) remains pointer-registered.
   - ~~Open Q2 (`0xb6814`/`0x136cf8`)~~ — RESOLVED (§2.11): typed-span
     marshaling/dispatch cluster (kind-tag contexts + `0x136cf8` driver), not
     a staging builder; markers `0x222ad8`/`0x222d40` = arguments of the dead
     splt path.
4. C2 stays unchanged (lower confidence; prior doc governs).
5. Housekeeping: `make test` green before every commit; TSVs and DFU fuzz
   session logs stay untracked; wrapper artifacts and `pc4/` cache never
   committed.
