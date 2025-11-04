#!/usr/bin/env python3
"""Step 1.4 – Generate Rename Script (Python edition).

Reads the rename mappings from Step 1.3, validates source files, and produces a
rename plan plus a Python executor script. Moving to Python keeps this step
straightforward and avoids huge PowerShell heredocs.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

DEFAULT_MAPPINGS_FILE = "rename_mappings.json"
SCRIPT_TEMPLATE = "execute_renames_{timestamp}.py"
PLAN_TEMPLATE = "rename_plan_{timestamp}.json"
INSTRUCTIONS_FILE = "README_Step_1_4_RUN.txt"


@dataclass
class RenameItem:
    category: str
    old_path: Path
    new_path: Path
    old_name: str
    new_name: str

    @classmethod
    def from_dict(cls, payload: dict) -> "RenameItem":
        try:
            return cls(
                category=payload["Category"],
                old_path=Path(payload["OldPath"]).expanduser(),
                new_path=Path(payload["NewPath"]).expanduser(),
                old_name=payload["OldFileName"],
                new_name=payload["NewFileName"],
            )
        except KeyError as exc:
            raise SystemExit(f"Rename mapping missing key: {exc}")


def load_mappings(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Rename mappings file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse rename mappings JSON: {exc}")

    if "RenameMappings" not in data:
        raise SystemExit("Input JSON missing 'RenameMappings' array.")

    return data


def partition_items(items: Iterable[RenameItem]) -> tuple[List[RenameItem], List[RenameItem]]:
    valid, missing = [], []
    for item in items:
        (valid if item.old_path.exists() else missing).append(item)
    return valid, missing


def detect_default_backup(mapping_data: dict) -> bool:
    config_path = mapping_data.get("ConfigUsed")
    if not config_path:
        return True

    path = Path(config_path)
    if not path.exists():
        return True

    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True

    global_settings = config.get("GlobalSettings", {})
    backup_originals = global_settings.get("BackupOriginals")
    if isinstance(backup_originals, bool):
        return backup_originals
    return True


def write_plan(plan_path: Path, items: List[RenameItem], default_backup: bool, source_mapping: Path, missing: List[RenameItem]) -> None:
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_mapping": str(source_mapping),
        "default_backup": default_backup,
        "summary": {
            "total": len(items) + len(missing),
            "included": len(items),
            "missing": len(missing),
        },
        "items": [
            {
                "category": item.category,
                "old_path": str(item.old_path),
                "new_path": str(item.new_path),
                "old_file_name": item.old_name,
                "new_file_name": item.new_name,
            }
            for item in items
        ],
        "missing_items": [
            {
                "category": item.category,
                "old_path": str(item.old_path),
                "old_file_name": item.old_name,
            }
            for item in missing
        ],
    }
    plan_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def generate_executor_script(script_path: Path, plan_filename: str) -> None:
    template = r'''#!/usr/bin/env python3
"""Golden Wings rename executor (generated).

Usage:
    python {{script_name}} [--plan PATH] [--what-if] [--force] [--backup | --no-backup] [--log-file PATH]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_PLAN_NAME = "__PLAN_FILENAME__"


def load_plan(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Plan file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse plan JSON: {exc}")
    if "items" not in data:
        raise SystemExit("Plan JSON missing 'items' array.")
    return data


def ensure_parent(path: Path, *, dry_run: bool) -> None:
    parent = path.parent
    if parent.exists():
        return
    if dry_run:
        print(f"[WHAT-IF] Would create directory: {parent}")
        return
    parent.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Created directory: {parent}")


def backup_file(src: Path, backup_dir: Path, *, dry_run: bool) -> None:
    backup_path = backup_dir / src.name
    if dry_run:
        print(f"[WHAT-IF] Would back up {src} -> {backup_path}")
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, backup_path)
    print(f"[INFO] Backed up to {backup_path}")


