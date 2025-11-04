# 🏆 Golden Wings Content Hunter - Notion AI Integration Guide

This guide provides comprehensive instructions for integrating your Golden Wings documentary content with Notion using AI automation.

## 🎯 Overview

The Golden Wings Content Hunter automatically finds, ranks, and imports your documentary files into a Notion database. It processes your content library and creates organized, searchable entries with relevance scoring.

## 🚀 Quick Start

### 1. Prerequisites
- ✅ Content Hunter script (already configured)
- ✅ TOP50.md file with ranked content
- ✅ Notion account and workspace
- ✅ Notion API integration token

### 2. One-Command Setup
```bash
cd D:\golden-wings-reconoganza
python notion_integration.py
```

## 📋 Detailed Setup Instructions

### Step 1: Get Your Notion API Token

1. **Visit Notion Developers**: https://developers.notion.com/
2. **Create New Integration**:
   - Click **"New integration"**
   - Name: `Golden Wings Content Hunter`
   - Description: `AI-powered documentary content management`
   - Choose **"Internal integration"**
3. **Copy Integration Token**:
   - Look for **"Internal Integration Token"**
   - Format: `ntn_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Important**: This token starts with `ntn_` (not `secret_`)

### Step 2: Update Environment Configuration

**Option A: Using .env file**
```bash
# Edit your .env file
export NOTION_SECRET="ntn_YOUR_TOKEN_HERE"
export NOTION_DATABASE_ID="27a61556bff380fd9a07c7d754aedeb8"
```

**Option B: Using PowerShell (recommended)**
```powershell
# Run this in PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\set_env_vars.ps1
```

### Step 3: Create or Configure Notion Database

#### Option A: Create New Database
1. **Open Notion** in your browser
2. **Create new database** (use **"Table"** view)
3. **Set database title**: `Golden Wings Content Library`
4. **Configure columns**:
   - **File Name** (Title field)
   - **Rank** (Number)
   - **Relevance Score** (Number)
   - **File Path** (Text)
   - **Volume** (Text)
   - **File Size** (Text)
   - **Last Modified** (Text)
   - **Extension** (Text)
   - **Keywords** (Multi-select)

#### Option B: Use Existing Database
1. **Open your existing database**
2. **Copy the Database ID** from the URL
3. **Ensure it has the required columns** (see above)

### Step 4: Share Database with Integration

1. **Open your Golden Wings database**
2. **Click "..."** (three dots, top right)
3. **Select "Add connections"**
4. **Search for**: `Golden Wings Content Hunter`
5. **Click "Confirm"** to share access

### Step 5: Test Integration

```bash
# Test the connection
python notion_integration.py
```

**Expected Output:**
```
🏆 Golden Wings Content Hunter - Notion Integration
==================================================
🔌 Testing Notion API connection...
   Using token: Bearer ntn_261278105479IRWlAo9...
✅ Notion API connection successful
   Connected as: THE COLLECTIVE
📖 Parsing TOP50.md...
📊 Found 50 entries to process
🔧 Setting up Notion database...
✅ Database already exists
📝 Creating 50 database entries...
✅ Created entry: golden-wings-history.txt
✅ Created entry: CONTENT-SUMMARY.md
...
✅ SUCCESS! All entries imported
```

## 🎮 Usage Commands

### Basic Workflow
```bash
# Complete workflow (hunt + import)
python notion_integration.py

# Or use npm scripts
npm run notion
```

### Individual Steps
```bash
# 1. Hunt for content (creates TOP50.md)
npm run hunt

# 2. Import to Notion
npm run notion

