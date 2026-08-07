# m1n1 integration contract

This project treats m1n1 as the preferred reference/adapter layer between an eventual J407 execution mechanism and `ipad-linux`.

The important design rule is that the vulnerability/entry mechanism is **not** part of the Linux loader ABI. Whatever first obtains legitimate research execution only needs to get us into an m1n1-like environment. From there, the handoff is deterministic.

## Upstream primitives we reuse

Current upstream m1n1 exposes the SMP APIs we need in `src/smp.h`:

```c
void smp_start_secondaries(void);
bool smp_is_alive(int cpu);
uint64_t smp_get_mpidr(int cpu);
u64 smp_get_release_addr(int cpu);
```

m1n1's Linux kboot path starts secondary CPUs, leaves them in its spin-table loop, and writes `smp_get_release_addr(cpu)` into each Linux `cpu-release-addr` property. We intentionally follow that model instead of writing a second T8103 CPU-start implementation in this repository.

## ipad-linux ABI

`src/boot/boot_info.h` version 4 contains everything Stage 2 needs:

- usable Linux RAM range;
- live Apple Device Tree pointer/size;
- current exception level and MMU state;
- optional debug callback;
- Linux Image, DTB and initrd locations;
- whether the platform has already been quiesced;
- whether the DTB may be patched in place;
- eight `{mpidr, release_addr}` entries for J407 SMP.

`src/boot/m1n1_handoff.c` builds this structure from a normalized `m1n1_handoff_input` and rejects internally inconsistent address/size pairs.

## Intended adapter sequence

The m1n1-side adapter should conceptually perform the following operations:

1. Parse/use the live Apple Device Tree and establish the usable Linux RAM range.
2. Start the T8103 secondary CPUs with `smp_start_secondaries()`.
3. Enumerate live CPUs and collect `smp_get_mpidr()` plus `smp_get_release_addr()`.
4. Verify that all eight J407 MPIDRs are represented.
5. Load the Linux `Image`, precompiled J407 DTB and optional initrd into appropriate physical memory.
6. Quiesce DMA-capable/firmware-owned devices using the proven m1n1 path.
7. Arrange the final EL/MMU/timer state required by the arm64 Linux boot protocol.
8. Build `struct boot_info` with `m1n1_handoff_build()`.
9. Enter the ipad-linux payload with `x0 = &boot_info`.

The payload then validates the runtime state again, patches RAM/initrd and CPU release slots into the mutable DTB, performs final cache maintenance, masks interrupts and enters Linux.

## J407 CPU mapping

Mainline `t8103.dtsi` describes these eight MPIDRs:

```text
Icestorm:  0x00000 0x00001 0x00002 0x00003
Firestorm: 0x10100 0x10101 0x10102 0x10103
```

`src/platform/j407/smp_contract.c` maps those MPIDRs to the corresponding Linux DT paths and rejects unknown, missing or duplicate CPUs.

The release slots are also required to live outside the memory range advertised as usable to Linux. Without that rule, Linux could allocate over the m1n1 holding-pen target words while secondary CPUs still depend on them.

## What is deliberately not implemented here

This repository does not duplicate m1n1's T8103 PMGR/RVBAR CPU-start sequence. Upstream already has the relevant SoC-specific implementation and tracks the Apple CPU-start details across SoC generations.

Likewise, this integration layer does not provide a secure-boot bypass or an iPadOS exploit. The unresolved initial-entry problem remains separate from the Linux handoff code.

## CI

`.github/workflows/m1n1.yml` now:

- checks out current upstream m1n1;
- verifies that the SMP APIs above still exist;
- compiles/tests our handoff builder;
- builds an upstream m1n1 binary.

That workflow is a compatibility gate. If upstream m1n1 changes its SMP contract, this project should fail CI instead of silently producing an invalid J407 handoff.
