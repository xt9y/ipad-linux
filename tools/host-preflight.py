#!/usr/bin/env python3
"""Check whether a macOS/Linux host is ready for J407 physical testing.

This script does not perform an iPad boot exploit or change device state. It
only validates local tooling/artifacts and reports whether an already-running
m1n1 USB CDC interface is visible.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import platform
import shutil
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
KIT_VERIFIER = ROOT / "tools" / "verify-first-boot-kit.py"


def command(name: str) -> str | None:
    return shutil.which(name)


def m1n1_devices(system: str) -> list[str]:
    if system == "Darwin":
        return sorted(glob.glob("/dev/cu.usbmodem*"))
    if system == "Linux":
        return sorted(glob.glob("/dev/ttyACM*"))
    return []


def check_m1n1_tree(path: pathlib.Path | None) -> dict[str, Any]:
    if path is None:
        return {"provided": False, "valid": None, "missing": []}

    required = (
        "proxyclient/tools/shell.py",
        "proxyclient/tools/linux.py",
        "proxyclient/tools/picocom-sec.sh",
    )
    missing = [name for name in required if not (path / name).is_file()]
    return {
        "provided": True,
        "valid": not missing,
        "path": str(path),
        "missing": missing,
    }


def verify_kit(path: pathlib.Path | None) -> dict[str, Any]:
    if path is None:
        return {"provided": False, "valid": None}

    result = subprocess.run(
        [sys.executable, str(KIT_VERIFIER), str(path)],
        text=True,
        capture_output=True,
    )
    return {
        "provided": True,
        "valid": result.returncode == 0,
        "path": str(path),
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    system = platform.system()
    required_commands = {
        "python3": command("python3"),
        "git": command("git"),
    }
    optional_commands = {
        "picocom": command("picocom"),
        "screen": command("screen"),
        "lsusb": command("lsusb") if system == "Linux" else None,
        "system_profiler": command("system_profiler") if system == "Darwin" else None,
    }

    devices = m1n1_devices(system)
    return {
        "schema": 1,
        "target": "iPad13,16 / J407AP / T8103",
        "host": {
            "system": system,
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "host_supported": system in ("Darwin", "Linux"),
        "required_commands": required_commands,
        "optional_commands": optional_commands,
        "m1n1_tree": check_m1n1_tree(args.m1n1),
        "artifact_kit": verify_kit(args.artifact_dir),
        "m1n1_usb_devices": devices,
        "m1n1_usb_visible": bool(devices),
        "initial_entry_status": (
            "not checked; this project requires an independently available legitimate "
            "J407 mechanism to start m1n1"
        ),
    }


def print_text(result: dict[str, Any]) -> None:
    host = result["host"]
    print("J407 hardware-test host preflight")
    print(f"host={host['system']} {host['release']} arch={host['machine']}")
    print(f"host_supported={result['host_supported']}")

    for name, path in result["required_commands"].items():
        print(f"required:{name}={'OK ' + path if path else 'MISSING'}")
    for name, path in result["optional_commands"].items():
        if path:
            print(f"optional:{name}=OK {path}")

    tree = result["m1n1_tree"]
    if tree["provided"]:
        print(f"m1n1_tree={'OK' if tree['valid'] else 'INVALID'} {tree['path']}")
        for missing in tree["missing"]:
            print(f"  missing={missing}")

    kit = result["artifact_kit"]
    if kit["provided"]:
        print(f"artifact_kit={'VERIFIED' if kit['valid'] else 'INVALID'} {kit['path']}")
        if kit.get("stderr"):
            print(kit["stderr"])

    print("m1n1_usb_devices=" + (", ".join(result["m1n1_usb_devices"]) or "none"))
    print(
        "note: no USB CDC device is expected until m1n1 has actually been started "
        "on the target and its USB gadget path works"
    )
    print("entry=" + result["initial_entry_status"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=pathlib.Path)
    parser.add_argument("--m1n1", type=pathlib.Path, help="path to an upstream m1n1 checkout")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = build_result(args)
    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        print()
    else:
        print_text(result)

    if not result["host_supported"]:
        return 2
    if not all(result["required_commands"].values()):
        return 2
    if result["m1n1_tree"]["provided"] and not result["m1n1_tree"]["valid"]:
        return 2
    if result["artifact_kit"]["provided"] and not result["artifact_kit"]["valid"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
