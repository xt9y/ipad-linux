# Hardware matrix

This document tracks what is known versus unknown for the initial M2 iPad target. Do not fill unknown fields from guesswork.

| Component | Existing Apple-Silicon Linux work | iPad-specific status |
|---|---|---|
| ARM64 CPU cores | Linux/Asahi support exists for Apple Silicon generations | Target model/board still unknown |
| Interrupt controller | Apple Silicon support exists | Device-tree/platform details unknown |
| DART / IOMMU | Linux driver support exists | iPad instance topology unknown |
| NVMe/storage | Apple platform support exists | iPad wiring/boot use unknown |
| USB | Apple Silicon support exists in parts | Controller/PHY configuration unknown |
| GPU | Asahi DRM/Mesa work exists | Firmware/platform integration must be verified |
| Display | Apple display support is platform-specific | Expected major iPad-specific work |
| Touch | — | Expected iPad-specific work |
| Wi-Fi/Bluetooth | Apple-platform support exists in parts | Firmware/device configuration unknown |
| Audio | Apple-platform support exists for some machines | iPad codec/topology unknown |
| Cameras | — | Deferred; expected substantial reverse engineering |

## Target identification checklist

Before making platform-specific changes, record:

- Marketing model
- Model number
- Hardware machine identifier
- Board identifier if obtainable
- SoC identifier
- iPadOS version and build
- Storage/RAM configuration where relevant

## Next source trees to study

- Asahi Linux `m1n1`
- upstream Linux `arch/arm64`
- upstream Linux Apple platform drivers
- Asahi Linux kernel branches where functionality is not yet upstream
- U-Boot Apple Silicon platform support

Every hardware claim added here should include a source in the commit or accompanying research notes.
