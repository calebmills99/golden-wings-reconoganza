#!/usr/bin/env python3
"""
Quick start script for Claude AI chat extraction.
Run this to extract your Claude conversations with minimal setup.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from claude_config import ClaudeExtractorConfig
from claude_extractor import ClaudeExtractor


def print_banner():
    """Print welcome banner."""
    print("\n" + "=" * 60)
    print("🤖 CLAUDE AI CHAT EXTRACTION PIPELINE")
    print("=" * 60)
    print("Extract and organize your Claude conversation history")
    print("=" * 60 + "\n")


def quick_extract(source_dir: str = None, output_dir: str = None, 
                  sample: int = None, debug: bool = False):
    """
    Quick extraction with minimal configuration.
    
    Args:
        source_dir: Path to JSON files (default: F:\\dev\\quivr)
        output_dir: Output directory (default: ./claude_output)
        sample: Process only N files for testing
        debug: Enable debug mode
    """
    print_banner()
    
    # Set defaults
    if not source_dir:
        source_dir = r"F:\dev\quivr"
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"./claude_output_{timestamp}"
    
    print(f"📁 Source: {source_dir}")
    print(f"💾 Output: {output_dir}")
    if sample:
        print(f"🧪 Sample mode: Processing {sample} files only")
    if debug:
        print(f"🔍 Debug mode: Enabled")
    print()
    
    # Initialize configuration
    config = ClaudeExtractorConfig()
    config.source_directory = source_dir
    config.output_directory = output_dir
    
    if sample:
        config.processing.sample_size = sample
    if debug:
        config.processing.debug_mode = True
    
    # Create extractor
    extractor = ClaudeExtractor(config)
    
    # Run extraction pipeline
    print("🚀 Starting extraction pipeline...\n")
    
    try:
        # Phase 1: Discovery
        print("📂 Phase 1: Discovering files...")
        discovery_result = extractor.discover()
        
        if not discovery_result or discovery_result.total_files == 0:
            print("❌ No files found. Please check the source directory.")
            return False
        
        print(f"✅ Found {discovery_result.total_files} files")
        print(f"   Valid: {discovery_result.valid_files}")
        print(f"   Invalid: {discovery_result.invalid_files}")
        
        # Phase 2: Extraction
        print(f"\n🔄 Phase 2: Extracting conversations...")
        if sample:
            print(f"   (Processing first {sample} files only)")
        
        conversations = extractor.extract(discovery_result)
        
        if not conversations:
            print("❌ No conversations extracted")
            return False
        
        print(f"✅ Extracted {len(conversations)} conversations")
        
        # Calculate statistics
        total_messages = sum(len(c.messages) for c in conversations)
        print(f"   Total messages: {total_messages}")
        print(f"   Avg messages/conversation: {total_messages/len(conversations):.1f}")
        
        # Phase 3: Export
        print(f"\n💾 Phase 3: Exporting data...")
        export_paths = extractor.export(conversations)
        
        if export_paths:
            print(f"✅ Data exported successfully:")
            for format_type, path in export_paths.items():
                print(f"   {format_type}: {path}")
        
        # Phase 4: Report
        print(f"\n📊 Phase 4: Generating report...")
        report_path = extractor.generate_report(conversations)
        
        if report_path:
            print(f"✅ Report generated: {report_path}")
        
        print("\n" + "=" * 60)
        print("🎉 EXTRACTION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Extraction interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Extraction failed: {str(e)}")
        if debug:
            import traceback
            traceback.print_exc()
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract Claude AI conversations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all conversations
  python run_claude_extraction.py
  
  # Extract from custom location
  python run_claude_extraction.py --source "C:\\my_chats" --output "./output"
  
  # Test with 10 files
  python run_claude_extraction.py --sample 10 --debug
  
  # Extract specific format
  python run_claude_extraction.py --format json,markdown
        """
    )
    
    parser.add_argument(
        '--source', '-s',
        type=str,
        help='Source directory with JSON files (default: F:\\dev\\quivr)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output directory (default: ./claude_output_TIMESTAMP)'
    )
    
    parser.add_argument(
        '--sample', '-n',
        type=int,
        help='Process only N files for testing'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        default='json,csv',
        help='Export formats: json,csv,markdown,sqlite (default: json,csv)'
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug mode'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run test mode (same as --sample 5 --debug)'
    )
    
    args = parser.parse_args()
    
    # Handle test mode
    if args.test:
        args.sample = 5
        args.debug = True
    
    # Run extraction
    success = quick_extract(
        source_dir=args.source,
        output_dir=args.output,
        sample=args.sample,
        debug=args.debug
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())