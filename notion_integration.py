#!/usr/bin/env python3
"""
Golden Wings Content Hunter - Notion Database Integration
Parses TOP50.md and creates/updates Notion database entries
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
import requests

# Attempt to load .env without requiring external dependencies
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # fallback defined below


def _fallback_load_dotenv(dotenv_path: str = ".env") -> None:
    try:
        p = Path(dotenv_path)
        if not p.exists():
            return
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            # do not override existing environment values
            if name and name not in os.environ:
                os.environ[name] = value
    except Exception:
        # Silent fallback; environment remains unchanged
        pass

# Load environment variables from .env if available
if load_dotenv:
    load_dotenv()
else:
    _fallback_load_dotenv()

NOTION_SECRET_ENV = os.getenv("NOTION_SECRET", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
NOTION_DATABASE_NAME = os.getenv("NOTION_DATABASE_NAME", "")

# Notion API configuration
NOTION_API_URL = "https://api.notion.com/v1"
HEADERS = {}

def _make_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

def _looks_placeholder(token: str) -> bool:
    if not token:
        return True
    lowered = token.lower()
    return any(x in lowered for x in ["<your", "{your", "<token", "your_notion", "changeme"]) or token.endswith("=")

def _test_token(token: str) -> bool:
    try:
        hdrs = _make_headers(token)
        resp = requests.get(f"{NOTION_API_URL}/users", headers=hdrs, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False

def resolve_notion_secret() -> str:
    """Resolve the Notion token strictly from environment/.env.
    No hardcoded fallback to avoid leaking secrets and to satisfy push-protection.
    """
    if NOTION_SECRET_ENV and not _looks_placeholder(NOTION_SECRET_ENV):
        if _test_token(NOTION_SECRET_ENV):
            print("🔑 Using NOTION_SECRET from .env / environment")
            return NOTION_SECRET_ENV
        else:
            print("❌ NOTION_SECRET from .env appears invalid. Please update your .env and retry.")
    # No valid token available
    return ""

# Resolve token on import so all helpers share the same headers
NOTION_SECRET = resolve_notion_secret()
HEADERS = _make_headers(NOTION_SECRET)

def _extract_db_title(db: dict) -> str:
    title = db.get("title", [])
    if isinstance(title, list) and title:
        return "".join([t.get("plain_text", "") for t in title])
    return ""

def _search_databases(query: str, page_size: int = 50) -> list:
    """Search Notion for databases matching a query string."""
    try:
        payload = {
            "query": query or "",
            "filter": {"value": "database", "property": "object"},
            "page_size": page_size,
        }
        resp = requests.post(f"{NOTION_API_URL}/search", headers=HEADERS, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("results", [])
        else:
            print(f"❌ Database search failed: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return []
    except Exception as e:
        print(f"❌ Error searching databases: {e}")
        return []

def resolve_database_id() -> str:
    """Resolve database ID via env ID, or by name, or list available DBs."""
    global NOTION_DATABASE_ID
    if NOTION_DATABASE_ID:
        return NOTION_DATABASE_ID

    if NOTION_DATABASE_NAME:
        results = _search_databases(NOTION_DATABASE_NAME)
        if not results:
            print(f"❌ No databases found matching name: {NOTION_DATABASE_NAME}")
            return ""

        # prefer exact (case-insensitive) title match, else first result
        exact = None
        for db in results:
            if _extract_db_title(db).strip().lower() == NOTION_DATABASE_NAME.strip().lower():
                exact = db
                break
        chosen = exact or results[0]
        chosen_id = chosen.get("id", "").replace("-", "")
        chosen_title = _extract_db_title(chosen)
        if chosen_id:
            # Convert to dashed UUID format if necessary
            if len(chosen_id) == 32:
                dashed = f"{chosen_id[0:8]}-{chosen_id[8:12]}-{chosen_id[12:16]}-{chosen_id[16:20]}-{chosen_id[20:32]}"
            else:
                dashed = chosen.get("id", "")
            NOTION_DATABASE_ID = dashed
            print(f"✅ Selected database by name: '{chosen_title}' ({NOTION_DATABASE_ID})")
            return NOTION_DATABASE_ID
        return ""

    # No ID and no name provided: list available databases to help user choose
    results = _search_databases("")
    if not results:
        print("❌ No databases accessible to this integration. Share a database with it and retry.")
        return ""
    print("📚 Available databases (name → id):")
    for db in results[:20]:
        t = _extract_db_title(db) or "(untitled)"
        raw = db.get("id", "").replace("-", "")
        if len(raw) == 32:
            dashed = f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"
        else:
            dashed = db.get("id", "")
        print(f" - {t} → {dashed}")
    print("💡 Set NOTION_DATABASE_NAME to one of the names above, or set NOTION_DATABASE_ID directly.")
    return ""

def parse_top50_file(file_path):
    """Parse TOP50.md file and extract file information"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into individual file entries
    entries = []
    sections = content.split('---')

    for section in sections[1:]:  # Skip the header
        if not section.strip():
            continue

        # Extract information using regex patterns
        entry = {}

        # Extract rank and filename
        rank_match = re.search(r'## (\d+)\. (.+)', section)
        if rank_match:
            entry['rank'] = int(rank_match.group(1))
            entry['filename'] = rank_match.group(2)

        # Extract score
        score_match = re.search(r'\*\*Score:\*\* (\d+)', section)
        if score_match:
            entry['relevance_score'] = int(score_match.group(1))

        # Extract path
        path_match = re.search(r'\*\*Path:\*\* `([^`]+)`', section)
        if path_match:
            entry['file_path'] = path_match.group(1)

        # Extract volume
        volume_match = re.search(r'\*\*Volume:\*\* ([^\n]+)', section)
        if volume_match:
            entry['volume'] = volume_match.group(1).strip()

        # Extract size
        size_match = re.search(r'\*\*Size:\*\* ([^\n]+)', section)
        if size_match:
            entry['file_size'] = size_match.group(1).strip()

        # Extract modified date
        modified_match = re.search(r'\*\*Modified:\*\* ([^\n]+)', section)
        if modified_match:
            entry['last_modified'] = modified_match.group(1).strip()

        # Extract keywords
        keywords_match = re.search(r'\*\*Keywords:\*\* (.+)', section)
        if keywords_match:
            keywords_text = keywords_match.group(1)
            # Split by comma and clean up
            entry['keywords'] = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]

        # Extract extension
        extension_match = re.search(r'\*\*Extension:\*\* ([^\n]+)', section)
        if extension_match:
            entry['file_extension'] = extension_match.group(1).strip()

        if entry:  # Only add if we have data
            entries.append(entry)

    return entries

