ive me creaa<#
.SYNOPSIS
    Windows Path Shortener - Automatically create short links for long paths to avoid Windows path length limitations.

.DESCRIPTION
    This script analyzes directory structures, identifies paths exceeding Windows limits (typically 260 characters),
    and creates appropriate symbolic links, junctions, or hard links to provide shorter access paths.
    All operations are tracked in a JSON-based database with rollback capabilities.

.PARAMETER TargetPath
    The root directory to analyze for long paths. Defaults to current directory.

.PARAMETER FromEnvVar
    Name of an environment variable containing the target path to analyze. When specified, the path will be read from this environment variable instead of using TargetPath.

.PARAMETER MaxPathLength
    Maximum allowed path length before creating short links. Default: 200 characters.

.PARAMETER ShortLinkRoot
    Root directory where short links will be created. Default: C:\ShortLinks

.PARAMETER DatabasePath
    Path to JSON database for tracking operations. Default: .\PathShortener.db.json

.PARAMETER LinkType
    Preferred link type: Auto, Junction, SymbolicLink, HardLink. Default: Auto

.PARAMETER DryRun
    Run in simulation mode without making actual changes.

.PARAMETER Force
    Skip confirmation prompts for batch operations.

.PARAMETER Rollback
    Roll back previous operations using database records.

.PARAMETER LogLevel
    Logging level: Debug, Info, Warning, Error. Default: Info

.PARAMETER ConfigFile
    Path to configuration file. Default: .\ShortPath.config.json

.EXAMPLE
    .\ShortPath.ps1 -TargetPath "C:\VeryLongPathNames" -DryRun
    Analyze paths without making changes

.EXAMPLE
    .\ShortPath.ps1 -TargetPath "C:\Projects" -MaxPathLength 150 -Force
    Shorten all paths longer than 150 characters without prompts

.EXAMPLE
    .\ShortPath.ps1 -FromEnvVar "DUMY" -DryRun
    Read target path from DUMY environment variable and analyze without making changes

.EXAMPLE
    .\ShortPath.ps1 -FromEnvVar "MY_PROJECT_PATH" -ShortLinkRoot "C:\Links" -Force
    Read path from MY_PROJECT_PATH environment variable and create short links in C:\Links

.EXAMPLE
    .\ShortPath.ps1 -Rollback -DatabasePath "C:\Temp\PathShortener.db.json"
    Rollback all operations recorded in the specified database

.NOTES
    Author: Path Shortener Script
    Version: 1.1
    Requires: PowerShell 5.1+, Windows 7+, Administrator privileges for some operations
    Database: Pure PowerShell JSON-based storage (no external dependencies)
#>

[CmdletBinding(DefaultParameterSetName = 'Analyze')]
param(
    [Parameter(ParameterSetName = 'Analyze', Position = 0)]
    [Parameter(ParameterSetName = 'Rollback')]
    [string]$TargetPath,

    [Parameter(ParameterSetName = 'Analyze')]
    [string]$FromEnvVar,

    [Parameter(ParameterSetName = 'Analyze')]
    [ValidateRange(50, 32767)]
    [int]$MaxPathLength = 200,

    [Parameter(ParameterSetName = 'Analyze')]
    [string]$ShortLinkRoot = "C:\ShortLinks",

    [Parameter(ParameterSetName = 'Analyze')]
    [Parameter(ParameterSetName = 'Rollback')]
    [string]$DatabasePath = ".\PathShortener.db.json",

    [Parameter(ParameterSetName = 'Analyze')]
    [ValidateSet('Auto', 'Junction', 'SymbolicLink', 'HardLink')]
    [string]$LinkType = 'Auto',

    [Parameter(ParameterSetName = 'Analyze')]
    [switch]$DryRun,

    [Parameter(ParameterSetName = 'Analyze')]
    [switch]$Force,

    [Parameter(ParameterSetName = 'Rollback', Mandatory)]
    [switch]$Rollback,

    [ValidateSet('Debug', 'Info', 'Warning', 'Error')]
    [string]$LogLevel = 'Info',

    [string]$ConfigFile = ".\ShortPath.config.json"
)

