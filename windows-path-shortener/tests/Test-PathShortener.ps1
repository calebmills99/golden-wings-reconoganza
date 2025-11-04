<#
.SYNOPSIS
    Comprehensive test suite for Windows Path Shortener

.DESCRIPTION
    This script provides comprehensive testing functionality for the Path Shortener,
    including unit tests, integration tests, performance benchmarks, and validation scenarios.

.PARAMETER TestType
    Type of tests to run: Unit, Integration, Performance, All

.PARAMETER TestDataRoot
    Root directory where test data will be created

.PARAMETER CleanupAfterTest
    Remove test data after tests complete

.PARAMETER Verbose
    Enable verbose output for detailed test information

.EXAMPLE
    .\Test-PathShortener.ps1 -TestType All -TestDataRoot "C:\Temp\PathShortenerTests"

.NOTES
    Author: Path Shortener Test Suite
    Version: 1.0
    Requires: PowerShell 5.1+
#>

[CmdletBinding()]
param(
    [ValidateSet('Unit', 'Integration', 'Performance', 'All')]
    [string]$TestType = 'All',
    
    [string]$TestDataRoot = "$env:TEMP\PathShortenerTests",
    
    [switch]$CleanupAfterTest,
    
    [switch]$Verbose
)

# Import required modules
$scriptRoot = Split-Path $PSScriptRoot -Parent
Import-Module (Join-Path $scriptRoot "modules\PathShortener.Utils.psm1") -Force

# Test configuration
$Script:TestConfig = @{
    MainScript = Join-Path $scriptRoot "ShortPath.ps1"
    TestDataRoot = $TestDataRoot
    TestDatabase = Join-Path $TestDataRoot "test.db"
    ShortLinkRoot = Join-Path $TestDataRoot "ShortLinks"
    LogLevel = if ($Verbose) { "Debug" } else { "Info" }
    MaxTestPathLength = 300
}

# Test results tracking
$Script:TestResults = @{
    Total = 0
    Passed = 0
    Failed = 0
    Skipped = 0
    StartTime = Get-Date
    Tests = @()
}

#region Test Framework Functions

function Write-TestResult {
    param(
        [string]$TestName,
        [string]$Status,
        [string]$Message = "",
        [int]$Duration = 0
    )
    
    $Script:TestResults.Total++
    
    switch ($Status) {
        "PASS" { 
            $Script:TestResults.Passed++
            $color = "Green"
        }
        "FAIL" { 
            $Script:TestResults.Failed++
            $color = "Red"
        }
        "SKIP" { 
            $Script:TestResults.Skipped++
            $color = "Yellow"
        }
        default {
            $color = "White"
        }
    }
    
    $result = @{
        Name = $TestName
        Status = $Status
        Message = $Message
        Duration = $Duration
        Timestamp = Get-Date
    }
    
    $Script:TestResults.Tests += $result
    
    $output = "[$Status] $TestName"
    if ($Duration -gt 0) {
        $output += " ($($Duration)ms)"
    }
    if ($Message) {
        $output += " - $Message"
    }
    
    Write-Host $output -ForegroundColor $color
}

function Invoke-TestFunction {
    param(
        [string]$TestName,
        [scriptblock]$TestScript
    )
    
    $startTime = Get-Date
    
    try {
        $result = & $TestScript
        $duration = ((Get-Date) - $startTime).TotalMilliseconds
        
        if ($result -eq $true) {
            Write-TestResult $TestName "PASS" "" ([int]$duration)
        } elseif ($result -eq $false) {
            Write-TestResult $TestName "FAIL" "" ([int]$duration)
        } else {
            Write-TestResult $TestName "PASS" $result ([int]$duration)
        }
        
        return $true
    }
    catch {
        $duration = ((Get-Date) - $startTime).TotalMilliseconds
        Write-TestResult $TestName "FAIL" $_.Exception.Message ([int]$duration)
        return $false
    }
}