def rename_file(src: Path, dst: Path, *, dry_run: bool, force: bool) -> None:
    if dry_run:
        print(f"[WHAT-IF] Would rename {src} -> {dst}")
        return
    if dst.exists():
        if not force:
            raise FileExistsError(f"Destination exists: {dst}")
        if dst.is_file() or dst.is_symlink():
            dst.unlink()
        else:
            raise IsADirectoryError(f"Destination is a directory: {dst}")
    shutil.move(str(src), str(dst))
    print(f"[INFO] Renamed {src.name} -> {dst.name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute rename operations from a plan JSON.")
    parser.add_argument("--plan", type=Path, help="Path to the rename plan JSON.")
    parser.add_argument("--what-if", action="store_true", help="Preview without making changes.")
    parser.add_argument("--force", action="store_true", help="Overwrite destinations if they exist.")
    parser.add_argument("--no-backup", action="store_true", help="Disable backups even if the plan default is true.")
    parser.add_argument("--backup", action="store_true", help="Force backups even if the plan default is false.")
    parser.add_argument("--log-file", type=Path, help="Optional log file path.")
    args = parser.parse_args(argv)

    script_dir = Path(__file__).resolve().parent
    script_name = Path(__file__).name
    plan_path = args.plan or (script_dir / DEFAULT_PLAN_NAME)

    plan = load_plan(plan_path)
    items = plan.get("items", [])
    default_backup = bool(plan.get("default_backup", True))
    backup_enabled = default_backup
    if args.no_backup:
        backup_enabled = False
    if args.backup:
        backup_enabled = True

    log_lines: list[str] = []

    def log(level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] {message}"
        log_lines.append(line)
        colour = {
            "ERROR": "\u001b[31m",
            "WARNING": "\u001b[33m",
            "SUCCESS": "\u001b[32m",
        }.get(level, "")
        reset = "\u001b[0m" if colour else ""
        print(f"{colour}{message}{reset}")

    log("INFO", f"Executor: {script_name}")
    log("INFO", f"Plan file: {plan_path}")
    log("INFO", f"Total operations: {len(items)}")
    log("INFO", f"Backup enabled: {backup_enabled} (default: {default_backup})")

    missing = plan.get("missing_items", [])
    if missing:
        log("WARNING", f"Missing source files noted in plan: {len(missing)} (skipped)")

    backup_dir: Path | None = None
    if backup_enabled and not args.what_if:
        backup_dir = script_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        log("SUCCESS", f"Backup directory: {backup_dir}")

    renamed = skipped = errors = 0

    for entry in items:
        category = entry.get("category", "unknown")
        old_path = Path(entry["old_path"]).expanduser()
        new_path = Path(entry["new_path"]).expanduser()
        log("INFO", f"[{category}] {old_path.name} -> {new_path.name}")

        if not old_path.exists():
            log("WARNING", f"Source not found: {old_path}")
            skipped += 1
            continue

        try:
            ensure_parent(new_path, dry_run=args.what_if)
            if backup_enabled and backup_dir is not None:
                backup_file(old_path, backup_dir, dry_run=args.what_if)
            rename_file(old_path, new_path, dry_run=args.what_if, force=args.force)
            renamed += 1
        except Exception as exc:  # noqa: BLE001
            log("ERROR", f"Failed to rename {old_path}: {exc}")
            errors += 1

    log("SUCCESS", f"Renamed: {renamed}, Skipped: {skipped}, Errors: {errors}")

    if args.log_file:
        args.log_file.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        log("INFO", f"Log written to {args.log_file}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
'''

    content = template.replace("__PLAN_FILENAME__", plan_filename)
    script_path.write_text(content, encoding="utf-8")
    script_path.chmod(0o755)


def write_instructions(path: Path, executor_path: Path, plan_path: Path, valid: int, missing: int, total: int, default_backup: bool) -> None:
    summary = "Enabled" if default_backup else "Disabled"
    content = f"""# Golden Wings Rename Script Usage (Python)
# Generated: {datetime.now():%Y-%m-%d %H:%M:%S}

Executor script: {executor_path}
Rename plan JSON: {plan_path}

## Quick Start
1. Inspect the plan: `python -m json.tool {plan_path}`
2. Dry run: `python {executor_path} --what-if`
3. Execute: `python {executor_path}`

Default backup behaviour: {summary}
Override per run with `--no-backup` or `--backup`.

## Plan Summary
- Total mappings listed: {total}
- Valid files included: {valid}
- Missing source files skipped: {missing}

Keep the executor script and plan JSON together, or pass `--plan` with the path.
"""
    path.write_text(content, encoding="utf-8")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Python rename executor from Step 1.3 mappings.")
    parser.add_argument("--input", dest="input_file", type=Path, default=Path(DEFAULT_MAPPINGS_FILE), help="Path to rename_mappings.json")
    parser.add_argument("--output-script", dest="output_script", type=Path, help="Path for generated executor script")
    parser.add_argument("--plan", dest="plan_path", type=Path, help="Path for plan JSON (defaults beside script)")
    parser.add_argument("--dry-run", action="store_true", help="Preview the plan without writing files")
    parser.add_argument("--include-backup", action="store_true", help="Force default backup to enabled")
    parser.add_argument("--no-backup", action="store_true", help="Force default backup to disabled")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    input_file = args.input_file.expanduser().resolve()
    mapping_data = load_mappings(input_file)
    rename_items = [RenameItem.from_dict(item) for item in mapping_data["RenameMappings"]]
    valid, missing = partition_items(rename_items)

    if not valid:
        print("❌ No valid rename operations found (all sources missing).", file=sys.stderr)
        return 1

    default_backup = detect_default_backup(mapping_data)
    if args.include_backup:
        default_backup = True
    if args.no_backup:
        default_backup = False

    print(f"Loaded {len(rename_items)} mappings. Valid: {len(valid)}, Missing: {len(missing)}")
    print(f"Default backup behaviour for executor: {'Enabled' if default_backup else 'Disabled'}")

    if args.dry_run:
        for item in valid[:10]:
            print(f" • [{item.category}] {item.old_path.name} -> {item.new_name}")
        if len(valid) > 10:
            print(f"   … and {len(valid) - 10} more")
        if missing:
            print(f"(!) {len(missing)} source files are missing and would be skipped")
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan_path = (args.plan_path.expanduser().resolve() if args.plan_path else input_file.parent / PLAN_TEMPLATE.format(timestamp=timestamp))
    output_script = (args.output_script.expanduser().resolve() if args.output_script else input_file.parent / SCRIPT_TEMPLATE.format(timestamp=timestamp))

    write_plan(plan_path, valid, default_backup, input_file, missing)
    generate_executor_script(output_script, plan_path.name)

    instructions_path = input_file.parent / INSTRUCTIONS_FILE
    write_instructions(instructions_path, output_script, plan_path, len(valid), len(missing), len(rename_items), default_backup)

    print(f"✅ Generated executor script: {output_script}")
    print(f"📦 Plan JSON: {plan_path}")
    print(f"📋 Usage instructions: {instructions_path}")
    if missing:
        print(f"⚠️  Skipped {len(missing)} missing sources. See plan JSON for details.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
