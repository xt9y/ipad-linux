# Execution contract

The payload must not depend on a particular iPadOS release, jailbreak, kernel exploit, iBoot exploit, recovery primitive, or future loader implementation.

The entry mechanism and the Linux bring-up code are deliberately separate. Any future authorized/research entry path should terminate at the same `boot_info` ABI.

## Entry ABI

The loader enters `_start` with:

```text
x0 = pointer to struct boot_info, or 0 when no contract is available
```

The payload preserves `x0`, establishes its temporary internal stack, and passes the pointer to `kernel_main()`.

`struct boot_info` is versioned and begins with a fixed magic value. Current version: `4` (see `src/boot/boot_info.h`, `IPL_BOOT_INFO_VERSION`).

Current fields cover:

- one contiguous **usable** RAM range (`memory_base`, `memory_size`);
- Apple Device Tree address/size;
- this payload's address/size;
- actual exception level reported by the entry loader;
- optional loader debug callback;
- optional preloaded Linux `Image`;
- optional preloaded Linux DTB;
- optional initrd;
- up to eight `{mpidr, release_addr}` spin-table entries
  (`BOOT_INFO_HAS_CPU_RELEASES`).

Unknown fields and reserved fields must be zeroed.

## Flags

```text
BOOT_INFO_HAS_ADT
BOOT_INFO_MMU_ENABLED
BOOT_INFO_HAS_DEBUG_WRITE
BOOT_INFO_HAS_LINUX_IMAGE
BOOT_INFO_HAS_DTB
BOOT_INFO_HAS_INITRD
BOOT_INFO_PLATFORM_QUIESCED
BOOT_INFO_DTB_MUTABLE
BOOT_INFO_HAS_CPU_RELEASES
```

`BOOT_INFO_MMU_ENABLED` is not trusted blindly. The payload reads the active `SCTLR_EL1` or `SCTLR_EL2` and refuses Linux entry when the runtime state disagrees with the loader metadata.

`BOOT_INFO_PLATFORM_QUIESCED` is an explicit promise by the preceding stage that DMA-capable devices have been stopped or otherwise made safe for Linux handoff. The current J407 helper only handles a small subset of watchdog/device state and is not sufficient to assert this flag on its own.

`BOOT_INFO_DTB_MUTABLE` means the DTB resides in writable RAM and is the J407-style template with fixed-size runtime placeholders. Only then may the payload change it in place.

`BOOT_INFO_HAS_CPU_RELEASES` means `cpu_releases[]` carries one
`{mpidr, release_addr}` entry per J407 CPU. The release slots are the
loader's own spin-table words and the Linux-usable RAM range must protect
them (see the SMP section below).

## RAM semantics

`memory_base` / `memory_size` describe memory Linux is actually allowed to use, not necessarily all physical DRAM installed in the device.

T8103 DRAM begins at physical `0x8_00000000`, but firmware/device carveouts may make parts of the installed DRAM unavailable. The entry loader must not include such carveouts inside the usable range unless they are represented safely to Linux as reserved memory.

The current ABI supports one contiguous usable range. If J407 requires multiple disjoint usable regions, the ABI must be extended before native boot.

## Mutable Linux DTB contract

The precompiled J407 Linux DTB contains fixed-size placeholders:

```text
/memory@800000000/reg             16 bytes
/chosen/linux,initrd-start         8 bytes
/chosen/linux,initrd-end           8 bytes
```

`linux_fdt_patch_runtime()` patches them without growing or moving the FDT.

The FDT patcher is fail-closed but not transactional: if a later property is missing, an earlier property may already have changed. Any patch failure therefore invalidates the DTB for that boot attempt.

Because the FDT is fixed-size, the payload cannot add new structure (for example a `/reserved-memory` node or extra memreserve entries). Anything the kernel must not allocate over has to be excluded from the advertised RAM range by the entry loader, or handled inside a DTB that was built for it.

`linux_fdt_patch_cpu_releases()` patches the existing 64-bit
`cpu-release-addr` properties of the eight J407 CPU nodes in place, using
the `boot_info` release table.

## Linux Image placement

Before entry the payload validates:

- EL1 or EL2;
- MMU disabled in the actual current EL;
- valid non-zero `CNTFRQ`;
- DTB 8-byte alignment and <= 2 MiB total size;
- Linux `Image` magic/header;
- little-endian kernel;
- `text_offset` placement relative to a 2 MiB-aligned base;
- image contained in usable RAM;
- DTB contained in usable RAM and non-overlapping with the image;
- optional initrd contained in RAM and non-overlapping;
- optional initrd/kernel contained by one <=32 GiB window with a 1 GiB-aligned base;
- 48-bit physical-address requirement when Image flags bit 3 requests it.

Immediately before entry the boot CPU:

- at EL2, normalizes `CNTVOFF_EL2` to zero;
- cleans the kernel Image, DTB and initrd data to the Point of Coherency;
- invalidates stale instruction-cache lines covering the Image;
- masks all PSTATE.DAIF interrupt classes;
- sets `x0 = dtb` and `x1..x3 = 0` in `linux_enter()`.

## Timer limitation at EL1

When entering Linux at EL1, the payload can verify `CNTFRQ`, but it cannot repair EL2-only timer state from EL1. The preceding stage remains responsible for `CNTHCTL_EL2`/`CNTVOFF_EL2` requirements where EL2 exists.

EL2 remains the preferred future entry level.

## SMP contract

Upstream `t8103.dtsi` declares all eight M1 CPUs with `enable-method = "spin-table"` and zero-valued `cpu-release-addr` placeholders.

The m1n1 adapter (`integration/m1n1/ipad_linux_adapter.c`) reuses m1n1's
`smp_start_secondaries()` and collects the live `{mpidr, release_addr}`
table into `boot_info`. The Stage-2 payload patches all eight
`cpu-release-addr` properties from that table before entering Linux.

Mainline Linux does not reserve the `cpu-release-addr` words itself
(verified against `arch/arm64/kernel/smp_spin_table.c` on current
mainline): protecting them is the loader's job. Upstream m1n1 protects its
spin-table words with `fdt_add_mem_rsv()` covering the whole m1n1 image,
which also covers the `.data.smp_shared` spin table. Because this payload's
DTB is fixed-size, it cannot add memreserve entries; instead the Stage-2
contract (`j407_build_smp_patch()`) refuses any release slot inside the
advertised Linux-usable RAM, and the adapter path excludes the m1n1 image
region (holding pens plus spin table) from the memory range handed to the
payload. If that exclusion would split the usable range into two disjoint
regions, the handoff fails closed: the current single-range `boot_info`
ABI cannot express that case (see "RAM semantics").

## Apple Device Tree

The ADT parser follows the m1n1 format:

```text
node:
    u32 property_count
    u32 child_count
    property[property_count]
    node[child_count]

property:
    char name[32]
    u32 encoded_size
    u8 value[encoded_size & 0x7fffffff]
    padding to 4-byte alignment
```

The parser now provides bounded validation, node/path lookup, property lookup and `reg` translation through parent `ranges`. J407 discovery code uses this instead of copying physical addresses from a Mac board file.

## Position independence

C code is compiled freestanding with PIE options and CI rejects remaining AArch64 runtime relocations in the final payload. The linker VMA is still a build-time placeholder, not a discovered J407 load address.

Before a real entry adapter is considered usable, it must additionally prove that the chosen raw/ELF loading method and the payload's linker-generated stack are valid for the actual execution environment.

## Remaining mandatory work before a real Linux jump

1. Implement/reuse T8103 secondary-CPU bring-up and spin-table holding pens.
2. Patch all eight `cpu-release-addr` properties.
3. Establish required coherency state for all CPUs.
4. Verify remaining architected/system-register requirements for the actual entry EL.
5. Quiesce every DMA-capable J407 device, not just watchdogs.
6. Represent firmware carveouts/reserved memory correctly in the DTB.
7. Validate the complete J407 DTB against a real/public firmware ADT and then on owned hardware.

References:

- Linux AArch64 boot protocol: https://www.kernel.org/doc/html/latest/arch/arm64/booting.html
- m1n1 `kboot.c`: https://github.com/AsahiLinux/m1n1/blob/main/src/kboot.c
- m1n1 `smp.c`: https://github.com/AsahiLinux/m1n1/blob/main/src/smp.c