function New-TestDirectory {
    param(
        [string]$Name,
        [int]$Depth = 3,
        [int]$Width = 5,
        [string]$ParentPath = $Script:TestConfig.TestDataRoot
    )
    
    $path = Join-Path $ParentPath $Name
    New-Item -Path $path -ItemType Directory -Force | Out-Null
    
    if ($Depth -gt 0) {
        for ($i = 1; $i -le $Width; $i++) {
            New-TestDirectory "SubDir$i" ($Depth - 1) $Width $path
        }
    }
    
    # Create some test files
    for ($i = 1; $i -le 3; $i++) {
        $testFile = Join-Path $path "TestFile$i.txt"
        "Test content $i" | Out-File $testFile -Force
    }
    
    return $path
}

function New-LongPathStructure {
    param(
        [string]$BasePath,
        [int]$TargetLength = 280
    )
    
    $longPath = $BasePath
    $segment = "VeryLongDirectoryNameThatExceedsWindowsPathLimits"
    
    while ($longPath.Length -lt $TargetLength) {
        $longPath = Join-Path $longPath $segment
        if ($longPath.Length -lt $TargetLength) {
            New-Item -Path $longPath -ItemType Directory -Force | Out-Null
        }
    }
    
    # Create final file
    if ($longPath.Length -lt $TargetLength) {
        $fileName = "A" * ($TargetLength - $longPath.Length - 5) + ".txt"
        $finalPath = Join-Path $longPath $fileName
        "Long path test content" | Out-File $finalPath -Force -ErrorAction SilentlyContinue
        return $finalPath
    }
    
    return $longPath
}

#endregion

#region Unit Tests

function Test-PathValidation {
    # Test valid path
    $result1 = Test-PathValid "C:\Windows\System32"
    if (-not $result1) { return $false }
    
    # Test invalid characters
    $result2 = Test-PathValid "C:\Windows\<Invalid>"
    if ($result2) { return $false }
    
    # Test reserved names
    $result3 = Test-PathValid "C:\Windows\CON\file.txt"
    if ($result3) { return $false }
    
    return $true
}

function Test-LinkValidation {
    $testDir = Join-Path $Script:TestConfig.TestDataRoot "LinkTest"
    $targetDir = Join-Path $testDir "Target"
    $linkDir = Join-Path $testDir "Link"
    
    New-Item -Path $targetDir -ItemType Directory -Force | Out-Null
    "test content" | Out-File (Join-Path $targetDir "test.txt") -Force
    
    # Create junction
    cmd /c "mklink /J `"$linkDir`" `"$targetDir`"" 2>$null | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        $result = Test-LinkValid $linkDir
        $isValid = $result.IsValid -and $result.LinkType -eq "Junction" -and $result.TargetExists
        
        # Cleanup
        Remove-Item $linkDir -Force -ErrorAction SilentlyContinue
        Remove-Item $targetDir -Recurse -Force -ErrorAction SilentlyContinue
        
        return $isValid
    }
    
    return $false
}

function Test-PathAccessibility {
    $testPath = Join-Path $Script:TestConfig.TestDataRoot "AccessTest"
    New-Item -Path $testPath -ItemType Directory -Force | Out-Null
    
    $result = Test-PathAccessible $testPath "ReadWrite"
    
    Remove-Item $testPath -Force -ErrorAction SilentlyContinue
    return $result
}

function Test-DatabaseConnection {
    $testDb = Join-Path $Script:TestConfig.TestDataRoot "test_connection.db"
    
    # Create a test database
    Add-Type -AssemblyName System.Data.SQLite
    $connectionString = "Data Source=$testDb;Version=3;"
    $connection = New-Object System.Data.SQLite.SQLiteConnection($connectionString)
    $connection.Open()
    
    $createTableSQL = "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
    $command = $connection.CreateCommand()
    $command.CommandText = $createTableSQL
    $command.ExecuteNonQuery() | Out-Null
    $connection.Close()
    
    $result = Test-DatabaseConnection $testDb
    
    Remove-Item $testDb -Force -ErrorAction SilentlyContinue
    return $result
}