# 3. Full workflow automation
python workflow.py
```

## 📊 Database Structure

Your Notion database will contain:

| Column | Type | Description |
|--------|------|-------------|
| **File Name** | Title | Name of the content file |
| **Rank** | Number | Position in relevance ranking (1-50) |
| **Relevance Score** | Number | AI-calculated relevance score |
| **File Path** | Text | Full system path to file |
| **Volume** | Text | Drive/storage location |
| **File Size** | Text | File size in KB/MB |
| **Last Modified** | Text | When file was last updated |
| **Extension** | Text | File type (.txt, .md, .mp4, etc.) |
| **Keywords** | Multi-select | Relevant tags for filtering |

## 🔍 Advanced Features

### Filtering and Views
Create custom Notion views:
- **By Relevance**: Sort by score (highest first)
- **By File Type**: Group by extension
- **By Volume**: Filter by storage location
- **By Keywords**: Multi-select filtering

### Visual Indicators
- **Score Bars**: `████████` visual representation
- **Color Coding**: High scores = green, medium = yellow
- **Icons**: File type icons for easy recognition

## 🛠️ Troubleshooting

### Common Issues

#### 1. "API token is invalid" (401)
**Solution**: Verify your token format
```bash
# Check token starts with ntn_
python -c "import os; token=os.getenv('NOTION_SECRET'); print('Format:', token[:10])"
```

#### 2. "Database not found" (404)
**Solution**: Check database sharing
1. Open database in Notion
2. Click `...` → **"Add connections"**
3. Find your integration and confirm

#### 3. "Database access failed"
**Solution**: Verify database permissions
- Ensure integration has **"Edit"** permissions
- Check if database is in a shared workspace

### Debug Mode
```bash
# Run with verbose output
python -c "
import requests, os
token = os.getenv('NOTION_SECRET')
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
response = requests.get('https://api.notion.com/v1/users', headers=headers)
print('Status:', response.status_code)
print('Response:', response.text[:200])
"
```

## 🔄 Automation

### Scheduled Updates
Set up automatic updates using Windows Task Scheduler:

1. **Create Task**:
   - Name: `Golden Wings Content Update`
   - Trigger: Daily at 2 AM
   - Action: Run `python D:\golden-wings-reconoganza\notion_integration.py`

2. **PowerShell Script**:
   ```powershell
   cd "D:\golden-wings-reconoganza"
   python notion_integration.py
   ```

### Batch Processing
```bash
# Process multiple workspaces
python workflow.py --workspace "D:\Film Projects\Golden Wings"
python workflow.py --workspace "F:\Archive\Documentary"
```

## 📈 Analytics & Insights

### Content Analysis
Your database provides insights into:
- **Content Distribution**: Files by type and location
- **Relevance Patterns**: High-scoring content themes
- **Storage Optimization**: File sizes and locations
- **Update Frequency**: Modification patterns

### AI-Powered Features
- **Smart Ranking**: Relevance-based scoring
- **Auto-tagging**: Keyword extraction
- **Duplicate Detection**: Identifies redundant files
- **Content Relationships**: Linked file connections

## 🎯 Best Practices

### Database Management
- **Regular Backups**: Export database periodically
- **Archive Old Entries**: Move outdated content
- **Custom Properties**: Add project-specific fields
- **Template Pages**: Create entry templates

### Content Strategy
- **Priority Lists**: Focus on high-relevance content
- **Project Planning**: Use for production scheduling
- **Team Collaboration**: Share database with collaborators
- **Progress Tracking**: Monitor content discovery

## 🔗 Integration Examples

### Project Planning View
```notion
Filter: Relevance Score > 15
Sort: Last Modified (descending)
Group: File Type
```

### Archive Management View
```notion
Filter: Volume = "Archive Drive"
Sort: File Size (descending)
Group: Extension
```

### Research View
```notion
Filter: Keywords contains "interview" OR "transcript"
Sort: Relevance Score (descending)
```

## 🚨 Security Notes

- **Token Security**: Never share your integration token
- **Database Privacy**: Set appropriate sharing permissions
- **Access Control**: Limit who can edit the database
- **Regular Reviews**: Audit database access periodically

## 📞 Support

### Getting Help
1. **Check this guide** for common solutions
2. **Test API connection** before database operations
3. **Verify permissions** for database access
4. **Review logs** for detailed error information

### Common Questions
- **Q: Why can't I see my database?**
  - A: Check sharing permissions and database URL

- **Q: How do I update content?**
  - A: Run the integration script again

- **Q: Can I customize the database?**
  - A: Yes, add custom properties as needed

---

## 🎉 Success Checklist

- [ ] ✅ API token configured (ntn_ format)
- [ ] ✅ Database created/shared with integration
- [ ] ✅ Test connection successful (status 200)
- [ ] ✅ First 50 entries imported
- [ ] ✅ Database customized for your workflow
- [ ] ✅ Team members invited (if applicable)

---

**Happy content hunting! 🎬✨**

*Generated by Golden Wings Content Hunter AI*