def create_notion_database():
    """Create a new Notion database for Golden Wings content"""
    if not NOTION_DATABASE_ID:
        print("❌ NOTION_DATABASE_ID not set. Please create a Notion database first.")
        return None

    # Check if database already exists
    try:
        response = requests.get(f"{NOTION_API_URL}/databases/{NOTION_DATABASE_ID}", headers=HEADERS)
        if response.status_code == 200:
            print("✅ Database already exists")
            return NOTION_DATABASE_ID
        elif response.status_code == 404:
            print("❌ Database not found (404). Please check:")
            print(f"   1. Database URL: https://notion.so/{NOTION_DATABASE_ID.replace('-', '')}")
            print("   2. Make sure the database is shared with your integration")
            print("   3. Verify the database ID is correct")
            return None
        else:
            print(f"❌ Database access failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        return None

def create_database_entry(entry):
    """Create or update a database entry (UPSERT)."""
    # Try to find an existing page by a stable key. Prefer File Path, fall back to File Name.
    def _find_existing_page():
        try:
            filters = []
            file_path = entry.get('file_path', '').strip()
            file_name = entry.get('filename', '').strip()

            if file_path:
                filters.append({
                    "property": "File Path",
                    "rich_text": {"equals": file_path}
                })
            if file_name:
                filters.append({
                    "property": "File Name",
                    "title": {"equals": file_name}
                })

            if not filters:
                return None

            payload = {"filter": {"and": filters}, "page_size": 1}
            resp = requests.post(
                f"{NOTION_API_URL}/databases/{NOTION_DATABASE_ID}/query",
                headers=HEADERS,
                json=payload,
                timeout=10,
            )
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                return results[0] if results else None
            return None
        except Exception:
            return None

    properties = {
        "Rank": {
            "number": entry.get('rank', 0)
        },
        "File Name": {
            "title": [{"text": {"content": entry.get('filename', 'Unknown')}}]
        },
        "Relevance Score": {
            "number": entry.get('relevance_score', 0)
        },
        "File Path": {
            "rich_text": [{"text": {"content": entry.get('file_path', '')}}]
        },
        "Volume": {
            "rich_text": [{"text": {"content": entry.get('volume', '')}}]
        },
        "File Size": {
            "rich_text": [{"text": {"content": entry.get('file_size', '')}}]
        },
        "Last Modified": {
            "rich_text": [{"text": {"content": entry.get('last_modified', '')}}]
        },
        "Extension": {
            "rich_text": [{"text": {"content": entry.get('file_extension', '')}}]
        },
        "Keywords": {
            "multi_select": [{"name": kw} for kw in entry.get('keywords', [])]
        }
    }

    # UPSERT: update existing, else create new
    existing = _find_existing_page()
    if existing and existing.get('id'):
        page_id = existing['id']
        response = requests.patch(
            f"{NOTION_API_URL}/pages/{page_id}",
            headers=HEADERS,
            json={"properties": properties},
            timeout=10,
        )
        if response.status_code == 200:
            print(f"🔁 Updated entry: {entry.get('filename', 'Unknown')}")
            return response.json()
        else:
            print(f"❌ Failed to update entry: {entry.get('filename', 'Unknown')} - {response.status_code}")
            print(response.text)
            return None

    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties
    }
    response = requests.post(f"{NOTION_API_URL}/pages", headers=HEADERS, json=data, timeout=10)
    if response.status_code == 200:
        print(f"✅ Created entry: {entry.get('filename', 'Unknown')}")
        return response.json()
    else:
        print(f"❌ Failed to create entry: {entry.get('filename', 'Unknown')} - {response.status_code}")
        print(response.text)
        return None

