"""
Claude AI Chat Data File Discovery Module

Scans directories for Claude AI conversation files, validates their structure,
handles duplicates, and extracts file-level metadata.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

from claude_config import get_config


@dataclass
class FileMetadata:
    """Metadata for a conversation file."""
    file_path: Path
    file_size: int
    modified_time: datetime
    conversation_id: str
    part_number: Optional[int]
    is_valid: bool
    error_message: Optional[str] = None
    content_hash: Optional[str] = None


@dataclass
class DiscoveryResult:
    """Results of file discovery operation."""
    total_files: int
    valid_files: int
    invalid_files: int
    duplicate_files: int
    file_metadata: List[FileMetadata]
    processing_time: float
    errors: List[str]


class FileDiscoverer:
    """Discovers and validates Claude AI conversation files."""

    def __init__(self):
        """Initialize the file discoverer."""
        self.config = get_config()
        self.file_pattern = re.compile(r'^conversation_conv_(\d+)(?:_(\d+))?\.json$')

    def discover_files(self, source_directory: Optional[str] = None) -> DiscoveryResult:
        """
        Discover and validate Claude AI conversation files.

        Args:
            source_directory: Directory to scan (uses config default if None)

        Returns:
            DiscoveryResult with discovery statistics and metadata
        """
        start_time = datetime.now()

        if source_directory is None:
            source_directory = self.config.source_directory

        source_path = Path(source_directory)

        if not source_path.exists():
            error_msg = f"Source directory does not exist: {source_directory}"
            print(f"❌ {error_msg}")
            return DiscoveryResult(
                total_files=0, valid_files=0, invalid_files=0, duplicate_files=0,
                file_metadata=[], processing_time=0.0, errors=[error_msg]
            )

        print(f"🔍 Scanning directory: {source_path}")
        print(f"   📂 Pattern: conversation_conv_*.json")
        print(f"   🔎 Validating content structure...")

        # Find all files matching the pattern
        all_files = list(source_path.glob("conversation_conv_*.json"))
        print(f"   📄 Found {len(all_files)} potential conversation files")

        # Process files
        file_metadata = []
        seen_hashes = set()
        duplicate_count = 0

        for file_path in all_files:
            metadata = self._analyze_file(file_path)

            # Check for duplicates
            if metadata.content_hash and metadata.content_hash in seen_hashes:
                metadata.is_valid = False
                metadata.error_message = "Duplicate content hash"
                duplicate_count += 1
            elif metadata.content_hash:
                seen_hashes.add(metadata.content_hash)

            file_metadata.append(metadata)

        # Calculate statistics
        valid_files = sum(1 for m in file_metadata if m.is_valid)
        invalid_files = len(file_metadata) - valid_files

        processing_time = (datetime.now() - start_time).total_seconds()

        result = DiscoveryResult(
            total_files=len(file_metadata),
            valid_files=valid_files,
            invalid_files=invalid_files,
            duplicate_files=duplicate_count,
            file_metadata=file_metadata,
            processing_time=processing_time,
            errors=[]
        )

        self._print_discovery_summary(result)
        return result

    def _analyze_file(self, file_path: Path) -> FileMetadata:
        """
        Analyze a single conversation file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            FileMetadata with analysis results
        """
        try:
            # Get basic file info
            stat = file_path.stat()
            modified_time = datetime.fromtimestamp(stat.st_mtime)

            # Parse filename
            conversation_id, part_number = self._parse_filename(file_path.name)

            if conversation_id is None:
                return FileMetadata(
                    file_path=file_path,
                    file_size=stat.st_size,
                    modified_time=modified_time,
                    conversation_id="",
                    part_number=None,
                    is_valid=False,
                    error_message="Invalid filename format"
                )

            # Validate file content
            is_valid, error_msg, content_hash = self._validate_file_content(file_path)

            return FileMetadata(
                file_path=file_path,
                file_size=stat.st_size,
                modified_time=modified_time,
                conversation_id=conversation_id,
                part_number=part_number,
                is_valid=is_valid,
                error_message=error_msg,
                content_hash=content_hash
            )

        except Exception as e:
            return FileMetadata(
                file_path=file_path,
                file_size=0,
                modified_time=datetime.now(),
                conversation_id="",
                part_number=None,
                is_valid=False,
                error_message=f"Analysis error: {str(e)}"
            )

    def _parse_filename(self, filename: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Parse conversation ID and part number from filename.

        Args:
            filename: Filename to parse

        Returns:
            Tuple of (conversation_id, part_number) or (None, None) if invalid
        """
        match = self.file_pattern.match(filename)
        if not match:
            return None, None

        conversation_id = match.group(1)
        part_number = int(match.group(2)) if match.group(2) else None

        return conversation_id, part_number

    def _validate_file_content(self, file_path: Path) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate the content of a conversation file.

        Args:
            file_path: Path to the file to validate

        Returns:
            Tuple of (is_valid, error_message, content_hash)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if content is empty
            if not content.strip():
                return False, "File is empty", None

            # Try to parse as JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                # Try partial parsing for truncated files
                return self._validate_partial_json(content, str(e))

            # Validate required fields
            required_fields = ['id', 'title', 'content', 'metadata', 'source']
            missing_fields = []
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)

            if missing_fields:
                return False, f"Missing required fields: {', '.join(missing_fields)}", None

            # Validate content field (should be JSON string)
            content_str = data.get('content', '')
            if not isinstance(content_str, str):
                return False, "Content field is not a string", None

            if not content_str.strip():
                return False, "Content field is empty", None

            # Try to parse the inner content
            try:
                inner_content = json.loads(content_str)
            except json.JSONDecodeError as e:
                # Try partial parsing of inner content
                return self._validate_partial_inner_content(content_str, str(e))

            # Validate inner content structure
            if 'chat_messages' not in inner_content:
                return False, "Missing chat_messages in inner content", None

            chat_messages = inner_content.get('chat_messages', [])
            if not isinstance(chat_messages, list):
                return False, "chat_messages is not a list", None

            if len(chat_messages) == 0:
                return False, "No messages in conversation", None

            # Generate content hash for duplicate detection
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

            return True, None, content_hash

        except Exception as e:
            return False, f"Content validation error: {str(e)}", None

    def _validate_partial_json(self, content: str, original_error: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Attempt to validate partially truncated JSON files.

        Args:
            content: Raw file content
            original_error: Original JSON parsing error

        Returns:
            Tuple of (is_valid, error_message, content_hash)
        """
        try:
            # Try to extract basic metadata even from truncated JSON
            # Look for key patterns in the content

            # Check for basic structure indicators
            if not ('"id":' in content and '"title":' in content):
                return False, f"Missing basic metadata fields: {original_error}", None

            # Try to extract conversation ID
            id_match = re.search(r'"id"\s*:\s*"([^"]+)"', content)
            if not id_match:
                return False, f"Cannot extract conversation ID: {original_error}", None

            # Check if content field exists
            if '"content":' not in content:
                return False, f"Missing content field: {original_error}", None

            # For truncated files, we'll mark as partially valid
            # The content parser will handle the partial data
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

            return True, f"Partially valid (truncated): {original_error}", content_hash

        except Exception as e:
            return False, f"Partial validation failed: {str(e)}", None

    def _validate_partial_inner_content(self, content_str: str, original_error: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Attempt to validate partially truncated inner JSON content.

        Args:
            content_str: Inner content JSON string
            original_error: Original JSON parsing error

        Returns:
            Tuple of (is_valid, error_message, content_hash)
        """
        try:
            # Check for basic inner structure
            if '"chat_messages"' not in content_str:
                return False, f"Missing chat_messages in inner content: {original_error}", None

            # Try to find at least one complete message
            if '"sender":' not in content_str or '"text":' not in content_str:
                return False, f"No recognizable messages: {original_error}", None

            # For partially valid inner content, we'll accept it
            # The parser will extract what it can
            return True, f"Partially valid inner content (truncated): {original_error}", None

        except Exception as e:
            return False, f"Partial inner content validation failed: {str(e)}", None

    def get_valid_files(self, discovery_result: DiscoveryResult) -> List[FileMetadata]:
        """
        Get list of valid files from discovery result.

        Args:
            discovery_result: Result from discover_files()

        Returns:
            List of valid FileMetadata objects
        """
        return [metadata for metadata in discovery_result.file_metadata if metadata.is_valid]

    def group_files_by_conversation(self, discovery_result: DiscoveryResult) -> Dict[str, List[FileMetadata]]:
        """
        Group files by conversation ID.

        Args:
            discovery_result: Result from discover_files()

        Returns:
            Dictionary mapping conversation IDs to lists of file metadata
        """
        conversations = {}

        for metadata in discovery_result.file_metadata:
            if metadata.is_valid and metadata.conversation_id:
                if metadata.conversation_id not in conversations:
                    conversations[metadata.conversation_id] = []
                conversations[metadata.conversation_id].append(metadata)

        # Sort files within each conversation by part number
        for conv_id, files in conversations.items():
            files.sort(key=lambda x: x.part_number if x.part_number is not None else -1)

        return conversations

    def _print_discovery_summary(self, result: DiscoveryResult) -> None:
        """Print a summary of the discovery results."""
        print("\n📊 File Discovery Summary")
        print("=" * 50)
        print(f"📂 Total files scanned: {result.total_files}")
        print(f"✅ Valid files: {result.valid_files}")
        print(f"❌ Invalid files: {result.invalid_files}")
        print(f"🔄 Duplicate files: {result.duplicate_files}")
        print(f"⏱️  Processing time: {result.processing_time:.2f}s")
        print(f"📈 Success rate: {(result.valid_files / result.total_files * 100):.1f}%" if result.total_files > 0 else "0.0%")

        if result.errors:
            print(f"⚠️  Errors encountered: {len(result.errors)}")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"   • {error}")
            if len(result.errors) > 5:
                print(f"   ... and {len(result.errors) - 5} more")

        # Show conversation distribution
        if result.valid_files > 0:
            conversations = self.group_files_by_conversation(result)
            single_part = sum(1 for files in conversations.values() if len(files) == 1)
            multi_part = sum(1 for files in conversations.values() if len(files) > 1)

            print(f"💬 Conversations: {len(conversations)} total")
            print(f"   📄 Single-part: {single_part}")
            print(f"   📚 Multi-part: {multi_part}")

        print("=" * 50)


def discover_claude_files(source_directory: Optional[str] = None) -> DiscoveryResult:
    """
    Convenience function to discover Claude AI files.

    Args:
        source_directory: Directory to scan (optional)

    Returns:
        DiscoveryResult with file discovery data
    """
    discoverer = FileDiscoverer()
    return discoverer.discover_files(source_directory)


if __name__ == "__main__":
    # Test file discovery
    result = discover_claude_files()
    print(f"\n🎯 Discovery complete: {result.valid_files} valid files found")