# Global variables for script configuration
$Script:Config = $null
$Script:Database = $null
$Script:LogFile = $null
$Script:OperationId = [Guid]::NewGuid().ToString()

# Pure PowerShell JSON Database Implementation
class PathShortenerDatabase {
    [string]$DatabasePath
    [PSCustomObject]$Data
    
    PathShortenerDatabase([string]$path) {
        $this.DatabasePath = $path
        $this.Initialize()
    }
    
    [void]Initialize() {
        if (Test-Path $this.DatabasePath) {
            try {
                $content = Get-Content $this.DatabasePath -Raw -ErrorAction Stop
                $jsonData = $content | ConvertFrom-Json -ErrorAction Stop
                
                # Convert to hashtable manually for PowerShell 5.1 compatibility
                $this.Data = @{
                    operations = @()
                    path_mappings = @()
                    path_analysis = @()
                    metadata = @{}
                }
                
                if ($jsonData.operations) { $this.Data.operations = @($jsonData.operations) }
                if ($jsonData.path_mappings) { $this.Data.path_mappings = @($jsonData.path_mappings) }
                if ($jsonData.path_analysis) { $this.Data.path_analysis = @($jsonData.path_analysis) }
                if ($jsonData.metadata) { 
                    $this.Data.metadata = @{
                        created = $jsonData.metadata.created
                        version = $jsonData.metadata.version
                        last_updated = $jsonData.metadata.last_updated
                    }
                }
            }
            catch {
                Write-Warning "Failed to load existing database, creating new one: $($_.Exception.Message)"
                $this.CreateNewDatabase()
            }
        }
        else {
            $this.CreateNewDatabase()
        }
        
        # Ensure all required collections exist
        if (-not $this.Data.ContainsKey('operations')) { $this.Data['operations'] = @() }
        if (-not $this.Data.ContainsKey('path_mappings')) { $this.Data['path_mappings'] = @() }
        if (-not $this.Data.ContainsKey('path_analysis')) { $this.Data['path_analysis'] = @() }
        if (-not $this.Data.ContainsKey('metadata')) { 
            $this.Data['metadata'] = @{
                created = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
                version = '1.1'
                last_updated = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
            }
        }
    }
    
    [void]CreateNewDatabase() {
        $this.Data = @{
            operations = @()
            path_mappings = @()
            path_analysis = @()
            metadata = @{
                created = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
                version = '1.1'
                last_updated = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
            }
        }
        $this.Save()
    }
    
    [void]Save() {
        try {
            $this.Data.metadata.last_updated = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
            $this.Data | ConvertTo-Json -Depth 10 | Set-Content $this.DatabasePath -Encoding UTF8
        }
        catch {
            Write-Error "Failed to save database: $($_.Exception.Message)"
        }
    }
    
    [void]AddOperation([hashtable]$operation) {
        $this.Data.operations += $operation
        $this.Save()
    }
    
    [void]UpdateOperation([string]$id, [hashtable]$updates) {
        for ($i = 0; $i -lt $this.Data.operations.Count; $i++) {
            if ($this.Data.operations[$i].id -eq $id) {
                foreach ($key in $updates.Keys) {
                    $this.Data.operations[$i][$key] = $updates[$key]
                }
                break
            }
        }
        $this.Save()
    }
    
    [void]AddPathMapping([hashtable]$mapping) {
        $this.Data.path_mappings += $mapping
        $this.Save()
    }
    
    [void]AddPathAnalysis([hashtable]$analysis) {
        $this.Data.path_analysis += $analysis
        $this.Save()
    }
    
    [array]GetSuccessfulOperations() {
        return $this.Data.operations | Where-Object { $_.status -eq 'SUCCESS' -and $_.operation_type -eq 'CREATE_LINK' }
    }
    
    [void]Close() {
        $this.Save()
    }
}

