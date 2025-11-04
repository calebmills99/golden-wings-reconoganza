# PowerShell script for Step 1.1: Parse TOP50.md Structure (FIXED VERSION)
# Golden Wings Documentary - File Organization Project
# Author: AI Assistant for Caleb Stewart
# Date: September 26, 2025

Write-Host "🔍 Step 1.1: Parse TOP50.md Structure (FIXED)" -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Yellow
Write-Host ""

# Set working directory and file paths
$scriptDir = "D:\golden-wings-reconoganza"
$top50File = Join-Path $scriptDir "TOP50.md"
Set-Location $scriptDir

# Initialize data structures
$top50Files = @()
$missingFiles = @()
$parseErrors = @()
$summary = @{
    TotalParsed = 0
    FilesFound = 0
    FilesMissing = 0
    ParseErrors = 0
    SkippedRanks = 0
}

Write-Host "📁 Working directory: $scriptDir" -ForegroundColor Cyan
Write-Host "📄 Parsing file: TOP50.md" -ForegroundColor Cyan
Write-Host ""

# Check if TOP50.md exists
if (-not (Test-Path $top50File)) {
    Write-Host "❌ ERROR: TOP50.md not found at $top50File" -ForegroundColor Red
    exit 1
}

# Read the TOP50.md file
try {
    $content = Get-Content $top50File -Raw -Encoding UTF8
    Write-Host "✅ TOP50.md loaded successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Failed to read TOP50.md - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Split content into entries using the --- separator
$entries = $content -split "---" | Where-Object { $_ -match "^## \d+" }

Write-Host "🔢 Found $($entries.Count) entries in TOP50.md" -ForegroundColor Cyan
Write-Host ""

# Process each entry
foreach ($entry in $entries) {
    try {
        # Extract rank and filename from header
        if ($entry -match "## (\d+)\.\s*(.+)") {
            $rank = [int]$matches[1]
            $fileName = $matches[2].Trim()
            
            # Skip ranks 1-4 (already processed)
            if ($rank -le 4) {
                Write-Host "⏭️  Rank $rank`: $fileName (SKIPPED - already processed)" -ForegroundColor Yellow
                $summary.SkippedRanks++
                continue
            }
            
            Write-Host "📄 Rank $rank`: $fileName" -ForegroundColor White
            
            # Extract metadata with simple regex patterns
            $score = if ($entry -match '\*\*Score:\*\*\s+(\d+)') { [int]$matches[1] } else { 0 }
            $fullPath = if ($entry -match '\*\*Path:\*\*\s+`([^`]+)`') { $matches[1].Trim() } else { "" }
            $sizeStr = if ($entry -match '\*\*Size:\*\*\s+([^\r\n]+)') { $matches[1].Trim() } else { "" }
            $modifiedStr = if ($entry -match '\*\*Modified:\*\*\s+([^\r\n]+)') { $matches[1].Trim() } else { "" }
            $keywordsStr = if ($entry -match '\*\*Keywords:\*\*\s+([^\r\n]+)') { $matches[1].Trim() } else { "" }
            
            # Parse file details
            $directory = if ($fullPath) { Split-Path $fullPath -Parent } else { "" }
            $extension = [System.IO.Path]::GetExtension($fileName).ToLower()
            $drive = if ($fullPath -match "^([A-Z]:)") { $matches[1] } else { "Unknown" }
            
            # Parse size to bytes
            $sizeBytes = 0
            if ($sizeStr -match "(\d+\.?\d*)\s*(KB|MB|GB|bytes?)") {
                $sizeNum = [double]$matches[1]
                $sizeUnit = $matches[2].ToUpper()
                switch ($sizeUnit) {
                    "BYTES" { $sizeBytes = [long]$sizeNum }
                    "KB" { $sizeBytes = [long]($sizeNum * 1024) }
                    "MB" { $sizeBytes = [long]($sizeNum * 1024 * 1024) }
                    "GB" { $sizeBytes = [long]($sizeNum * 1024 * 1024 * 1024) }
                }
            }
            
            # Parse modification date
            $modifiedDate = Get-Date
            try {
                if ($modifiedStr) {
                    $modifiedDate = [datetime]::Parse($modifiedStr)
                }
            } catch {
                Write-Host "   ⚠️  Could not parse date: $modifiedStr" -ForegroundColor Yellow
            }
            
            # Split keywords
            $keywords = @()
            if ($keywordsStr) {
                $keywords = $keywordsStr -split ",\s*" | ForEach-Object { $_.Trim() }
            }
            
            # Check if file exists
            $fileExists = Test-Path $fullPath
            if ($fileExists) {
                Write-Host "   ✅ File found" -ForegroundColor Green
                $summary.FilesFound++
            } else {
                Write-Host "   ❌ File missing: $fullPath" -ForegroundColor Red
                $missingFiles += @{
                    Rank = $rank
                    FileName = $fileName
                    Path = $fullPath
                }
                $summary.FilesMissing++
            }
            
            # Create file data object
            $fileData = @{
                Rank = $rank
                FileName = $fileName
                Score = $score
                FullPath = $fullPath
                Directory = $directory
                Extension = $extension
                Drive = $drive
                Size = $sizeStr
                SizeBytes = $sizeBytes
                Modified = $modifiedDate
                Keywords = $keywords
                FileExists = $fileExists
            }
            
            $top50Files += $fileData
            $summary.TotalParsed++
            
        } else {
            Write-Host "❌ Could not parse entry header" -ForegroundColor Red
            $parseErrors += "Could not parse entry header"
            $summary.ParseErrors++
        }
        
    } catch {
        Write-Host "❌ Parse error for entry $rank`: $($_.Exception.Message)" -ForegroundColor Red
        $parseErrors += "Entry $rank`: $($_.Exception.Message)"
        $summary.ParseErrors++
    }
}

# Generate summary statistics
Write-Host ""
Write-Host "=======================================" -ForegroundColor Yellow
Write-Host "📊 PARSING SUMMARY" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Yellow
Write-Host "📄 Total entries parsed: $($summary.TotalParsed)" -ForegroundColor White
Write-Host "✅ Files found: $($summary.FilesFound)" -ForegroundColor Green
Write-Host "❌ Files missing: $($summary.FilesMissing)" -ForegroundColor Red
Write-Host "⏭️  Entries skipped (ranks 1-4): $($summary.SkippedRanks)" -ForegroundColor Yellow
Write-Host "❌ Parse errors: $($summary.ParseErrors)" -ForegroundColor Red
Write-Host ""

# File type breakdown
Write-Host "📁 FILE TYPE BREAKDOWN:" -ForegroundColor Cyan
$extensionGroups = $top50Files | Group-Object Extension | Sort-Object Count -Descending
foreach ($group in $extensionGroups) {
    $ext = if ($group.Name) { $group.Name } else { "(no extension)" }
    Write-Host "   $ext`: $($group.Count) files" -ForegroundColor White
}
Write-Host ""

# Drive breakdown
Write-Host "💽 DRIVE BREAKDOWN:" -ForegroundColor Cyan
$driveGroups = $top50Files | Group-Object Drive | Sort-Object Count -Descending
foreach ($group in $driveGroups) {
    Write-Host "   $($group.Name): $($group.Count) files" -ForegroundColor White
}
Write-Host ""

# Score range breakdown
Write-Host "📊 SCORE RANGE BREAKDOWN:" -ForegroundColor Cyan
$veryHigh = ($top50Files | Where-Object { $_.Score -ge 100 }).Count
$high = ($top50Files | Where-Object { $_.Score -ge 50 -and $_.Score -lt 100 }).Count
$medium = ($top50Files | Where-Object { $_.Score -ge 25 -and $_.Score -lt 50 }).Count
$low = ($top50Files | Where-Object { $_.Score -ge 1 -and $_.Score -lt 25 }).Count

Write-Host "   Very High (100+): $veryHigh files" -ForegroundColor Green
Write-Host "   High (50-99): $high files" -ForegroundColor Yellow
Write-Host "   Medium (25-49): $medium files" -ForegroundColor Cyan
Write-Host "   Low (1-24): $low files" -ForegroundColor Gray
Write-Host ""

# Missing files report
if ($missingFiles.Count -gt 0) {
    Write-Host "❌ MISSING FILES:" -ForegroundColor Red
    foreach ($missing in $missingFiles) {
        Write-Host "   Rank $($missing.Rank): $($missing.FileName)" -ForegroundColor Red
        Write-Host "      Path: $($missing.Path)" -ForegroundColor Gray
    }
    Write-Host ""
}

# Parse errors report
if ($parseErrors.Count -gt 0) {
    Write-Host "❌ PARSE ERRORS:" -ForegroundColor Red
    foreach ($error in $parseErrors) {
        Write-Host "   $error" -ForegroundColor Red
    }
    Write-Host ""
}

# Export data to JSON
$outputFile = Join-Path $scriptDir "top50_parsed_data.json"
try {
    $exportData = @{
        GeneratedDate = Get-Date
        Summary = $summary
        Files = $top50Files
        MissingFiles = $missingFiles
        ParseErrors = $parseErrors
    }
    
    $exportData | ConvertTo-Json -Depth 10 | Out-File $outputFile -Encoding UTF8
    Write-Host "💾 Data exported to: top50_parsed_data.json" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to export data: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "✅ Step 1.1 Complete!" -ForegroundColor Green
Write-Host "Next: Use the parsed data for Step 1.2 (Content Type Classification)" -ForegroundColor Cyan
"
