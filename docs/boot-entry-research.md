# Boot-entry research status

Target: iPad Air 5 Wi-Fi (`iPad13,16`, `J407AP`, M1/T8103).

This document separates mechanisms that can actually hand control to a native Linux loader from mechanisms that merely provide code execution inside iPadOS.

## Required capability

The project ultimately needs an execution environment that can hand the machine to Linux with enough control to:

- execute our AArch64 payload at EL1 or EL2;
- supply or recover the live Apple Device Tree and RAM layout;
- stop or quiesce DMA-capable devices;
- mask interrupts;
- perform required cache maintenance;
- turn the MMU off before Linux entry;
- place a Linux `Image` and DTB in valid physical RAM;
- branch to the Linux entry point with `x0 = dtb` and `x1..x3 = 0`.

A normal application sandbox escape is not sufficient. A conventional jailbreak may be useful research infrastructure, but it is not automatically equivalent to a Linux chainloader.

## Current avenues

### 1. Mac-style alternate OS boot

**Status: unavailable on iPad.**

Apple Silicon Macs expose configurable boot policy that Asahi Linux uses for a fully untrusted/custom OS. iPad does not expose an equivalent user-authorized custom kernel path.

### 2. Normal signed restore/recovery images

**Status: cannot directly boot our kernel.**

The iPad secure-boot chain begins in immutable Boot ROM. Boot ROM verifies Apple-signed iBoot, and iBoot verifies the kernel. A custom unsigned kernel/loader therefore needs either an Apple-supported authorization path (not available here) or a vulnerability/primitive capable of redirecting this chain.

### 3. Userspace / jailbreak code execution

**Status: useful but insufficient by itself.**

Historical M1 iPad kernel/jailbreak techniques show that M1 iPads can be researched from iPadOS, but native Linux handoff additionally requires control over MMU, caches, interrupts, DMA, physical memory and platform state. Modern integrity mechanisms also make "kernel read/write" less equivalent to unrestricted machine control than on older devices.

### 4. Current iPadOS kernel vulnerabilities

**Status: research lead, no public complete Linux-entry chain known.**

Apple's iPadOS 26.6 security advisory lists multiple recently fixed kernel memory corruption/write issues and a code-signing issue. Those CVEs demonstrate continuing attack surface but do not, from public information, provide a ready-made J407 native boot chain. The project does not assume an exploit exists for the currently installed release.

### 5. Recovery/iBoot vulnerability

**Status: theoretically strong, no verified public T8103 path found.**

An iBoot/recovery primitive that permits sufficiently privileged unsigned execution could be a direct bridge to this project's `boot_info` ABI. Modern iBoot on this generation includes additional memory/type-safety hardening, so this is a difficult target.

### 6. Boot ROM / DFU vulnerability

**Status: ideal class of primitive; no public M1/T8103 exploit found.**

A Boot ROM exploit is attractive because the ROM cannot be patched by an OS update. The 2026 `usbliter8` research proves that public post-checkm8 SecureROM exploitation is still possible, but its published supported processor families are A12/A13 (plus related variants), not M1/T8103. It therefore cannot currently be used on J407.

## What would count as success

Any future mechanism is usable by this project if it can eventually implement a small adapter equivalent to:

```c
struct boot_info info = { /* physical RAM, ADT, EL, flags, debug */ };
ipad_linux_entry(&info);
```

The rest of the loader is deliberately independent of the vulnerability or boot-entry technique.

## Current conclusion

The native-boot blocker is **entry**, not basic T8103 Linux support. No public M1/T8103 Boot ROM or iBoot path was verified as of August 2026. Software development should therefore continue up to a clean chainloader boundary while boot-security research proceeds independently.
