# Windows Path Shortener

A comprehensive PowerShell solution for managing Windows path length limitations by automatically creating symbolic links, junctions, and hard links for paths that exceed specified length thresholds.

## Overview

Windows has historically imposed path length limitations (typically 260 characters) that can cause issues with deeply nested directory structures, long filenames, or complex project hierarchies. This tool automatically identifies paths exceeding your specified limits and creates appropriate short links to provide alternative access routes.

## Features

### Core Functionality
- **Automatic Path Discovery**: Recursively scans directory structures to identify long paths
- **Smart Link Creation**: Automatically selects optimal link types (junctions, symbolic links, hard links)
- **Hash-based Naming**: Generates collision-resistant short names using configurable hash algorithms
- **Conflict Resolution**: Handles naming conflicts with automatic suffixing
- **Database Tracking**: Complete operation history with SQLite database integration

### Safety & Reliability
- **Dry Run Mode**: Preview operations without making changes
- **Atomic Operations**: Database transactions ensure consistency
- **Rollback Capability**: Undo all operations with complete history tracking
- **Pre-flight Validation**: Comprehensive path and permission checking
- **Comprehensive Logging**: Detailed operation logs with configurable verbosity

### Performance & Scalability
- **Memory Efficient**: Optimized for large directory trees
- **Progress Reporting**: Real-time feedback during long operations
- **Configurable Batching**: Process large datasets in manageable chunks
- **Performance Monitoring**: Built-in benchmarking and statistics

## Installation

### Prerequisites
- **PowerShell 5.1 or later**
- **Windows 7 or later**
- **Administrator privileges** (required for some link types)
- **.NET Framework 4.5 or later** (for SQLite support)

### Quick Setup
1. **Download** the complete `windows-path-shortener` directory
2. **Place** the directory in your preferred location (e.g., `C:\Tools\PathShortener`)
3. **Run** the initialization command:
   ```powershell
   .\ShortPath.ps1 -TargetPath "C:\YourLongPaths" -DryRun
   ```

### Detailed Installation
1. **Clone or download** all files maintaining directory structure:
   ```
   windows-path-shortener/
   ├── ShortPath.ps1              # Main script
   ├── ShortPath.config.json      # Configuration file
   ├── modules/
   │   └── PathShortener.Utils.psm1  # Utility functions
   └── tests/
       └── Test-PathShortener.ps1     # Test suite
   ```

2. **Verify prerequisites**:
   ```powershell
   # Check PowerShell version
   $PSVersionTable.PSVersion
   
   # Test SQLite support
   Add-Type -AssemblyName System.Data.SQLite
   ```

3. **Run initial test**:
   ```powershell
   .\tests\Test-PathShortener.ps1 -TestType Unit
   ```

## Configuration

### Configuration File
The script uses `ShortPath.config.json` for default settings. Key configurations include:

```json
{
  "MaxPathLength": 200,
  "ShortLinkRoot": "C:\\ShortLinks",
  "LinkType": "Auto",
  "LogLevel": "Info",
  "ExcludePatterns": [
    "*.tmp", "*.temp", "*\\$Recycle.Bin\\*", 
    "*\\.git\\*", "*\\node_modules\\*"
  ]
}
```

### Command Line Parameters
All configuration options can be overridden via command line:

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `TargetPath` | Root directory to analyze | Current directory | `-TargetPath "C:\Projects"` |
| `MaxPathLength` | Path length threshold | 200 | `-MaxPathLength 150` |
| `ShortLinkRoot` | Where to create short links | `C:\ShortLinks` | `-ShortLinkRoot "D:\Links"` |
| `LinkType` | Preferred link type | Auto | `-LinkType Junction` |
| `DryRun` | Preview mode | False | `-DryRun` |
| `Force` | Skip confirmations | False | `-Force` |
| `Rollback` | Undo operations | False | `-Rollback` |

## Usage Examples

### Basic Usage

#### 1. Analyze Directory (Dry Run)
```powershell
.\ShortPath.ps1 -TargetPath "C:\VeryLongProjectNames" -DryRun
```
**Output Example:**
```
[INFO] Found 15 paths that need shortening.
[INFO]   Directory: 8 items
[INFO]   File: 7 items
[DRY RUN] Would create Junction: C:\ShortLinks\MyLongProject_a1b2c3d4 -> C:\VeryLongProjectNames\MyLongProjectWithExcessivelyLongName
```

#### 2. Create Short Links
```powershell
.\ShortPath.ps1 -TargetPath "C:\Projects" -MaxPathLength 150 -Force
```

#### 3. Rollback All Operations
```powershell
.\ShortPath.ps1 -Rollback -Force
```

### Advanced Usage

#### 1. Custom Configuration
```powershell
# Use specific short link location and junction preference
.\ShortPath.ps1 -TargetPath "D:\Development" -ShortLinkRoot "D:\Dev-Links" -LinkType Junction -MaxPathLength 180
```

