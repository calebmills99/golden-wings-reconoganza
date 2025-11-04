# Repository Guidelines

## Project Structure & Module Organization
- Root Python automation (`workflow.py`, `notion_integration.py`, `job_*` scripts) orchestrates hunts, data cleanup, and Notion sync; keep new pipelines under the project root.
- Node scanners (`simple-content-hunter.js`, `content-hunter-fixed.js`) house search rules and run via npm scripts; reuse `CONFIG` for keyword updates.
- `windows-path-shortener/` stores the path alias module plus `tests/` and `examples/`; treat it as a standalone tool but version alongside the main workflow.
- `scripts/` contains helper PowerShell/Python utilities and a local `venv`; install experimental dependencies there instead of globally.
- Generated analytics live in `TOP*.md`, `rename_plan_*.json`, and `content_*` reports—regenerate rather than hand-editing.

## Build, Test, and Development Commands
- `npm run workflow` stitches together the hunt and Notion sync by calling `workflow.py`.
- `npm run hunt` reruns `simple-content-hunter.js`; follow with `npm run notion` when pushing refreshed scores to Notion.
- `python workflow.py` mirrors the npm entry point when Node tooling is unavailable.
- `pwsh -File windows-path-shortener/ShortPath.ps1` shortens long Windows paths using `ShortPath.config.json` mappings.
- Tests: `pwsh -File windows-path-shortener/tests/Test-PathShortener.ps1` exercises the path shortener module.

## Coding Style & Naming Conventions
- Python: target 3.10+, 4-space indents, module docstrings, and descriptive functions (`run_command`, `parse_top100_entries`). Prefer pathlib/f-strings and keep emoji-rich status logs when extending workflows.
- JavaScript: stay with CommonJS (`require`), single quotes, 4-space blocks, and uppercase config constants (e.g., `CONFIG`).
- JSON/Markdown artifacts use snake_case with timestamp suffixes (`top51_100_parsed_data_20250927_125856.json`); continue that pattern for generated files.

## Testing Guidelines
- Extend `Test-PathShortener.ps1` with isolated, idempotent cases; retain the existing Arrange–Act–Assert commentary style.
- New Python or Node modules should ship with sibling test files (`tests/test_<module>.py`, `<module>.spec.js`) and an npm or PowerShell entry so CI can invoke them.
- Keep sample payloads minimal; large fixtures belong under `windows-path-shortener/examples/` or external storage.

## Commit & Pull Request Guidelines
- Follow current history: imperative, concise subjects (e.g., `Fix`, `Refactor`, `Restore …`), capitalized, under 72 characters.
- PRs must summarize workflow impact, call out new commands/configs, and attach before/after snippets for regenerated artifacts (top file counts, rename plans).
- Link tracking issues when present and double-check that secrets (`.env`, `PathShortener.db`) stay ignored.