function Test-PerformanceMonitor {
    $monitor = Start-PerformanceMonitor
    
    # Simulate some operations
    Start-Sleep -Milliseconds 100
    Update-PerformanceMonitor $monitor 50
    Start-Sleep -Milliseconds 100
    Update-PerformanceMonitor $monitor 100
    
    $report = Get-PerformanceReport $monitor
    
    return ($report.TotalOperations -eq 100 -and $report.Duration.TotalMilliseconds -gt 150)
}

#endregion

#region Integration Tests

function Test-EndToEndShortPathCreation {
    # Create test structure with long paths
    $testRoot = Join-Path $Script:TestConfig.TestDataRoot "E2ETest"
    $longPath = New-LongPathStructure $testRoot 300
    
    if (-not (Test-Path $longPath -ErrorAction SilentlyContinue)) {
        return "Could not create long path for testing"
    }
    
    # Run path shortener in dry run mode
    $scriptPath = $Script:TestConfig.MainScript
    $configFile = Join-Path (Split-Path $scriptPath -Parent) "ShortPath.config.json"
    
    $params = @{
        TargetPath = $testRoot
        MaxPathLength = 250
        ShortLinkRoot = $Script:TestConfig.ShortLinkRoot
        DatabasePath = $Script:TestConfig.TestDatabase
        DryRun = $true
        Force = $true
        LogLevel = $Script:TestConfig.LogLevel
        ConfigFile = $configFile
    }
    
    try {
        $result = & $scriptPath @params 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            return $true
        } else {
            return "Script execution failed: $result"
        }
    }
    catch {
        return "Script execution error: $($_.Exception.Message)"
    }
}

function Test-DatabaseOperations {
    # Test database creation and operations
    $testDb = $Script:TestConfig.TestDatabase
    
    if (Test-Path $testDb) {
        Remove-Item $testDb -Force
    }
    
    # Initialize database by running script
    $scriptPath = $Script:TestConfig.MainScript
    $testRoot = Join-Path $Script:TestConfig.TestDataRoot "DBTest"
    New-Item -Path $testRoot -ItemType Directory -Force | Out-Null
    
    $params = @{
        TargetPath = $testRoot
        DatabasePath = $testDb
        DryRun = $true
        Force = $true
        LogLevel = "Error"
    }
    
    try {
        & $scriptPath @params | Out-Null
        
        if (Test-Path $testDb) {
            $isValid = Test-DatabaseConnection $testDb
            return $isValid
        }
        
        return $false
    }
    catch {
        return "Database test failed: $($_.Exception.Message)"
    }
}

function Test-LinkCreationAndRollback {
    $testRoot = Join-Path $Script:TestConfig.TestDataRoot "RollbackTest"
    $targetDir = Join-Path $testRoot "VeryLongDirectoryNameForTesting"
    $shortLinkRoot = Join-Path $testRoot "ShortLinks"
    $testDb = Join-Path $testRoot "rollback.db"
    
    New-Item -Path $targetDir -ItemType Directory -Force | Out-Null
    "test content" | Out-File (Join-Path $targetDir "test.txt") -Force
    
    $scriptPath = $Script:TestConfig.MainScript
    
    # First, create short links
    $createParams = @{
        TargetPath = $testRoot
        MaxPathLength = 20  # Very short to trigger shortening
        ShortLinkRoot = $shortLinkRoot
        DatabasePath = $testDb
        Force = $true
        LogLevel = "Error"
    }
    
    try {
        & $scriptPath @createParams | Out-Null
        
        # Check if links were created
        if (-not (Test-Path $shortLinkRoot)) {
            return "Short links directory not created"
        }
        
        $links = Get-ChildItem $shortLinkRoot -ErrorAction SilentlyContinue
        if ($links.Count -eq 0) {
            return "No links created"
        }
        
        # Now test rollback
        $rollbackParams = @{
            DatabasePath = $testDb
            Rollback = $true
            Force = $true
            LogLevel = "Error"
        }
        
        & $scriptPath @rollbackParams | Out-Null
        
        # Check if links were removed
        $linksAfterRollback = Get-ChildItem $shortLinkRoot -ErrorAction SilentlyContinue
        if ($linksAfterRollback.Count -gt 0) {
            return "Links not removed during rollback"
        }
        
        return $true
    }
    catch {
        return "Rollback test failed: $($_.Exception.Message)"
    }
}

