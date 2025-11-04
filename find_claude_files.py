#!/usr/bin/env python3
"""
Quick script to find Claude AI conversation files in the directory structure.
"""

import os
from pathlib import Path

def find_conversation_files(base_dir: str, max_depth: int = 3):
    """Find conversation files in directory structure."""
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print(f"❌ Directory does not exist: {base_path}")
        return
    
    print(f"🔍 Searching for Claude conversation files in: {base_path}")
    print(f"   Max depth: {max_depth} levels")
    print()
    
    # Patterns to search for
    patterns = [
        "conversation_conv_*.json",
        "conv_*.json", 
        "*conversation*.json",
        "claude_*.json",
        "chat_*.json"
    ]
    
    found_files = {}
    
    # Search with each pattern
    for pattern in patterns:
        matches = []
        
        # Search up to max_depth levels
        for depth in range(max_depth + 1):
            glob_pattern = "/".join(["*"] * depth) + "/" + pattern if depth > 0 else pattern
            try:
                for file in base_path.glob(glob_pattern):
                    if file.is_file():
                        matches.append(file)
            except Exception as e:
                continue
        
        if matches:
            found_files[pattern] = matches
    
    # Display results
    if found_files:
        print("✅ Found conversation files:")
        for pattern, files in found_files.items():
            print(f"\n📂 Pattern: {pattern}")
            print(f"   Found {len(files)} files")
            # Show first 5 files as examples
            for i, file in enumerate(files[:5]):
                relative_path = file.relative_to(base_path)
                print(f"   {i+1}. {relative_path}")
                # Show parent directory to understand structure
                if file.parent != base_path:
                    print(f"      Parent: {file.parent.relative_to(base_path)}")
            
            if len(files) > 5:
                print(f"   ... and {len(files) - 5} more files")
    else:
        print("❌ No conversation files found")
        print("\n📁 Directory structure (first 3 levels):")
        
        # Show directory structure to help understand layout
        for root, dirs, files in os.walk(base_path):
            level = len(Path(root).relative_to(base_path).parts)
            if level > 3:
                dirs.clear()  # Don't recurse deeper
                continue
            
            indent = "  " * level
            rel_path = Path(root).relative_to(base_path)
            print(f"{indent}📁 {rel_path if str(rel_path) != '.' else '/'}")
            
            # Show JSON files
            json_files = [f for f in files if f.endswith('.json')]
            if json_files:
                for file in json_files[:5]:
                    print(f"{indent}  📄 {file}")
                if len(json_files) > 5:
                    print(f"{indent}  ... {len(json_files) - 5} more JSON files")
    
    print("\n" + "=" * 60)
    
    # Also check the quivr_parsed_data directory
    parsed_data_dir = Path(base_dir) / "quivr_parsed_data"
    if parsed_data_dir.exists():
        print(f"\n📂 Also found: {parsed_data_dir}")
        txt_files = list(parsed_data_dir.glob("conversation_conv_*.txt"))
        if txt_files:
            print(f"   Contains {len(txt_files)} .txt conversation files")
            print("   💡 Original JSON files might be in the parent directory")


if __name__ == "__main__":
    import sys
    
    # Default to F:\dev\quivr or use command line argument
    search_dir = sys.argv[1] if len(sys.argv) > 1 else r"F:\dev\quivr"
    
    print("=" * 60)
    print("🔍 CLAUDE CONVERSATION FILE FINDER")
    print("=" * 60)
    print()
    
    find_conversation_files(search_dir)
    
    # Also try some alternative locations
    alternative_dirs = [
        Path(search_dir) / "data",
        Path(search_dir) / "conversations", 
        Path(search_dir) / "exports",
        Path(search_dir) / "claude",
        Path(search_dir) / "chats"
    ]
    
    for alt_dir in alternative_dirs:
        if alt_dir.exists():
            print(f"\n🔍 Checking alternative location: {alt_dir}")
            find_conversation_files(str(alt_dir), max_depth=1)