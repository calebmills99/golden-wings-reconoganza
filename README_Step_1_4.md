# Step 1.4 – Generate Rename Script (Python)

We moved this step from PowerShell to Python because the old generator had to
embed a 400+ line heredoc inside another PowerShell script. That made every
change brittle and slow. The new Python tooling produces the same deliverables—a
plan file, a rewrite script, and usage notes—but is dramatically easier to
maintain and extend.

## Prerequisites

- Python 3.10 or newer (Python 3.12 is bundled on this workstation)
- `rename_mappings.json` from Step 1.3
- Write access to the directories that contain the files you plan to rename

## Files in this step

| File | Purpose |
| --- | --- |
| `generate_rename_script.py` | Reads the mappings and generates the plan + executor |
| `rename_plan_YYYYMMDD_HHMMSS.json` | Normalised rename plan JSON |
| `execute_renames_YYYYMMDD_HHMMSS.py` | Stand-alone rename executor |
| `README_Step_1_4_RUN.txt` | Usage cheat-sheet generated alongside the plan |

> *Legacy note:* `generate_rename_script.ps1` is still in the repo for reference,
> but the Python flow is now the supported path.

## Usage

```bash
python generate_rename_script.py [--input PATH] [--plan PATH] [--output-script PATH]
                                 [--include-backup | --no-backup] [--dry-run]
```

### Common scenarios

- **Default run** – read `rename_mappings.json`, write a timestamped plan + executor:
  ```bash
  python generate_rename_script.py
  ```

- **Preview only** – see what would be generated without writing files:
  ```bash
  python generate_rename_script.py --dry-run
  ```

- **Custom destination folder**:
  ```bash
  python generate_rename_script.py --plan ./out/my_plan.json --output-script ./out/rename.py
  ```

### Options

| Flag | Description |
| --- | --- |
| `--input` | Path to the mappings JSON (default `rename_mappings.json`) |
| `--plan` | Where to write the plan JSON (default: timestamped file next to input) |
| `--output-script` | Where to write the executor Python script |
| `--include-backup / --no-backup` | Override the default backup behaviour inferred from Step 1.3 |
| `--dry-run` | Print a summary of planned operations without writing files |

## Generated artefacts

1. **Plan JSON** – lists every rename operation, the inferred default backup flag,
   and any missing source files detected during validation.
2. **Executor script** – a Python CLI that can run the plan with `--what-if`,
   `--force`, `--backup`, `--no-backup`, and `--log-file` switches.
3. **Usage note** – `README_Step_1_4_RUN.txt` summarises the commands to preview
   and execute the plan.

## Recommended workflow

1. `python generate_rename_script.py --dry-run` – sanity-check the mappings.
2. `python generate_rename_script.py` – write the plan and executor.
3. `python execute_renames_YYYYMMDD_HHMMSS.py --what-if` – preview rename actions.
4. `python execute_renames_YYYYMMDD_HHMMSS.py` – perform the renames (backups
   follow the inferred default, override with `--backup` or `--no-backup`).
5. Review the log output (use `--log-file path/to/log.txt` if you want a file on disk).
6. If needed, restore from the `backup_<timestamp>` folder created by the executor.

## Executor capabilities

- Validates source files before attempting each rename.
- Creates destination directories when necessary.
- Supports What-If previews.
- Optional backups (inferred from Step 1.3, override per run).
- Colour-coded console output and optional log file.
- Leaves missing files and failures recorded so you can rerun once issues are fixed.

## Why Python?

- **Maintenance speed** – swapping a few lines in Python is far quicker than
  editing a long PowerShell-generated script.
- **Cross-platform flexibility** – the executor runs anywhere Python is
  available (Windows/macOS/Linux), which is useful if files live on different
  machines.
- **Cleaner separation** – the JSON plan is now a first-class file, so automation
  or audits can consume it without parsing a monolithic script.

Feel free to customise either script—they are small and intentionally readable.