#### 2. Batch Processing with Logging
```powershell
# Process large directory with debug logging
.\ShortPath.ps1 -TargetPath "E:\DataArchive" -LogLevel Debug -ConfigFile "E:\custom-config.json"
```

#### 3. Integration with Build Systems
```powershell
# Example: Pre-build step
$result = .\ShortPath.ps1 -TargetPath $env:BUILD_SOURCESDIRECTORY -MaxPathLength 200 -Force -LogLevel Warning
if ($LASTEXITCODE -ne 0) {
    throw "Path shortening failed: $result"
}
```

### Real-World Scenarios

#### Scenario 1: Node.js Projects with Deep Dependencies
```powershell
# Handle node_modules path issues
.\ShortPath.ps1 -TargetPath "C:\WebProjects" -MaxPathLength 200 -ExcludePatterns @("*\\node_modules\\*", "*.log") -Force
```

#### Scenario 2: Git Repository with Long Branch Names
```powershell
# Shorten paths but preserve .git integrity
.\ShortPath.ps1 -TargetPath "C:\GitRepos" -MaxPathLength 180 -ExcludePatterns @("*\\.git\\*") -LinkType SymbolicLink
```

#### Scenario 3: Archive Migration
```powershell
# Create shortcuts for archived projects before moving to new drive
.\ShortPath.ps1 -TargetPath "D:\Archives" -ShortLinkRoot "C:\QuickAccess" -MaxPathLength 100 -Force

# Later, rollback if needed
.\ShortPath.ps1 -Rollback -DatabasePath "D:\Archives\PathShortener.db" -Force
```

## Link Types

### Automatic Selection (Recommended)
When `LinkType` is set to `Auto`, the script chooses the optimal link type:

| Scenario | Selected Link Type | Reason |
|----------|-------------------|--------|
| Directory, same volume | Junction | Best performance, no elevation required |
| File, same volume | Hard Link | Transparent to applications |
| Cross-volume | Symbolic Link | Only option for different drives |

### Manual Selection
You can force specific link types:

```powershell
# Force junctions for all directories
.\ShortPath.ps1 -TargetPath "C:\Projects" -LinkType Junction

# Force symbolic links (requires elevation)
.\ShortPath.ps1 -TargetPath "C:\Projects" -LinkType SymbolicLink
```

### Link Type Characteristics
| Type | Directories | Files | Cross-Volume | Admin Required | Notes |
|------|-------------|-------|--------------|----------------|-------|
| **Junction** | ✅ | ❌ | ❌ | ❌ | Fastest, most compatible |
| **Symbolic Link** | ✅ | ✅ | ✅ | ✅* | Most flexible |
| **Hard Link** | ❌ | ✅ | ❌ | ❌ | Transparent to apps |

*Admin required by default, can be changed in Windows 10 Developer Mode

## Database Operations

### Database Schema
The script maintains a SQLite database with three main tables:

#### Operations Table
```sql
CREATE TABLE operations (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    source_path TEXT NOT NULL,
    target_path TEXT,
    link_type TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    rollback_data TEXT
);
```

#### Path Mappings Table
```sql
CREATE TABLE path_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL,
    original_path TEXT NOT NULL,
    short_path TEXT NOT NULL,
    hash_value TEXT NOT NULL,
    created_timestamp TEXT NOT NULL
);
```

### Database Queries
```powershell
# Import utility module
Import-Module .\modules\PathShortener.Utils.psm1

# Export database report
Export-DatabaseReport -DatabasePath ".\PathShortener.db" -OutputPath "report.html" -Format HTML

# Check database health
Test-DatabaseConnection -DatabasePath ".\PathShortener.db"
```

## Testing

### Running Tests
```powershell
# Run all tests
.\tests\Test-PathShortener.ps1 -TestType All

# Run specific test categories
.\tests\Test-PathShortener.ps1 -TestType Unit
.\tests\Test-PathShortener.ps1 -TestType Integration
.\tests\Test-PathShortener.ps1 -TestType Performance

# Custom test directory
.\tests\Test-PathShortener.ps1 -TestDataRoot "C:\Temp\MyTests" -CleanupAfterTest
```

### Test Categories

#### Unit Tests
- Path validation functions
- Link creation and validation
- Database connectivity
- Configuration loading

#### Integration Tests
- End-to-end path shortening
- Database operations
- Rollback functionality

#### Performance Tests
- Large directory handling (20,000+ files)
- Memory usage monitoring
- Processing speed benchmarks

## Troubleshooting

### Common Issues

#### 1. "Access Denied" Errors
**Problem**: Cannot create symbolic links
**Solution**: 
```powershell
# Run as Administrator, or enable Developer Mode (Windows 10+)
# Or use junctions instead:
.\ShortPath.ps1 -LinkType Junction
```

#### 2. "Path Too Long" During Scanning
**Problem**: Script cannot access some paths due to length
**Solution**:
```powershell
# Use shorter intermediate paths or UNC format
.\ShortPath.ps1 -TargetPath "\\?\C:\VeryLongPath"
```