#region Helper Functions

function Write-Log {
    param(
        [Parameter(Mandatory)]
        [string]$Message,
        
        [ValidateSet('Debug', 'Info', 'Warning', 'Error')]
        [string]$Level = 'Info',
        
        [switch]$NoConsole
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # Write to log file
    if ($Script:LogFile) {
        Add-Content -Path $Script:LogFile -Value $logEntry -Encoding UTF8
    }
    
    # Write to console based on log level with null checking
    if (-not $NoConsole) {
        $levelPriority = @{
            'Debug' = 0; 'Info' = 1; 'Warning' = 2; 'Error' = 3
        }
        
        # Safe null checking for configuration
        $configuredLevel = if ($Script:Config -and $Script:Config.LogLevel) {
            $levelPriority[$Script:Config.LogLevel]
        } else {
            $levelPriority['Info'] # Default to Info level if config not available
        }
        
        $messageLevel = $levelPriority[$Level]
        
        if ($messageLevel -ge $configuredLevel) {
            switch ($Level) {
                'Debug'   { Write-Host $logEntry -ForegroundColor Gray }
                'Info'    { Write-Host $logEntry -ForegroundColor White }
                'Warning' { Write-Host $logEntry -ForegroundColor Yellow }
                'Error'   { Write-Host $logEntry -ForegroundColor Red }
            }
        }
    }
}

function Initialize-Configuration {
    param([string]$ConfigPath)
    
    $defaultConfig = @{
        MaxPathLength = 200
        ShortLinkRoot = "C:\ShortLinks"
        DatabasePath = ".\PathShortener.db.json"
        LinkType = "Auto"
        LogLevel = "Info"
        HashLength = 8
        PrefixLength = 16
        ExcludePatterns = @("*.tmp", "*.temp", "*\$Recycle.Bin\*", "*\System Volume Information\*")
        LinkPreferences = @{
            Directory = "Junction"
            File = "HardLink"
            CrossVolume = "SymbolicLink"
        }
        BackupEnabled = $true
        MaxOperationsPerBatch = 1000
    }
    
    if (Test-Path $ConfigPath) {
        try {
            $loadedConfig = Get-Content $ConfigPath -Raw | ConvertFrom-Json
            
            # Merge configurations
            foreach ($key in $defaultConfig.Keys) {
                if ($loadedConfig.PSObject.Properties.Name -contains $key) {
                    $defaultConfig[$key] = $loadedConfig.$key
                }
            }
            
            Write-Log "Configuration loaded from $ConfigPath" -Level Info
        }
        catch {
            Write-Log "Failed to load configuration from $ConfigPath`: $($_.Exception.Message)" -Level Warning
            Write-Log "Using default configuration" -Level Info
        }
    }
    else {
        # Create default configuration file
        $defaultConfig | ConvertTo-Json -Depth 10 | Set-Content $ConfigPath -Encoding UTF8
        Write-Log "Default configuration created at $ConfigPath" -Level Info
    }
    
    return [PSCustomObject]$defaultConfig
}

function Initialize-Database {
    param([string]$DatabasePath)
    
    try {
        $database = [PathShortenerDatabase]::new($DatabasePath)
        Write-Log "Database initialized at $DatabasePath" -Level Info
        return $database
    }
    catch {
        Write-Log "Failed to initialize database: $($_.Exception.Message)" -Level Error
        throw
    }
}

function Get-PathHash {
    param([string]$Path)
    
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Path.ToLowerInvariant())
    $hash = $sha256.ComputeHash($bytes)
    $hashString = [System.BitConverter]::ToString($hash).Replace("-", "").ToLowerInvariant()
    
    return $hashString.Substring(0, $Script:Config.HashLength)
}

