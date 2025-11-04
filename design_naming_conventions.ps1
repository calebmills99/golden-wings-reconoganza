[CmdletBinding()]
param(
    [string]$InputFile,
    [string]$ConfigFile,
    [switch]$NoPause,
    [switch]$PreviewOnly
)

Write-Host "🏷️  Step 1.3: Naming Convention Design" -ForegroundColor Yellow
Write-Host "=====================================" -ForegroundColor Yellow
Write-Host ""

# Resolve working directory and default paths
$scriptDir = if ($PSScriptRoot) {
    $PSScriptRoot
} elseif ($MyInvocation.MyCommand.Path) {
    Split-Path -Path $MyInvocation.MyCommand.Path -Parent
} else {
    Get-Location | Select-Object -ExpandProperty Path
}

if ([string]::IsNullOrWhiteSpace($InputFile)) {
    $InputFile = Join-Path -Path $scriptDir -ChildPath "content_classification_results.json"
}

if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path -Path $scriptDir -ChildPath "naming_convention_config.json"
}

Write-Host "📁 Working directory: $scriptDir" -ForegroundColor Cyan
Write-Host "📄 Reading classification results: $InputFile" -ForegroundColor Cyan
Write-Host "🧠 Using naming config: $ConfigFile" -ForegroundColor Cyan
if ($PreviewOnly) {
    Write-Host "👁️  Preview mode: No files will be renamed" -ForegroundColor Yellow
}
Write-Host ""

