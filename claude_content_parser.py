"""
"""
Claude AI Chat Data Content Parser Module

Parses JSON conversation files, extracts chat messages, reconstructs
conversations, and normalizes data for further processing.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

from claude_config import get_config
from claude_file_discovery import FileMetadata


@dataclass
class Message:
    """Represents a single chat message."""
    uuid: str
    sender: str  # "human" or "assistant"
    text: str
    created_at: datetime
    updated_at: datetime
    has_attachments: bool
    attachment_count: int
    content_length: int
    message_index: int = 0


@dataclass
class Conversation:
    """Represents a complete conversation."""
    conversation_id: str
    title: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    account_uuid: str
    total_messages: int
    human_messages: int
    assistant_messages: int
    duration_seconds: Optional[int]
    file_parts: List[Path]
    metadata: Dict[str, Any]


@dataclass
class ParseResult:
    """Results of parsing operation."""
    conversations: List[Conversation]
    total_messages: int
    successful_parses: int
    failed_parses: int
    processing_time: float
    errors: List[str]


class ContentParser:
    """Parses Claude AI conversation content from JSON files."""

    def __init__(self):
        """Initialize the content parser."""
        self.config = get_config()

    def parse_files(self, file_metadata: List[FileMetadata]) -> ParseResult:
        """
        Parse multiple conversation files.

        Args:
            file_metadata: List of valid file metadata to parse

        Returns:
            ParseResult with parsed conversations and statistics
        """
        start_time = datetime.now()

        print(f"📖 Parsing {len(file_metadata)} conversation files...")

        conversations = []
        total_messages = 0
        successful_parses = 0
        failed_parses = 0
        errors = []

        # Group files by conversation ID
        conv_groups = self._group_files_by_conversation(file_metadata)

        for conv_id, files in conv_groups.items():
            try:
                conversation = self._parse_conversation(conv_id, files)
                if conversation:
                    conversations.append(conversation)
                    total_messages += conversation.total_messages
                    successful_parses += 1
                    print(f"   ✅ Parsed conversation {conv_id} ({conversation.total_messages} messages)")
                else:
                    failed_parses += 1
                    errors.append(f"Failed to parse conversation {conv_id}")
            except Exception as e:
                failed_parses += 1
                error_msg = f"Error parsing conversation {conv_id}: {str(e)}"
                errors.append(error_msg)
                print(f"   ❌ {error_msg}")

        processing_time = (datetime.now() - start_time).total_seconds()

        result = ParseResult(
            conversations=conversations,
            total_messages=total_messages,
            successful_parses=successful_parses,
            failed_parses=failed_parses,
            processing_time=processing_time,
            errors=errors
        )

        self._print_parse_summary(result)
        return result

    def _group_files_by_conversation(self, file_metadata: List[FileMetadata]) -> Dict[str, List[FileMetadata]]:
        """
        Group files by conversation ID.

        Args:
            file_metadata: List of file metadata

        Returns:
            Dictionary mapping conversation IDs to file lists
        """
        conversations = {}

        for metadata in file_metadata:
            if metadata.is_valid and metadata.conversation_id:
                if metadata.conversation_id not in conversations:
                    conversations[metadata.conversation_id] = []
                conversations[metadata.conversation_id].append(metadata)

        # Sort files within each conversation by part number
        for conv_id, files in conversations.items():
            files.sort(key=lambda x: x.part_number if x.part_number is not None else -1)

        return conversations

    def _parse_conversation(self, conv_id: str, files: List[FileMetadata]) -> Optional[Conversation]:
        """
        Parse a complete conversation from one or more files.

        Args:
            conv_id: Conversation ID
            files: List of files belonging to this conversation

        Returns:
            Conversation object or None if parsing failed
        """
        all_messages = []
        conversation_title = ""
        account_uuid = ""
        created_at = None
        updated_at = None
        file_parts = []

        for file_metadata in files:
            try:
                # Parse individual file
                file_conversation = self._parse_single_file(file_metadata.file_path)

                if file_conversation:
                    # Merge messages from this file
                    file_messages = file_conversation['messages']
                    all_messages.extend(file_messages)

                    # Use metadata from first file
                    if not conversation_title:
                        conversation_title = file_conversation['title']
                        account_uuid = file_conversation['account_uuid']
                        created_at = file_conversation['created_at']
                        updated_at = file_conversation['updated_at']

                    file_parts.append(file_metadata.file_path)

            except Exception as e:
                print(f"   ⚠️  Error parsing file {file_metadata.file_path}: {e}")
                continue

        if not all_messages:
            return None

        # Sort messages by creation time
        all_messages.sort(key=lambda x: x.created_at)

        # Re-index messages
        for i, msg in enumerate(all_messages):
            msg.message_index = i

        # Calculate conversation statistics
        human_messages = sum(1 for msg in all_messages if msg.sender == "human")
        assistant_messages = sum(1 for msg in all_messages if msg.sender == "assistant")

        # Calculate duration
        duration_seconds = None
        if len(all_messages) > 1:
            start_time = all_messages[0].created_at
            end_time = all_messages[-1].created_at
            duration_seconds = int((end_time - start_time).total_seconds())

        # Create conversation metadata
        metadata = {
            "file_count": len(files),
            "file_parts": [str(p) for p in file_parts],
            "parsing_timestamp": datetime.now().isoformat(),
            "message_distribution": {
                "human": human_messages,
                "assistant": assistant_messages
            }
        }

        return Conversation(
            conversation_id=conv_id,
            title=conversation_title,
            messages=all_messages,
            created_at=created_at,
            updated_at=updated_at,
            account_uuid=account_uuid,
            total_messages=len(all_messages),
            human_messages=human_messages,
            assistant_messages=assistant_messages,
            duration_seconds=duration_seconds,
            file_parts=file_parts,
            metadata=metadata
        )

    def _parse_single_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Parse a single conversation file.

        Args:
            file_path: Path to the file to parse

        Returns:
            Dictionary with parsed conversation data or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse outer JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Try partial parsing for truncated outer JSON
                data = self._parse_partial_outer_json(content)
                if not data:
                    return None

            # Extract and parse inner content
            inner_content_str = data.get('content', '')
            if not inner_content_str:
                return None

            # Try to parse inner content
            try:
                inner_content = json.loads(inner_content_str)
            except json.JSONDecodeError:
                # Try partial parsing of inner content
                inner_content = self._parse_partial_inner_json(inner_content_str)
                if not inner_content:
                    return None

            # Extract conversation metadata
            account_uuid = inner_content.get('account', {}).get('uuid', '')
            chat_messages = inner_content.get('chat_messages', [])

            # Parse messages (handle partial messages)
            messages = []
            for msg_data in chat_messages:
                message = self._parse_message(msg_data)
                if message:
                    messages.append(message)

            # If no messages parsed but we have partial data, try alternative extraction
            if not messages and chat_messages:
                messages = self._extract_partial_messages(inner_content_str)

            # Extract timestamps
            created_at_str = data.get('created_at', '')
            updated_at_str = inner_content.get('updated_at', created_at_str)

            created_at = self._parse_timestamp(created_at_str)
            updated_at = self._parse_timestamp(updated_at_str)

            return {
                'title': data.get('title', ''),
                'account_uuid': account_uuid,
                'messages': messages,
                'created_at': created_at,
                'updated_at': updated_at,
                'metadata': data.get('metadata', {}),
                'is_partial': len(messages) < len(chat_messages) if chat_messages else False
            }

        except Exception as e:
            print(f"   ❌ Error parsing file {file_path}: {e}")
            return None

    def _parse_partial_outer_json(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse partially truncated outer JSON.

        Args:
            content: Raw JSON content

        Returns:
            Parsed dictionary or None if parsing failed
        """
        try:
            # Try to extract key fields using regex patterns
            data = {}

            # Extract ID
            id_match = re.search(r'"id"\s*:\s*"([^"]+)"', content)
            if id_match:
                data['id'] = id_match.group(1)

            # Extract title
            title_match = re.search(r'"title"\s*:\s*"([^"]*)"', content)
            if title_match:
                data['title'] = title_match.group(1)

            # Extract created_at
            created_match = re.search(r'"created_at"\s*:\s*"([^"]+)"', content)
            if created_match:
                data['created_at'] = created_match.group(1)

            # Extract content field (the tricky part)
            content_start = content.find('"content":')
            if content_start != -1:
                # Find the start of the content value
                content_value_start = content.find('"', content_start + 10)
                if content_value_start != -1:
                    # Try to find the matching closing quote
                    # This is simplified - in practice, we'd need more sophisticated parsing
                    content_value_end = content.rfind('"')
                    if content_value_end > content_value_start:
                        data['content'] = content[content_value_start + 1:content_value_end]

            # Extract metadata if present
            metadata_match = re.search(r'"metadata"\s*:\s*({[^}]+})', content)
            if metadata_match:
                try:
                    data['metadata'] = json.loads(metadata_match.group(1))
                except:
                    data['metadata'] = {}

            return data if data.get('content') else None

        except Exception as e:
            print(f"   ⚠️  Partial outer JSON parsing failed: {e}")
            return None

    def _parse_partial_inner_json(self, content_str: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse partially truncated inner JSON content.

        Args:
            content_str: Inner JSON content string

        Returns:
            Parsed dictionary or None if parsing failed
        """
        try:
            # Try to fix common truncation issues
            if not content_str.endswith('}'):
                content_str += '}'  # Add closing brace if missing

            # Try parsing the "fixed" content
            try:
                return json.loads(content_str)
            except json.JSONDecodeError:
                pass

            # If that fails, try to extract messages manually
            messages = self._extract_partial_messages(content_str)
            if messages:
                return {
                    'account': {'uuid': ''},
                    'chat_messages': messages,
                    'updated_at': None
                }

            return None

        except Exception as e:
            print(f"   ⚠️  Partial inner JSON parsing failed: {e}")
            return None

    def _extract_partial_messages(self, content_str: str) -> List[Dict[str, Any]]:
        """
        Extract messages from partially truncated JSON using regex patterns.

        Args:
            content_str: JSON content string

        Returns:
            List of extracted message dictionaries
        """
        messages = []

        try:
            # Find all message objects using regex
            # This is a simplified approach - look for sender and text patterns
            message_blocks = re.findall(r'{[^{}]*(?:"sender"\s*:\s*"[^"]*")[^{}]*(?:"text"\s*:\s*"[^"]*")[^{}]*}', content_str)

            for block in message_blocks:
                try:
                    # Try to parse each block as JSON
                    msg_data = json.loads(block)
                    message = self._parse_message(msg_data)
                    if message:
                        messages.append(message)
                except:
                    # If JSON parsing fails, try manual extraction
                    manual_msg = self._extract_manual_message(block)
                    if manual_msg:
                        messages.append(manual_msg)

        except Exception as e:
            print(f"   ⚠️  Message extraction failed: {e}")

        return messages

    def _extract_manual_message(self, message_block: str) -> Optional[Dict[str, Any]]:
        """
        Manually extract message data from a text block using regex.

        Args:
            message_block: Raw message text block

        Returns:
            Message dictionary or None if extraction failed
        """
        try:
            message = {}

            # Extract sender
            sender_match = re.search(r'"sender"\s*:\s*"([^"]+)"', message_block)
            if sender_match:
                message['sender'] = sender_match.group(1)

            # Extract text (this is tricky due to potential nested quotes)
            text_match = re.search(r'"text"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', message_block)
            if text_match:
                message['text'] = text_match.group(1)

            # Extract UUID
            uuid_match = re.search(r'"uuid"\s*:\s*"([^"]+)"', message_block)
            if uuid_match:
                message['uuid'] = uuid_match.group(1)

            # Extract timestamps
            created_match = re.search(r'"created_at"\s*:\s*"([^"]+)"', message_block)
            if created_match:
                message['created_at'] = created_match.group(1)

            updated_match = re.search(r'"updated_at"\s*:\s*"([^"]+)"', message_block)
            if updated_match:
                message['updated_at'] = updated_match.group(1)

            return message if message.get('text') else None

        except Exception as e:
            print(f"   ⚠️  Manual message extraction failed: {e}")
            return None

    def _parse_message(self, msg_data: Dict[str, Any]) -> Optional[Message]:
        """
        Parse a single message from JSON data.

        Args:
            msg_data: Message data from JSON

        Returns:
            Message object or None if parsing failed
        """
        try:
            # Extract basic fields
            uuid = msg_data.get('uuid', '')
            sender = msg_data.get('sender', '')
            created_at_str = msg_data.get('created_at', '')
            updated_at_str = msg_data.get('updated_at', '')

            # Parse timestamps
            created_at = self._parse_timestamp(created_at_str)
            updated_at = self._parse_timestamp(updated_at_str)

            # Extract text content
            text = self._extract_message_text(msg_data)

            # Check for attachments
            attachments = msg_data.get('attachments', [])
            has_attachments = len(attachments) > 0
            attachment_count = len(attachments)

            content_length = len(text) if text else 0

            return Message(
                uuid=uuid,
                sender=sender,
                text=text,
                created_at=created_at,
                updated_at=updated_at,
                has_attachments=has_attachments,
                attachment_count=attachment_count,
                content_length=content_length
            )

        except Exception as e:
            print(f"   ⚠️  Error parsing message: {e}")
            return None

    def _extract_message_text(self, msg_data: Dict[str, Any]) -> str:
        """
        Extract text content from message data.

        Args:
            msg_data: Message data

        Returns:
            Extracted text content
        """
        # Try different sources for text content
        if 'text' in msg_data and msg_data['text']:
            return msg_data['text']

        # Try content array
        content = msg_data.get('content', [])
        if isinstance(content, list) and len(content) > 0:
            # Extract text from content items
            text_parts = []
            for item in content:
                if isinstance(item, dict) and 'text' in item:
                    text_parts.append(item['text'])
                elif isinstance(item, str):
                    text_parts.append(item)

            if text_parts:
                return ' '.join(text_parts)

        return ""

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse timestamp string to datetime object.

        Args:
            timestamp_str: ISO timestamp string

        Returns:
            Datetime object (defaults to current time if parsing fails)
        """
        if not timestamp_str:
            return datetime.now()

        try:
            # Handle different timestamp formats
            if timestamp_str.endswith('Z'):
                # ISO format with Z
                return datetime.fromisoformat(timestamp_str[:-1])
            else:
                # Try direct parsing
                return datetime.fromisoformat(timestamp_str)
        except (ValueError, AttributeError):
            # Fallback to current time
            return datetime.now()

    def _print_parse_summary(self, result: ParseResult) -> None:
        """Print a summary of parsing results."""
        print("\n📊 Content Parsing Summary")
        print("=" * 50)
        print(f"💬 Conversations parsed: {result.successful_parses}")
        print(f"❌ Failed parses: {result.failed_parses}")
        print(f"💌 Total messages: {result.total_messages}")
        print(f"⏱️  Processing time: {result.processing_time:.2f}s")
        print(f"📈 Success rate: {(result.successful_parses / (result.successful_parses + result.failed_parses) * 100):.1f}%" if (result.successful_parses + result.failed_parses) > 0 else "0.0%")

        if result.conversations:
            # Show conversation statistics
            avg_messages = sum(c.total_messages for c in result.conversations) / len(result.conversations)
            max_messages = max(c.total_messages for c in result.conversations)
            min_messages = min(c.total_messages for c in result.conversations)

            print("📈 Conversation Statistics:")
            print(f"   📏 Range: {min_messages} - {max_messages} messages")

            # Show message distribution
            total_human = sum(c.human_messages for c in result.conversations)
            total_assistant = sum(c.assistant_messages for c in result.conversations)

            print(
"👥 Message Distribution:")
            print(f"   🧑 Human: {total_human}")
            print(f"   🤖 Assistant: {total_assistant}")

        if result.errors:
            print(f"\n⚠️  Errors encountered: {len(result.errors)}")
            for error in result.errors[:3]:  # Show first 3 errors
                print(f"   • {error}")
            if len(result.errors) > 3:
                print(f"   ... and {len(result.errors) - 3} more")

        print("=" * 50)


def parse_claude_content(file_metadata: List[FileMetadata]) -> ParseResult:
    """
    Convenience function to parse Claude AI content.

    Args:
        file_metadata: List of file metadata to parse

    Returns:
        ParseResult with parsed conversations
    """
    parser = ContentParser()
    return parser.parse_files(file_metadata)


if __name__ == "__main__":
    # Test content parsing
    from claude_file_discovery import discover_claude_files

    print("🧪 Testing Claude content parser...")

    # Discover files
    discovery_result = discover_claude_files()
    if discovery_result.valid_files > 0:
        valid_files = [m for m in discovery_result.file_metadata if m.is_valid]

        # Parse content
        parse_result = parse_claude_content(valid_files[:5])  # Test with first 5 files

        print(f"\n🎯 Parsing test complete: {parse_result.successful_parses} conversations parsed")
    else:
        print("❌ No valid files found for testing")