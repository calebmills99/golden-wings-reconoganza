<#
.SYNOPSIS
    Utility functions module for Windows Path Shortener

.DESCRIPTION
    This module provides utility functions for path validation, link testing,
    performance monitoring, and other supporting functionality for the main
    Path Shortener script.

.NOTES
    Author: Path Shortener Script
    Version: 1.1
    Requires: PowerShell 5.1+
    Database: Pure PowerShell JSON-based storage (no external dependencies)
#>

# Module variables
$Script:ModuleConfig = $null

#region Path Validation Functions

function Test-PathValid {
    <#
    .SYNOPSIS
        Validates if a path is valid for Windows filesystem
    
    .PARAMETER Path
        Path to validate
    
    .RETURNS
        Boolean indicating if path is valid
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )
    
    try {
        # Check for invalid characters
        $invalidChars = [System.IO.Path]::GetInvalidPathChars()
        foreach ($char in $invalidChars) {
            if ($Path.Contains($char)) {
                Write-Verbose "Path contains invalid character: $char"
                return $false
            }
        }
        
        # Check path length
        if ($Path.Length -gt 32767) {
            Write-Verbose "Path exceeds maximum length: $($Path.Length)"
            return $false
        }
        
        # Check for reserved names
        $reservedNames = @('CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9')
        $pathParts = $Path.Split([System.IO.Path]::DirectorySeparatorChar)
        
        foreach ($part in $pathParts) {
            if ($part -in $reservedNames) {
                Write-Verbose "Path contains reserved name: $part"
                return $false
            }
        }
        
        return $true
    }
    catch {
        Write-Verbose "Path validation failed: $($_.Exception.Message)"
        return $false
    }
}

function Test-PathAccessible {
    <#
    .SYNOPSIS
        Tests if a path is accessible with current permissions
    
    .PARAMETER Path
        Path to test
    
    .PARAMETER AccessType
        Type of access to test: Read, Write, ReadWrite
    
    .RETURNS
        Boolean indicating if path is accessible
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        
        [ValidateSet('Read', 'Write', 'ReadWrite')]
        [string]$AccessType = 'Read'
    )
    
    try {
        if (-not (Test-Path $Path)) {
            return $false
        }
        
        $item = Get-Item $Path -Force -ErrorAction Stop
        $acl = Get-Acl $Path -ErrorAction Stop
        
        # Test read access
        if ($AccessType -eq 'Read' -or $AccessType -eq 'ReadWrite') {
            try {
                if ($item.PSIsContainer) {
                    Get-ChildItem $Path -Force -ErrorAction Stop | Select-Object -First 1 | Out-Null
                } else {
                    [System.IO.File]::OpenRead($Path).Close()
                }
            }
            catch {
                Write-Verbose "Read access test failed: $($_.Exception.Message)"
                return $false
            }
        }
        
        # Test write access
        if ($AccessType -eq 'Write' -or $AccessType -eq 'ReadWrite') {
            try {
                $testFile = Join-Path (Split-Path $Path -Parent) "~test_write_access.tmp"
                "test" | Out-File $testFile -Force -ErrorAction Stop
                Remove-Item $testFile -Force -ErrorAction Stop
            }
            catch {
                Write-Verbose "Write access test failed: $($_.Exception.Message)"
                return $false
            }
        }
        
        return $true
    }
    catch {
        Write-Verbose "Path accessibility test failed: $($_.Exception.Message)"
        return $false
    }
}

#endregion

#region Link Testing Functions

