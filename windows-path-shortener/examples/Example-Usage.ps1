<#
.SYNOPSIS
    Example usage scenarios for Windows Path Shortener

.DESCRIPTION
    This script demonstrates practical implementation patterns and common use cases
    for the Windows Path Shortener tool across different scenarios.

.NOTES
    Author: Path Shortener Examples
    Version: 1.0
    Run these examples from the windows-path-shortener directory
#>

# Get script root directory
$ScriptRoot = Split-Path $PSScriptRoot -Parent
$MainScript = Join-Path $ScriptRoot "ShortPath.ps1"

Write-Host "Windows Path Shortener - Example Usage Scenarios" -ForegroundColor Magenta
Write-Host "=================================================" -ForegroundColor Magenta

#region Example 1: Basic Directory Analysis

Write-Host "`n=== Example 1: Basic Directory Analysis ===" -ForegroundColor Cyan
Write-Host "Scenario: Analyze a directory for long paths without making changes" -ForegroundColor Yellow

$ExampleCommand1 = @"
# Analyze current directory for paths longer than 200 characters
& '$MainScript' -TargetPath . -MaxPathLength 200 -DryRun -LogLevel Info

# Key benefits:
# - Safe preview mode
# - No changes made to filesystem
# - Clear visibility of what would be affected
"@

Write-Host $ExampleCommand1 -ForegroundColor Gray

Write-Host "`nTo run this example:" -ForegroundColor Green
Write-Host "& `"$MainScript`" -TargetPath . -MaxPathLength 200 -DryRun" -ForegroundColor White

#endregion

#region Example 2: Development Project Management

Write-Host "`n=== Example 2: Development Project Management ===" -ForegroundColor Cyan
Write-Host "Scenario: Managing long paths in software development projects" -ForegroundColor Yellow

$ExampleCommand2 = @"
# Handle typical development issues
& '$MainScript' -TargetPath "C:\Development\Projects" ``
    -MaxPathLength 180 ``
    -ShortLinkRoot "C:\DevLinks" ``
    -LinkType Junction ``
    -Force ``
    -ConfigFile "dev-config.json"

# Create custom configuration for development:
@{
    MaxPathLength = 180
    ShortLinkRoot = "C:\DevLinks"
    LinkType = "Junction"
    ExcludePatterns = @(
        "*\.git\*"          # Preserve Git integrity
        "*\node_modules\*"  # Skip npm dependencies
        "*\bin\Debug\*"     # Skip build outputs
        "*\bin\Release\*"
        "*\obj\*"
        "*.tmp"
        "*.log"
    )
    LinkPreferences = @{
        Directory = "Junction"
        File = "HardLink"
        CrossVolume = "SymbolicLink"
    }
} | ConvertTo-Json -Depth 3 | Set-Content "dev-config.json"
"@

Write-Host $ExampleCommand2 -ForegroundColor Gray

#endregion

#region Example 3: Archive and Backup Scenarios

Write-Host "`n=== Example 3: Archive and Backup Management ===" -ForegroundColor Cyan
Write-Host "Scenario: Creating accessible shortcuts for archived content" -ForegroundColor Yellow

$ExampleCommand3 = @"
# Create quick access links for archived projects
& '$MainScript' -TargetPath "D:\Archives\OldProjects" ``
    -ShortLinkRoot "C:\QuickAccess\Archives" ``
    -MaxPathLength 100 ``
    -LinkType SymbolicLink ``
    -Force

# Later, when archives are moved, rollback the links
& '$MainScript' -Rollback -DatabasePath "D:\Archives\OldProjects\PathShortener.db" -Force

# Export report before rollback for documentation
Import-Module '$ScriptRoot\modules\PathShortener.Utils.psm1'
Export-DatabaseReport -DatabasePath "PathShortener.db" ``
    -OutputPath "archive-migration-report.html" ``
    -Format HTML
"@

Write-Host $ExampleCommand3 -ForegroundColor Gray

#endregion

#region Example 4: CI/CD Pipeline Integration

Write-Host "`n=== Example 4: CI/CD Pipeline Integration ===" -ForegroundColor Cyan
Write-Host "Scenario: Automated path management in build pipelines" -ForegroundColor Yellow

