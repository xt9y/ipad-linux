#!/usr/bin/env python3
"""Classify a captured J407 first-boot serial log.

The analyzer is intentionally heuristic: it never guesses a hardware result
which is not explicitly present in the log. Its main purpose is to turn one
UART/USB-console capture into a concise bring-up checklist.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys


STAGES = [
    ("m1n1", ("m1n1", "Running proxy", "Booting Linux")),
    ("linux", ("Linux version ",)),
    ("pid1", ("ipad-linux early userspace",)),
    ("diagnostics", ("FIRST_BOOT_DIAGNOSTICS_COMPLETE",)),
]


def any_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def parse_summary(text: str) -> dict[str, object]:
    reached: list[str] = []
    for name, markers in STAGES:
        if any_marker(text, markers):
            reached.append(name)

    def explicit_state(prefix: str) -> str:
        match = re.search(rf"^\s*{re.escape(prefix)}=(\S+)\s*$", text, re.MULTILINE)
        return match.group(1) if match else "unknown"

    def count(name: str) -> int | None:
        match = re.search(rf"^\s*{re.escape(name)}=(\d+)", text, re.MULTILINE)
        return int(match.group(1)) if match else None

    return {
        "last_stage": reached[-1] if reached else "no-known-marker",
        "stages_reached": reached,
        "smp": explicit_state("SMP"),
        "nvme": explicit_state("ANS2/NVMe"),
        "usb": explicit_state("USB"),
        "typec": explicit_state("TYPEC"),
        "wifi4387": explicit_state("BCM4387-WIFI"),
        "bt4387": explicit_state("BCM4387-BT"),
        "wlan_interface": explicit_state("WLAN-INTERFACE"),
        "bluetooth_class": explicit_state("BLUETOOTH-CLASS"),
        "input": explicit_state("INPUT"),
        "sound": explicit_state("SOUND"),
        "graphics": explicit_state("framebuffer/DRM"),
        "cpu_nodes": count("cpu_nodes"),
        "block_devices": count("block_devices"),
        "nvme_controllers": count("nvme_controllers"),
        "graphics_entries": count("graphics_entries"),
        "usb_entries": count("usb_entries"),
        "typec_entries": count("typec_entries"),
        "pci_functions": count("pci_functions"),
        "net_interfaces": count("net_interfaces"),
        "wlan_interfaces": count("wlan_interfaces"),
        "bluetooth_entries": count("bluetooth_entries"),
        "input_entries": count("input_entries"),
        "sound_entries": count("sound_entries"),
        "aarch64_exception": "ipad-linux: AArch64 exception" in text,
        "linux_panic": "Kernel panic - not syncing" in text,
    }


def print_text(result: dict[str, object]) -> None:
    print(f"last_stage: {result['last_stage']}")
    print("stages: " + ", ".join(result["stages_reached"]))
    print(f"SMP: {result['smp']} (cpu_nodes={result['cpu_nodes']})")
    print(
        f"ANS2/NVMe: {result['nvme']} "
        f"(controllers={result['nvme_controllers']}, block_devices={result['block_devices']})"
    )
    print(f"USB: {result['usb']} (entries={result['usb_entries']})")
    print(f"Type-C: {result['typec']} (entries={result['typec_entries']})")
    print(
        f"BCM4387: wifi={result['wifi4387']} bt={result['bt4387']} "
        f"(pci_functions={result['pci_functions']})"
    )
    print(
        f"network: wlan={result['wlan_interface']} "
        f"(net={result['net_interfaces']}, wlan={result['wlan_interfaces']})"
    )
    print(
        f"bluetooth-class: {result['bluetooth_class']} "
        f"(entries={result['bluetooth_entries']})"
    )
    print(f"input: {result['input']} (entries={result['input_entries']})")
    print(f"sound: {result['sound']} (entries={result['sound_entries']})")
    print(f"graphics: {result['graphics']} (entries={result['graphics_entries']})")
    print(f"stage2_exception: {result['aarch64_exception']}")
    print(f"kernel_panic: {result['linux_panic']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=pathlib.Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        text = args.log.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"analyze-first-boot: {exc}", file=sys.stderr)
        return 1

    result = parse_summary(text)
    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        print()
    else:
        print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
