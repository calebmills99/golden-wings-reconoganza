#!/usr/bin/env python3
"""
Step 1B.1: Parse TOP100.md for entries 51-100
Golden Wings Documentary - File Organization Project
Python version with enhanced error handling and flexibility
"""

import argparse
import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys

class TOP100Parser:
    def __init__(self, input_file: str, start_rank: int = 51, end_rank: int = 100):
        self.input_file = Path(input_file)
        self.start_rank = start_rank
        self.end_rank = end_rank
        self.parsed_files = []
        self.missing_files = []
        self.parse_errors = []
        self.summary = {
            'total_parsed': 0,
            'files_found': 0,
            'files_missing': 0,
            'parse_errors': 0,
            'skipped_ranks': 0
        }

    def parse_markdown(self) -> bool:
        """Parse the TOP100.md file and extract entries in the specified range."""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"✅ Loaded {self.input_file.name} successfully")
            
            # Split content into individual entries using the separator
            entries = re.split(r'\n---\n', content)
            
            # Filter entries that start with "## [number]."
            rank_entries = [entry for entry in entries if re.match(r'^\s*## \d+\.', entry.strip())]
            
            print(f"🔢 Found {len(rank_entries)} total entries in {self.input_file.name}")
            print("")
            
            for entry in rank_entries:
                self._parse_entry(entry.strip())
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR: Failed to read {self.input_file} - {e}")
            return False

    def _parse_entry(self, entry: str) -> None:
        """Parse a single markdown entry."""
        try:
            # Extract rank and filename from header
            header_match = re.match(r'## (\d+)\.\s*(.+)', entry)
            if not header_match:
                return
            
            rank = int(header_match.group(1))
            filename = header_match.group(2).strip()
            
            # Skip entries outside our target range
            if rank < self.start_rank or rank > self.end_rank:
                if rank < self.start_rank:
                    self.summary['skipped_ranks'] += 1
                return
            
            print(f"📄 Rank {rank}: {filename}")
            
            # Extract metadata using regex patterns
            score_match = re.search(r'\*\*Score:\*\*\s+(\d+)', entry)
            path_match = re.search(r'\*\*Path:\*\*\s+`([^`]+)`', entry)
            size_match = re.search(r'\*\*Size:\*\*\s+([^\n]+)', entry)
            modified_match = re.search(r'\*\*Modified:\*\*\s+([^\n]+)', entry)
            keywords_match = re.search(r'\*\*Keywords:\*\*\s+([^\n]+)', entry)
            # Extract values or use defaults
            score = int(score_match.group(1)) if score_match else 0
            full_path = path_match.group(1).strip() if path_match else ""
            size_str = size_match.group(1).strip() if size_match else ""
            modified_str = modified_match.group(1).strip() if modified_match else ""
            keywords_str = keywords_match.group(1).strip() if keywords_match else ""
            
            # Derive extension from filename
            extension = Path(filename).suffix if filename else ""
            
            # Parse file details
            directory = str(Path(full_path).parent) if full_path else ""
            drive_match = re.match(r'^([A-Z]:)', full_path)
            drive = drive_match.group(1) if drive_match else "Unknown"
            
            # Parse size to bytes
            size_bytes = self._parse_size_to_bytes(size_str)
            
            # Parse modification date
            modified_date = self._parse_date(modified_str)
            
            # Parse keywords
            keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()] if keywords_str else []
            
            # Check if file exists
            file_exists = Path(full_path).exists() if full_path else False
            if file_exists:
                print(f"   ✅ File found")
                self.summary['files_found'] += 1
            else:
                print(f"   ❌ File missing: {full_path}")
                self.missing_files.append({
                    'rank': rank,
                    'filename': filename,
                    'path': full_path,
                    'score': score
                })
                self.summary['files_missing'] += 1
            
            # Create file data object
            file_data = {
                'rank': rank,
                'filename': filename,
                'score': score,
                'full_path': full_path,
                'directory': directory,
                'size': size_str,
                'size_bytes': size_bytes,
                'modified': modified_date,
                'keywords': keywords,
                'extension': extension,
                'drive': drive,
                'exists': file_exists
            }
            
            self.parsed_files.append(file_data)
            self.summary['total_parsed'] += 1
            
        except Exception as e:
            print(f"❌ Parse error for entry: {e}")
            self.parse_errors.append({
                'error': str(e),
                'entry_preview': entry[:200] + "..." if len(entry) > 200 else entry
            })
            self.summary['parse_errors'] += 1

    def _parse_size_to_bytes(self, size_str: str) -> int:
        """Convert size string to bytes."""
        if not size_str:
            return 0
        
        size_match = re.match(r'(\d+\.?\d*)\s*(KB|MB|GB|bytes?)', size_str, re.IGNORECASE)
        if not size_match:
            return 0
        
        size_num = float(size_match.group(1))
        size_unit = size_match.group(2).upper()
        
        multipliers = {
            'BYTES': 1, 'BYTE': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024
        }
        
        return int(size_num * multipliers.get(size_unit, 1))

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format."""
        if not date_str:
            return None
        
        try:
            # Try common date formats
            for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y']:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.isoformat()
                except ValueError:
                    continue
            
            # If no format matches, return as-is
            return date_str
            
        except Exception:
            return date_str

    def generate_summary(self) -> None:
        """Generate and display parsing summary."""
        print("")
        print("=" * 50)
        print("📊 PARSING SUMMARY")
        print("=" * 50)
        print(f"📄 Total entries parsed: {self.summary['total_parsed']}")
        print(f"✅ Files found: {self.summary['files_found']}")
        print(f"❌ Files missing: {self.summary['files_missing']}")
        print(f"⏭️  Entries skipped (outside range): {self.summary['skipped_ranks']}")
        print(f"❌ Parse errors: {self.summary['parse_errors']}")
        print("")

        # File type breakdown
        if self.parsed_files:
            extensions = {}
            for file_data in self.parsed_files:
                ext = file_data['extension'] or "(no extension)"
                extensions[ext] = extensions.get(ext, 0) + 1
            
            print("📁 FILE TYPE BREAKDOWN:")
            for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
                print(f"   {ext}: {count} files")
            print("")

        # Drive breakdown
        if self.parsed_files:
            drives = {}
            for file_data in self.parsed_files:
                drive = file_data['drive']
                drives[drive] = drives.get(drive, 0) + 1
            
            print("💽 DRIVE BREAKDOWN:")
            for drive, count in sorted(drives.items(), key=lambda x: x[1], reverse=True):
                print(f"   {drive}: {count} files")
            print("")

        # Score range breakdown
        if self.parsed_files:
            score_ranges = {
                'Very High (100+)': len([f for f in self.parsed_files if f['score'] >= 100]),
                'High (50-99)': len([f for f in self.parsed_files if 50 <= f['score'] < 100]),
                'Medium (25-49)': len([f for f in self.parsed_files if 25 <= f['score'] < 50]),
                'Low (1-24)': len([f for f in self.parsed_files if 1 <= f['score'] < 25])
            }
            
            print("📊 SCORE RANGE BREAKDOWN:")
            for range_name, count in score_ranges.items():
                if count > 0:
                    print(f"   {range_name}: {count} files")
            print("")

        # Missing files report
        if self.missing_files:
            print("❌ MISSING FILES:")
            for missing in self.missing_files:
                print(f"   Rank {missing['rank']}: {missing['filename']}")
                print(f"      Path: {missing['path']}")
            print("")

        # Parse errors report
        if self.parse_errors:
            print("❌ PARSE ERRORS:")
            for error in self.parse_errors:
                print(f"   Error: {error['error']}")
            print("")

    def export_data(self, output_file: str) -> bool:
        """Export parsed data to JSON file."""
        try:
            export_data = {
                'generated_date': datetime.now().isoformat(),
                'source_file': str(self.input_file),
                'rank_range': f"{self.start_rank}-{self.end_rank}",
                'summary': self.summary,
                'files': self.parsed_files,
                'missing_files': self.missing_files,
                'parse_errors': self.parse_errors
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Parsed data exported to: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to export data: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Parse TOP100.md for specified rank range')
    parser.add_argument('--input', default='TOP100.md', help='Input markdown file (default: TOP100.md)')
    parser.add_argument('--output', help='Output JSON file (default: auto-generated)')
    parser.add_argument('--start-rank', type=int, default=51, help='Start rank (default: 51)')
    parser.add_argument('--end-rank', type=int, default=100, help='End rank (default: 100)')
    parser.add_argument('--dry-run', action='store_true', help='Parse without writing output file')
    
    args = parser.parse_args()
    
    # Generate default output filename if not provided
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"top{args.start_rank}_{args.end_rank}_parsed_data_{timestamp}.json"
    
    print(f"🔍 Step 1B.1: Parse TOP100.md for entries {args.start_rank}-{args.end_rank}")
    print("=" * 60)
    print(f"📁 Input file: {args.input}")
    print(f"📄 Output file: {args.output}")
    print(f"🎯 Target range: Ranks {args.start_rank}-{args.end_rank}")
    if args.dry_run:
        print("👁️  Dry run mode: No output file will be written")
    print("")
    
    # Check if input file exists
    if not Path(args.input).exists():
        print(f"❌ ERROR: Input file '{args.input}' not found.")
        sys.exit(1)
    
    # Initialize parser and process
    top100_parser = TOP100Parser(args.input, args.start_rank, args.end_rank)
    
    if not top100_parser.parse_markdown():
        sys.exit(1)
    
    # Generate summary
    top100_parser.generate_summary()
    
    # Export data unless dry run
    if not args.dry_run:
        if top100_parser.export_data(args.output):
            print("")
            print("🎉 Step 1B.1 Complete! Ready for Step 1B.2 - Content Classification")
        else:
            sys.exit(1)
    else:
        print("👁️  Dry run complete - no files written")


if __name__ == '__main__':
    main()
