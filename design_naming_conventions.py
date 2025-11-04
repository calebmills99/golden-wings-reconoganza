#!/usr/bin/env python3
"""Step 1.3 – Naming Convention Design (Python edition).

Mirrors the PowerShell implementation by consuming classification results,
applies naming rules, and emits a rename mapping report without touching the
source files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

DATE_TOKEN_PATTERN = re.compile(r"(\d{4})(\d{2})(\d{2})|(\d{4})[-_](\d{2})[-_](\d{2})")
SUPPORTED_CONDITIONS = {"filename", "fullpath", "keywords", "extension"}
DATE_FORMAT_REPLACEMENTS = {
    "yyyy": "%Y",
    "yyy": "%Y",
    "yy": "%y",
    "MM": "%m",
    "dd": "%d",
    "HH": "%H",
    "hh": "%I",
    "mm": "%M",
    "ss": "%S",
}


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Failed to read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path}: {exc}") from exc


def ensure_rules(config: dict) -> Dict[str, dict]:
    rules = config.get("NamingRules")
    if not isinstance(rules, dict):
        raise RuntimeError("Config missing 'NamingRules' object")
    return rules


def ensure_global_settings(config: dict) -> dict:
    settings = dict(config.get("GlobalSettings", {}))
    settings.setdefault("DateFormat", "yyyy-MM-dd")
    settings.setdefault("HandleDuplicates", "AddVersion")
    settings.setdefault("PreservePaths", True)
    return settings


def translate_date_format(net_format: str) -> str:
    result = net_format
    for token, replacement in DATE_FORMAT_REPLACEMENTS.items():
        result = result.replace(token, replacement)
    return result


def normalize_extension(value: Optional[str]) -> str:
    if not value:
        return ""
    # Keep the dot for the extension
    clean_ext = value.strip().lower()
    if not clean_ext.startswith("."):
        clean_ext = "." + clean_ext
    return clean_ext


def normalize_keywords(values: Iterable[str]) -> List[str]:
    return [str(item).lower() for item in values if item is not None]


def evaluate_condition(key: str, expected, context: dict) -> bool:
    lowered = key.lower()
    if lowered == "filename":
        pattern = str(expected)
        return re.search(pattern, context["file_name"], re.IGNORECASE) is not None
    if lowered == "fullpath":
        if not context["full_path"]:
            return False
        return re.search(str(expected), context["full_path"], re.IGNORECASE) is not None
    if lowered == "keywords":
        if isinstance(expected, Iterable) and not isinstance(expected, str):
            required = expected
        else:
            required = [expected]
        normalized = [str(item).lower() for item in required if item is not None]
        if not normalized:
            return True
        keywords = set(context["keywords"])
        return all(keyword in keywords for keyword in normalized)
    if lowered == "extension":
        expected_value = normalize_extension(expected)
        return context["extension"] == expected_value
    print(f"⚠️  WARNING: Unsupported condition '{key}'.")
    return False


def copy_mapping(mapping: Optional[dict]) -> dict:
    if not mapping:
        return {}
    return deepcopy(mapping)


def apply_rules(category_config: dict, context: dict) -> dict:
    rules = category_config.get("Rules") or []
    for rule in rules:
        conditions = rule.get("Condition") or {}
        if not isinstance(conditions, dict):
            continue
        if all(evaluate_condition(key, conditions[key], context) for key in conditions):
            return copy_mapping(rule.get("Mapping"))
    return copy_mapping(category_config.get("DefaultMapping"))


def derive_date(file_name: str, modified_value: Optional[str]) -> datetime:
    match = DATE_TOKEN_PATTERN.search(file_name)
    if match:
        try:
            if match.group(1):
                return datetime.strptime(match.group(1) + match.group(2) + match.group(3), "%Y%m%d")
            return datetime.strptime(
                f"{match.group(4)}-{match.group(5)}-{match.group(6)}",
                "%Y-%m-%d",
            )
        except ValueError:
            pass
    if modified_value:
        for pattern in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(modified_value, pattern)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(modified_value)
        except ValueError:
            pass
    return datetime.now()


def replace_placeholders(pattern: str, mapping: dict) -> str:
    result = pattern
    for key, value in mapping.items():
        token = "{" + str(key) + "}"
        text = "" if value is None else str(value)
        result = result.replace(token, text if text else "Unknown")
    return re.sub(r"\{[^}]+\}", "Unknown", result)


def build_context(file_entry: dict) -> dict:
    extension = normalize_extension(file_entry.get("Extension"))
    keywords = normalize_keywords(file_entry.get("Keywords", []))
    return {
        "file_name": str(file_entry.get("FileName", "")),
        "full_path": str(file_entry.get("FullPath", "")) if file_entry.get("FullPath") else "",
        "extension": extension,
        "keywords": keywords,
    }


def resolve_destination(file_entry: dict, script_dir: Path, preserve_paths: bool) -> Path:
    if preserve_paths:
        full_path = file_entry.get("FullPath")
        if full_path:
            try:
                return Path(full_path).expanduser().resolve().parent
            except (OSError, RuntimeError):
                pass
        directory = file_entry.get("Directory")
        if directory:
            try:
                return Path(directory).expanduser().resolve()
            except (OSError, RuntimeError):
                pass
    return script_dir


def handle_conflicts(rename_mappings: List[dict], settings: dict) -> int:
    by_path: Dict[str, List[dict]] = defaultdict(list)
    for item in rename_mappings:
        by_path[item["NewPath"]].append(item)
    conflict_groups = [(path, entries) for path, entries in by_path.items() if len(entries) > 1]
    if not conflict_groups:
        return 0
    print(f"⚠️  Found {len(conflict_groups)} naming conflicts:")
    for new_path, items in conflict_groups:
        print(f"   Conflict: {new_path}")
        items.sort(key=lambda entry: entry.get("OriginalFile", {}).get("Score", 0), reverse=True)
        for index, entry in enumerate(items):
            original = entry.get("OldFileName", "<unknown>")
            rank = entry.get("OriginalFile", {}).get("Rank", "?")
            print(f"      • {original} (Rank {rank})")
            if index == 0:
                continue
            strategy = str(settings.get("HandleDuplicates", "AddVersion"))
            name = entry["NewFileName"]
            extension = Path(name).suffix
            stem = name[: -len(extension)] if extension else name
            if strategy == "AddVersion":
                entry["NewFileName"] = f"{stem}_v{index + 1}{extension}"
            elif strategy == "AppendRank":
                entry["NewFileName"] = f"{stem}_rank{rank}{extension}"
            else:
                print(f"      → Duplicate handling set to '{strategy}' - no automatic fix applied.")
                continue
            new_full_path = Path(entry["NewPath"]).parent / entry["NewFileName"]
            entry["NewPath"] = str(new_full_path)
            print(f"      → Resolved to: {entry['NewFileName']}")
    print("")
    return len(conflict_groups)


def export_results(script_dir: Path, summary: dict, rename_mappings: List[dict], config_path: Path, preview_only: bool) -> None:
    payload = {
        "GeneratedDate": datetime.now().isoformat(timespec="seconds"),
        "Summary": summary,
        "RenameMappings": rename_mappings,
        "ConfigUsed": str(config_path.resolve()),
        "PreviewOnly": preview_only,
    }
    output_path = script_dir / "rename_mappings.json"
    try:
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"💾 Rename mappings exported to: {output_path}")
    except OSError as exc:
        print(f"❌ Failed to export rename mappings: {exc}")


def process_classification(classification_data: dict, config: dict, script_dir: Path, preview_only: bool) -> Tuple[dict, List[dict]]:
    summary = {
        "TotalFiles": 0,
        "FilesRenamed": 0,
        "Conflicts": 0,
        "Errors": 0,
    }
    global_settings = ensure_global_settings(config)
    date_format = translate_date_format(str(global_settings.get("DateFormat", "yyyy-MM-dd")))
    category_rules = ensure_rules(config)
    rename_mappings: List[dict] = []

    classifications = classification_data.get("Classifications", {})
    if not isinstance(classifications, dict):
        raise RuntimeError("Classification data missing 'Classifications'")

    for category_name, files in classifications.items():
        if not files:
            continue
        category_config = category_rules.get(category_name)
        if not category_config:
            print(f"⚠️  WARNING: No naming rules configured for category '{category_name}'. Skipping.")
            summary["Errors"] += len(files)
            continue
        pattern = category_config.get("Pattern")
        if not pattern:
            print(f"⚠️  WARNING: Category '{category_name}' is missing a pattern. Skipping.")
            summary["Errors"] += len(files)
            continue
        print(f"📂 Processing {category_name} ({len(files)} files):")
        for file_entry in files:
            try:
                summary["TotalFiles"] += 1
                context = build_context(file_entry)
                mapping = apply_rules(category_config, context)
                if "{Date}" in pattern and "Date" not in mapping:
                    date_value = derive_date(context["file_name"], file_entry.get("Modified"))
                    mapping["Date"] = date_value.strftime(date_format)
                if "{ext}" in pattern and "ext" not in mapping:
                    mapping["ext"] = context["extension"]
                if "{Rank}" in pattern and "Rank" not in mapping:
                    mapping["Rank"] = str(file_entry.get("Rank", ""))
                new_file_name = replace_placeholders(pattern, mapping)
                if not new_file_name:
                    raise RuntimeError(f"Failed to build new file name from pattern '{pattern}'")
                destination = resolve_destination(file_entry, script_dir, bool(global_settings.get("PreservePaths", True)))
                new_path = destination / new_file_name
                rename_mappings.append(
                    {
                        "OriginalFile": file_entry,
                        "Category": category_name,
                        "OldFileName": file_entry.get("FileName"),
                        "NewFileName": new_file_name,
                        "OldPath": file_entry.get("FullPath"),
                        "NewPath": str(new_path),
                        "Mapping": mapping,
                        "PatternUsed": pattern,
                    }
                )
                summary["FilesRenamed"] += 1
                print(f"   ✅ {file_entry.get('FileName')} → {new_file_name}")
            except Exception as exc:  # noqa: BLE001
                summary["Errors"] += 1
                print(f"   ❌ Error processing {file_entry.get('FileName')}: {exc}")
        print("")

    print("🔍 Checking for naming conflicts...")
    conflicts = handle_conflicts(rename_mappings, global_settings)
    summary["Conflicts"] = conflicts
    if conflicts == 0:
        print("✅ No naming conflicts detected.\n")
    return summary, rename_mappings


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design naming conventions from classification data")
    parser.add_argument("--input-file", type=Path, help="Path to classification results JSON")
    parser.add_argument("--config-file", type=Path, help="Path to naming convention config JSON")
    parser.add_argument("--preview-only", action="store_true", help="Preview mode; no renames performed")
    parser.add_argument("--no-pause", action="store_true", help="Skip pause prompt at the end")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    script_dir = Path(__file__).resolve().parent

    print("🏷️  Step 1.3: Naming Convention Design")
    print("=====================================")
    print("")

    input_path = args.input_file.resolve() if args.input_file else script_dir / "content_classification_results.json"
    config_path = args.config_file.resolve() if args.config_file else script_dir / "naming_convention_config.json"

    print(f"📁 Working directory: {script_dir}")
    print(f"📄 Reading classification results: {input_path}")
    print(f"🧠 Using naming config: {config_path}")
    if args.preview_only:
        print("👁️  Preview mode: No files will be renamed")
    print("")

    if not input_path.exists():
        print(f"❌ ERROR: Classification results file not found at '{input_path}'. Run Step 1.2 first.")
        return 1
    if not config_path.exists():
        print(f"❌ ERROR: Naming convention config file not found at '{config_path}'.")
        print("   Create one from the template in README_Step_1_3.md or copy the default repo version.")
        return 1

    try:
        classification_data = load_json(input_path)
        print("✅ Loaded classification results")
    except RuntimeError as exc:
        print(f"❌ ERROR: {exc}")
        return 1

    try:
        naming_config = load_json(config_path)
        print("✅ Loaded naming convention config")
    except RuntimeError as exc:
        print(f"❌ ERROR: {exc}")
        return 1

    print("")
    try:
        summary, rename_mappings = process_classification(classification_data, naming_config, script_dir, args.preview_only)
    except RuntimeError as exc:
        print(f"❌ ERROR: {exc}")
        return 1

    print("=====================================")
    print("📊 NAMING CONVENTION SUMMARY")
    print("=====================================")
    print(f"📄 Total files processed: {summary['TotalFiles']}")
    print(f"✅ Files with new names: {summary['FilesRenamed']}")
    print(f"⚠️  Naming conflicts resolved: {summary['Conflicts']}")
    print(f"❌ Processing errors: {summary['Errors']}")
    print("")

    export_results(script_dir, summary, rename_mappings, config_path, args.preview_only)

    print("")
    print("🎉 Step 1.3 Complete! Ready for Step 1.4 - Generate Rename Script")
    print("")

    if not args.no_pause:
        try:
            input("Press Enter to exit...")
        except EOFError:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