# Ensure inputs exist
if (-not (Test-Path -LiteralPath $InputFile)) {
    Write-Host "❌ ERROR: Classification results file not found at '$InputFile'. Run Step 1.2 first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $ConfigFile)) {
    Write-Host "❌ ERROR: Naming convention config file not found at '$ConfigFile'." -ForegroundColor Red
    Write-Host "   Create one from the template in README_Step_1_3.md or copy the default repo version." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# Helper functions
function Convert-ToHashtable {
    param($InputObject)

    $hash = @{}
    if ($null -eq $InputObject) { return $hash }

    if ($InputObject -is [System.Collections.IDictionary]) {
        foreach ($key in $InputObject.Keys) {
            $hash[$key] = $InputObject[$key]
        }
        return $hash
    }

    foreach ($prop in $InputObject.PSObject.Properties) {
        $hash[$prop.Name] = $prop.Value
    }

    return $hash
}

function Convert-Rules {
    param($Rules)
    $result = @()
    foreach ($rule in @($Rules)) {
        if ($null -eq $rule) { continue }
        $result += [pscustomobject]@{
            Conditions = Convert-ToHashtable $rule.Condition
            Mapping    = Convert-ToHashtable $rule.Mapping
        }
    }
    return $result
}

function Get-DateFromFile {
    param(
        [string]$FileName,
        $ModifiedDate
    )

    $dateMatch = [regex]::Match($FileName, '(\d{4})(\d{2})(\d{2})|(\d{4})[-_](\d{2})[-_](\d{2})')
    if ($dateMatch.Success) {
        try {
            if ($dateMatch.Groups[1].Success) {
                return [datetime]::ParseExact(
                    "$($dateMatch.Groups[1].Value)$($dateMatch.Groups[2].Value)$($dateMatch.Groups[3].Value)",
                    'yyyyMMdd',
                    $null
                )
            }
            return [datetime]::ParseExact(
                "$($dateMatch.Groups[4].Value)-$($dateMatch.Groups[5].Value)-$($dateMatch.Groups[6].Value)",
                'yyyy-MM-dd',
                $null
            )
        } catch {
            # continue to fallbacks
        }
    }

    if ($ModifiedDate) {
        try {
            return [datetime]$ModifiedDate
        } catch {
            # continue to default
        }
    }

    return Get-Date
}

function Test-Condition {
    param(
        [string]$Key,
        $Value,
        $Context
    )

    switch ($Key.ToLowerInvariant()) {
        'filename' {
            return [regex]::IsMatch($Context.FileName, $Value, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        }
        'fullpath' {
            if ([string]::IsNullOrWhiteSpace($Context.FullPath)) { return $false }
            return [regex]::IsMatch($Context.FullPath, $Value, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        }
        'keywords' {
            $required = @($Value) | ForEach-Object { $_.ToString().ToLowerInvariant() }
            if ($required.Count -eq 0) { return $true }
            foreach ($keyword in $required) {
                if ($Context.Keywords -notcontains $keyword) {
                    return $false
                }
            }
            return $true
        }
        'extension' {
            $expected = $Value.ToString().TrimStart('.').ToLowerInvariant()
            return $Context.Extension -eq $expected
        }
        default {
            Write-Host "⚠️  WARNING: Unsupported condition '$Key'." -ForegroundColor Yellow
            return $false
        }
    }
}

function Copy-Hashtable {
    param([hashtable]$Source)
    $copy = @{}
    foreach ($key in $Source.Keys) {
        $copy[$key] = $Source[$key]
    }
    return $copy
}

function Apply-NamingRules {
    param(
        $CategoryConfig,
        $Context
    )

    foreach ($rule in $CategoryConfig.Rules) {
        $matchesAll = $true
        foreach ($conditionKey in $rule.Conditions.Keys) {
            if (-not (Test-Condition -Key $conditionKey -Value $rule.Conditions[$conditionKey] -Context $Context)) {
                $matchesAll = $false
                break
            }
        }

        if ($matchesAll) {
            return Copy-Hashtable (Convert-ToHashtable $rule.Mapping)
        }
    }

    return Copy-Hashtable (Convert-ToHashtable $CategoryConfig.DefaultMapping)
}

# ---------------------------------------------------------------------------
# Load classification results
try {
    $jsonContent = Get-Content -LiteralPath $InputFile -Raw -Encoding UTF8
    $classificationData = $jsonContent | ConvertFrom-Json -ErrorAction Stop
    Write-Host "✅ Loaded classification results" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Failed to load classification results - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Load naming configuration
try {
    $configContent = Get-Content -LiteralPath $ConfigFile -Raw -Encoding UTF8
    $namingConfig = $configContent | ConvertFrom-Json -ErrorAction Stop
    Write-Host "✅ Loaded naming convention config" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Failed to load naming config - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

if (-not $namingConfig.NamingRules) {
    Write-Host "❌ ERROR: Config missing 'NamingRules'." -ForegroundColor Red
    exit 1
}

$globalSettings = Convert-ToHashtable $namingConfig.GlobalSettings
if (-not $globalSettings.ContainsKey('DateFormat')) { $globalSettings['DateFormat'] = 'yyyy-MM-dd' }
if (-not $globalSettings.ContainsKey('HandleDuplicates')) { $globalSettings['HandleDuplicates'] = 'AddVersion' }
if (-not $globalSettings.ContainsKey('PreservePaths')) { $globalSettings['PreservePaths'] = $true }

$categoryConfigs = @{}
foreach ($categoryProp in $namingConfig.NamingRules.PSObject.Properties) {
    $categoryConfigs[$categoryProp.Name] = [pscustomobject]@{
        Pattern        = $categoryProp.Value.Pattern
        Rules          = Convert-Rules $categoryProp.Value.Rules
        DefaultMapping = Convert-ToHashtable $categoryProp.Value.DefaultMapping
    }
}

Write-Host ""
Write-Host "🔍 Processing files for rename mapping..." -ForegroundColor Cyan
Write-Host ""

$renameMappings = [System.Collections.Generic.List[object]]::new()
$summary = [ordered]@{
    TotalFiles   = 0
    FilesRenamed = 0
    Conflicts    = 0
    Errors       = 0
}

$classificationProperties = $classificationData.Classifications.PSObject.Properties

foreach ($categoryProperty in $classificationProperties) {
    $categoryName = $categoryProperty.Name
    $files = @($categoryProperty.Value)
    if (-not $files -or $files.Count -eq 0) { continue }

    if (-not $categoryConfigs.ContainsKey($categoryName)) {
        Write-Host "⚠️  WARNING: No naming rules configured for category '$categoryName'. Skipping." -ForegroundColor Yellow
        $summary.Errors += $files.Count
        continue
    }

    $categoryConfig = $categoryConfigs[$categoryName]
    if ([string]::IsNullOrWhiteSpace($categoryConfig.Pattern)) {
        Write-Host "⚠️  WARNING: Category '$categoryName' is missing a pattern. Skipping." -ForegroundColor Yellow
        $summary.Errors += $files.Count
        continue
    }

    Write-Host "📂 Processing $categoryName ($($files.Count) files):" -ForegroundColor White

    foreach ($file in $files) {
        try {
            $summary.TotalFiles++

            $extensionValue = ''
            if ($file.Extension) {
                $extensionValue = $file.Extension.ToString().TrimStart('.').ToLowerInvariant()
            }

            $keywords = @($file.Keywords) | Where-Object { $_ -ne $null } | ForEach-Object { $_.ToString().ToLowerInvariant() }

            $context = [pscustomobject]@{
                FileName  = [string]$file.FileName
                FullPath  = [string]$file.FullPath
                Extension = $extensionValue
                Keywords  = $keywords
            }

            $mapping = Apply-NamingRules -CategoryConfig $categoryConfig -Context $context

            if ($categoryConfig.Pattern -like '*{Date}*' -and -not $mapping.ContainsKey('Date')) {
                $fileDate = Get-DateFromFile -FileName $file.FileName -ModifiedDate $file.Modified
                $mapping['Date'] = $fileDate.ToString($globalSettings['DateFormat'])
            }

            if ($categoryConfig.Pattern -like '*{ext}*' -and -not $mapping.ContainsKey('ext')) {
                $mapping['ext'] = $extensionValue
            }

            if ($categoryConfig.Pattern -like '*{Rank}*' -and -not $mapping.ContainsKey('Rank')) {
                $mapping['Rank'] = [string]$file.Rank
            }

            $newFileName = $categoryConfig.Pattern
            foreach ($key in $mapping.Keys) {
                $placeholder = "{${key}}"
                $value = if ($null -ne $mapping[$key] -and $mapping[$key].ToString().Length -gt 0) {
                    $mapping[$key].ToString()
                } else {
                    'Unknown'
                }
                $newFileName = $newFileName.Replace($placeholder, $value)
            }

            $newFileName = [regex]::Replace($newFileName, '\{[^}]+\}', 'Unknown')

            if (-not $newFileName) {
                throw "Failed to build new file name from pattern '$($categoryConfig.Pattern)'"
            }

            $destinationDirectory = if ($globalSettings['PreservePaths']) {
                if ($file.FullPath) {
                    Split-Path -Path $file.FullPath -Parent
                } else {
                    $scriptDir
                }
            } else {
                $scriptDir
            }

            $renameMappings.Add([pscustomobject]@{
                OriginalFile = $file
                Category     = $categoryName
                OldFileName  = $file.FileName
                NewFileName  = $newFileName
                OldPath      = $file.FullPath
                NewPath      = Join-Path -Path $destinationDirectory -ChildPath $newFileName
                Mapping      = $mapping
                PatternUsed  = $categoryConfig.Pattern
            })

            $summary.FilesRenamed++
            Write-Host "   ✅ $($file.FileName) → $newFileName" -ForegroundColor Green
        } catch {
            Write-Host "   ❌ Error processing $($file.FileName): $($_.Exception.Message)" -ForegroundColor Red
            $summary.Errors++
        }
    }

    Write-Host ""
}

# ---------------------------------------------------------------------------
# Resolve naming conflicts
Write-Host "🔍 Checking for naming conflicts..." -ForegroundColor Cyan
$conflictGroups = $renameMappings | Group-Object NewPath | Where-Object { $_.Count -gt 1 }

if ($conflictGroups.Count -gt 0) {
    Write-Host "⚠️  Found $($conflictGroups.Count) naming conflicts:" -ForegroundColor Yellow

    foreach ($group in $conflictGroups) {
        Write-Host "   Conflict: $($group.Name)" -ForegroundColor Red
        $items = $group.Group | Sort-Object -Property { $_.OriginalFile.Score } -Descending

        for ($i = 0; $i -lt $items.Count; $i++) {
            $item = $items[$i]
            Write-Host "      • $($item.OldFileName) (Rank $($item.OriginalFile.Rank))" -ForegroundColor Gray

            if ($i -gt 0) {
                switch ($globalSettings['HandleDuplicates']) {
                    'AddVersion' {
                        $extension = [System.IO.Path]::GetExtension($item.NewFileName)
                        $nameWithoutExt = [System.IO.Path]::GetFileNameWithoutExtension($item.NewFileName)
                        $item.NewFileName = '{0}_v{1}{2}' -f $nameWithoutExt, ($i + 1), $extension
                        $item.NewPath = Join-Path -Path (Split-Path -Path $item.NewPath -Parent) -ChildPath $item.NewFileName
                        Write-Host "      → Resolved to: $($item.NewFileName)" -ForegroundColor Green
                    }
                    'AppendRank' {
                        $extension = [System.IO.Path]::GetExtension($item.NewFileName)
                        $nameWithoutExt = [System.IO.Path]::GetFileNameWithoutExtension($item.NewFileName)
                        $item.NewFileName = '{0}_rank{1}{2}' -f $nameWithoutExt, $item.OriginalFile.Rank, $extension
                        $item.NewPath = Join-Path -Path (Split-Path -Path $item.NewPath -Parent) -ChildPath $item.NewFileName
                        Write-Host "      → Resolved to: $($item.NewFileName)" -ForegroundColor Green
                    }
                    default {
                        Write-Host "      → Duplicate handling set to '$($globalSettings['HandleDuplicates'])' - no automatic fix applied." -ForegroundColor Yellow
                    }
                }
            }
        }

        $summary.Conflicts++
    }

    Write-Host ""
} else {
    Write-Host "✅ No naming conflicts detected." -ForegroundColor Green
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Summary
Write-Host "=====================================" -ForegroundColor Yellow
Write-Host "📊 NAMING CONVENTION SUMMARY" -ForegroundColor Yellow
Write-Host "=====================================" -ForegroundColor Yellow
Write-Host "📄 Total files processed: $($summary.TotalFiles)" -ForegroundColor Cyan
Write-Host "✅ Files with new names: $($summary.FilesRenamed)" -ForegroundColor Green
Write-Host "⚠️  Naming conflicts resolved: $($summary.Conflicts)" -ForegroundColor Yellow
Write-Host "❌ Processing errors: $($summary.Errors)" -ForegroundColor Red
Write-Host ""

# ---------------------------------------------------------------------------
# Export rename mappings
$outputFile = Join-Path -Path $scriptDir -ChildPath "rename_mappings.json"
try {
    $exportData = [ordered]@{
        GeneratedDate  = Get-Date
        Summary        = $summary
        RenameMappings = $renameMappings
        ConfigUsed     = (Resolve-Path -LiteralPath $ConfigFile).Path
        PreviewOnly    = $PreviewOnly.IsPresent
    }

    $exportData | ConvertTo-Json -Depth 10 | Out-File -LiteralPath $outputFile -Encoding UTF8
    Write-Host "💾 Rename mappings exported to: $outputFile" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to export rename mappings: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎉 Step 1.3 Complete! Ready for Step 1.4 - Generate Rename Script" -ForegroundColor Green
Write-Host ""

if (-not $NoPause) {
    Write-Host "Press any key to exit..." -ForegroundColor Gray
    try {
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } catch {
        # Ignore when host doesn't support interactive key reads
    }
}