$ExampleCommand4 = @"
# Pre-build step: Ensure build paths are manageable
try {
    & '$MainScript' -TargetPath `$env:BUILD_SOURCESDIRECTORY ``
        -MaxPathLength 200 ``
        -Force ``
        -LogLevel Warning
    
    if (`$LASTEXITCODE -ne 0) {
        throw "Path shortening failed with exit code `$LASTEXITCODE"
    }
    
    Write-Host "✓ Build paths optimized successfully" -ForegroundColor Green
}
catch {
    Write-Error "❌ Failed to optimize build paths: `$(`$_.Exception.Message)"
    exit 1
}

# Post-build cleanup (optional)
& '$MainScript' -Rollback -Force -LogLevel Error
"@

Write-Host $ExampleCommand4 -ForegroundColor Gray

#endregion

#region Example 5: Maintenance and Monitoring

Write-Host "`n=== Example 5: System Maintenance and Monitoring ===" -ForegroundColor Cyan
Write-Host "Scenario: Regular maintenance and health monitoring" -ForegroundColor Yellow

$ExampleCommand5 = @"
# Weekly maintenance script
Import-Module '$ScriptRoot\modules\PathShortener.Utils.psm1'

# Check database health
if (-not (Test-DatabaseConnection -DatabasePath ".\PathShortener.db")) {
    Write-Warning "Database health check failed"
}

# Generate status report
Export-DatabaseReport -DatabasePath ".\PathShortener.db" ``
    -OutputPath "weekly-report-`$(Get-Date -Format 'yyyyMMdd').html" ``
    -Format HTML

# Check for orphaned links
`$orphaned = Remove-OrphanedLinks -Path "C:\ShortLinks" -Recursive -WhatIf
if (`$orphaned.Count -gt 0) {
    Write-Host "Found `$(`$orphaned.Count) orphaned links that need cleanup" -ForegroundColor Yellow
}

# Get link statistics
`$stats = Get-LinkStatistics -Path "C:\ShortLinks" -Recursive
Write-Host "Link Statistics:" -ForegroundColor Green
Write-Host "  Total Links: `$(`$stats.TotalLinks)" -ForegroundColor White
Write-Host "  Valid Links: `$(`$stats.ValidLinks)" -ForegroundColor White
Write-Host "  Broken Links: `$(`$stats.BrokenLinks)" -ForegroundColor White
"@

Write-Host $ExampleCommand5 -ForegroundColor Gray

#endregion

#region Example 6: Advanced Configuration Scenarios

Write-Host "`n=== Example 6: Advanced Configuration Management ===" -ForegroundColor Cyan
Write-Host "Scenario: Environment-specific configurations" -ForegroundColor Yellow

$ExampleCommand6 = @"
# Production configuration
`$ProdConfig = @{
    MaxPathLength = 200
    ShortLinkRoot = "E:\ProductionLinks"
    DatabasePath = "E:\PathShortener\production.db"
    LinkType = "Junction"
    LogLevel = "Warning"
    ExcludePatterns = @(
        "*.tmp", "*.temp", "*\$Recycle.Bin\*",
        "*\System Volume Information\*"
    )
    BackupEnabled = `$true
    MaxOperationsPerBatch = 500
    AdvancedSettings = @{
        ValidateLinksAfterCreation = `$true
        CleanupOrphanedLinks = `$true
        MaxRetryAttempts = 3
    }
} | ConvertTo-Json -Depth 3 | Set-Content "production-config.json"

# Development configuration  
`$DevConfig = @{
    MaxPathLength = 150
    ShortLinkRoot = "C:\DevLinks"
    DatabasePath = ".\dev-pathshortener.db"
    LinkType = "Auto"
    LogLevel = "Debug"
    ExcludePatterns = @(
        "*\.git\*", "*\node_modules\*", "*\bin\*", "*\obj\*",
        "*.tmp", "*.log", "*\.vs\*"
    )
    BackupEnabled = `$true
    MaxOperationsPerBatch = 1000
    PerformanceSettings = @{
        UseParallelProcessing = `$true
        MaxParallelJobs = 4
    }
} | ConvertTo-Json -Depth 3 | Set-Content "dev-config.json"

# Use environment-specific config
& '$MainScript' -TargetPath "C:\Projects" -ConfigFile "dev-config.json" -Force
"@

Write-Host $ExampleCommand6 -ForegroundColor Gray

#endregion

#region Example 7: Disaster Recovery

Write-Host "`n=== Example 7: Disaster Recovery and Backup ===" -ForegroundColor Cyan
Write-Host "Scenario: Backing up and restoring link configurations" -ForegroundColor Yellow

$ExampleCommand7 = @"
# Before major changes - backup current state
Import-Module '$ScriptRoot\modules\PathShortener.Utils.psm1'

# Export current database
Export-DatabaseReport -DatabasePath ".\PathShortener.db" ``
    -OutputPath "backup-`$(Get-Date -Format 'yyyyMMdd-HHmmss').json" ``
    -Format JSON

# Copy database file
Copy-Item ".\PathShortener.db" ".\PathShortener-backup-`$(Get-Date -Format 'yyyyMMdd').db"

# Export link list for manual recreation if needed
Get-ChildItem "C:\ShortLinks" -Recurse | Where-Object { 
    `$_.Attributes -band [System.IO.FileAttributes]::ReparsePoint 
} | ForEach-Object {
    [PSCustomObject]@{
        LinkPath = `$_.FullName
        Target = `$_.Target
        LinkType = if (`$_.PSIsContainer) { "Junction/DirSymLink" } else { "FileSymLink" }
        Created = `$_.CreationTime
    }
} | Export-Csv "link-inventory-`$(Get-Date -Format 'yyyyMMdd').csv" -NoTypeInformation

Write-Host "✓ Backup completed - database, inventory, and configuration saved" -ForegroundColor Green
"@

Write-Host $ExampleCommand7 -ForegroundColor Gray

#endregion

#region Example 8: Performance Testing

Write-Host "`n=== Example 8: Performance Testing and Optimization ===" -ForegroundColor Cyan
Write-Host "Scenario: Benchmarking and performance monitoring" -ForegroundColor Yellow

$ExampleCommand8 = @"
# Run comprehensive performance tests
& '$ScriptRoot\tests\Test-PathShortener.ps1' -TestType Performance -Verbose

# Custom performance monitoring
Import-Module '$ScriptRoot\modules\PathShortener.Utils.psm1'

`$monitor = Start-PerformanceMonitor

# Simulate large operation
for (`$i = 1; `$i -le 1000; `$i++) {
    Update-PerformanceMonitor `$monitor `$i
    if (`$i % 100 -eq 0) {
        `$report = Get-PerformanceReport `$monitor
        Write-Host "Progress: `$i operations, `$([math]::Round(`$report.OperationsPerSecond, 1)) ops/sec" -ForegroundColor Yellow
    }
    Start-Sleep -Milliseconds 10  # Simulate work
}

