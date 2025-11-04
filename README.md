# golden-wings-reconoganza
find those text files, gworl!

## 🎯 Project Purpose
This repository is designed for text file discovery and processing functionality.

## 🔧 Development Setup
This project is optimized for use with **Cursor IDE** and its background AI agent:

- **Remote Origin**: Ready to go at `https://github.com/calebmills99/golden-wings-reconoganza`
- **AI-Enhanced**: Includes `.cursor-context` and `.cursorrules` for optimal AI assistance
- **Clean Workspace**: Configured `.gitignore` to keep your repository tidy

## 🚀 Getting Started
1. Clone this repository to your local machine
2. Open in Cursor IDE
3. The AI background agent will automatically understand the project context
4. Start building your text file processing features!

## 📁 Key Files
- `README.md` - You are here
- `DEVELOPMENT.md` - Detailed development guide
- `workflow.py` - Complete workflow automation
- `notion_integration.py` - Notion database integration
- `TOP50.md` - Top 50 files by relevance (generated)
- `.cursor-context` - Helps AI understand the project
- `.cursorrules` - Defines AI behavior for this project

## 🚀 Quick Start

### One-Command Workflow
```powershell
npm run workflow
```

### Individual Steps
```powershell
# 1. Find and rank Golden Wings content (simple scanner)
npm run hunt

# 2. Import to Notion database
npm run notion
```

### Adapt this to any topic
You can retarget the enhanced hunter to any domain (research project, client, product, case study) using a JSON config.

1. Copy the example and edit keywords and search roots:
   - PowerShell
     ```powershell
     Copy-Item topic_config.example.json topic_config.json
     ```
   - Or manually duplicate the file and rename to topic_config.json
2. Edit topic_config.json:
   - KEYWORDS: add your domain terms, people, places, jargon
   - TARGET_DIRECTORIES: drives/folders to scan (e.g., C:\\, D:\\MyDocs)
   - Optionally adjust SEARCH_EXTENSIONS, SKIP_PATTERNS, BACKUP_PATTERNS
3. Run with your topic config:
   ```powershell
   npm run hunt:topic
   ```
   - Generate a 25-file control group ignoring .huntignore (for unbiased sampling):
   ```powershell
   npm run control25:topic
   ```

Notes
- The enhanced hunter merges your config with sane defaults. Fields you omit will use the built-in values.
- .huntignore is honored in normal topic runs; control mode bypasses .huntignore but still excludes self-generated outputs.
- Reports (TOP*.md, content-inventory.csv, JSON) are written to the repo root by default. Edit REPORTS in the config if you prefer different names.

## 🔗 Notion Integration

The workflow automatically creates a Notion database with your top Golden Wings content:

1. **Setup**: copy `notion_env_example.txt` to `.env` and fill `NOTION_SECRET` plus either `NOTION_DATABASE_ID` or `NOTION_DATABASE_NAME`.
2. **Run**: `npm run workflow` to create/update your Notion database
3. **View**: Check your Notion workspace for the new or updated database

The database includes:
- File rankings by relevance score
- Complete metadata (path, size, modification date)
- Keyword tags for easy filtering
- Visual score indicators

Ready to find those text files! 🔍✨



## Convert EPUB to TXT or ODT (ODF)
You can now convert .epub ebooks to plain text (.txt) or OpenDocument Text (.odt) without leaving this project.

Quick start (Windows PowerShell or any shell):
- Convert to TXT with npm:
  - npm run epub:txt -- path\to\book.epub
- Convert to ODT with npm:
  - npm run epub:odt -- path\to\book.epub
- Or use Python directly:
  - python convert_epub.py path\to\book.epub --txt
  - python convert_epub.py path\to\book.epub --odt
- Specify an explicit output path:
  - python convert_epub.py path\to\book.epub --txt -o out\book.txt

How it works
- Python-first path (no external tools):
  - Uses ebooklib to read EPUB, BeautifulSoup to extract readable text, and odfpy to write .odt when requested.
- Automatic fallback:
  - If those Python libraries aren’t installed, the script looks for Calibre’s ebook-convert and uses it instead.

Optional dependencies
- For best results without Calibre, install:
  - pip install -r requirements-epub.txt
  (Contains: ebooklib, beautifulsoup4, and odfpy for ODT.)

Calibre fallback
- If you prefer to avoid installing Python libs, install Calibre:
  - https://calibre-ebook.com/download
- On Windows, the tool will auto-detect common paths like:
  - C:\\Program Files\\Calibre\\ebook-convert.exe
  - C:\\Program Files (x86)\\Calibre2\\ebook-convert.exe

Troubleshooting
- DRM-protected EPUBs cannot be converted by this script; you’ll see a parse error.
- If you get a “tool not found” message:
  - Install the Python libs (above), or
  - Install Calibre and ensure ebook-convert is on PATH or at one of the known paths.
- Unicode issues: outputs are UTF-8. Open in an editor that supports UTF-8.

Notes
- Outputs are created alongside the .epub by default (same base name, .txt or .odt). Use -o to choose a different location.
- The content hunters already try to ignore generated artifacts like reports; your converted files may still be scanned unless covered by existing ignore patterns.