def test_notion_connection():
    """Test the Notion API connection"""
    print(f"   Using token: {HEADERS['Authorization'][:30]}...")
    try:
        response = requests.get(f"{NOTION_API_URL}/users", headers=HEADERS, timeout=10)
        if response.status_code == 200:
            print("✅ Notion API connection successful")
            user_data = response.json()
            bot_name = user_data.get('results', [{}])[0].get('name', 'Unknown')
            print(f"   Connected as: {bot_name}")
            return True
        else:
            print(f"❌ Notion API connection failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to Notion API: {e}")
        return False

def check_database_compatibility():
    """Check if database is compatible with the API"""
    try:
        response = requests.get(f"{NOTION_API_URL}/databases/{NOTION_DATABASE_ID}", headers=HEADERS, timeout=10)

        if response.status_code == 200:
            db_data = response.json()
            print("✅ Database structure is compatible")
            return True

        elif response.status_code == 400:
            error_data = response.json()
            error_code = error_data.get('code', 'unknown')

            if error_code == 'multiple_data_sources_for_database':
                print("❌ Database has multiple data sources (synced/linked databases)")
                print("💡 Solutions:")
                print("   1. Create a new, simple database (not synced)")
                print("   2. Or use an existing simple database without sync")
                print("   3. Copy the content to a new database")
                print(f"   🔗 Database URL: https://notion.so/{NOTION_DATABASE_ID.replace('-', '')}")
                return False
            else:
                print(f"❌ Database configuration error: {error_code}")
                print(f"   Details: {error_data.get('message', 'Unknown error')}")
                return False

        elif response.status_code == 404:
            print("❌ Database not found")
            print("💡 Please ensure:")
            print(f"   1. Database URL: https://notion.so/{NOTION_DATABASE_ID.replace('-', '')}")
            print("   2. Database is shared with your integration")
            print("   3. Database ID is correct")
            return False

        else:
            print(f"❌ Unexpected database error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False

def main():
    """Main function to parse TOP50.md and create Notion database entries"""
    print("🏆 Golden Wings Content Hunter - Notion Integration")
    print("=" * 50)

    # Check for required environment variables
    if not NOTION_SECRET:
        print("❌ NOTION_SECRET not found in environment variables")
        print("💡 Make sure to run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser")
        print("💡 Then run the set_env_vars.ps1 script")
        return

    # Resolve database target (ID or by name, or list for guidance)
    if not NOTION_DATABASE_ID:
        resolved = resolve_database_id()
        if not resolved:
            return

    # Test API connection
    print("🔌 Testing Notion API connection...")
    if not test_notion_connection():
        return

    # Check for database issues
    print("🔍 Checking database configuration...")
    if not check_database_compatibility():
        return

    # Parse TOP50.md file
    top50_file = "TOP50.md"
    if not os.path.exists(top50_file):
        print(f"❌ TOP50.md file not found at {os.path.abspath(top50_file)}")
        return

    print(f"📖 Parsing {top50_file}...")
    entries = parse_top50_file(top50_file)

    if not entries:
        print("❌ No entries found in TOP50.md")
        return

    print(f"📊 Found {len(entries)} entries to process")

    # Create database (if needed)
    print("🔧 Setting up Notion database...")
    db_id = create_notion_database()

    if not db_id:
        print("❌ Failed to access or create database")
        return

    # Create entries in batches
    print(f"📝 Creating {len(entries)} database entries...")
    successful = 0
    failed = 0

    for i, entry in enumerate(entries, 1):
        print(f"   Processing {i}/{len(entries)}: {entry.get('filename', 'Unknown')}")

        try:
            result = create_database_entry(entry)
            if result:
                successful += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Error processing entry: {e}")
            failed += 1

        # Add small delay to avoid rate limiting
        import time
        time.sleep(0.1)

    print("\n" + "=" * 50)
    print(f"🎉 Integration Complete!")
    print(f"✅ Successful entries: {successful}")
    print(f"❌ Failed entries: {failed}")
    print(f"📊 Total processed: {successful + failed}")

    if successful > 0:
        print(f"\n🔗 Your Notion database: https://notion.so/{NOTION_DATABASE_ID.replace('-', '')}")

if __name__ == "__main__":
    main()
