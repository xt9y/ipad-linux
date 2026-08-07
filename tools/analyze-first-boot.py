#!/usr/bin/env python3
"""Classify a captured J407 first-boot serial log.

The analyzer is intentionally heuristic: it never guesses a hardware result
which is not explicitly present in the log. Its main purpose is to turn one
UART capture into a concise bring-up checklist.
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

    cpu_match = re.search(r"^\s*cpu_nodes=(\d+)", text, re.MULTILINE)
    block_match = re.search(r"^\s*block_devices=(\d+)", text, re.MULTILINE)
    nvme_count_match = re.search(r"^\s*nvme_controllers=(\d+)", text, re.MULTILINE)
    graphics_match = re.search(r"^\s*graphics_entries=(\d+)", text, re.MULTILINE)

    return {
        "last_stage": reached[-1] if reached else "no-known-marker",
        "stages_reached": reached,
        "smp": explicit_state("SMP"),
        "nvme": explicit_state("ANS2/NVMe"),
        "graphics": explicit_state("framebuffer/DRM"),
        "cpu_nodes": int(cpu_match.group(1)) if cpu_match else None,
        "block_devices": int(block_match.group(1)) if block_match else None,
        "nvme_controllers": int(nvme_count_match.group(1)) if nvme_count_match else None,
        "graphics_entries": int(graphics_match.group(1)) if graphics_match else None,
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
