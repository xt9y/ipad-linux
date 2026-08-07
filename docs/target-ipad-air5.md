# Target: iPad Air 5 Wi-Fi

Immediate hardware target:

- Marketing name: iPad Air (5th generation) Wi-Fi
- ProductType: `iPad13,16`
- BoardConfig: `J407AP`
- Model: `A2588`
- SoC: Apple M1 / `T8103`
- CPID: `0x8103`
- BDID: `0x10`
- Architecture: ARM64 / arm64e Apple userspace ABI

## Why this target is useful

T8103 is the same SoC family used by first-generation M1 Macs. Asahi Linux and m1n1 therefore already contain substantial low-level T8103 knowledge. That does **not** make the iPad boot chain equivalent to the Mac boot chain, but it gives us a strong starting point for CPU, interrupt-controller, DART/IOMMU, storage, USB, and other SoC-level research.

## Known T8103 references

Asahi documentation publishes an incomplete T8103 memory map and identifies, among other blocks, the Apple interrupt controller, PMGR, GPIO, watchdog, UARTs, and DRAM region. These values are useful research references, but the project must not assume that every Mac-oriented bring-up sequence or peripheral route is valid on J407AP.

m1n1 contains explicit T8103 support in its SoC and GPU/platform code. The long-term strategy is therefore to reuse or adapt proven T8103 support rather than reimplementing the SoC from scratch.

## Current platform policy

`src/platform/j407/` contains only verified identity constants today. It deliberately performs no MMIO writes. Hardware initialization will be introduced one subsystem at a time after we establish the environment in which our payload executes.

## Next technical gates

1. Record the installed iPadOS version/build on the physical device.
2. Determine what public boot/recovery research applies to J407AP/T8103 at that version.
3. Identify a viable code-execution stage capable of replacing or chainloading past XNU.
4. Establish a transport for early debugging, preferably USB-based if UART access is impractical.
5. Once execution exists, obtain the Apple Device Tree presented on this exact board and compare it against T8103 Mac ADTs.
6. Replace the placeholder linker address with memory supplied/verified by the execution mechanism.
7. Bring up exception handling, timers, and a debug console before attempting Linux.
8. Integrate/adapt m1n1-style XNU-to-FDT/Linux handoff logic.

## Sources

- Asahi Linux T8103 memory-map documentation
- Asahi Linux open-OS interoperability / m1n1 documentation
- AsahiLinux/m1n1 source tree
- IPSW device metadata for iPad13,16 / J407AP