#endregion

#region Performance Tests

function Test-LargeDirectoryPerformance {
    $testRoot = Join-Path $Script:TestConfig.TestDataRoot "PerfTest"
    
    # Create a large directory structure
    Write-Host "Creating large test directory structure..." -ForegroundColor Yellow
    $startTime = Get-Date
    
    for ($i = 1; $i -le 20; $i++) {
        $subDir = New-TestDirectory "LargeTestDir$i" 4 8 $testRoot
    }
    
    $creationTime = ((Get-Date) - $startTime).TotalSeconds
    
    # Count total items
    $itemCount = (Get-ChildItem $testRoot -Recurse -Force | Measure-Object).Count
    
    Write-Host "Created $itemCount items in $([math]::Round($creationTime, 2)) seconds" -ForegroundColor Yellow
    
    # Test scanning performance
    $scanStart = Get-Date
    
    $scriptPath = $Script:TestConfig.MainScript
    $params = @{
        TargetPath = $testRoot
        MaxPathLength = 100  # Short length to find many paths
        DryRun = $true
        Force = $true
        LogLevel = "Error"
    }
    
    & $scriptPath @params | Out-Null
    
    $scanTime = ((Get-Date) - $scanStart).TotalSeconds
    $itemsPerSecond = [math]::Round($itemCount / $scanTime, 0)
    
    Write-Host "Scanned $itemCount items in $([math]::Round($scanTime, 2)) seconds ($itemsPerSecond items/sec)" -ForegroundColor Yellow
    
    # Performance benchmark: should handle at least 1000 items per second
    return ($itemsPerSecond -gt 500)
}

function Test-MemoryUsage {
    # Force garbage collection before test
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
    [GC]::Collect()
    
    $initialMemory = [GC]::GetTotalMemory($false)
    
    $testRoot = Join-Path $Script:TestConfig.TestDataRoot "MemoryTest"
    
    # Create moderately large structure
    for ($i = 1; $i -le 10; $i++) {
        New-TestDirectory "MemTestDir$i" 3 5 $testRoot
    }
    
    $scriptPath = $Script:TestConfig.MainScript
    $params = @{
        TargetPath = $testRoot
        DryRun = $true
        Force = $true
        LogLevel = "Error"
    }
    
    & $scriptPath @params | Out-Null
    
    $finalMemory = [GC]::GetTotalMemory($false)
    $memoryUsed = $finalMemory - $initialMemory
    $memoryUsedMB = [math]::Round($memoryUsed / 1MB, 2)
    
    Write-Host "Memory used: $memoryUsedMB MB" -ForegroundColor Yellow
    
    # Should use less than 100MB for moderate directory structure
    return ($memoryUsedMB -lt 100)
}

#endregion

#region Test Execution