function Test-LinkValid {
    <#
    .SYNOPSIS
        Tests if a symbolic link, junction, or hard link is valid and functional
    
    .PARAMETER LinkPath
        Path to the link to test
    
    .RETURNS
        HashTable with validation results
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$LinkPath
    )
    
    $result = @{
        IsValid = $false
        LinkType = $null
        Target = $null
        TargetExists = $false
        Error = $null
    }
    
    try {
        if (-not (Test-Path $LinkPath)) {
            $result.Error = "Link path does not exist"
            return $result
        }
        
        $item = Get-Item $LinkPath -Force
        
        # Determine link type
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            if ($item.PSIsContainer) {
                # Could be junction or directory symlink
                $target = $item.Target
                if ($target) {
                    $result.LinkType = "Junction"
                    $result.Target = $target[0]
                } else {
                    $result.LinkType = "DirectorySymbolicLink"
                    # Try to get target using fsutil for directory symlinks
                    $fsutilOutput = cmd /c "fsutil reparsepoint query `"$LinkPath`"" 2>$null
                    if ($fsutilOutput -match "Substitute Name: (.+)") {
                        $result.Target = $matches[1].Trim()
                    }
                }
            } else {
                $result.LinkType = "FileSymbolicLink"
                $result.Target = $item.Target[0]
            }
        } elseif ($item.LinkType -eq "HardLink") {
            $result.LinkType = "HardLink"
            $result.Target = $LinkPath # Hard links point to same data
        } else {
            $result.Error = "Not a link"
            return $result
        }
        
        # Test if target exists and is accessible
        if ($result.Target) {
            $result.TargetExists = Test-Path $result.Target
            if ($result.TargetExists) {
                $result.IsValid = Test-PathAccessible $result.Target
            }
        } else {
            $result.Error = "Could not determine target"
        }
        
        return $result
    }
    catch {
        $result.Error = $_.Exception.Message
        return $result
    }
}

function Get-LinkStatistics {
    <#
    .SYNOPSIS
        Gets statistics about links in a directory
    
    .PARAMETER Path
        Directory to analyze
    
    .PARAMETER Recursive
        Include subdirectories in analysis
    
    .RETURNS
        HashTable with link statistics
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        
        [switch]$Recursive
    )
    
    $stats = @{
        TotalLinks = 0
        ValidLinks = 0
        BrokenLinks = 0
        LinkTypes = @{}
        Errors = @()
    }
    
    try {
        $items = if ($Recursive) {
            Get-ChildItem $Path -Recurse -Force -ErrorAction SilentlyContinue
        } else {
            Get-ChildItem $Path -Force -ErrorAction SilentlyContinue
        }
        
        foreach ($item in $items) {
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint -or $item.LinkType -eq "HardLink") {
                $stats.TotalLinks++
                
                $linkTest = Test-LinkValid $item.FullName
                if ($linkTest.IsValid) {
                    $stats.ValidLinks++
                } else {
                    $stats.BrokenLinks++
                    $stats.Errors += @{
                        Path = $item.FullName
                        Error = $linkTest.Error
                    }
                }
                
                if ($linkTest.LinkType) {
                    if (-not $stats.LinkTypes.ContainsKey($linkTest.LinkType)) {
                        $stats.LinkTypes[$linkTest.LinkType] = 0
                    }
                    $stats.LinkTypes[$linkTest.LinkType]++
                }
            }
        }
        
        return $stats
    }
    catch {
        $stats.Errors += @{
            Path = $Path
            Error = $_.Exception.Message
        }
        return $stats
    }
}

#endregion

#region Performance Monitoring Functions

function Start-PerformanceMonitor {
    <#
    .SYNOPSIS
        Starts performance monitoring for operations
    
    .RETURNS
        Performance monitor object
    #>
    [CmdletBinding()]
    param()
    
    $monitor = @{
        StartTime = Get-Date
        StartMemory = [GC]::GetTotalMemory($false)
        Operations = 0
        LastUpdate = Get-Date
    }
    
    return $monitor
}

function Update-PerformanceMonitor {
    <#
    .SYNOPSIS
        Updates performance monitor with current operation count
    
    .PARAMETER Monitor
        Performance monitor object
    
    .PARAMETER OperationCount
        Number of operations completed
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Monitor,
        
        [Parameter(Mandatory)]
        [int]$OperationCount
    )
    
    $Monitor.Operations = $OperationCount
    $Monitor.LastUpdate = Get-Date
}

function Get-PerformanceReport {
    <#
    .SYNOPSIS
        Gets performance report from monitor
    
    .PARAMETER Monitor
        Performance monitor object
    
    .RETURNS
        Performance report as HashTable
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Monitor
    )
    
    $endTime = Get-Date
    $duration = $endTime - $Monitor.StartTime
    $currentMemory = [GC]::GetTotalMemory($false)
    $memoryDelta = $currentMemory - $Monitor.StartMemory
    
    $report = @{
        Duration = $duration
        TotalOperations = $Monitor.Operations
        OperationsPerSecond = if ($duration.TotalSeconds -gt 0) { $Monitor.Operations / $duration.TotalSeconds } else { 0 }
        MemoryUsed = $memoryDelta
        PeakMemoryMB = [math]::Round($currentMemory / 1MB, 2)
    }
    
    return $report
}

#endregion

#region Database Utility Functions

function Test-DatabaseConnection {
    <#
    .SYNOPSIS
        Tests JSON database connection and validates structure
    
    .PARAMETER DatabasePath
        Path to JSON database file
    
    .RETURNS
        Boolean indicating if database is valid
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$DatabasePath
    )
    
    try {
        if (-not (Test-Path $DatabasePath)) {
            Write-Verbose "Database file does not exist: $DatabasePath"
            return $false
        }
        
        # Try to load and parse JSON
        $content = Get-Content $DatabasePath -Raw -ErrorAction Stop
        $database = $content | ConvertFrom-Json -ErrorAction Stop
        
        # Test required collections exist
        $requiredCollections = @('operations', 'path_mappings', 'path_analysis', 'metadata')
        
        foreach ($collection in $requiredCollections) {
            $hasProperty = $false
            foreach ($prop in $database.PSObject.Properties) {
                if ($prop.Name -eq $collection) {
                    $hasProperty = $true
                    break
                }
            }
            if (-not $hasProperty) {
                Write-Verbose "Required collection missing: $collection"
                return $false
            }
        }
        
        # Test metadata structure
        $hasVersion = $false
        $hasCreated = $false
        foreach ($prop in $database.metadata.PSObject.Properties) {
            if ($prop.Name -eq 'version') { $hasVersion = $true }
            if ($prop.Name -eq 'created') { $hasCreated = $true }
        }
        
        if (-not $hasVersion -or -not $hasCreated) {
            Write-Verbose "Invalid metadata structure"
            return $false
        }
        
        Write-Verbose "JSON database validation successful"
        return $true
    }
    catch {
        Write-Verbose "Database connection test failed: $($_.Exception.Message)"
        return $false
    }
}

function Export-DatabaseReport {
    <#
    .SYNOPSIS
        Exports JSON database contents to report formats
    
    .PARAMETER DatabasePath
        Path to JSON database file
    
    .PARAMETER OutputPath
        Path for output file
    
    .PARAMETER Format
        Report format: JSON, CSV, HTML
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$DatabasePath,
        
        [Parameter(Mandatory)]
        [string]$OutputPath,
        
        [ValidateSet('JSON', 'CSV', 'HTML')]
        [string]$Format = 'JSON'
    )
    
    try {
        if (-not (Test-Path $DatabasePath)) {
            throw "Database file does not exist: $DatabasePath"
        }
        
        # Load JSON database
        $content = Get-Content $DatabasePath -Raw -ErrorAction Stop
        $database = $content | ConvertFrom-Json -ErrorAction Stop
        
        # Prepare report data
        $reportData = @{
            GeneratedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
            DatabaseVersion = $database.metadata.version
            DatabaseCreated = $database.metadata.created
            Operations = @($database.operations)
            PathMappings = @($database.path_mappings)
            PathAnalysis = @($database.path_analysis | Select-Object -Last 1000) # Limit to last 1000 for performance
        }
        
        # Export in requested format
        switch ($Format) {
            'JSON' {
                $reportData | ConvertTo-Json -Depth 10 | Set-Content $OutputPath -Encoding UTF8
            }
            'CSV' {
                # Export operations to CSV
                if ($reportData.Operations.Count -gt 0) {
                    $reportData.Operations | Export-Csv "$($OutputPath)_operations.csv" -NoTypeInformation
                }
                if ($reportData.PathMappings.Count -gt 0) {
                    $reportData.PathMappings | Export-Csv "$($OutputPath)_mappings.csv" -NoTypeInformation
                }
                if ($reportData.PathAnalysis.Count -gt 0) {
                    $reportData.PathAnalysis | Export-Csv "$($OutputPath)_analysis.csv" -NoTypeInformation
                }
            }
            'HTML' {
                $html = @"
<!DOCTYPE html>
<html>
<head>
    <title>Path Shortener Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .stats { background-color: #f9f9f9; padding: 10px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>Path Shortener Report</h1>
    <div class="stats">
        <p><strong>Generated:</strong> $($reportData.GeneratedAt)</p>
        <p><strong>Database Version:</strong> $($reportData.DatabaseVersion)</p>
        <p><strong>Database Created:</strong> $($reportData.DatabaseCreated)</p>
        <p><strong>Total Operations:</strong> $($reportData.Operations.Count)</p>
        <p><strong>Total Path Mappings:</strong> $($reportData.PathMappings.Count)</p>
        <p><strong>Paths Analyzed:</strong> $($reportData.PathAnalysis.Count)</p>
    </div>
    
    <h2>Recent Operations</h2>
    <table>
        <tr><th>Timestamp</th><th>Type</th><th>Source</th><th>Target</th><th>Status</th></tr>
"@
                foreach ($op in ($reportData.Operations | Select-Object -Last 50)) {
                    $html += "<tr><td>$($op.timestamp)</td><td>$($op.operation_type)</td><td>$($op.source_path)</td><td>$($op.target_path)</td><td>$($op.status)</td></tr>`n"
                }
                
                $html += @"
    </table>
    
    <h2>Path Mappings</h2>
    <table>
        <tr><th>Original Path</th><th>Short Path</th><th>Created</th></tr>
"@
                foreach ($mapping in ($reportData.PathMappings | Select-Object -Last 50)) {
                    $html += "<tr><td>$($mapping.original_path)</td><td>$($mapping.short_path)</td><td>$($mapping.created_timestamp)</td></tr>`n"
                }
                
                $html += "</table></body></html>"
                
                $html | Set-Content $OutputPath -Encoding UTF8
            }
        }
        
        Write-Verbose "Report exported to: $OutputPath"
    }
    catch {
        Write-Error "Failed to export database report: $($_.Exception.Message)"
    }
}

