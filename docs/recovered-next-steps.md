# Recovered next steps

This file captures the safe, non-exploit-specific technical direction for the iPad Linux project.

## Current target recorded in this branch

The existing `ipad-air-5` branch currently records:

- Product type: `iPad13,16`
- Board config: `J407AP`
- Model number: `A2588`
- SoC: `T8103`

Treat these identifiers as project target metadata and continue validating them against device/firmware evidence before using device-specific register assumptions.

## Boot architecture

The project should keep these problems separate:

```text
Apple boot chain
    -> legitimate/research execution entry
    -> small AArch64 bootstrap
    -> m1n1-derived or compatible platform layer
    -> Linux arm64 kernel handoff
    -> initramfs/userspace
```

The repository should not assume that a working boot exploit exists.

## What is already useful in this branch

The branch now contains infrastructure that can be developed and tested without touching undocumented hardware registers:

- Freestanding AArch64 payload and linker script.
- Position-independent build checks and relocation verification.
- Platform metadata split into `src/platform/j407/`.
- A small boot-info ABI for memory/ADT/image metadata.
- A bounded Apple Device Tree parser with host-side tests.
- Memory-range helpers.
- Exception-vector scaffolding.
- Debug-output abstraction with no hard-coded transport.
- Linux arm64 handoff assembly.
- GitHub Actions CI for the payload and ADT tests.

## Next engineering milestones

### 1. Make the execution contract precise

Before adding device-specific hardware access, define exactly what the first custom stage must provide:

- Exception level on entry.
- Whether the MMU and caches are enabled.
- Physical memory range available to the payload.
- Payload load address and size.
- Apple Device Tree address and size, if available.
- Which registers are owned by the handoff ABI.
- Whether interrupts are masked.

The existing `struct boot_info` is the starting point for this contract.

### 2. Expand ADT support safely

Implement read-only helpers for:

- Walking child nodes.
- Reading `compatible` string lists.
- Reading `reg` properties while respecting parent address/size cell widths.
- Looking up nodes by path.
- Enumerating CPU, AIC, DART, storage and USB nodes.

Keep the parser bounded: every property/node access must be checked against the supplied ADT size.

### 3. Build a hardware inventory instead of hard-coding MMIO

Generate a structured inventory from device-tree/firmware evidence containing, where available:

- Node path.
- Compatible strings.
- Register regions.
- Interrupt descriptions.
- Power/clock dependencies.
- DART/IOMMU relationships.

Only move a value into platform source after its provenance is documented.

### 4. Add an architecture-state report

Create helpers that can report state supplied by a legitimate early-boot environment, including:

- `CurrentEL`.
- MMU/cache state.
- Entry PC/image base.
- ADT validity.
- RAM range validity.

Feed the report through the abstract debug sink rather than assuming UART addresses.

### 5. Keep Linux handoff compatible with arm64 expectations

For a later kernel jump, keep the handoff layer isolated and verify the Linux arm64 boot contract against current kernel documentation. Device-tree preparation, MMU state, interrupt state and register contents should be explicit prerequisites rather than implicit assumptions.

### 6. Reuse Asahi/m1n1 by interface, not by copied addresses

Useful upstream references include m1n1's ADT handling and Apple-Silicon platform abstractions. Reuse parsers, concepts and Linux-facing conventions where appropriate, but do not copy Mac board constants into J407 simply because the SoC family is related.

## Development rule

Until there is verified device-specific evidence, this project should prefer:

1. parsers,
2. validators,
3. boot/handoff ABIs,
4. architecture-neutral tests,
5. CI,

and postpone raw MMIO writes.

That lets most of the loader architecture mature before the unresolved early-boot entry problem is solved.