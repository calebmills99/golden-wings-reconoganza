# Claude AI Chat Extraction Pipeline 🤖

## Quick Start Guide

### What This Does
Extracts and organizes your Claude AI conversation history from JSON files, providing:
- 📊 Structured data extraction from ~13,047 conversation files
- 🏷️ Automatic categorization and tagging
- 📤 Multiple export formats (JSON, CSV, Markdown, SQLite)
- 📈 Analytics and insights generation
- 🔍 Searchable conversation index

### Prerequisites
```bash
# Python 3.10+ required
python --version

# Install required packages
pip install pathlib json hashlib typing dataclasses
```

## 🚀 Quick Start (3 Steps)

### Step 1: Test the Pipeline
```bash
# Run a quick test with 5 sample files
python test_claude_extraction.py
```

### Step 2: Extract Sample Data
```bash
# Test with 10 conversations
python run_claude_extraction.py --test

# Or specify custom sample size
python run_claude_extraction.py --sample 50 --debug
```

### Step 3: Run Full Extraction
```bash
# Extract all conversations from default location (F:\dev\quivr)
python run_claude_extraction.py

# Or specify custom paths
python run_claude_extraction.py --source "F:\dev\quivr" --output "./my_output"
```

## 📁 File Structure

```
Your Project/
├── claude_config.py           # Configuration settings
├── claude_file_discovery.py   # File scanning & validation
├── claude_content_parser.py   # JSON parsing & extraction
├── claude_extractor.py        # Main orchestrator
├── claude_error_handler.py    # Error management
├── claude_progress_tracker.py # Progress monitoring
├── test_claude_extraction.py  # Test suite
├── run_claude_extraction.py   # Quick start script
└── CLAUDE_EXTRACTION_PLAN.md  # Detailed documentation
```

## 🔧 Configuration Options

### Basic Usage
```bash
python run_claude_extraction.py [OPTIONS]

Options:
  -s, --source PATH    Source directory with JSON files
  -o, --output PATH    Output directory for results
  -n, --sample N       Process only N files (for testing)
  -f, --format FORMAT  Export formats (json,csv,markdown,sqlite)
  -d, --debug          Enable debug mode
  --test               Run test mode (samples 5 files)
```

### Advanced Configuration
Edit `claude_config.py` or create a config file:

```python
config = ClaudeConfig()
config.source_directory = r"F:\dev\quivr"
config.output_directory = "./claude_output"
config.processing.batch_size = 100
config.processing.max_workers = 4
config.extraction.extract_code_blocks = True
config.extraction.extract_artifacts = True
```

## 📊 Output Formats

### JSON Export
```json
{
  "conversation_id": "conv_12345",
  "title": "Python Data Analysis",
  "messages": [...],
  "categories": ["programming", "data-science"],
  "created_at": "2024-01-01T00:00:00Z"
}
```

### CSV Export
| Conversation ID | Title | Messages | Categories | Created |
|----------------|-------|----------|------------|---------|
| conv_12345 | Python Data Analysis | 42 | programming, data-science | 2024-01-01 |

### Markdown Report
- Conversation summaries
- Topic analysis
- Code snippets extracted
- Statistics and insights

### SQLite Database
- Queryable conversation database
- Full-text search capability
- Indexed for fast retrieval

## 🎯 Extraction Process

### Phase 1: Discovery
- Scans source directory for `conversation_conv_*.json` files
- Validates JSON structure
- Groups multi-part conversations
- Handles truncated files gracefully

### Phase 2: Parsing
- Extracts nested JSON content
- Parses conversation messages
- Extracts metadata (timestamps, models, etc.)
- Recovers partial data from corrupted files

### Phase 3: Processing
- Categorizes conversations by topic
- Tags programming languages
- Extracts code blocks
- Generates summaries

### Phase 4: Export
- Saves data in requested formats
- Generates analytics reports
- Creates searchable index
- Produces statistics

## ⚡ Performance Tips

### For Large Datasets (10K+ files)
```bash
# Process in batches
python run_claude_extraction.py --batch-size 500

# Use multiple workers
python claude_extractor.py --workers 8

# Enable checkpointing
python claude_extractor.py --checkpoint
```

### Memory Optimization
```bash
# Stream large files
python claude_extractor.py --stream

# Clear cache periodically
python claude_extractor.py --clear-cache 1000
```

## 🐛 Troubleshooting

### Common Issues

**No files found:**
```bash
# Check source directory
ls "F:\dev\quivr\conversation_conv_*.json"

# Verify path in config
python -c "from claude_config import *; print(ClaudeConfig().source_directory)"
```

**JSON decode errors:**
```bash
# Test single file
python -c "import json; json.load(open('path/to/file.json'))"

# Use partial parsing
python claude_extractor.py --partial
```

**Memory errors:**
```bash
# Reduce batch size
python run_claude_extraction.py --batch-size 50

# Process fewer files
python run_claude_extraction.py --sample 1000
```

## 📈 Expected Results

### Success Metrics
- ✅ 95%+ extraction success rate
- ⚡ ~1000 files/minute processing speed
- 💾 <1GB memory usage
- 📊 Zero data loss

### Sample Output
```
🚀 Starting extraction pipeline...

📂 Phase 1: Discovering files...
✅ Found 13,047 files
   Valid: 13,000
   Invalid: 47

🔄 Phase 2: Extracting conversations...
✅ Extracted 13,000 conversations
   Total messages: 521,834
   Avg messages/conversation: 40.1

💾 Phase 3: Exporting data...
✅ Data exported successfully:
   json: ./claude_output/conversations.json
   csv: ./claude_output/conversations.csv

📊 Phase 4: Generating report...
✅ Report generated: ./claude_output/report.md

🎉 EXTRACTION COMPLETED SUCCESSFULLY!
```

## 🔍 Next Steps

After extraction, you can:

1. **Search conversations:** Use the generated index
2. **Analyze patterns:** Review the analytics report
3. **Export to Notion:** Use the Notion integration
4. **Build a UI:** Create a web interface for browsing
5. **Train models:** Use extracted data for ML

## 📚 Additional Resources

- [Detailed Plan](CLAUDE_EXTRACTION_PLAN.md) - Complete technical documentation
- [API Reference](docs/api.md) - Module documentation
- [Examples](examples/) - Sample code and usage

## 🆘 Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Run in debug mode: `python run_claude_extraction.py --debug`
3. Review error logs in `./claude_output/errors.log`
4. Check truncated file handling in the parser

## 🎉 Ready to Extract!

Start with the test command to verify everything works:
```bash
python test_claude_extraction.py
```

Then run the full extraction:
```bash
python run_claude_extraction.py
```

Happy extracting! 🚀