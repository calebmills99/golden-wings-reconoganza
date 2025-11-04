#!/usr/bin/env python3
"""
Step 1B.2: Content classification for Golden Wings documentary workflow (Python edition).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import re

DEFAULT_INPUT_CANDIDATES = [
    "top51_100_parsed_data_*.json",
    "top51_100_parsed_data.json",
    "top50_parsed_data.json",
]
DEFAULT_CONFIG_PATH = "content_classification_config.json"
DEFAULT_OUTPUT_BASENAME = "content_classification_results.json"

PERSON_PATTERNS = [
    (re.compile(r"\bcaleb\b", re.IGNORECASE), "Caleb_Stewart"),
    (re.compile(r"\brobyn\b", re.IGNORECASE), "Robyn_Stewart"),
    (re.compile(r"\bhenry\b", re.IGNORECASE), "Henry_Stewart"),
    (re.compile(r"\bjay\b", re.IGNORECASE), "Jay_Ricks"),
    (re.compile(r"\bjock\b", re.IGNORECASE), "Jock_Bethune"),
    (re.compile(r"\bbethune\b", re.IGNORECASE), "Jock_Bethune"),
    (re.compile(r"\bstewart\b", re.IGNORECASE), "Stewart_Family"),
]

FESTIVAL_PATTERNS = [
    (re.compile(r"all[ _-]*around", re.IGNORECASE), "All_Around_Film_Festival"),
    (re.compile(r"sundance", re.IGNORECASE), "Sundance_Film_Festival"),
    (re.compile(r"tribeca", re.IGNORECASE), "Tribeca_Film_Festival"),
    (re.compile(r"outfest", re.IGNORECASE), "Outfest"),
    (re.compile(r"slamdance", re.IGNORECASE), "Slamdance"),
]

CONTEXT_PATTERNS: Dict[str, List[re.Pattern[str]]] = {
    "production_meta": [
        re.compile(r"behind[ _-]*the[ _-]*scenes", re.IGNORECASE),
        re.compile(r"\bproduction\b", re.IGNORECASE),
        re.compile(r"\bworkflow\b", re.IGNORECASE),
        re.compile(r"film[ _-]*journey", re.IGNORECASE),
    ],
    "subject_research": [
        re.compile(r"\bhistory\b", re.IGNORECASE),
        re.compile(r"\bresearch\b", re.IGNORECASE),
        re.compile(r"\bbackground\b", re.IGNORECASE),
    ],
    "technical_interview": [
        re.compile(r"\bmixdown\b", re.IGNORECASE),
        re.compile(r"\baudio\b", re.IGNORECASE),
    ],
}


@dataclass
class Trigger:
    type: str
    score: int
    target: str = "FileName"
    pattern: Optional[re.Pattern[str]] = None
    values: Sequence[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Trigger":
        trigger_type = str(payload.get("Type", "")).strip().lower()
        score = int(payload.get("Score", 0))
        if score <= 0:
            raise ValueError("Score must be positive")
        target = str(payload.get("Target", "FileName"))
        if trigger_type == "regex":
            pattern_text = payload.get("Pattern")
            if not pattern_text:
                raise ValueError("Regex trigger missing pattern")
            pattern = re.compile(pattern_text, re.IGNORECASE)
            return cls(type="regex", score=score, target=target, pattern=pattern)
        if trigger_type == "keyword":
            values = [str(v).lower() for v in payload.get("Values", []) if v is not None]
            if not values:
                raise ValueError("Keyword trigger missing values")
            return cls(type="keyword", score=score, values=values)
        if trigger_type == "extension":
            values: List[str] = []
            for value in payload.get("Values", []):
                if value is None:
                    continue
                text = str(value).lower()
                if not text.startswith("."):
                    text = f".{text}"
                values.append(text)
            if not values:
                raise ValueError("Extension trigger missing values")
            return cls(type="extension", score=score, values=values)
        raise ValueError(f"Unsupported trigger type '{payload.get('Type')}'")

    def matches(self, record: "FileRecord") -> bool:
        if self.type == "regex":
            value = record.get_text_for_target(self.target)
            return bool(value and self.pattern and self.pattern.search(value))
        if self.type == "keyword":
            return any(val in record.keywords_lower for val in self.values)
        if self.type == "extension":
            return record.extension_lower in self.values
        return False

    def describe(self) -> Dict[str, Any]:
        if self.type == "regex" and self.pattern:
            return {"type": "Regex", "target": self.target, "pattern": self.pattern.pattern, "score": self.score}
        if self.type == "keyword":
            return {"type": "Keyword", "values": list(self.values), "score": self.score}
        if self.type == "extension":
            return {"type": "Extension", "values": list(self.values), "score": self.score}
        return {"type": self.type, "score": self.score}


@dataclass
class CategoryConfig:
    name: str
    triggers: List[Trigger]
    naming_convention: Optional[str] = None


@dataclass
class FileRecord:
    raw: Dict[str, Any]
    insights: Dict[str, Any] = field(default_factory=dict)
    category_scores: Dict[str, int] = field(default_factory=dict)
    matched_triggers: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    winning_category: str = "Unknown"
    winning_score: int = 0

    def __post_init__(self) -> None:
        self.rank = self.raw.get("rank") or self.raw.get("Rank")
        self.score = self.raw.get("score") or self.raw.get("Score")
        self.file_name = self.raw.get("FileName") or self.raw.get("filename")
        full_path_raw = self.raw.get("FullPath") or self.raw.get("full_path")
        if not self.file_name and full_path_raw:
            self.file_name = Path(full_path_raw).name
        self.full_path = full_path_raw or ""
        self.directory = self.raw.get("Directory") or self.raw.get("directory") or ""
        self.size = self.raw.get("Size") or self.raw.get("size")
        self.size_bytes = self.raw.get("SizeBytes") or self.raw.get("size_bytes")
        self.modified = self.raw.get("Modified") or self.raw.get("modified")
        keywords = self.raw.get("Keywords") or self.raw.get("keywords") or []
        self.keywords = [str(item) for item in keywords if item is not None]
        self.keywords_lower = {item.lower() for item in self.keywords}
        extension = self.raw.get("Extension") or self.raw.get("extension") or ""
        if extension and not str(extension).startswith("."):
            extension = f".{extension}"
        self.extension = str(extension)
        self.extension_lower = self.extension.lower()
        self.drive = self.raw.get("Drive") or self.raw.get("drive")
        exists_value = self.raw.get("Exists") if "Exists" in self.raw else self.raw.get("exists")
        self.exists = bool(exists_value)
        extra_fields = [
            self.file_name or "",
            self.full_path,
            self.directory,
            " ".join(self.keywords),
        ]
        self.extra_text = " ".join(part for part in extra_fields if part)

    def get_text_for_target(self, target: str) -> str:
        if not target:
            return self.file_name or ""
        value = target.lower()
        if value in {"filename", "name"}:
            return self.file_name or ""
        if value in {"fullpath", "path"}:
            return self.full_path
        if value in {"directory", "folder"}:
            return self.directory
        if value == "keywords":
            return " ".join(self.keywords)
        return self.file_name or ""

    def prepare_insights(self) -> None:
        persons = {label for pattern, label in PERSON_PATTERNS if pattern.search(self.extra_text)}
        festivals = {label for pattern, label in FESTIVAL_PATTERNS if pattern.search(self.extra_text)}
        if "festival" in self.keywords_lower and not festivals:
            festivals.add("Festival")
        context_flags = {
            flag
            for flag, patterns in CONTEXT_PATTERNS.items()
            if any(p.search(self.extra_text) for p in patterns)
        }
        self.insights = {
            "Persons": sorted(persons),
            "Festivals": sorted(festivals),
            "ContextFlags": sorted(context_flags),
        }

    def to_export(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "Rank": self.rank,
            "FileName": self.file_name,
            "Score": self.score,
            "FullPath": self.full_path,
            "Directory": self.directory,
            "Size": self.size,
            "SizeBytes": self.size_bytes,
            "Modified": self.modified,
            "Keywords": self.keywords,
            "Extension": self.extension,
            "Drive": self.drive,
            "Exists": self.exists,
            "Category": self.winning_category,
            "CategoryScore": self.winning_score,
        }
        if self.category_scores:
            payload["CategoryScores"] = self.category_scores
        if self.insights:
            payload["Insights"] = self.insights
        if self.matched_triggers:
            payload["MatchedTriggers"] = self.matched_triggers
        return payload


def apply_insight_adjustments(record: FileRecord, scores: Dict[str, int], matches: Dict[str, List[Dict[str, Any]]]) -> None:
    festivals = record.insights.get("Festivals", [])
    if festivals:
        if "Interview_Transcripts" in scores:
            scores["Interview_Transcripts"] = scores.get("Interview_Transcripts", 0) + 1
            matches.setdefault("Interview_Transcripts", []).append(
                {"type": "Heuristic", "reason": "Festival context bonus", "score": 1}
            )
        if "Strategy_Documents" in scores:
            scores["Strategy_Documents"] = scores.get("Strategy_Documents", 0) + 1
            matches.setdefault("Strategy_Documents", []).append(
                {"type": "Heuristic", "reason": "Festival context bonus", "score": 1}
            )
    flags = set(record.insights.get("ContextFlags", []))
    if "production_meta" in flags and "Production_Documents" in scores:
        scores["Production_Documents"] = scores.get("Production_Documents", 0) + 1
        matches.setdefault("Production_Documents", []).append(
            {"type": "Heuristic", "reason": "Production meta context", "score": 1}
        )
    if "subject_research" in flags and "Data_Reports" in scores:
        scores["Data_Reports"] = scores.get("Data_Reports", 0) + 1
        matches.setdefault("Data_Reports", []).append(
            {"type": "Heuristic", "reason": "Subject research context", "score": 1}
        )
    if "technical_interview" in flags and "Interview_Transcripts" in scores:
        scores["Interview_Transcripts"] = scores.get("Interview_Transcripts", 0) + 1
        matches.setdefault("Interview_Transcripts", []).append(
            {"type": "Heuristic", "reason": "Technical interview context", "score": 1}
        )


def choose_best_category(scores: Dict[str, int], priority: Sequence[str]) -> Tuple[str, int]:
    best_category = "Unknown"
    best_score = -1
    for name in priority:
        score = scores.get(name, 0)
        if score > best_score:
            best_category = name
            best_score = score
    return best_category, best_score


class Classifier:
    def __init__(self, categories: Sequence[CategoryConfig], priority: Sequence[str]):
        self.configs = {cfg.name: cfg for cfg in categories}
        seen: List[str] = []
        for name in priority:
            if name in self.configs and name not in seen:
                seen.append(name)
        for name in self.configs:
            if name not in seen:
                seen.append(name)
        self.priority = seen

    def classify(self, records: Iterable[FileRecord]) -> Tuple[Dict[str, List[FileRecord]], int]:
        buckets: Dict[str, List[FileRecord]] = {name: [] for name in self.priority}
        buckets["Unknown"] = []
        errors = 0
        for record in records:
            try:
                record.prepare_insights()
                scores = {name: 0 for name in self.priority}
                matches = {name: [] for name in self.priority}
                for name in self.priority:
                    config = self.configs.get(name)
                    if not config:
                        continue
                    for trigger in config.triggers:
                        if trigger.matches(record):
                            scores[name] += trigger.score
                            matches[name].append(trigger.describe())
                apply_insight_adjustments(record, scores, matches)
                best_category, best_score = choose_best_category(scores, self.priority)
                if best_score <= 0:
                    best_category = "Unknown"
                    best_score = 0
                record.category_scores = {k: v for k, v in scores.items() if v > 0}
                record.matched_triggers = {k: v for k, v in matches.items() if v}
                record.winning_category = best_category
                record.winning_score = best_score
                buckets.setdefault(best_category, []).append(record)
            except Exception as exc:
                errors += 1
                record.winning_category = "Unknown"
                record.winning_score = 0
                buckets.setdefault("Unknown", []).append(record)
                print(f"❌ Classification error for {record.file_name or 'unknown file'}: {exc}", file=sys.stderr)
        return buckets, errors


def resolve_input_path(explicit: Optional[Path]) -> Path:
    if explicit:
        path = explicit.expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"Parsed data file not found: {path}")
        return path
    cwd = Path.cwd()
    for pattern in DEFAULT_INPUT_CANDIDATES:
        matches = sorted(
            (p for p in cwd.glob(pattern) if p.is_file()),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if matches:
            selected = matches[0].resolve()
            print(f"🔍 Auto-selected parsed data: {selected.name}")
            return selected
    raise SystemExit("Unable to determine parsed data input. Provide --input.")


def load_parsed_data(path: Path) -> Tuple[List[FileRecord], Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Parsed data file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse JSON from {path}: {exc}")
    files = data.get("files") or data.get("Files")
    if files is None:
        raise SystemExit("Parsed JSON missing 'files' array.")
    records = [FileRecord(raw=dict(item)) for item in files]
    return records, data


def load_config(path: Path) -> Tuple[List[CategoryConfig], List[str], Dict[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Config file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse config JSON: {exc}")
    categories_node = data.get("Categories")
    if not categories_node:
        raise SystemExit("Config missing 'Categories' section.")
    priority = list(dict.fromkeys(data.get("CategoryPriority", [])))
    categories: List[CategoryConfig] = []
    naming_map: Dict[str, str] = {}
    for name, body in categories_node.items():
        triggers: List[Trigger] = []
        for trigger_payload in body.get("Triggers", []) or []:
            try:
                triggers.append(Trigger.from_dict(trigger_payload))
            except ValueError as exc:
                print(f"⚠️  Skipping trigger for {name}: {exc}", file=sys.stderr)
        naming = body.get("NamingConvention")
        if naming:
            naming_map[name] = naming
        categories.append(CategoryConfig(name=name, triggers=triggers, naming_convention=naming))
    priority = list(dict.fromkeys(priority + [cfg.name for cfg in categories]))
    return categories, priority, naming_map


def resolve_output_path(input_path: Path, requested: Optional[Path]) -> Path:
    if requested:
        return requested.expanduser().resolve()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = input_path.name
    if name.startswith("top51_100"):
        return input_path.parent / f"content_classification_results_top51_100_{timestamp}.json"
    if name.startswith("top") and name.endswith(".json"):
        return input_path.parent / f"content_classification_results_{timestamp}.json"
    return input_path.parent / DEFAULT_OUTPUT_BASENAME


def print_header(input_path: Path, config_path: Path, output_path: Path, dry_run: bool) -> None:
    print("📂 Step 1B.2: Content Type Classification (Python)")
    print("========================================")
    print(f"📁 Parsed data: {input_path}")
    print(f"🧠 Config: {config_path}")
    print(f"💾 Output: {output_path}")
    if dry_run:
        print("👁️  Dry run enabled: output will not be written")
    print()


def print_file_results(records: Sequence[FileRecord], trace: bool) -> None:
    for record in records:
        print(f"📄 Rank {record.rank}: {record.file_name}")
        hints: List[str] = []
        persons = record.insights.get("Persons") if record.insights else []
        festivals = record.insights.get("Festivals") if record.insights else []
        flags = record.insights.get("ContextFlags") if record.insights else []
        if persons:
            hints.append(f"Persons={','.join(persons)}")
        if festivals:
            hints.append(f"Festivals={','.join(festivals)}")
        if flags:
            hints.append(f"Flags={','.join(flags)}")
        if hints:
            print(f"   🧭 Insights: {' | '.join(hints)}")
        print(f"   🏷️  Category: {record.winning_category} (Score {record.winning_score})")
        if trace and record.matched_triggers:
            for category, details in record.matched_triggers.items():
                for detail in details:
                    desc = detail.get("pattern") or ",".join(detail.get("values", [])) or detail.get("reason", "")
                    suffix = f" [{desc}]" if desc else ""
                    print(f"      ➕ {category}: {detail['type']}{suffix} +{detail.get('score', 0)}")
        print()


def score_key(record: FileRecord) -> Tuple[float, str]:
    score = record.score if isinstance(record.score, (int, float)) else float("-inf")
    return score, record.file_name or ""


def print_summary(buckets: Dict[str, List[FileRecord]], errors: int, priority: Sequence[str]) -> None:
    total = sum(len(items) for items in buckets.values())
    print("========================================")
    print("📊 CLASSIFICATION SUMMARY")
    print("========================================")
    print(f"📄 Total files classified: {total}")
    print(f"❌ Classification errors: {errors}")
    print()
    ordered = [name for name in priority if name in buckets]
    ordered.sort(key=lambda name: len(buckets[name]), reverse=True)
    for name in ordered:
        items = buckets[name]
        if not items:
            continue
        print(f"   {name}: {len(items)} files")
        top_items = sorted(items, key=score_key, reverse=True)[:3]
        for rec in top_items:
            raw_score = rec.score if isinstance(rec.score, (int, float)) else "n/a"
            print(f"      • {rec.file_name} (Score: {raw_score})")
        print()
    unknown_items = buckets.get("Unknown", [])
    if unknown_items:
        print(f"   Unknown: {len(unknown_items)} files")
        for rec in unknown_items[:3]:
            print(f"      • {rec.file_name or 'Unknown'}")
        print()


def export_results(
    output_path: Path,
    buckets: Dict[str, List[FileRecord]],
    naming_map: Dict[str, str],
    config_path: Path,
    input_path: Path,
    source_meta: Dict[str, Any],
    errors: int,
) -> None:
    total = sum(len(items) for items in buckets.values())
    export_payload: Dict[str, Any] = {
        "GeneratedDate": datetime.now().isoformat(timespec="seconds"),
        "Summary": {
            "TotalClassified": total,
            "ClassificationErrors": errors,
        },
        "Classifications": {
            name: [record.to_export() for record in items]
            for name, items in buckets.items()
        },
        "NamingConventions": naming_map,
        "ConfigUsed": str(config_path.resolve()),
        "SourceData": {
            "InputFile": str(input_path.resolve()),
        },
    }
    summary_node = source_meta.get("summary") or source_meta.get("Summary")
    if summary_node:
        export_payload["SourceData"]["OriginalSummary"] = summary_node
    missing_node = source_meta.get("missing_files") or source_meta.get("MissingFiles")
    if missing_node:
        export_payload["SourceData"]["MissingFiles"] = missing_node
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(export_payload, indent=2), encoding="utf-8")
    print(f"💾 Classification results exported to: {output_path}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Golden Wings content classification (Step 1B.2).")
    parser.add_argument("--input", type=Path, help="Path to parsed data JSON.")
    parser.add_argument("--config", type=Path, default=Path(DEFAULT_CONFIG_PATH), help="Classification config JSON.")
    parser.add_argument("--output", type=Path, help="Destination for classification results.")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing output JSON.")
    parser.add_argument("--trace", action="store_true", help="Display trigger matches per file.")
    parser.add_argument(
        "--update-default",
        action="store_true",
        help=f"Also write {DEFAULT_OUTPUT_BASENAME} alongside the main output.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    input_path = resolve_input_path(args.input)
    config_path = args.config.expanduser().resolve()
    if not config_path.is_file():
        raise SystemExit(f"Config file not found: {config_path}")
    output_path = resolve_output_path(input_path, args.output)
    print_header(input_path, config_path, output_path, args.dry_run)
    records, source_meta = load_parsed_data(input_path)
    print(f"✅ Loaded {len(records)} files from parsed data")
    print()
    categories, priority, naming_map = load_config(config_path)
    print(f"✅ Loaded {len(categories)} categories from config")
    print()
    classifier = Classifier(categories, priority)
    print(f"🔍 Classifying {len(records)} files by content type...\n")
    buckets, errors = classifier.classify(records)
    print_file_results(records, args.trace)
    print_summary(buckets, errors, classifier.priority)
    if args.dry_run:
        print("👁️  Dry run requested: skipping write")
        return 0
    export_results(output_path, buckets, naming_map, config_path, input_path, source_meta, errors)
    if args.update_default and output_path.name != DEFAULT_OUTPUT_BASENAME:
        default_path = output_path.parent / DEFAULT_OUTPUT_BASENAME
        default_path.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"📄 Default results updated at: {default_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
