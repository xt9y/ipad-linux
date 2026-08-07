#!/usr/bin/env python3
"""Build a privacy-conscious J407 physical-test report.

The report intentionally records reproducibility data (source revisions,
artifact checksums, boot-stage classification, ADT hash) but not hostname,
username, serial number or other account-specific host information.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import platform
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "analyze-first-boot.py"


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_optional(path: pathlib.Path | None) -> str | None:
    if path is None:
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def analyze_boot_log(path: pathlib.Path) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(ANALYZER), "--json", str(path)],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "boot-log analyzer failed")
    return json.loads(result.stdout)


def file_record(path: pathlib.Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return {
        "name": path.name,
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def markdown(report: dict[str, Any]) -> str:
    boot = report["boot_analysis"]
    files = report["files"]
    lines = [
        "# J407 physical boot report",
        "",
        f"Generated: `{report['generated_utc']}`",
        "",
        "## Target",
        "",
        f"- ProductType: `{report['target']['product_type']}`",
        f"- BoardConfig: `{report['target']['board_config']}`",
        f"- SoC: `{report['target']['soc']}`",
        f"- iPadOS reported by tester: `{report['target']['ipad_os']}`",
        "",
        "## Host",
        "",
        f"- OS: `{report['host']['system']} {report['host']['release']}`",
        f"- Architecture: `{report['host']['machine']}`",
        f"- Python: `{report['host']['python']}`",
        "",
        "## Boot result",
        "",
        f"- Last stage: **{boot['last_stage']}**",
        f"- Stages: `{', '.join(boot['stages_reached'])}`",
        f"- SMP: `{boot['smp']}` / CPUs: `{boot['cpu_nodes']}`",
        f"- NVMe: `{boot['nvme']}` / controllers: `{boot['nvme_controllers']}`",
        f"- USB: `{boot['usb']}` / Type-C: `{boot['typec']}`",
        f"- BCM4387 PCI functions: Wi-Fi `{boot['wifi4387']}`, BT `{boot['bt4387']}`",
        f"- WLAN interface: `{boot['wlan_interface']}`",
        f"- Bluetooth class: `{boot['bluetooth_class']}`",
        f"- Graphics: `{boot['graphics']}`",
        f"- Input: `{boot['input']}`",
        f"- Sound: `{boot['sound']}`",
        f"- Kernel panic: `{boot['linux_panic']}`",
        f"- Stage2 exception: `{boot['aarch64_exception']}`",
        "",
        "## Evidence files",
        "",
    ]

    for label, record in files.items():
        if record is None:
            lines.append(f"- {label}: not supplied")
        else:
            lines.append(
                f"- {label}: `{record['name']}` — {record['size']} bytes — "
                f"SHA-256 `{record['sha256']}`"
            )

    lines.extend(["", "## Source revisions", ""])
    source_commits = report.get("source_commits")
    if source_commits:
        lines.append("```text")
        lines.extend(source_commits.rstrip().splitlines())
        lines.append("```")
    else:
        lines.append("Not supplied.")

    lines.extend(["", "## Artifact checksum manifest", ""])
    checksum_manifest = report.get("checksum_manifest")
    if checksum_manifest:
        lines.append("```text")
        lines.extend(checksum_manifest.rstrip().splitlines())
        lines.append("```")
    else:
        lines.append("Not supplied.")

    adt_report = report.get("adt_report")
    lines.extend(["", "## Live ADT inspector output", ""])
    if adt_report:
        lines.append("```text")
        lines.extend(adt_report.rstrip().splitlines())
        lines.append("```")
    else:
        lines.append("Not supplied; collect this only after m1n1 proxy mode is available.")

    lines.extend(
        [
            "",
            "## What to send back",
            "",
            "Send this Markdown report together with the complete, unedited `boot.log`. ",
            "If a live ADT was collected, include `j407-live-adt.bin` as a separate file too.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boot-log", required=True, type=pathlib.Path)
    parser.add_argument("--adt-bin", type=pathlib.Path)
    parser.add_argument("--adt-report", type=pathlib.Path)
    parser.add_argument("--source-commits", type=pathlib.Path)
    parser.add_argument("--checksums", type=pathlib.Path)
    parser.add_argument("--ipad-os", default="unknown")
    parser.add_argument("--output-prefix", type=pathlib.Path,
                        default=pathlib.Path("j407-hardware-report"))
    args = parser.parse_args()

    for path in (
        args.boot_log,
        args.adt_bin,
        args.adt_report,
        args.source_commits,
        args.checksums,
    ):
        if path is not None and not path.is_file():
            print(f"build-hardware-report: file not found: {path}", file=sys.stderr)
            return 1

    try:
        boot_analysis = analyze_boot_log(args.boot_log)
        source_commits = read_optional(args.source_commits)
        checksum_manifest = read_optional(args.checksums)
        adt_report = read_optional(args.adt_report)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"build-hardware-report: {exc}", file=sys.stderr)
        return 1

    report: dict[str, Any] = {
        "schema": 1,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "target": {
            "product_type": "iPad13,16",
            "board_config": "J407AP",
            "soc": "T8103 / Apple M1",
            "ipad_os": args.ipad_os,
        },
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "boot_analysis": boot_analysis,
        "files": {
            "boot_log": file_record(args.boot_log),
            "live_adt": file_record(args.adt_bin),
            "adt_report": file_record(args.adt_report),
            "source_commits": file_record(args.source_commits),
            "checksums": file_record(args.checksums),
        },
        "source_commits": source_commits,
        "checksum_manifest": checksum_manifest,
        "adt_report": adt_report,
    }

    json_path = args.output_prefix.with_suffix(".json")
    md_path = args.output_prefix.with_suffix(".md")
    try:
        json_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        md_path.write_text(markdown(report), encoding="utf-8")
    except OSError as exc:
        print(f"build-hardware-report: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
