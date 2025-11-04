#!/usr/bin/env python3
"""
Golden Wings Content Hunter - Complete Workflow
Runs content hunting and Notion integration in one command
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    print(f"   Command: {command}")

    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"   Error: {e.stderr}")
        return False

def main():
    """Main workflow function"""
    print("🚀 Golden Wings Content Hunter - Complete Workflow")
    print("=" * 60)

    # Step 1: Check if TOP50.md exists (from previous run)
    top50_file = Path("TOP50.md")
    if top50_file.exists():
        print("📋 Found existing TOP50.md file")
        response = input("   Run fresh content hunt? (y/N): ").lower().strip()
        if response != 'y':
            print("⏭️  Skipping content hunt, using existing TOP50.md")
            skip_hunt = True
        else:
            skip_hunt = False
    else:
        print("📋 No existing TOP50.md found")
        skip_hunt = False

    # Step 2: Run content hunter if needed
    if not skip_hunt:
        success = run_command("node content-hunter-fixed.js", "Content Hunting")
        if not success:
            print("❌ Content hunting failed. Cannot proceed with Notion integration.")
            return 1

    # Step 3: Check for Notion credentials
    notion_secret = os.getenv('NOTION_SECRET')
    notion_db_id = os.getenv('NOTION_DATABASE_ID')

    if not notion_secret:
        print("❌ NOTION_SECRET not found in environment variables")
        print("💡 Please run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser")
        print("💡 Then run: .\\scripts\\set_env_vars.ps1")
        return 1

    if not notion_db_id:
        print("❌ NOTION_DATABASE_ID not set")
        print("💡 Please create a Notion database and set its ID in the .env file")
        print("💡 Database ID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        return 1

    # Step 4: Run Notion integration
    success = run_command("python notion_integration.py", "Notion Database Integration")
    if not success:
        return 1

    # Step 5: Summary
    print("\n" + "=" * 60)
    print("🎉 Workflow Complete!")
    print("✅ Content hunt completed")
    print("✅ Notion database populated")
    print("🔗 Check your Notion workspace for the new database")

    # Show next steps
    print("\n📋 Next Steps:")
    print("1. Open Notion and locate your Golden Wings Content database")
    print("2. Customize the database view and properties as needed")
    print("3. Share the database with your team if desired")
    print("4. Run this workflow periodically to keep content updated")

    print("\n🔄 Quick Commands:")
    print("   npm run hunt        - Run content hunt only")
    print("   npm run notion      - Update Notion database only")
    print("   npm run workflow    - Run complete workflow")

    return 0

if __name__ == "__main__":
    sys.exit(main())
