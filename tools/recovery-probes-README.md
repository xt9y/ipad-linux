# Recovery-arc probe scripts (LOCAL-run device drivers)

These scripts drove the user-approved device arcs recorded in
`docs/dfu-ep0-recon-2026-10-27.md` §7.11 (upload reject-path matrix) and
§7.12 (consumer-trigger ladder). They are committed so the exact protocol
shapes and safety rails survive with the research. Their **output logs are
NOT committed** — every `dfu-probe-log-*.tsv` is LOCAL ONLY (already
gitignored): class-level protocol bytes only, but they are still session
state, not knowledge.

## Scripts

- `dfu_probe_recovery.py` — §7.7-era ep0 DNLOAD-side acceptance probe
  (mismatch-shaped vectors, fail-safe by design). Hardcoded vector list,
  no loops/randomization.
- `upload_probe_recovery.py` — §7.11: census → console baseline → per-vector
  fresh `0x41/0` opener → malformed/unsigned synthetic payloads on bulk
  `0x04` OUT → console-health drain after every step.
- `boot_trigger_recovery.py` / `...2.py` / `...3.py` — §7.12 sanctioned
  consumer-trigger ladder: staged synthetic payloads, then `go`/`bootx` on
  the vendor `0x40` bRequest `1` execution channel; personality re-checked
  every step.

## Ground rules baked into every script

1. No DETACH (`0x00`), no ABORT (`0x06`), no CLRSTATUS (`0x04`).
2. No DFU-class requests (`0x21`/`0xA1`) — they stall in recovery (§7.7).
3. No `saveenv` (nothing persistent); synthetic unsigned payloads only;
   no Apple-proprietary data touched or handled.
4. Console-health check after every step; halt on wedge or personality flip
   (enumeration = the authority: PID over screen).
5. Log lines carry class-level material only (timestamps, sizes, byte
   digests) — never ECID/UDID/serial/nonce material.

## The persistent-handle discipline (§7.12, mandatory)

macOS grants bulk-OUT access per-handle: the handle that performs the first
successful bulk write keeps working; any LATER-created handle fails with
`USBError [Errno 13] Access denied` on bulk OUT (and `set_configuration()`
does not clear it) until the device re-enumerates. Any future device work
must therefore open ONE handle at session start and use it for control and
bulk traffic alike, re-finding the device only for read-only PID checks.

(tools outputs, poll loops and ad-hoc census snippets stay local; only the
approved-arc drivers are tracked here.)
