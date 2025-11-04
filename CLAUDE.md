# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the "Golden Wings Reconoganza" project - a content discovery and processing tool specifically designed to find files related to a documentary project about Golden Wings. The repository contains Node.js-based content hunting scripts that scan file systems for documentary-related content using keyword matching.

## Key Commands

### Content Hunting
- `npm run hunt` - Run the main content hunter script (content-hunter.js)
- `node content-hunter-fixed.js` - Run the preferred version with Windows compatibility and enhanced filtering
- `python script.py` - Alternative Python-based content processing script

### Development
- The project uses Node.js with no additional dependencies beyond built-in modules
- Scripts are designed to work cross-platform with Windows-specific compatibility fixes
- Use `content-hunter-fixed.js` for production runs - it includes PowerShell-based drive detection and improved filtering

## Architecture

### Main Components

**content-hunter.js** - Primary content discovery script that:
- Scans file systems for documentary-related files using comprehensive keyword matching
- Supports multiple file formats (.md, .txt, .json, .docx, .pdf, .mp4, .mov, etc.)
- Uses worker threads for parallel processing
- Generates detailed inventory reports in JSON format
- Includes Windows volume detection and cross-platform path handling

**Configuration System**:
- Keywords cover people (Robyn Stewart, Jay Ricks, Henry Stewart, etc.)
- Project names (Golden Wings, Fifty Year Flight Path, etc.)
- Aviation terms, themes, and production-related terms
- Configurable file extensions and search patterns

**Output Generation**:
- Creates comprehensive JSON inventories (golden-wings-content-inventory.json)
- Generates summary reports (CONTENT-SUMMARY.md)
- Produces CSV exports for spreadsheet analysis

### File Structure Patterns
- Multiple versions of content-hunter scripts exist for different iterations:
  - `content-hunter-fixed.js` - Production version with Windows compatibility and enhanced filtering
  - `content-hunter-enhanced.js` - Enhanced version with additional features
  - `content-hunter.js` - Original version (may have compatibility issues on Windows)
- Scripts directory contains utility scripts and Python alternatives
- Output files follow naming convention: golden-wings-content-*
- `.huntignore` file contains comprehensive filtering patterns to exclude false positives from cybersecurity, system files, and generic business content

## Cursor IDE Integration

This project includes Cursor-specific configuration:
- `.cursorrules` - Defines AI behavior focused on text file processing, code clarity, and cross-platform compatibility
- `.cursor-context` - Provides project context for AI assistance
- Emphasizes practical solutions, clear code, and comprehensive error handling

## Development Notes

- The content hunter is designed to be run from any location on the file system
- Includes robust error handling for permission issues and cross-platform differences
- Uses worker threads for performance when processing large directory structures
- All scripts maintain detailed logging and progress reporting
- Keyword matching is case-insensitive and handles various text encodings

## Filtering System

The project uses a two-tier filtering approach:
1. **Script-level filtering** - Built-in SKIP_PATTERNS in the hunter scripts exclude common false positives
2. **File-level filtering** - `.huntignore` file provides comprehensive glob patterns for precise exclusion of:
   - Security/hacking tools and tutorials
   - System files and browser data
   - Generic business databases and customer data
   - Legal documents (EULA, LICENSE, terms of service, etc.)
   - Development files and temporary content

## Important Files for Context

- **CONTENT-SUMMARY.md** - Generated summary of discovered content with analysis
- **golden-wings-content-inventory.json** - Complete JSON inventory of found files with metadata
- **content-inventory.csv** - Spreadsheet-friendly export of results
- **.huntignore** - Filtering patterns to exclude false positives (similar to .gitignore)