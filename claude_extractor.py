#!/usr/bin/env python3
"""
Claude AI Chat Data Extractor

Main orchestrator for extracting and processing Claude AI conversation data.
Provides command-line interface and coordinates all extraction modules.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from claude_config import get_config_manager, ClaudeExtractorConfig
from claude_file_discovery import discover_claude_files, FileMetadata
from claude_content_parser import parse_claude_content, Conversation, ParseResult
from claude_progress_tracker import ProgressTracker
from claude_error_handler import ErrorHandler


class ClaudeExtractor:
    """Main Claude AI data extraction orchestrator."""

    def __init__(self, config: Optional[ClaudeExtractorConfig] = None):
        """
        Initialize the Claude extractor.

        Args:
            config: Configuration object (uses default if None)
        """
        self.config = config or get_config_manager().get_config()
        self.progress_tracker = ProgressTracker()
        self.error_handler = ErrorHandler()

        print("🚀 Claude AI Chat Data Extractor Initialized")
        print(f"   📂 Source: {self.config.source_directory}")
        print(f"   💾 Output: {self.config.output.output_directory}")
        print(f"   ⚙️  Batch Size: {self.config.processing.batch_size}")
        print(f"   🧵 Workers: {self.config.processing.max_workers}")

    def run_extraction(self, limit_files: Optional[int] = None) -> bool:
        """
        Run the complete extraction pipeline.

        Args:
            limit_files: Limit number of files to process (for testing)

        Returns:
            True if extraction completed successfully
        """
        try:
            print("\n🎯 Starting Claude AI Chat Data Extraction")
            print("=" * 60)

            # Phase 1: File Discovery
            print("\n📂 Phase 1: File Discovery")
            discovery_result = self._run_file_discovery()

            if discovery_result.valid_files == 0:
                print("❌ No valid conversation files found. Aborting extraction.")
                return False

            # Apply file limit for testing
            valid_files = discovery_result.file_metadata
            if limit_files:
                valid_files = valid_files[:limit_files]
                print(f"🧪 Limiting to {limit_files} files for testing")

            # Phase 2: Content Parsing
            print("\n📖 Phase 2: Content Parsing")
            parse_result = self._run_content_parsing(valid_files)

            if not parse_result.conversations:
                print("❌ No conversations could be parsed. Aborting extraction.")
                return False

            # Phase 3: Output Generation
            print("\n💾 Phase 3: Output Generation")
            output_success = self._run_output_generation(parse_result)

            if not output_success:
                print("❌ Output generation failed.")
                return False

            # Phase 4: Notion Integration (if enabled)
            if self.config.notion.enabled:
                print("\n🗃️  Phase 4: Notion Integration")
                notion_success = self._run_notion_integration(parse_result)
                if not notion_success:
                    print("⚠️  Notion integration failed, but extraction completed.")
            else:
                print("\n🗃️  Phase 4: Notion Integration - Skipped (disabled)")

            # Final Summary
            self._print_final_summary(discovery_result, parse_result)

            print("\n✅ Claude AI Chat Data Extraction Completed Successfully!")
            return True

        except Exception as e:
            error_msg = f"Critical error during extraction: {str(e)}"
            print(f"\n❌ {error_msg}")
            self.error_handler.log_error("extraction_failed", error_msg, str(e))
            return False

    def _run_file_discovery(self):
        """Run file discovery phase."""
        self.progress_tracker.start_phase("file_discovery")

        discovery_result = discover_claude_files(self.config.source_directory)

        self.progress_tracker.end_phase("file_discovery", discovery_result.processing_time)

        if discovery_result.errors:
            for error in discovery_result.errors:
                self.error_handler.log_error("file_discovery", error)

        return discovery_result

    def _run_content_parsing(self, valid_files: List[FileMetadata]) -> ParseResult:
        """Run content parsing phase."""
        self.progress_tracker.start_phase("content_parsing")

        parse_result = parse_claude_content(valid_files)

        self.progress_tracker.end_phase("content_parsing", parse_result.processing_time)

        if parse_result.errors:
            for error in parse_result.errors:
                self.error_handler.log_error("content_parsing", error)

        return parse_result

    def _run_output_generation(self, parse_result: ParseResult) -> bool:
        """Run output generation phase."""
        try:
            self.progress_tracker.start_phase("output_generation")

            # Import here to avoid circular imports
            from claude_output_generator import OutputGenerator

            output_gen = OutputGenerator(self.config)
            success = output_gen.generate_outputs(parse_result)

            processing_time = self.progress_tracker.end_phase("output_generation")
            print(f"   ⏱️  Output generation completed in {processing_time:.2f}s")

            return success

        except Exception as e:
            self.error_handler.log_error("output_generation", f"Output generation failed: {str(e)}", str(e))
            return False

    def _run_notion_integration(self, parse_result: ParseResult) -> bool:
        """Run Notion integration phase."""
        try:
            self.progress_tracker.start_phase("notion_integration")

            # Import here to avoid circular imports
            from claude_notion_integration import NotionIntegrator

            integrator = NotionIntegrator(self.config)
            success = integrator.integrate_conversations(parse_result.conversations)

            processing_time = self.progress_tracker.end_phase("notion_integration")
            print(f"   ⏱️  Notion integration completed in {processing_time:.2f}s")

            return success

        except Exception as e:
            self.error_handler.log_error("notion_integration", f"Notion integration failed: {str(e)}", str(e))
            return False

    def _print_final_summary(self, discovery_result, parse_result: ParseResult):
        """Print final extraction summary."""
        print("\n🎉 Final Extraction Summary")
        print("=" * 60)

        total_time = self.progress_tracker.get_total_time()

        print(f"📂 Files Discovered: {discovery_result.total_files}")
        print(f"✅ Valid Files: {discovery_result.valid_files}")
        print(f"💬 Conversations Parsed: {parse_result.successful_parses}")
        print(f"💌 Total Messages: {parse_result.total_messages}")
        print(f"⏱️  Total Processing Time: {total_time:.2f}s")

        if parse_result.conversations:
            avg_msgs = sum(c.total_messages for c in parse_result.conversations) / len(parse_result.conversations)
            print(f"📊 Average Messages/Conversation: {avg_msgs:.1f}")

        # Phase timing breakdown
        print("\n⏱️  Phase Timing:")
        for phase, time in self.progress_tracker.get_phase_times().items():
            phase_name = phase.replace('_', ' ').title()
            print(f"   {phase_name}: {time:.2f}s")

        print(f"\n💾 Output Directory: {self.config.output.output_directory}")
        if self.config.notion.enabled:
            print(f"🗃️  Notion Database: {self.config.notion.database_name}")

        print("=" * 60)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Extract and process Claude AI conversation data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python claude_extractor.py                          # Run full extraction
  python claude_extractor.py --limit 10               # Test with 10 files
  python claude_extractor.py --config my_config.json  # Use custom config
  python claude_extractor.py --output ./results       # Custom output directory
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration JSON file'
    )

    parser.add_argument(
        '--source',
        type=str,
        help='Source directory containing Claude conversation files'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output directory for generated files'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of files to process (for testing)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        help='Batch size for processing'
    )

    parser.add_argument(
        '--workers',
        type=int,
        help='Number of worker threads'
    )

    parser.add_argument(
        '--formats',
        type=str,
        nargs='+',
        choices=['json', 'csv', 'markdown', 'sqlite'],
        help='Output formats to generate'
    )

    parser.add_argument(
        '--enable-notion',
        action='store_true',
        help='Enable Notion integration'
    )

    parser.add_argument(
        '--notion-db',
        type=str,
        help='Notion database name'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing'
    )

    return parser


def main():
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Load configuration
    config_manager = get_config_manager(args.config)

    # Override config with command-line arguments
    if args.source:
        config_manager.config.source_directory = args.source
    if args.output:
        config_manager.config.output.output_directory = args.output
    if args.batch_size:
        config_manager.config.processing.batch_size = args.batch_size
    if args.workers:
        config_manager.config.processing.max_workers = args.workers
    if args.formats:
        config_manager.config.output.formats = args.formats
    if args.enable_notion:
        config_manager.config.notion.enabled = True
    if args.notion_db:
        config_manager.config.notion.database_name = args.notion_db

    # Validate configuration
    config_manager._validate_config()

    if args.verbose:
        config_manager.print_config_summary()

    if args.dry_run:
        print("🔍 Dry run mode - would process:")
        print(f"   📂 Source: {config_manager.config.source_directory}")
        print(f"   💾 Output: {config_manager.config.output.output_directory}")
        print(f"   📋 Formats: {', '.join(config_manager.config.output.formats)}")
        print(f"   🗃️  Notion: {'Enabled' if config_manager.config.notion.enabled else 'Disabled'}")
        return

    # Create and run extractor
    extractor = ClaudeExtractor(config_manager.config)

    success = extractor.run_extraction(limit_files=args.limit)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()