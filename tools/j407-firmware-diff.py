#!/usr/bin/env python3
"""Compare two J407/iPad13 IPSW BuildManifests for boot-chain research.

The tool reads only BuildManifest.plist files (specified directly, or via
a directory that contains one). It diffs top-level identity fields,
restore identities, boot-chain components (digests, build numbers and
per-component restore policy) and NeRD-type policy keys.

Sanitization contract: nothing device-unique is ever printed. Keys whose
name mentions ECID/serial/UDID are reported as present but redacted,
digest values are summarized as short SHA-256 prefixes, and binary blobs
only as their byte length. The report is written for the research notes.

Usage:
  tools/j407-firmware-diff.py <buildA> <buildB> [--fail-on-difference]

Exit codes: 0 comparision ok, 1 differences found (only with
--fail-on-difference), 2 input/usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import plistlib
import sys

REDACT_KEY_FRAGMENTS = ("ecid", "serial", "udid")
POLICY_KEY_FRAGMENT = "nerd"
MANIFEST_FILENAME = "BuildManifest.plist"
MAX_TEXT = 96


def resolve_manifest(path: pathlib.Path) -> pathlib.Path:
    if path.is_dir():
        path = path / MANIFEST_FILENAME
    if not path.is_file():
        print(f"j407-firmware-diff: no manifest at {path}", file=sys.stderr)
        raise SystemExit(2)
    return path


def load_manifest(path: pathlib.Path) -> dict:
    try:
        with open(path, "rb") as handle:
            return plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException) as err:
        print(f"j407-firmware-diff: cannot parse {path}: {err}", file=sys.stderr)
        raise SystemExit(2)


def digest_prefix(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def sanitize_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, bytes):
        return f"<data:{len(value)}B>"
    if isinstance(value, dict):
        return f"<table:{len(value)}keys>"
    if isinstance(value, list):
        return f"<list:{len(value)}>"
    text = str(value)
    if len(text) > MAX_TEXT:
        text = text[: MAX_TEXT - 1] + "…"
    return text


def sanitize_value_of(key: str, value) -> str:
    lowered = key.lower()
    if any(fragment in lowered for fragment in REDACT_KEY_FRAGMENTS):
        return "<redacted>"
    return sanitize_value(value)


def scan_policy_keys(node, out: dict, depth: int = 0) -> None:
    """Collect every nested key mentioning the policy fragment with a scalar value."""
    if depth > 4:
        return
    if isinstance(node, dict):
        for key, value in node.items():
            if POLICY_KEY_FRAGMENT in str(key).lower() and isinstance(
                value, (bool, int, float, str)
            ):
                out[str(key)] = sanitize_value_of(str(key), value)
            scan_policy_keys(value, out, depth + 1)


def identity_info(identity: dict) -> dict:
    info = identity.get("Info", {})
    return info if isinstance(info, dict) else {}


def summarize_component(name: str, entry) -> dict:
    if not isinstance(entry, dict):
        return {"name": name, "malformed": True}
    info = entry.get("Info", {}) if isinstance(entry.get("Info"), dict) else {}
    digest = entry.get("Digest")
    rules = info.get("RestoreRequestRules", [])
    return {
        "name": name,
        "build": str(entry.get("BuildNumber", "")) or None,
        "digest": digest_prefix(digest) if isinstance(digest, bytes) else None,
        "personalize": bool(info.get("Personalize", entry.get("Personalize", False))),
        "rules": len(rules) if isinstance(rules, list) else None,
        "rule_actions": (
            sorted(
                {
                    action_name
                    for rule in rules
                    if isinstance(rule, dict)
                    for action_name in iter_rule_action_names(rule)
                }
            )
            if isinstance(rules, list)
            else None
        ),
    }


def iter_rule_action_names(rule: dict):
    if isinstance(rule.get("Action"), dict):
        yield from rule["Action"].keys()
    for item in rule.get("Actions", []) or []:
        if isinstance(item, dict) and isinstance(item.get("Action"), dict):
            yield from item["Action"].keys()


def summarize_identity(identity: dict) -> dict:
    info = identity_info(identity)
    components = {
        name: summarize_component(str(name), entry)
        for name, entry in sorted(identity.get("Manifest", {}).items())
    }
    policy: dict = {}
    scan_policy_keys(identity, policy)
    return {
        "variant": str(info.get("Variant", "<unknown>")),
        "restore_behavior": str(info.get("RestoreBehavior", "<unknown>")),
        "build_number": str(info.get("BuildNumber", "<unknown>")),
        "device_class": str(info.get("DeviceClass", "<unknown>")),
        "chipid": identity.get("ApChipID"),
        "boardid": identity.get("ApBoardID"),
        "security_domain": identity.get("ApSecurityDomain"),
        "components": components,
        "policy": policy,
    }


def summarize_manifest(manifest: dict) -> dict:
    identities = manifest.get("BuildIdentities", [])
    if not isinstance(identities, list) or not identities:
        print("j407-firmware-diff: manifest has no BuildIdentities array", file=sys.stderr)
        raise SystemExit(2)
    variants: dict = {}
    for identity in identities:
        if not isinstance(identity, dict):
            continue
        summary = summarize_identity(identity)
        variants[summary["variant"]] = summary
    policy: dict = {}
    scan_policy_keys(manifest, policy)
    return {
        "product_type": manifest.get("ProductType"),
        "product_version": manifest.get("ProductVersion"),
        "supported_product_types": list(manifest.get("SupportedProductTypes", [])),
        "manifest_version": manifest.get("ManifestVersion"),
        "unique_build_id": (
            digest_prefix(manifest["UniqueBuildID"])
            if isinstance(manifest.get("UniqueBuildID"), bytes)
            else None
        ),
        "variants": variants,
        "policy": policy,
        "identity_count": len(identities),
    }


def fmt_change(a, b) -> str:
    av, bv = sanitize_value(a), sanitize_value(b)
    return "same: " + av if a == b else f"changed: {av} -> {bv}"


def compare_components(name, a, b) -> list[str]:
    lines = []
    if name not in a:
        lines.append(f"    [only-in-B] {name}")
        return lines
    if name not in b:
        lines.append(f"    [only-in-A] {name}")
        return lines
    ca, cb = a[name], b[name]
    if ca == cb:
        personalize = "y" if ca["personalize"] else "n"
        rules = "" if ca["rules"] is None else f" rules={ca['rules']}"
        actions = ""
        if ca["rule_actions"]:
            actions = " actions=" + ",".join(ca["rule_actions"])
        lines.append(
            f"    [identical] {name}  build={ca['build']}  digest={ca['digest']}"
            f"  personalize={personalize}{rules}{actions}"
        )
        return lines
    what = []
    if ca["digest"] != cb["digest"]:
        what.append(
            f"digest {ca['digest']} -> {cb['digest']}"
            if ca["digest"] and cb["digest"]
            else "digest (none -> present or vice versa)"
        )
    if ca["build"] != cb["build"]:
        what.append(f"build {ca['build']} -> {cb['build']}")
    if ca["personalize"] != cb["personalize"]:
        what.append(f"personalize {ca['personalize']} -> {cb['personalize']}")
    if ca["rules"] != cb["rules"]:
        what.append(f"rules {ca['rules']} -> {cb['rules']}")
    context = []
    if ca["personalize"] == cb["personalize"]:
        context.append(f"personalize={'y' if ca['personalize'] else 'n'}")
    if ca["rules"] == cb["rules"] and ca["rules"] is not None:
        context.append(f"rules={ca['rules']}")
        if ca["rule_actions"]:
            context.append("actions=" + ",".join(ca["rule_actions"]))
    tail = ("  " + " ".join(context)) if context else ""
    lines.append(f"    [changed]   {name}  " + "; ".join(what) + tail)
    return lines


def fmt_policy_list(policy: dict) -> str:
    if not policy:
        return "(none found)"
    return ", ".join(f"{key}={policy[key]}" for key in sorted(policy))


def compare_policy(a: dict, b: dict) -> list[str]:
    lines = []
    keys_a, keys_b = set(a), set(b)
    for key in sorted(keys_a - keys_b):
        lines.append(f"  only-in-A: {key}={a[key]}")
    for key in sorted(keys_b - keys_a):
        lines.append(f"  only-in-B: {key}={b[key]}")
    for key in sorted(keys_a & keys_b):
        if a[key] != b[key]:
            lines.append(f"  changed:   {key}: {a[key]} -> {b[key]}")
    return lines


def build_report(a: dict, b: dict) -> tuple[list[str], int]:
    lines: list[str] = []
    differences = 0
    if a == b:
        return ["result: no differences"], 0

    report: list[str] = []
    report.append("top-level identity")
    for field in ("product_type", "product_version", "manifest_version", "unique_build_id"):
        change = fmt_change(a[field], b[field])
        if not change.startswith("same: "):
            differences += 1
        report.append(f"  {field}: {change}")
    types_same = a["supported_product_types"] == b["supported_product_types"]
    if not types_same:
        differences += 1
    report.append(f"  supported_product_types: {'same' if types_same else 'changed'}")

    policy_lines = compare_policy(a["policy"], b["policy"])
    differences += len(policy_lines)
    report.append("policy (NeRD-type fragments across the manifest)")
    report.append("  A: " + fmt_policy_list(a["policy"]))
    report.append("  B: " + fmt_policy_list(b["policy"]))
    if policy_lines:
        report.extend("  " + line for line in policy_lines)
    else:
        report.append("  no policy-fragment differences between A and B")
    if not (a["policy"] or b["policy"]):
        report.append("  (absence is itself the finding: check again per-build)")

    report.append(f"identities (A has {a['identity_count']}, B has {b['identity_count']})")
    for variant in sorted(set(a["variants"]) | set(b["variants"])):
        if variant not in a["variants"]:
            differences += 1
            report.append(f"  [only-in-B] Variant={variant}")
            continue
        if variant not in b["variants"]:
            differences += 1
            report.append(f"  [only-in-A] Variant={variant}")
            continue
        va, vb = a["variants"][variant], b["variants"][variant]
        report.append(f"  [matched]   Variant={variant}")
        for field in ("restore_behavior", "build_number", "device_class", "chipid", "boardid"):
            if va[field] == vb[field]:
                report.append(f"      {field}: {fmt_change(va[field], vb[field])}")
            else:
                differences += 1
                report.append(f"      {field}: {fmt_change(va[field], vb[field])}")
        identities_policy = compare_policy(va["policy"], vb["policy"])
        if identities_policy:
            differences += len(identities_policy)
            report.extend("      " + line for line in identities_policy)
        components = []
        for name in sorted(set(va["components"]) | set(vb["components"])):
            components.extend(compare_components(name, va["components"], vb["components"]))
        report.append("    components:")
        report.extend(components)
        differences += sum(
            1 for line in components if not line.strip().startswith("[identical]")
        )

    return report, differences


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_a", type=pathlib.Path)
    parser.add_argument("manifest_b", type=pathlib.Path)
    parser.add_argument(
        "--fail-on-difference",
        action="store_true",
        help="exit 1 when the manifests differ (0 otherwise)",
    )
    args = parser.parse_args()

    a = summarize_manifest(load_manifest(resolve_manifest(args.manifest_a)))
    b = summarize_manifest(load_manifest(resolve_manifest(args.manifest_b)))

    print("J407/iPad13 BuildManifest comparison (sanitized report)")
    print(f"  A: {args.manifest_a}")
    print(f"  B: {args.manifest_b}")
    print(f"  A identity: ProductType={sanitize_value(a['product_type'])}"
          f" ProductVersion={sanitize_value(a['product_version'])}")
    print(f"  B identity: ProductType={sanitize_value(b['product_type'])}"
          f" ProductVersion={sanitize_value(b['product_version'])}")

    report, differences = build_report(a, b)
    print()
    print("\n".join(report))
    print()
    print(f"differences: {differences}")
    if args.fail_on_difference and differences:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