#### 3. Database Lock Errors
**Problem**: Database locked by another process
**Solution**:
```powershell
# Close other PowerShell sessions or specify different database
.\ShortPath.ps1 -DatabasePath "C:\Temp\PathShortener_$(Get-Date -Format 'yyyyMMdd').db"
```

#### 4. Links Point to Wrong Locations
**Problem**: Relative paths in links
**Solution**:
```powershell
# Verify with link validation
Import-Module .\modules\PathShortener.Utils.psm1
Test-LinkValid "C:\ShortLinks\MyLink_12345"

# Use absolute paths in configuration
$Script:Config.ShortLinkRoot = "C:\ShortLinks"  # Not .\ShortLinks
```

### Performance Optimization

#### Large Directory Structures
```powershell
# Process in smaller batches
.\ShortPath.ps1 -TargetPath "C:\BigProject" -MaxOperationsPerBatch 500

# Enable parallel processing (if available)
# Edit config: "UseParallelProcessing": true
```

#### Memory Management
```powershell
# Monitor memory usage during operation
.\tests\Test-PathShortener.ps1 -TestType Performance -Verbose

# Use shorter exclusion patterns to reduce processing
# Edit config: "ExcludePatterns": ["*.tmp", "*\\.git\\*"]
```

### Logging and Debugging

#### Enable Detailed Logging
```powershell
# Maximum verbosity
.\ShortPath.ps1 -LogLevel Debug -Verbose

# Log to specific file
# Logs automatically saved to: logs\ShortPath_YYYYMMDD_HHMMSS.log
```

#### Analyze Log Files
```powershell
# Search for errors
Select-String -Path "logs\*.log" -Pattern "\[ERROR\]"

# Count operations
Select-String -Path "logs\*.log" -Pattern "Created.*link" | Measure-Object
```

## Architecture

### Design Principles
1. **Safety First**: All operations are reversible and logged
2. **Performance**: Optimized for large directory structures
3. **Flexibility**: Configurable behavior for different scenarios
4. **Reliability**: Comprehensive error handling and validation
5. **Maintainability**: Modular design with clear separation of concerns

### Module Structure
- **ShortPath.ps1**: Main orchestration and CLI interface
- **PathShortener.Utils.psm1**: Core utility functions
- **ShortPath.config.json**: Configuration management
- **Test-PathShortener.ps1**: Comprehensive test suite

### Key Algorithms

#### Hash-based Naming
```powershell
function Get-PathHash {
    param([string]$Path)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Path.ToLowerInvariant())
    $hash = $sha256.ComputeHash($bytes)
    return [System.BitConverter]::ToString($hash).Replace("-", "").Substring(0, 8)
}
```

#### Conflict Resolution
```powershell
# Automatic suffix generation for naming conflicts
if (Test-Path $shortPath) {
    $counter = 1
    do {
        $shortPath = "${basePath}_${counter}"
        $counter++
    } while (Test-Path $shortPath -and $counter -lt 100)
}
```

## Contributing

### Development Setup
1. Fork the repository
2. Create feature branch
3. Run tests: `.\tests\Test-PathShortener.ps1 -TestType All`
4. Make changes
5. Run tests again
6. Submit pull request

### Code Standards
- Use PowerShell approved verbs
- Include comprehensive help documentation
- Add unit tests for new functions
- Follow existing error handling patterns
- Use Write-Log for all output

## License

This project is provided as-is for educational and practical use. Feel free to modify and distribute according to your needs.

## Version History

### v1.0 (Current)
- Initial release
- Core path shortening functionality
- SQLite database integration
- Comprehensive test suite
- Full rollback capability
- Performance optimizations

## Support

For issues and questions:
1. Check this README for common solutions
2. Run diagnostic tests: `.\tests\Test-PathShortener.ps1 -TestType Unit`
3. Enable debug logging: `.\ShortPath.ps1 -LogLevel Debug`
4. Review log files in the `logs` directory

## Best Practices

### Before Using in Production
1. **Test thoroughly** with `-DryRun` first
2. **Backup important data** before making changes
3. **Use version control** for configuration files
4. **Monitor disk space** in short link locations
5. **Document custom configurations** for team use

### Maintenance
```powershell
# Regular health checks
Test-DatabaseConnection -DatabasePath ".\PathShortener.db"
Get-LinkStatistics -Path "C:\ShortLinks" -Recursive

# Cleanup orphaned links
Remove-OrphanedLinks -Path "C:\ShortLinks" -WhatIf
```

### Integration Examples
```powershell
# CI/CD Pipeline integration
- name: Shorten Build Paths
  run: |
    .\ShortPath.ps1 -TargetPath ${{ github.workspace }} -Force -LogLevel Warning
    if ($LASTEXITCODE -ne 0) { exit 1 }

# Scheduled maintenance
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File C:\Tools\PathShortener\ShortPath.ps1 -TargetPath C:\Projects -Force"
Register-ScheduledTask -TaskName "PathShortener" -Trigger $trigger -Action $action
```