#!/usr/bin/env python3
"""
Test script for Claude AI chat extraction pipeline.
Tests file discovery, parsing, and extraction with JSON files.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from claude_config import ClaudeExtractorConfig, ProcessingConfig
from claude_file_discovery import FileDiscoverer
from claude_content_parser import ContentParser
from claude_error_handler import ErrorHandler
from claude_progress_tracker import ProgressTracker


def test_configuration():
    """Test configuration setup."""
    print("\n" + "=" * 60)
    print("🔧 Testing Configuration")
    print("=" * 60)
    
    try:
        config = ClaudeExtractorConfig()
        # Update to use the original JSON source
        config.source_directory = r"F:\dev\quivr"
        config.output_directory = "./claude_test_output"
        
        print(f"✅ Source directory: {config.source_directory}")
        print(f"✅ Output directory: {config.output_directory}")
        print(f"✅ Batch size: {config.processing.batch_size}")
        print(f"✅ Max workers: {config.processing.max_workers}")
        
        return config
    except Exception as e:
        print(f"❌ Configuration failed: {str(e)}")
        return None


def test_file_discovery(config: ClaudeExtractorConfig):
    """Test file discovery with JSON files."""
    print("\n" + "=" * 60)
    print("🔍 Testing File Discovery")
    print("=" * 60)
    
    try:
        discovery = FileDiscoverer()
        result = discovery.discover_files(config.source_directory)
        
        print(f"📊 Discovery Results:")
        print(f"   Total files found: {result.total_files}")
        print(f"   Valid JSON files: {result.valid_files}")
        print(f"   Invalid files: {result.invalid_files}")
        print(f"   Duplicate files: {result.duplicate_files}")
        
        if result.total_files == 0:
            print("⚠️ No files found. Checking directory...")
            source_path = Path(config.source_directory)
            if not source_path.exists():
                print(f"❌ Directory does not exist: {source_path}")
            else:
                json_files = list(source_path.glob("*.json"))
                print(f"   Found {len(json_files)} .json files in directory")
                if json_files:
                    print(f"   Sample files: {[f.name for f in json_files[:5]]}")
        else:
            # Show sample of discovered files
            print(f"\n📁 Sample files discovered:")
            for i, metadata in enumerate(result.file_metadata[:5]):
                status = "✅" if metadata.is_valid else "❌"
                print(f"   {status} {metadata.filename}")
                if metadata.error_message:
                    print(f"      Error: {metadata.error_message}")
        
        # Test conversation grouping
        conversations = discovery.group_files_by_conversation(result)
        print(f"\n💬 Conversations found: {len(conversations)}")
        
        if conversations:
            # Show sample conversation
            conv_id = list(conversations.keys())[0]
            print(f"   Sample conversation: {conv_id}")
            print(f"   Parts: {len(conversations[conv_id])}")
        
        return result
    except Exception as e:
        print(f"❌ File discovery failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_content_parsing(discovery_result):
    """Test content parsing with sample files."""
    print("\n" + "=" * 60)
    print("📄 Testing Content Parsing")
    print("=" * 60)
    
    if not discovery_result or not discovery_result.file_metadata:
        print("⚠️ No files to parse")
        return None
    
    try:
        parser = ContentParser()
        error_handler = ErrorHandler()
        
        # Get first valid file for testing
        valid_files = [m for m in discovery_result.file_metadata if m.is_valid]
        if not valid_files:
            print("⚠️ No valid files found for parsing")
            return None
        
        test_file = valid_files[0]
        print(f"🧪 Testing with file: {test_file.filename}")
        
        # Parse the file
        result = parser.parse_files([test_file])
        
        if result and result.conversations:
            conversation = result.conversations[0]
            print(f"✅ Successfully parsed conversation")
            print(f"   ID: {conversation.conversation_id}")
            print(f"   Title: {conversation.title[:50]}..." if conversation.title else "   Title: None")
            print(f"   Model: {conversation.model if hasattr(conversation, 'model') else 'N/A'}")
            print(f"   Messages: {len(conversation.messages)}")
            print(f"   Created: {conversation.created_at}")
            
            if conversation.messages:
                print(f"\n   First message:")
                msg = conversation.messages[0]
                content_preview = msg.text[:100] if msg.text else "Empty"
                print(f"      Role: {msg.sender}")
                print(f"      Content: {content_preview}...")
            
            return conversation
        else:
            print("❌ Failed to parse conversation")
            if error_handler.get_error_summary():
                print(f"   Errors: {error_handler.get_error_summary()}")
            return None
            
    except Exception as e:
        print(f"❌ Content parsing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_batch_processing(discovery_result, config: ClaudeExtractorConfig):
    """Test batch processing with progress tracking."""
    print("\n" + "=" * 60)
    print("⚡ Testing Batch Processing")
    print("=" * 60)
    
    if not discovery_result or not discovery_result.file_metadata:
        print("⚠️ No files to process")
        return None
    
    try:
        parser = ContentParser()
        tracker = ProgressTracker()
        
        # Process first 10 files as a test
        test_files = discovery_result.file_metadata[:10]
        total_files = len(test_files)
        
        print(f"📦 Processing {total_files} files in batch...")
        tracker.start_phase("parsing", total_items=total_files)
        
        successful = 0
        failed = 0
        conversations = []
        
        for i, metadata in enumerate(test_files):
            try:
                if metadata.is_valid:
                    parse_result = parser.parse_files([metadata])
                    if parse_result and parse_result.conversations:
                        conversations.extend(parse_result.conversations)
                        successful += 1
                    else:
                        failed += 1
                else:
                    failed += 1
                    
                tracker.update_progress(i + 1)
                
                # Show progress every 3 files
                if (i + 1) % 3 == 0:
                    metrics = tracker.get_current_metrics()
                    print(f"   Progress: {metrics['progress']:.1f}% "
                          f"(ETA: {metrics['eta']})")
                    
            except Exception as e:
                failed += 1
                print(f"   ❌ Error processing {metadata.filename}: {str(e)}")
        
        tracker.end_phase()
        
        print(f"\n📊 Batch Processing Results:")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Success rate: {(successful/total_files*100):.1f}%")
        
        # Calculate statistics
        if conversations:
            total_messages = sum(len(c.messages) for c in conversations)
            avg_messages = total_messages / len(conversations)
            print(f"   Total messages extracted: {total_messages}")
            print(f"   Average messages per conversation: {avg_messages:.1f}")
        
        return conversations
        
    except Exception as e:
        print(f"❌ Batch processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def generate_test_report(results: Dict):
    """Generate a test report."""
    print("\n" + "=" * 60)
    print("📋 Test Report Summary")
    print("=" * 60)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"📅 Test completed at: {timestamp}")
    
    # Check results
    all_passed = True
    
    print("\n🔍 Test Results:")
    for test_name, test_result in results.items():
        if test_result is not None:
            print(f"   ✅ {test_name}: PASSED")
        else:
            print(f"   ❌ {test_name}: FAILED")
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed successfully!")
        print("✅ The extraction pipeline is ready for full processing")
    else:
        print("\n⚠️ Some tests failed. Please review the errors above.")
        print("🔧 Fix the issues before running full extraction")
    
    # Save report to file
    report_path = Path("claude_test_report.json")
    report_data = {
        "timestamp": timestamp,
        "tests": {name: (result is not None) for name, result in results.items()},
        "all_passed": all_passed
    }
    
    try:
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        print(f"\n💾 Test report saved to: {report_path}")
    except Exception as e:
        print(f"⚠️ Could not save report: {str(e)}")


def main():
    """Run all tests."""
    print("\n" + "🚀 " * 20)
    print(" CLAUDE AI CHAT EXTRACTION PIPELINE TEST")
    print("🚀 " * 20)
    
    results = {}
    
    # Test 1: Configuration
    config = test_configuration()
    results["Configuration"] = config
    
    if not config:
        print("\n❌ Cannot proceed without valid configuration")
        generate_test_report(results)
        return 1
    
    # Test 2: File Discovery
    discovery_result = test_file_discovery(config)
    results["File Discovery"] = discovery_result
    
    # Test 3: Content Parsing (single file)
    if discovery_result and discovery_result.file_metadata:
        conversation = test_content_parsing(discovery_result)
        results["Content Parsing"] = conversation
    else:
        print("\n⚠️ Skipping content parsing test (no files found)")
        results["Content Parsing"] = None
    
    # Test 4: Batch Processing
    if discovery_result and discovery_result.file_metadata:
        conversations = test_batch_processing(discovery_result, config)
        results["Batch Processing"] = conversations
    else:
        print("\n⚠️ Skipping batch processing test (no files found)")
        results["Batch Processing"] = None
    
    # Generate report
    generate_test_report(results)
    
    return 0 if all(v is not None for v in results.values()) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)