# Step 1.1 – Parse TOP50.md (Python)

We replaced the original PowerShell parser with a concise Python script because
maintaining a 300+ line PowerShell heredoc slowed iteration to a crawl. Python’s
standard library handles the regex parsing, JSON export, and path validation in a
few dozen lines, and the script runs anywhere Python 3.10+ is available.

## Files

| File | Purpose |
| --- | --- |
| `parse_top50.py` | Parses `TOP50.md` into structured JSON |
| `top50_parsed_data.json` | Output consumed by Step 1.2 |
| `TOP50.md` | Markdown source document |

The legacy PowerShell scripts (`parse_top50.ps1`, `parse_top50_fixed.ps1`) remain
in the repository for reference but are no longer part of the primary workflow.

## Usage

```bash
python parse_top50.py [--input PATH_TO_TOP50.md] [--output PATH_TO_JSON] [--skip-ranks N]
```

- `--input` defaults to `TOP50.md`
- `--output` defaults to `top50_parsed_data.json`
- `--skip-ranks` skips the first N entries (defaults to 4 to match the earlier pipeline)

### Example

```bash
python parse_top50.py --input TOP50.md --output top50_parsed_data.json
```

The script prints:
- File-type, drive, and score-range breakdowns
- Any missing files and parse errors
- A confirmation of the exported JSON location

## Output Structure

`top50_parsed_data.json` matches the schema used by the downstream steps:

```json
{
  "Summary": {
    "TotalParsed": 46,
    "FilesFound": 10,
    "FilesMissing": 36,
    "ParseErrors": 0,
    "SkippedRanks": 4
  },
  "Files": [
    {
      "Rank": 5,
      "FileName": "profile_update_history.html",
      "Score": 105,
      "FullPath": "D:\\gdrive\\…",
      "Directory": "D:\\gdrive\\…",
      "Size": "88 KB",
      "SizeBytes": 90112,
      "Modified": "2025-05-24T11:23:00",
      "Keywords": ["facebook", "profile"],
      "Extension": ".html",
      "Drive": "D:",
      "Exists": false
    }
  ],
  "MissingFiles": [ … ],
  "ParseErrors": [ … ],
  "GeneratedDate": "2025-09-27T11:30:18"
}
```

## Why the change?

- **Speed** – editing and testing the parser is now seconds, not minutes.
- **Portability** – Python runs easily on Windows/macOS/Linux, which is handy if
  you reproduce the pipeline elsewhere.
- **Clarity** – the JSON plan is identical to before, so Steps 1.2+ needed no
  adjustments.

If you still need the PowerShell version for archival reasons, it’s in the repo;
just be aware it hasn’t been updated since the migration.