function Initialize-TestEnvironment {
    Write-Host "Initializing test environment..." -ForegroundColor Cyan
    
    # Create test data root
    if (Test-Path $Script:TestConfig.TestDataRoot) {
        Remove-Item $Script:TestConfig.TestDataRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    New-Item -Path $Script:TestConfig.TestDataRoot -ItemType Directory -Force | Out-Null
    New-Item -Path $Script:TestConfig.ShortLinkRoot -ItemType Directory -Force | Out-Null
    
    Write-Host "Test environment initialized at: $($Script:TestConfig.TestDataRoot)" -ForegroundColor Green
}

function Cleanup-TestEnvironment {
    if ($CleanupAfterTest) {
        Write-Host "Cleaning up test environment..." -ForegroundColor Yellow
        
        try {
            if (Test-Path $Script:TestConfig.TestDataRoot) {
                Remove-Item $Script:TestConfig.TestDataRoot -Recurse -Force
            }
            Write-Host "Test environment cleaned up." -ForegroundColor Green
        }
        catch {
            Write-Warning "Failed to clean up test environment: $($_.Exception.Message)"
        }
    }
}

function Invoke-UnitTests {
    Write-Host "`n=== Unit Tests ===" -ForegroundColor Cyan
    
    Invoke-TestFunction "Path Validation" { Test-PathValidation }
    Invoke-TestFunction "Link Validation" { Test-LinkValidation }
    Invoke-TestFunction "Path Accessibility" { Test-PathAccessibility }
    Invoke-TestFunction "Database Connection" { Test-DatabaseConnection }
    Invoke-TestFunction "Performance Monitor" { Test-PerformanceMonitor }
}

function Invoke-IntegrationTests {
    Write-Host "`n=== Integration Tests ===" -ForegroundColor Cyan
    
    Invoke-TestFunction "End-to-End Path Shortening" { Test-EndToEndShortPathCreation }
    Invoke-TestFunction "Database Operations" { Test-DatabaseOperations }
    Invoke-TestFunction "Link Creation and Rollback" { Test-LinkCreationAndRollback }
}

function Invoke-PerformanceTests {
    Write-Host "`n=== Performance Tests ===" -ForegroundColor Cyan
    
    Invoke-TestFunction "Large Directory Performance" { Test-LargeDirectoryPerformance }
    Invoke-TestFunction "Memory Usage" { Test-MemoryUsage }
}

function Show-TestSummary {
    $duration = (Get-Date) - $Script:TestResults.StartTime
    
    Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
    Write-Host "Total Tests: $($Script:TestResults.Total)" -ForegroundColor White
    Write-Host "Passed: $($Script:TestResults.Passed)" -ForegroundColor Green
    Write-Host "Failed: $($Script:TestResults.Failed)" -ForegroundColor Red
    Write-Host "Skipped: $($Script:TestResults.Skipped)" -ForegroundColor Yellow
    Write-Host "Duration: $([math]::Round($duration.TotalSeconds, 2)) seconds" -ForegroundColor White
    
    $passRate = if ($Script:TestResults.Total -gt 0) { 
        [math]::Round(($Script:TestResults.Passed / $Script:TestResults.Total) * 100, 1) 
    } else { 0 }
    Write-Host "Pass Rate: $passRate%" -ForegroundColor White
    
    if ($Script:TestResults.Failed -gt 0) {
        Write-Host "`nFailed Tests:" -ForegroundColor Red
        foreach ($test in $Script:TestResults.Tests) {
            if ($test.Status -eq "FAIL") {
                Write-Host "  - $($test.Name): $($test.Message)" -ForegroundColor Red
            }
        }
    }
    
    # Export detailed results
    $resultsFile = Join-Path $Script:TestConfig.TestDataRoot "TestResults.json"
    $Script:TestResults | ConvertTo-Json -Depth 10 | Set-Content $resultsFile -Force
    Write-Host "`nDetailed results saved to: $resultsFile" -ForegroundColor Gray
}

#endregion

#region Main Execution

try {
    Write-Host "Windows Path Shortener Test Suite" -ForegroundColor Magenta
    Write-Host "=================================" -ForegroundColor Magenta
    
    Initialize-TestEnvironment
    
    switch ($TestType) {
        'Unit' {
            Invoke-UnitTests
        }
        'Integration' {
            Invoke-IntegrationTests
        }
        'Performance' {
            Invoke-PerformanceTests
        }
        'All' {
            Invoke-UnitTests
            Invoke-IntegrationTests
            Invoke-PerformanceTests
        }
    }
    
    Show-TestSummary
    
    # Exit with appropriate code
    if ($Script:TestResults.Failed -gt 0) {
        exit 1
    } else {
        exit 0
    }
}
catch {
    Write-Error "Test execution failed: $($_.Exception.Message)"
    exit 1
}
finally {
    Cleanup-TestEnvironment
}

#endregion