function Get-DatabaseStatistics {
    <#
    .SYNOPSIS
        Gets statistics from the JSON database
    
    .PARAMETER DatabasePath
        Path to JSON database file
    
    .RETURNS
        HashTable with database statistics
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$DatabasePath
    )
    
    try {
        if (-not (Test-Path $DatabasePath)) {
            throw "Database file does not exist: $DatabasePath"
        }
        
        $content = Get-Content $DatabasePath -Raw -ErrorAction Stop
        $database = $content | ConvertFrom-Json -ErrorAction Stop
        
        $stats = @{
            DatabaseVersion = $database.metadata.version
            DatabaseCreated = $database.metadata.created
            LastUpdated = $database.metadata.last_updated
            TotalOperations = @($database.operations).Count
            SuccessfulOperations = @($database.operations | Where-Object { $_.status -eq 'SUCCESS' }).Count
            FailedOperations = @($database.operations | Where-Object { $_.status -eq 'FAILED' }).Count
            RolledBackOperations = @($database.operations | Where-Object { $_.status -eq 'ROLLED_BACK' }).Count
            TotalPathMappings = @($database.path_mappings).Count
            TotalPathsAnalyzed = @($database.path_analysis).Count
            DatabaseFileSizeMB = [math]::Round((Get-Item $DatabasePath).Length / 1MB, 2)
        }
        
        return $stats
    }
    catch {
        Write-Error "Failed to get database statistics: $($_.Exception.Message)"
        return @{}
    }
}

