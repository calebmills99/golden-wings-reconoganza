[CmdletBinding()]
param(
    [string]$InputFile,
    [string]$ConfigFile,
    [switch]$NoPause
)

# Display header
Write-Host "📂 Step 1.2: Content Type Classification" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Resolve working directory and default paths relative to script location
$scriptDir = if ($PSScriptRoot) {
    $PSScriptRoot
} elseif ($MyInvocation.MyCommand.Path) {
    Split-Path -Path $MyInvocation.MyCommand.Path -Parent
} else {
    Get-Location | Select-Object -ExpandProperty Path
}

if ([string]::IsNullOrWhiteSpace($InputFile)) {
    $InputFile = Join-Path -Path $scriptDir -ChildPath "top50_parsed_data.json"
}

if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path -Path $scriptDir -ChildPath "content_classification_config.json"
}

Write-Host "📁 Working directory: $scriptDir" -ForegroundColor Cyan
Write-Host "📄 Reading parsed data: $InputFile" -ForegroundColor Cyan
Write-Host "🧠 Using classification config: $ConfigFile" -ForegroundColor Cyan
Write-Host ""

# Check if required files exist
if (-not (Test-Path -LiteralPath $InputFile)) {
    Write-Host "❌ ERROR: Parsed data file not found at '$InputFile'. Run Step 1.1 first or provide -InputFile." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $ConfigFile)) {
    Write-Host "❌ ERROR: Classification config file not found at '$ConfigFile'." -ForegroundColor Red
    exit 1
}