`$finalReport = Get-PerformanceReport `$monitor
Write-Host "Final Performance Report:" -ForegroundColor Green
Write-Host "  Operations: `$(`$finalReport.TotalOperations)" -ForegroundColor White
Write-Host "  Duration: `$([math]::Round(`$finalReport.Duration.TotalSeconds, 2)) seconds" -ForegroundColor White
Write-Host "  Rate: `$([math]::Round(`$finalReport.OperationsPerSecond, 1)) ops/sec" -ForegroundColor White
Write-Host "  Memory: `$(`$finalReport.PeakMemoryMB) MB" -ForegroundColor White
"@

Write-Host $ExampleCommand8 -ForegroundColor Gray

#endregion

Write-Host "`n=== Getting Started ===" -ForegroundColor Cyan
Write-Host "1. First, run a simple test:" -ForegroundColor Yellow
Write-Host "   & `"$MainScript`" -TargetPath . -DryRun" -ForegroundColor White

Write-Host "`n2. Run the test suite to verify installation:" -ForegroundColor Yellow
Write-Host "   & `"$(Join-Path $ScriptRoot "tests\Test-PathShortener.ps1")`" -TestType Unit" -ForegroundColor White

Write-Host "`n3. Create your first short links:" -ForegroundColor Yellow
Write-Host "   & `"$MainScript`" -TargetPath `"C:\YourLongPaths`" -MaxPathLength 200 -Force" -ForegroundColor White

Write-Host "`n4. Check the results:" -ForegroundColor Yellow
Write-Host "   Get-ChildItem C:\ShortLinks" -ForegroundColor White

Write-Host "`nFor more examples and detailed documentation, see README.md" -ForegroundColor Green
Write-Host "Happy path shortening! 🔗" -ForegroundColor Magenta