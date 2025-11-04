# PowerShell script for Step 1.1: Parse TOP50.md Structure
# Golden Wings Documentary - File Organization Project
# Author: AI Assistant for Caleb Stewart
# Date: September 26, 2025

Write-Host "🔍 Step 1.1: Parse TOP50.md Structure" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Yellow
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

# Regex patterns for data extraction
$entryPattern = '(?s)## (\d+)\.\s*(.+?)\n\n\*\*Score:\*\*\s*(\d+).*?\n\*\*Path:\*\*\s*`([^`]+)`\n\*\*Size:\*\*\s*([^\n]+)\n\*\*Modified:\*\*\s*([^\n]+)\n\*\*Keywords:\*\*\s*([^\n]+)'

# Find all entries
$entryMatches = [regex]::Matches($content, $entryPattern)

Write-Host "🔢 Found $($entryMatches.Count) entries in TOP50.md" -ForegroundColor Cyan
Write-Host ""

# Process each match
foreach ($match in $entryMatches) {
    try {
        $rank = [int]$match.Groups[1].Value
        $fileName = $match.Groups[2].Value.Trim()
        $score = [int]$match.Groups[3].Value
        $fullPath = $match.Groups[4].Value.Trim()
        $sizeStr = $match.Groups[5].Value.Trim()
        $modifiedStr = $match.Groups[6].Value.Trim()
        $keywordsStr = $match.Groups[7].Value.Trim()

        # Skip ranks 1-4 (already processed)
        if ($rank -le 4) {
            Write-Host "⏭️  Rank $rank`: $fileName (SKIPPED - already processed)" -ForegroundColor Yellow
            $summary.SkippedRanks++
            continue
        }

        Write-Host "📄 Rank $rank`: $fileName" -ForegroundColor White

        # Parse file details
        $directory = Split-Path $fullPath -Parent
        $extension = [System.IO.Path]::GetExtension($fileName).ToLower()
        $driveMatch = [regex]::Match($fullPath, '^([A-Z]:)')
        $drive = if ($driveMatch.Success) { $driveMatch.Groups[1].Value } else { "Unknown" }

        # Parse size to bytes
        $sizeBytes = 0
        $sizeMatch = [regex]::Match($sizeStr, '(?i)(\d+\.?\d*)\s*(KB|MB|GB|bytes?)')
        if ($sizeMatch.Success) {
            $sizeNum = [double]$sizeMatch.Groups[1].Value
            $sizeUnit = $sizeMatch.Groups[2].Value.ToUpper()
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
            $modifiedDate = [datetime]::Parse($modifiedStr)
        } catch {
            Write-Host "   ⚠️  Could not parse date: $modifiedStr" -ForegroundColor Yellow
        }

        # Parse keywords
        $keywords = $keywordsStr -split ',\s*' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }

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
                Score = $score
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
            Size = $sizeStr
            SizeBytes = $sizeBytes
            Modified = $modifiedDate
            Keywords = $keywords
            Extension = $extension
            Drive = $drive
            Exists = $fileExists
        }

        $top50Files += $fileData
        $summary.TotalParsed++

    } catch {
        Write-Host "❌ Parse error for entry $($match.Groups[1].Value): $($_.Exception.Message)" -ForegroundColor Red
        $parseErrors += @{
            Rank = $match.Groups[1].Value
            Error = $_.Exception.Message
            RawMatch = $match.Value.Substring(0, [Math]::Min(200, $match.Value.Length))
        }
        $summary.ParseErrors++
    }
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Yellow
Write-Host "📊 PARSING SUMMARY" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Yellow
Write-Host "📄 Total entries parsed: $($summary.TotalParsed)" -ForegroundColor Cyan
Write-Host "✅ Files found: $($summary.FilesFound)" -ForegroundColor Green
Write-Host "❌ Files missing: $($summary.FilesMissing)" -ForegroundColor Red
Write-Host "⏭️  Entries skipped (ranks 1-4): $($summary.SkippedRanks)" -ForegroundColor Yellow
Write-Host "❌ Parse errors: $($summary.ParseErrors)" -ForegroundColor Red
Write-Host ""

# Generate breakdown by file type
$extensionCounts = $top50Files | Group-Object Extension | Sort-Object Count -Descending
Write-Host "📁 FILE TYPE BREAKDOWN:" -ForegroundColor Cyan
foreach ($ext in $extensionCounts) {
    Write-Host "   $($ext.Name): $($ext.Count) files" -ForegroundColor White
}
Write-Host ""

# Generate breakdown by drive
$driveCounts = $top50Files | Group-Object Drive | Sort-Object Count -Descending
Write-Host "💽 DRIVE BREAKDOWN:" -ForegroundColor Cyan
foreach ($drive in $driveCounts) {
    Write-Host "   $($drive.Name): $($drive.Count) files" -ForegroundColor White
}
Write-Host ""

# Generate breakdown by score ranges
$scoreRanges = @{
    "Very High (100+)" = ($top50Files | Where-Object { $_.Score -ge 100 }).Count
    "High (50-99)" = ($top50Files | Where-Object { $_.Score -ge 50 -and $_.Score -lt 100 }).Count
    "Medium (25-49)" = ($top50Files | Where-Object { $_.Score -ge 25 -and $_.Score -lt 50 }).Count
    "Low (1-24)" = ($top50Files | Where-Object { $_.Score -ge 1 -and $_.Score -lt 25 }).Count
}

Write-Host "📊 SCORE RANGE BREAKDOWN:" -ForegroundColor Cyan
foreach ($range in $scoreRanges.GetEnumerator() | Sort-Object Value -Descending) {
    Write-Host "   $($range.Key): $($range.Value) files" -ForegroundColor White
}
Write-Host ""

# Show missing files if any
if ($missingFiles.Count -gt 0) {
    Write-Host "❌ MISSING FILES:" -ForegroundColor Red
    foreach ($missing in $missingFiles) {
        Write-Host "   Rank $($missing.Rank): $($missing.FileName)" -ForegroundColor Red
        Write-Host "      Path: $($missing.Path)" -ForegroundColor Gray
    }
    Write-Host ""
}

# Show parse errors if any
if ($parseErrors.Count -gt 0) {
    Write-Host "❌ PARSE ERRORS:" -ForegroundColor Red
    foreach ($error in $parseErrors) {
        Write-Host "   Rank $($error.Rank): $($error.Error)" -ForegroundColor Red
    }
    Write-Host ""
}

# Export data for next steps
$outputFile = Join-Path $scriptDir "top50_parsed_data.json"
try {
    $exportData = @{
        Summary = $summary
        Files = $top50Files
        MissingFiles = $missingFiles
        ParseErrors = $parseErrors
        GeneratedDate = Get-Date
    }
    
    $exportData | ConvertTo-Json -Depth 10 | Out-File $outputFile -Encoding UTF8
    Write-Host "💾 Parsed data exported to: top50_parsed_data.json" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to export data: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎉 Step 1.1 Complete! Ready for Step 1.2 - Content Type Classification" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