function Get-ShortName {
    param(
        [string]$OriginalPath,
        [string]$Type = "dir"
    )
    
    $baseName = Split-Path $OriginalPath -Leaf
    $prefix = if ($baseName.Length -gt $Script:Config.PrefixLength) {
        $baseName.Substring(0, $Script:Config.PrefixLength)
    } else {
        $baseName
    }
    
    $hash = Get-PathHash $OriginalPath
    $shortName = "${prefix}_${hash}"
    
    # Ensure valid Windows filename
    $shortName = $shortName -replace '[<>:"/\\|?*]', '_'
    
    return $shortName
}

function Test-PathLength {
    param([string]$Path)
    
    return $Path.Length -gt $Script:Config.MaxPathLength
}

function Get-OptimalLinkType {
    param(
        [string]$SourcePath,
        [string]$TargetPath,
        [string]$PreferredType = "Auto"
    )
    
    if ($PreferredType -ne "Auto") {
        return $PreferredType
    }
    
    $sourceInfo = Get-Item $SourcePath -Force -ErrorAction SilentlyContinue
    if (-not $sourceInfo) {
        return "SymbolicLink"
    }
    
    $sourceVolume = Split-Path $SourcePath -Qualifier
    $targetVolume = Split-Path $TargetPath -Qualifier
    
    if ($sourceVolume -ne $targetVolume) {
        return $Script:Config.LinkPreferences.CrossVolume
    }
    
    if ($sourceInfo.PSIsContainer) {
        return $Script:Config.LinkPreferences.Directory
    } else {
        return $Script:Config.LinkPreferences.File
    }
}

function New-ShortLink {
    param(
        [string]$SourcePath,
        [string]$TargetPath,
        [string]$LinkType
    )
    
    try {
        $targetDir = Split-Path $TargetPath -Parent
        if (-not (Test-Path $targetDir)) {
            New-Item -Path $targetDir -ItemType Directory -Force | Out-Null
            Write-Log "Created target directory: $targetDir" -Level Debug
        }
        
        switch ($LinkType) {
            "Junction" {
                if (-not (Get-Item $SourcePath).PSIsContainer) {
                    throw "Junction links can only be created for directories"
                }
                cmd /c "mklink /J `"$TargetPath`" `"$SourcePath`"" 2>$null
                if ($LASTEXITCODE -ne 0) {
                    throw "Failed to create junction link"
                }
            }
            
            "SymbolicLink" {
                $isDirectory = (Get-Item $SourcePath -Force).PSIsContainer
                $flag = if ($isDirectory) { "/D" } else { "" }
                cmd /c "mklink $flag `"$TargetPath`" `"$SourcePath`"" 2>$null
                if ($LASTEXITCODE -ne 0) {
                    throw "Failed to create symbolic link"
                }
            }
            
            "HardLink" {
                if ((Get-Item $SourcePath -Force).PSIsContainer) {
                    throw "Hard links cannot be created for directories"
                }
                cmd /c "mklink /H `"$TargetPath`" `"$SourcePath`"" 2>$null
                if ($LASTEXITCODE -ne 0) {
                    throw "Failed to create hard link"
                }
            }
            
            default {
                throw "Unsupported link type: $LinkType"
            }
        }
        
        Write-Log "Created $LinkType`: $TargetPath -> $SourcePath" -Level Info
        return $true
    }
    catch {
        Write-Log "Failed to create link: $($_.Exception.Message)" -Level Error
        return $false
    }
}

