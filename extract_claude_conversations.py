#!/usr/bin/env python3
"""
Extract Claude AI conversations from consolidated JSON export.
Processes the single conversations.json file and extracts all messages.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import sys


def extract_conversations(json_file: str = r"F:\dev\quivr\data-2025-07-02-20-51-09\conversations.json"):
    """Extract and analyze Claude conversations from JSON file."""
    
    print("🚀 Claude AI Conversation Extractor")
    print("=" * 60)
    
    # Load the JSON file
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
        print(f"✅ Loaded {len(conversations)} conversations")
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None
    
    # Process conversations
    print("\n📊 Processing conversations...")
    
    all_messages = []
    conversation_summaries = []
    
    for i, conv in enumerate(conversations):
        conv_id = conv.get('uuid', f'unknown_{i}')
        conv_name = conv.get('name', 'Untitled')
        created = conv.get('created_at', '')
        updated = conv.get('updated_at', '')
        messages = conv.get('chat_messages', [])
        
        # Count message types
        human_msgs = sum(1 for m in messages if m.get('sender') == 'human')
        assistant_msgs = sum(1 for m in messages if m.get('sender') == 'assistant')
        
        # Extract messages
        for msg in messages:
            msg_data = {
                'conversation_id': conv_id,
                'conversation_name': conv_name,
                'sender': msg.get('sender', 'unknown'),
                'text': msg.get('text', ''),
                'created_at': msg.get('created_at', ''),
                'uuid': msg.get('uuid', '')
            }
            all_messages.append(msg_data)
        
        # Create conversation summary
        summary = {
            'id': conv_id,
            'name': conv_name,
            'created': created,
            'updated': updated,
            'total_messages': len(messages),
            'human_messages': human_msgs,
            'assistant_messages': assistant_msgs
        }
        conversation_summaries.append(summary)
        
        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"   Processed {i + 1}/{len(conversations)} conversations...")
    
    print(f"✅ Extracted {len(all_messages)} total messages")
    
    # Calculate statistics
    print("\n📈 Statistics:")
    print(f"   Total conversations: {len(conversations)}")
    print(f"   Total messages: {len(all_messages)}")
    print(f"   Average messages per conversation: {len(all_messages) / len(conversations):.1f}")
    
    # Find date range
    dates = [c['created'] for c in conversation_summaries if c['created']]
    if dates:
        dates_sorted = sorted(dates)
        print(f"   Date range: {dates_sorted[0][:10]} to {dates_sorted[-1][:10]}")
    
    # Top conversations by message count
    top_convs = sorted(conversation_summaries, key=lambda x: x['total_messages'], reverse=True)[:10]
    
    print("\n📝 Top 10 Conversations by Message Count:")
    for i, conv in enumerate(top_convs, 1):
        name = conv['name'][:60] + '...' if len(conv['name']) > 60 else conv['name']
        print(f"   {i}. {name} ({conv['total_messages']} messages)")
    
    return {
        'conversations': conversation_summaries,
        'messages': all_messages,
        'statistics': {
            'total_conversations': len(conversations),
            'total_messages': len(all_messages),
            'avg_messages_per_conversation': len(all_messages) / len(conversations)
        }
    }


def save_extracted_data(data: Dict, output_dir: str = "./claude_extracted"):
    """Save extracted data to files."""
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save conversation summaries
    conv_file = output_path / f"conversation_summaries_{timestamp}.json"
    with open(conv_file, 'w', encoding='utf-8') as f:
        json.dump(data['conversations'], f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved conversation summaries to: {conv_file}")
    
    # Save all messages
    msg_file = output_path / f"all_messages_{timestamp}.json"
    with open(msg_file, 'w', encoding='utf-8') as f:
        json.dump(data['messages'], f, indent=2, ensure_ascii=False)
    print(f"💾 Saved all messages to: {msg_file}")
    
    # Save statistics
    stats_file = output_path / f"statistics_{timestamp}.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(data['statistics'], f, indent=2, ensure_ascii=False)
    print(f"💾 Saved statistics to: {stats_file}")
    
    # Create a markdown report
    report_file = output_path / f"extraction_report_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Claude AI Conversation Extraction Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Statistics\n\n")
        f.write(f"- Total Conversations: {data['statistics']['total_conversations']}\n")
        f.write(f"- Total Messages: {data['statistics']['total_messages']}\n")
        f.write(f"- Average Messages per Conversation: {data['statistics']['avg_messages_per_conversation']:.1f}\n\n")
        
        f.write("## Top Conversations\n\n")
        top_10 = sorted(data['conversations'], key=lambda x: x['total_messages'], reverse=True)[:10]
        for i, conv in enumerate(top_10, 1):
            f.write(f"{i}. **{conv['name']}** - {conv['total_messages']} messages\n")
    
    print(f"📄 Created extraction report: {report_file}")
    
    return output_path


def main():
    """Main function."""
    print("\n" + "=" * 60)
    print("🤖 CLAUDE AI CONVERSATION EXTRACTOR")
    print("=" * 60 + "\n")
    
    # Extract data
    data = extract_conversations()
    
    if data:
        # Save extracted data
        output_dir = save_extracted_data(data)
        
        print("\n" + "=" * 60)
        print("✅ EXTRACTION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\n📂 Output saved to: {output_dir}")
        print("\n🎯 Next steps:")
        print("   1. Review the extraction report")
        print("   2. Process conversation_summaries.json for analysis")
        print("   3. Use all_messages.json for detailed content extraction")
    else:
        print("\n❌ Extraction failed. Please check the error messages above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())