#endregion

#region Cleanup Functions

function Remove-OrphanedLinks {
    <#
    .SYNOPSIS
        Removes symbolic links that point to non-existent targets
    
    .PARAMETER Path
        Directory to scan for orphaned links
    
    .PARAMETER Recursive
        Include subdirectories in scan
    
    .PARAMETER WhatIf
        Show what would be removed without actually removing
    
    .RETURNS
        Array of removed link paths
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        
        [switch]$Recursive,
        [switch]$WhatIf
    )
    
    $removedLinks = @()
    
    try {
        $items = if ($Recursive) {
            Get-ChildItem $Path -Recurse -Force -ErrorAction SilentlyContinue
        } else {
            Get-ChildItem $Path -Force -ErrorAction SilentlyContinue
        }
        
        foreach ($item in $items) {
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                $linkTest = Test-LinkValid $item.FullName
                
                if (-not $linkTest.IsValid -and $linkTest.Target -and -not (Test-Path $linkTest.Target)) {
                    if ($WhatIf) {
                        Write-Host "Would remove orphaned link: $($item.FullName) -> $($linkTest.Target)" -ForegroundColor Yellow
                    } elseif ($PSCmdlet.ShouldProcess($item.FullName, "Remove orphaned link")) {
                        try {
                            Remove-Item $item.FullName -Force
                            $removedLinks += $item.FullName
                            Write-Verbose "Removed orphaned link: $($item.FullName)"
                        }
                        catch {
                            Write-Warning "Failed to remove orphaned link $($item.FullName): $($_.Exception.Message)"
                        }
                    }
                }
            }
        }
        
        return $removedLinks
    }
    catch {
        Write-Error "Failed to clean up orphaned links: $($_.Exception.Message)"
        return $removedLinks
    }
}

#endregion

# Export module functions
Export-ModuleMember -Function @(
    'Test-PathValid',
    'Test-PathAccessible',
    'Test-LinkValid',
    'Get-LinkStatistics',
    'Start-PerformanceMonitor',
    'Update-PerformanceMonitor',
    'Get-PerformanceReport',
    'Test-DatabaseConnection',
    'Export-DatabaseReport',
    'Get-DatabaseStatistics',
    'Remove-OrphanedLinks'
)