function Find-LongPaths {
    param([string]$RootPath)
    
    Write-Log "Scanning for long paths in: $RootPath" -Level Info
    $longPaths = @()
    $totalScanned = 0
    
    try {
        Get-ChildItem -Path $RootPath -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $totalScanned++
            
            if ($totalScanned % 1000 -eq 0) {
                Write-Progress -Activity "Scanning paths" -Status "Scanned $totalScanned items" -PercentComplete -1
            }
            
            $fullPath = $_.FullName
            $pathLength = $fullPath.Length
            
            # Check exclusion patterns
            $excluded = $false
            foreach ($pattern in $Script:Config.ExcludePatterns) {
                if ($fullPath -like $pattern) {
                    $excluded = $true
                    break
                }
            }
            
            if (-not $excluded -and (Test-PathLength $fullPath)) {
                $pathInfo = @{
                    Path = $fullPath
                    Length = $pathLength
                    Type = if ($_.PSIsContainer) { "Directory" } else { "File" }
                    LastModified = $_.LastWriteTime
                    Size = if (-not $_.PSIsContainer) { $_.Length } else { 0 }
                }
                
                $longPaths += $pathInfo
                
                # Store in database for analysis
                $analysisRecord = @{
                    scan_timestamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
                    path = $fullPath
                    length = $pathLength
                    type = $pathInfo.Type
                    needs_shortening = $true
                    shortening_attempted = $false
                }
                
                $Script:Database.AddPathAnalysis($analysisRecord)
            }
        }
    }
    catch {
        Write-Log "Error during path scanning: $($_.Exception.Message)" -Level Error
    }
    finally {
        Write-Progress -Activity "Scanning paths" -Completed
    }
    
    Write-Log "Scan complete. Found $($longPaths.Count) long paths out of $totalScanned total items." -Level Info
    return $longPaths
}

function Invoke-PathShortening {
    param(
        [array]$LongPaths,
        [switch]$DryRun
    )
    
    $processedCount = 0
    $successCount = 0
    $failureCount = 0
    
    Write-Log "Processing $($LongPaths.Count) long paths..." -Level Info
    
    foreach ($pathInfo in $LongPaths) {
        $processedCount++
        Write-Progress -Activity "Shortening paths" -Status "Processing $($pathInfo.Path)" -PercentComplete (($processedCount / $LongPaths.Count) * 100)
        
        try {
            $shortName = Get-ShortName $pathInfo.Path $pathInfo.Type.ToLower()
            $shortPath = Join-Path $Script:Config.ShortLinkRoot $shortName
            
            # Check for conflicts
            if (Test-Path $shortPath) {
                $existingTarget = (Get-Item $shortPath -Force).Target
                if ($existingTarget -and $existingTarget[0] -eq $pathInfo.Path) {
                    Write-Log "Link already exists: $shortPath -> $($pathInfo.Path)" -Level Debug
                    continue
                }
                
                # Handle conflict
                $counter = 1
                do {
                    $conflictShortName = "${shortName}_${counter}"
                    $shortPath = Join-Path $Script:Config.ShortLinkRoot $conflictShortName
                    $counter++
                } while (Test-Path $shortPath -and $counter -lt 100)
                
                if ($counter -eq 100) {
                    Write-Log "Too many conflicts for path: $($pathInfo.Path)" -Level Error
                    $failureCount++
                    continue
                }
            }
            
            $linkType = Get-OptimalLinkType $pathInfo.Path $shortPath $Script:Config.LinkType
            
            if ($DryRun) {
                Write-Log "[DRY RUN] Would create $linkType`: $shortPath -> $($pathInfo.Path)" -Level Info
                $successCount++
            } else {
                # Record operation start
                $operationId = [Guid]::NewGuid().ToString()
                $operation = @{
                    id = $operationId
                    timestamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
                    operation_type = 'CREATE_LINK'
                    source_path = $pathInfo.Path
                    target_path = $shortPath
                    link_type = $linkType
                    status = 'IN_PROGRESS'
                    error_message = $null
                    rollback_data = $null
                }
                
                $Script:Database.AddOperation($operation)
                
                if (New-ShortLink $pathInfo.Path $shortPath $linkType) {
                    # Record success
                    $Script:Database.UpdateOperation($operationId, @{ status = 'SUCCESS' })
                    
                    # Record mapping
                    $mapping = @{
                        operation_id = $operationId
                        original_path = $pathInfo.Path
                        short_path = $shortPath
                        hash_value = (Get-PathHash $pathInfo.Path)
                        created_timestamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
                    }
                    
                    $Script:Database.AddPathMapping($mapping)
                    $successCount++
                } else {
                    # Record failure
                    $Script:Database.UpdateOperation($operationId, @{ 
                        status = 'FAILED'
                        error_message = 'Link creation failed'
                    })
                    $failureCount++
                }
            }
        }
        catch {
            Write-Log "Error processing path $($pathInfo.Path): $($_.Exception.Message)" -Level Error
            $failureCount++
        }
    }
    
    Write-Progress -Activity "Shortening paths" -Completed
    Write-Log "Path shortening complete. Success: $successCount, Failures: $failureCount" -Level Info
}