# Load the parsed data
try {
    $jsonContent = Get-Content -LiteralPath $InputFile -Raw -Encoding UTF8
    $parsedData = $jsonContent | ConvertFrom-Json -ErrorAction Stop
    $files = @($parsedData.Files)
    if (-not $files) {
        Write-Host "⚠️  WARNING: No file entries found in the parsed data." -ForegroundColor Yellow
        $files = @()
    }
    Write-Host "✅ Loaded $($files.Count) files from parsed data" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Failed to load parsed data - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Load classification configuration
try {
    $configContent = Get-Content -LiteralPath $ConfigFile -Raw -Encoding UTF8
    $config = $configContent | ConvertFrom-Json -ErrorAction Stop
} catch {
    Write-Host "❌ ERROR: Failed to load classification config - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

if (-not $config.Categories) {
    Write-Host "❌ ERROR: Config file is missing the 'Categories' section." -ForegroundColor Red
    exit 1
}

$definedCategoryNames = @($config.Categories.PSObject.Properties.Name)
if (-not $definedCategoryNames) {
    Write-Host "❌ ERROR: Config file does not define any categories." -ForegroundColor Red
    exit 1
}

$categoryPriority = @($config.CategoryPriority)
if (-not $categoryPriority -or $categoryPriority.Count -eq 0) {
    $categoryPriority = $definedCategoryNames
} else {
    foreach ($categoryName in $definedCategoryNames) {
        if ($categoryPriority -notcontains $categoryName) {
            $categoryPriority += $categoryName
        }
    }
}

# Compile triggers and metadata from config
$categoriesConfig = @{}
foreach ($categoryName in $categoryPriority) {
    $categoryNode = $config.Categories.PSObject.Properties[$categoryName]
    if (-not $categoryNode) {
        Write-Host "⚠️  WARNING: Category '$categoryName' listed in priority but missing from config. Skipping." -ForegroundColor Yellow
        continue
    }

    $categoryData = $categoryNode.Value
    $compiledTriggers = @()

    foreach ($trigger in @($categoryData.Triggers)) {
        if (-not $trigger.Type) { continue }
        $score = [int]$trigger.Score
        if ($score -le 0) { continue }

        switch ($trigger.Type.ToString().ToLowerInvariant()) {
            'regex' {
                if (-not $trigger.Pattern) { continue }
                $target = if ($trigger.Target) { $trigger.Target.ToString() } else { 'FileName' }
                try {
                    $regex = [regex]::new($trigger.Pattern.ToString(), [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
                    $compiledTriggers += [pscustomobject]@{
                        Type   = 'Regex'
                        Target = $target
                        Regex  = $regex
                        Score  = $score
                    }
                } catch {
                    Write-Host "⚠️  WARNING: Invalid regex pattern for category '$categoryName' - $($_.Exception.Message)" -ForegroundColor Yellow
                }
            }
            'keyword' {
                $values = @($trigger.Values) | ForEach-Object {
                    if ($_ -ne $null) { $_.ToString().ToLowerInvariant() }
                }
                if ($values.Count -gt 0) {
                    $compiledTriggers += [pscustomobject]@{
                        Type   = 'Keyword'
                        Values = $values
                        Score  = $score
                    }
                }
            }
            'extension' {
                $values = @($trigger.Values) | ForEach-Object {
                    if ($_ -eq $null) { return }
                    $value = $_.ToString()
                    if ($value -notlike '.*') { $value = '.{0}' -f $value }
                    $value.ToLowerInvariant()
                }
                if ($values.Count -gt 0) {
                    $compiledTriggers += [pscustomobject]@{
                        Type   = 'Extension'
                        Values = $values
                        Score  = $score
                    }
                }
            }
            default {
                Write-Host "⚠️  WARNING: Unsupported trigger type '$($trigger.Type)' in category '$categoryName'." -ForegroundColor Yellow
            }
        }
    }

    $categoriesConfig[$categoryName] = [pscustomobject]@{
        Triggers         = $compiledTriggers
        NamingConvention = $categoryData.NamingConvention
    }
}

# Initialize classification buckets
$classifications = [ordered]@{}
foreach ($categoryName in $categoryPriority) {
    if ($categoriesConfig.ContainsKey($categoryName)) {
        $classifications[$categoryName] = @()
    }
}
$classifications['Unknown'] = @()

$summary = [ordered]@{
    TotalClassified = 0
    ClassificationErrors = 0
}

Write-Host "🔍 Classifying $($files.Count) files by content type..." -ForegroundColor Cyan
Write-Host ""

# Process each file using configured scoring
foreach ($file in $files) {
    try {
        $fileName = [string]($file.FileName ?? '')
        $extension = [string]($file.Extension ?? '')
        $keywordsRaw = @($file.Keywords) | Where-Object { $_ -ne $null }
        $path = [string]($file.FullPath ?? '')

        $fileNameLower = $fileName.ToLowerInvariant()
        $extensionLower = $extension.ToLowerInvariant()
        if ($extensionLower -and $extensionLower -notlike '.*') {
            $extensionLower = '.{0}' -f $extensionLower
        }
        $pathValue = $path
        $keywordsLower = $keywordsRaw | ForEach-Object { $_.ToString().ToLowerInvariant() }

        Write-Host "📄 Rank $($file.Rank): $fileName" -ForegroundColor White

        $categoryScores = @{}
        foreach ($categoryName in $classifications.Keys) {
            if ($categoryName -eq 'Unknown') { continue }
            $categoryScores[$categoryName] = 0
        }

        foreach ($categoryName in $categoryPriority) {
            if (-not $categoriesConfig.ContainsKey($categoryName)) { continue }
            $categoryData = $categoriesConfig[$categoryName]
            foreach ($trigger in $categoryData.Triggers) {
                switch ($trigger.Type) {
                    'Regex' {
                        $targetValue = switch ($trigger.Target.ToLowerInvariant()) {
                            'path' { $pathValue }
                            'fullpath' { $pathValue }
                            default { $fileName }
                        }
                        if ($trigger.Regex.IsMatch($targetValue)) {
                            $categoryScores[$categoryName] += $trigger.Score
                        }
                    }
                    'Keyword' {
                        foreach ($value in $trigger.Values) {
                            if ($keywordsLower -contains $value) {
                                $categoryScores[$categoryName] += $trigger.Score
                                break
                            }
                        }
                    }
                    'Extension' {
                        if ($trigger.Values -contains $extensionLower) {
                            $categoryScores[$categoryName] += $trigger.Score
                        }
                    }
                }
            }
        }

        $category = 'Unknown'
        $bestScore = -1
        foreach ($categoryName in $categoryPriority) {
            if (-not $categoryScores.ContainsKey($categoryName)) { continue }
            $score = $categoryScores[$categoryName]
            if ($score -gt $bestScore) {
                $bestScore = $score
                $category = $categoryName
            }
        }

        if ($bestScore -le 0 -or -not $classifications.Contains($category)) {
            $category = 'Unknown'
        }

        $classifications[$category] += $file

        Write-Host "   🏷️  Category: $category" -ForegroundColor Green
        $summary.TotalClassified++

    } catch {
        Write-Host "❌ Classification error for $($file.FileName): $($_.Exception.Message)" -ForegroundColor Red
        $classifications['Unknown'] += $file
        $summary.ClassificationErrors++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "📊 CLASSIFICATION SUMMARY" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "📄 Total files classified: $($summary.TotalClassified)" -ForegroundColor Cyan
Write-Host "❌ Classification errors: $($summary.ClassificationErrors)" -ForegroundColor Red
Write-Host ""

# Display classification results (sorted by descending count)
Write-Host "📂 CONTENT TYPE BREAKDOWN:" -ForegroundColor Cyan
$orderedCategories = $classifications.Keys | Where-Object { $_ -ne 'Unknown' } | Sort-Object -Property @{ Expression = { $classifications[$_].Count }; Descending = $true }, @{ Expression = { $_ } }
foreach ($categoryName in $orderedCategories) {
    $items = $classifications[$categoryName]
    $count = $items.Count
    if ($count -gt 0) {
        Write-Host "   $categoryName`: $count files" -ForegroundColor White

        $topFiles = $items | Sort-Object -Property @{ Expression = { $_.Score }; Descending = $true }, @{ Expression = { $_.FileName } } | Select-Object -First 3
        foreach ($topFile in $topFiles) {
            $score = $topFile.Score
            if ($null -eq $score -or ($score -isnot [double] -and $score -isnot [int])) {
                $score = 'n/a'
            }
            Write-Host "      • $($topFile.FileName) (Score: $score)" -ForegroundColor Gray
        }
        Write-Host ""
    }
}

if ($classifications['Unknown'].Count -gt 0) {
    Write-Host "   Unknown: $($classifications['Unknown'].Count) files" -ForegroundColor White
    $topUnknown = $classifications['Unknown'] | Select-Object -First 3
    foreach ($topFile in $topUnknown) {
        Write-Host "      • $($topFile.FileName)" -ForegroundColor Gray
    }
    Write-Host ""
}

# Generate naming convention recommendations from config
Write-Host "🏷️  NAMING CONVENTION RECOMMENDATIONS:" -ForegroundColor Yellow
Write-Host ""

$namingConventions = [ordered]@{}
foreach ($categoryName in $categoryPriority) {
    if ($categoriesConfig.ContainsKey($categoryName)) {
        $naming = $categoriesConfig[$categoryName].NamingConvention
        if ($naming) {
            $namingConventions[$categoryName] = $naming
        }
    }
}

foreach ($categoryName in $namingConventions.Keys) {
    if ($classifications[$categoryName].Count -gt 0) {
        Write-Host "   $categoryName`:" -ForegroundColor Cyan
        Write-Host "      Convention: $($namingConventions[$categoryName])" -ForegroundColor White
        Write-Host ""
    }
}

# Export classification results
$outputFile = Join-Path -Path $scriptDir -ChildPath "content_classification_results.json"
try {
    $exportData = [ordered]@{
        GeneratedDate    = Get-Date
        Summary          = $summary
        Classifications  = @{}
        NamingConventions = $namingConventions
        ConfigUsed        = (Resolve-Path -LiteralPath $ConfigFile).Path
    }

    foreach ($categoryName in $classifications.Keys) {
        $exportData.Classifications[$categoryName] = $classifications[$categoryName]
    }

    $exportData | ConvertTo-Json -Depth 10 | Out-File -LiteralPath $outputFile -Encoding UTF8
    Write-Host "💾 Classification results exported to: $outputFile" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to export classification data: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎉 Step 1.2 Complete! Ready for Step 1.3 - Naming Convention Design" -ForegroundColor Green
Write-Host ""

if (-not $NoPause) {
    Write-Host "Press any key to exit..." -ForegroundColor Gray
    try {
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } catch {
        # Ignore when host doesn't support interactive key reads
    }
}



