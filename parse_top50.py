#!/usr/bin/env python3
"""Step 1.1 – Parse TOP50.md (Python edition).

Parses the structured Markdown list, validates that referenced files exist, and
exports canonical data for downstream steps.

Why the rewrite? The original PowerShell script relied on a very long here-string
and interactive prompts, which made it slow to iterate. This Python version keeps
things concise, runs cross-platform, and offers richer CLI flags.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

DEFAULT_MARKDOWN = "TOP50.md"
DEFAULT_OUTPUT = "top50_parsed_data.json"
ENTRY_PATTERN = re.compile(
    r"(?s)## (\d+)\.\s*(.+?)\n\n\*\*Score:\*\*\s*(\d+).*?\n\*\*Path:\*\*\s*`([^`]+)`\n\*\*Size:\*\*\s*([^\n]+)\n\*\*Modified:\*\*\s*([^\n]+)\n\*\*Keywords:\*\*\s*([^\n]+)"
)


@dataclass
class ParsedEntry:
    rank: int
    file_name: str
    score: int
    full_path: Path
    size_raw: str
    size_bytes: int
    modified_raw: str
    modified_iso: str
    keywords: List[str]
    directory: Path
    extension: str
    drive: str
    exists: bool

    def to_dict(self) -> dict:
        return {
            "Rank": self.rank,
            "FileName": self.file_name,
            "Score": self.score,
            "FullPath": str(self.full_path),
            "Directory": str(self.directory),
            "Size": self.size_raw,
            "SizeBytes": self.size_bytes,
            "Modified": self.modified_iso,
            "Keywords": self.keywords,
            "Extension": self.extension,
            "Drive": self.drive,
            "Exists": self.exists,
        }


@dataclass
class MissingEntry:
    rank: int
    file_name: str
    path: Path
    score: int

    def to_dict(self) -> dict:
        return {
            "Rank": self.rank,
            "FileName": self.file_name,
            "Path": str(self.path),
            "Score": self.score,
        }


def parse_markdown_entries(markdown: str) -> Sequence[re.Match[str]]:
    matches = ENTRY_PATTERN.findall(markdown)
    if not matches:
        raise ValueError("No entries matched the expected TOP50.md format.")
    return ENTRY_PATTERN.finditer(markdown)


def parse_size(size_str: str) -> int:
    match = re.search(r"(?i)(\d+\.?\d*)\s*(bytes?|kb|mb|gb)", size_str)
    if not match:
        return 0
    number = float(match.group(1))
    unit = match.group(2).lower()
    if unit.startswith("byte"):
        factor = 1
    elif unit == "kb":
        factor = 1024
    elif unit == "mb":
        factor = 1024 ** 2
    elif unit == "gb":
        factor = 1024 ** 3
    else:
        factor = 1
    return int(number * factor)


def try_parse_datetime(value: str) -> str:
    value = value.strip()
    # Common patterns seen in the inventory
    patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y",
        "%d %b %Y %H:%M",
    ]
    for pattern in patterns:
        try:
            return datetime.strptime(value, pattern).isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value).isoformat()
    except ValueError:
        return value


def collect_entries(matches: Iterable[re.Match[str]], *, skip_ranks: int) -> tuple[List[ParsedEntry], List[MissingEntry], List[dict]]:
    parsed: List[ParsedEntry] = []
    missing: List[MissingEntry] = []
    errors: List[dict] = []

    for match in matches:
        try:
            rank = int(match.group(1))
            if rank <= skip_ranks:
                continue
            file_name = match.group(2).strip()
            score = int(match.group(3))
            full_path = Path(match.group(4).strip()).expanduser()
            size_raw = match.group(5).strip()
            modified_raw = match.group(6).strip()
            keywords_raw = match.group(7).strip()

            size_bytes = parse_size(size_raw)
            modified_iso = try_parse_datetime(modified_raw)
            keywords = [kw.strip() for kw in keywords_raw.split(',') if kw.strip()]
            extension = full_path.suffix.lower() or Path(file_name).suffix.lower()
            drive = full_path.drive or "Unknown"
            exists = full_path.exists()

            entry = ParsedEntry(
                rank=rank,
                file_name=file_name,
                score=score,
                full_path=full_path,
                size_raw=size_raw,
                size_bytes=size_bytes,
                modified_raw=modified_raw,
                modified_iso=modified_iso,
                keywords=keywords,
                directory=full_path.parent,
                extension=extension,
                drive=drive,
                exists=exists,
            )
            parsed.append(entry)

            if not exists:
                missing.append(MissingEntry(rank, file_name, full_path, score))

        except Exception as exc:  # noqa: BLE001
            errors.append(
                {
                    "Rank": match.group(1) if match.group(1) else "?",
                    "Error": str(exc),
                    "Raw": match.group(0)[:200],
                }
            )

    return parsed, missing, errors


def print_breakdown(parsed: List[ParsedEntry]) -> None:
    summary_line = f"Parsed {len(parsed)} entries."
    print(summary_line)

    ext_counts = Counter(entry.extension or "<none>" for entry in parsed)
    drive_counts = Counter(entry.drive for entry in parsed)

    def count_scores(condition) -> int:
        return sum(1 for entry in parsed if condition(entry.score))

    score_ranges = {
        "Very High (100+)": count_scores(lambda s: s >= 100),
        "High (50-99)": count_scores(lambda s: 50 <= s < 100),
        "Medium (25-49)": count_scores(lambda s: 25 <= s < 50),
        "Low (1-24)": count_scores(lambda s: 1 <= s < 25),
    }

    print("\nFile types:")
    for ext, count in ext_counts.most_common():
        print(f"  {ext}: {count}")

    print("\nDrives:")
    for drive, count in drive_counts.most_common():
        print(f"  {drive}: {count}")

    print("\nScore ranges:")
    for label, count in score_ranges.items():
        print(f"  {label}: {count}")


def write_output(output_path: Path, parsed: List[ParsedEntry], missing: List[MissingEntry], errors: List[dict], skipped: int) -> None:
    summary = {
        "TotalParsed": len(parsed),
        "FilesFound": sum(1 for p in parsed if p.exists),
        "FilesMissing": len(missing),
        "ParseErrors": len(errors),
        "SkippedRanks": skipped,
    }
    payload = {
        "Summary": summary,
        "Files": [entry.to_dict() for entry in parsed],
        "MissingFiles": [item.to_dict() for item in missing],
        "ParseErrors": errors,
        "GeneratedDate": datetime.now().isoformat(timespec="seconds"),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nExported parsed data to {output_path}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse TOP50.md into structured JSON")
    parser.add_argument("--input", type=Path, default=Path(DEFAULT_MARKDOWN), help="Path to TOP50.md")
    parser.add_argument("--output", type=Path, default=Path(DEFAULT_OUTPUT), help="Output JSON path")
    parser.add_argument("--skip-ranks", type=int, default=4, help="Skip entries up to this rank (default: 4)")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    md_path = args.input.expanduser().resolve()
    if not md_path.exists():
        print(f"❌ Cannot find Markdown file: {md_path}", file=sys.stderr)
        return 1

    try:
        markdown = md_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"❌ Failed to read {md_path}: {exc}", file=sys.stderr)
        return 1

    try:
        matches = parse_markdown_entries(markdown)
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    parsed, missing, errors = collect_entries(matches, skip_ranks=args.skip_ranks)

    print_breakdown(parsed)

    if missing:
        print("\nMissing files:")
        for item in missing:
            print(f"  Rank {item.rank}: {item.file_name} -> {item.path}")

    if errors:
        print("\nParse errors:")
        for err in errors:
            print(f"  Rank {err.get('Rank')}: {err.get('Error')}")

    output_path = args.output.expanduser().resolve()
    write_output(output_path, parsed, missing, errors, skipped=args.skip_ranks)
    print("\n✅ Step 1.1 complete. Ready for Step 1.2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