function Invoke-RollbackOperations {
    param([string]$DatabasePath)
    
    Write-Log "Starting rollback of operations..." -Level Info
    
    try {
        $successfulOps = $Script:Database.GetSuccessfulOperations()
        
        $rollbackCount = 0
        $rollbackErrors = 0
        
        foreach ($operation in $successfulOps) {
            $targetPath = $operation.target_path
            
            if (Test-Path $targetPath) {
                try {
                    Remove-Item $targetPath -Force
                    Write-Log "Removed link: $targetPath" -Level Info
                    $rollbackCount++
                    
                    # Update operation status
                    $Script:Database.UpdateOperation($operation.id, @{ status = 'ROLLED_BACK' })
                }
                catch {
                    Write-Log "Failed to remove link $targetPath`: $($_.Exception.Message)" -Level Error
                    $rollbackErrors++
                }
            }
        }
        
        Write-Log "Rollback complete. Removed: $rollbackCount links, Errors: $rollbackErrors" -Level Info
    }
    catch {
        Write-Log "Rollback failed: $($_.Exception.Message)" -Level Error
        throw
    }
}

function Get-TargetPathFromEnvVar {
    <#
    .SYNOPSIS
        Retrieves and validates a target path from an environment variable

    .PARAMETER EnvVarName
        Name of the environment variable to read

    .RETURNS
        Validated target path from the environment variable
    #>
    param(
        [Parameter(Mandatory)]
        [string]$EnvVarName
    )
    
    try {
        # Check if environment variable exists
        $envValue = [Environment]::GetEnvironmentVariable($EnvVarName)
        if ([string]::IsNullOrWhiteSpace($envValue)) {
            throw "Environment variable '$EnvVarName' does not exist or is empty."
        }
        
        Write-Log "Found environment variable '$EnvVarName' with value: $envValue" -Level Debug
        
        # Expand environment variables in the path if any
        $expandedPath = [Environment]::ExpandEnvironmentVariables($envValue)
        Write-Log "Expanded path: $expandedPath" -Level Debug
        
        # Validate the path exists and is a directory
        if (-not (Test-Path $expandedPath -PathType Container)) {
            throw "Path from environment variable '$EnvVarName' ('$expandedPath') does not exist or is not a directory."
        }
        
        # Get the full path to resolve any relative paths or shortcuts
        $fullPath = (Get-Item $expandedPath -Force).FullName
        Write-Log "Resolved full path: $fullPath" -Level Info
        
        return $fullPath
    }
    catch {
        Write-Log "Failed to get target path from environment variable '$EnvVarName': $($_.Exception.Message)" -Level Error
        throw
    }
}

#endregion

#region Main Script Logic

try {
    # Initialize configuration
    $Script:Config = Initialize-Configuration $ConfigFile
    
    # Override with command line parameters
    if ($PSBoundParameters.ContainsKey('MaxPathLength')) { $Script:Config.MaxPathLength = $MaxPathLength }
    if ($PSBoundParameters.ContainsKey('ShortLinkRoot')) { $Script:Config.ShortLinkRoot = $ShortLinkRoot }
    if ($PSBoundParameters.ContainsKey('DatabasePath')) { $Script:Config.DatabasePath = $DatabasePath }
    if ($PSBoundParameters.ContainsKey('LinkType')) { $Script:Config.LinkType = $LinkType }
    if ($PSBoundParameters.ContainsKey('LogLevel')) { $Script:Config.LogLevel = $LogLevel }
    
    # Initialize logging
    $logDir = Join-Path (Split-Path $Script:Config.DatabasePath -Parent) "logs"
    if (-not (Test-Path $logDir)) {
        New-Item -Path $logDir -ItemType Directory -Force | Out-Null
    }
    $Script:LogFile = Join-Path $logDir "ShortPath_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    
    Write-Log "Windows Path Shortener starting..." -Level Info
    Write-Log "Operation ID: $Script:OperationId" -Level Info
    Write-Log "Configuration: MaxPathLength=$($Script:Config.MaxPathLength), ShortLinkRoot=$($Script:Config.ShortLinkRoot), LinkType=$($Script:Config.LinkType)" -Level Info
    
    # Initialize database
    $Script:Database = Initialize-Database $Script:Config.DatabasePath
    
    if ($Rollback) {
        # Rollback mode
        $confirmation = Read-Host "This will remove all previously created short links. Continue? (y/N)"
        if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
            Write-Log "Rollback cancelled by user." -Level Info
            exit 0
        }
        
        Invoke-RollbackOperations $Script:Config.DatabasePath
    }
    else {
        # Analysis and shortening mode
        
        # Determine the target path source
        if ($PSBoundParameters.ContainsKey('FromEnvVar')) {
            if ($PSBoundParameters.ContainsKey('TargetPath')) {
                Write-Log "Warning: Both -FromEnvVar and -TargetPath specified. Using environment variable '$FromEnvVar'." -Level Warning
            }
            $resolvedTargetPath = Get-TargetPathFromEnvVar $FromEnvVar
            Write-Log "Using target path from environment variable '$FromEnvVar': $resolvedTargetPath" -Level Info
        }
        elseif ($PSBoundParameters.ContainsKey('TargetPath')) {
            $resolvedTargetPath = $TargetPath
            Write-Log "Using specified target path: $resolvedTargetPath" -Level Info
        }
        else {
            $resolvedTargetPath = (Get-Location).Path
            Write-Log "Using current directory as target path: $resolvedTargetPath" -Level Info
        }
        
        Write-Log "Target path: $resolvedTargetPath" -Level Info
        
        if ($DryRun) {
            Write-Log "DRY RUN MODE - No actual changes will be made" -Level Warning
        }
        
        # Find long paths
        $longPaths = Find-LongPaths $resolvedTargetPath
        
        if ($longPaths.Count -eq 0) {
            Write-Log "No paths found exceeding $($Script:Config.MaxPathLength) characters." -Level Info
        }
        else {
            Write-Log "Found $($longPaths.Count) paths that need shortening." -Level Info
            
            # Show summary
            $pathsByType = $longPaths | Group-Object Type
            foreach ($group in $pathsByType) {
                Write-Log "  $($group.Name): $($group.Count) items" -Level Info
            }
            
            if (-not $Force -and -not $DryRun) {
                Write-Host "`nPaths to be shortened:" -ForegroundColor Yellow
                $longPaths | Select-Object -First 10 | ForEach-Object {
                    Write-Host "  [$($_.Type)] $($_.Path) ($($_.Length) chars)" -ForegroundColor Gray
                }
                
                if ($longPaths.Count -gt 10) {
                    Write-Host "  ... and $($longPaths.Count - 10) more paths" -ForegroundColor Gray
                }
                
                $confirmation = Read-Host "`nProceed with creating short links? (y/N)"
                if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
                    Write-Log "Operation cancelled by user." -Level Info
                    exit 0
                }
            }
            
            # Create short links
            Invoke-PathShortening $longPaths -DryRun:$DryRun
        }
    }
    
    Write-Log "Windows Path Shortener completed successfully." -Level Info
}
catch {
    Write-Log "Fatal error: $($_.Exception.Message)" -Level Error
    Write-Log "Stack trace: $($_.ScriptStackTrace)" -Level Debug
    exit 1
}
finally {
    # Cleanup
    if ($Script:Database) {
        $Script:Database.Close()
    }
}

#endregion