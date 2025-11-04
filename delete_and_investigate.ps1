# GOLDEN WINGS - DELETE THE BULLSHIT & CHECK CONFIG
Write-Host "`n🔍 INVESTIGATION & DESTRUCTION SCRIPT" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor DarkGray

$targetDir = "D:\golden-wings-reconoganza"
Set-Location $targetDir

# PART 1: Check what npm run hunt actually does
Write-Host "`n📦 CHECKING PACKAGE.JSON..." -ForegroundColor Cyan
if (Test-Path ".\package.json") {
    $packageJson = Get-Content ".\package.json" | ConvertFrom-Json
    
    Write-Host "`nScripts found in package.json:" -ForegroundColor Green
    if ($packageJson.scripts) {
        if ($packageJson.scripts.hunt) {
            Write-Host "  npm run hunt = " -NoNewline -ForegroundColor Yellow
            Write-Host $packageJson.scripts.hunt -ForegroundColor White
        }
        if ($packageJson.scripts.workflow) {
            Write-Host "  npm run workflow = " -NoNewline -ForegroundColor Yellow
            Write-Host $packageJson.scripts.workflow -ForegroundColor White
        }
        if ($packageJson.scripts.notion) {
            Write-Host "  npm run notion = " -NoNewline -ForegroundColor Yellow
            Write-Host $packageJson.scripts.notion -ForegroundColor White
        }
        
        # Show all scripts
        Write-Host "`nAll available scripts:" -ForegroundColor Magenta
        $packageJson.scripts.PSObject.Properties | ForEach-Object {
            Write-Host "  $($_.Name): $($_.Value)" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  ❌ No package.json found!" -ForegroundColor Red
}

# PART 2: Check which content-hunter script exists
Write-Host "`n📁 CHECKING WHICH HUNTER SCRIPTS EXIST..." -ForegroundColor Cyan
$hunterScripts = @(
    "content-hunter.js",
    "content-hunter-fixed.js", 
    "content-hunter-enhanced.js",
    "simple-content-hunter.js"
)

foreach ($script in $hunterScripts) {
    if (Test-Path ".\$script") {
        $fileInfo = Get-Item ".\$script"
        Write-Host "  ✅ Found: $script ($('{0:N0}' -f ($fileInfo.Length / 1KB)) KB)" -ForegroundColor Green
    }
}

# PART 3: DELETE THE NARCISSISTIC BULLSHIT
Write-Host "`n💥 DELETING SELF-GENERATED GARBAGE..." -ForegroundColor Red

$deletePatterns = @(
    "GW_System_System*.json",
    "content_classification*.json",
    "duplicate_analysis*.json", 
    "current_files_analysis*.json",
    "top*parsed*.json",
    "top*fixed*.json",
    "top*ai*.json",
    "top*fresh*.json",
    "TOP*.md",
    "TOP*.json",
    "*_final_*.json",
    "*_fixed_*.json",
    "*_fresh_*.json",
    "*_v[0-9].json",
    "*_v[0-9][0-9].json",
    "rename_mappings.json",
    "rename_plan_*.json",
    "execute_renames_*.py",
    "golden-wings-content-inventory.json",
    "CONTENT-SUMMARY.md",
    "content-inventory.csv",
    "file_improvement_plan*.json",
    "conversation_summaries*.json",
    "*_analysis_*.json",
    "*_results*.json",
    "*_processed_*.json",
    "*_extracted_*.json",
    "PathShortener.db",
    "*.log"
)

$deletedCount = 0

foreach ($pattern in $deletePatterns) {
    $files = Get-ChildItem -Path . -Filter $pattern -File -ErrorAction SilentlyContinue
    
    if ($files) {
        foreach ($file in $files) {
            Remove-Item -Path $file.FullName -Force
            Write-Host "  ❌ DELETED: $($file.Name)" -ForegroundColor Red
            $deletedCount++
        }
    }
}

# Delete the claude_extracted folder
if (Test-Path ".\claude_extracted") {
    Remove-Item -Path ".\claude_extracted" -Recurse -Force
    Write-Host "  ❌ DELETED: claude_extracted folder" -ForegroundColor Red
    $deletedCount++
}

Write-Host "`n✅ DESTRUCTION COMPLETE!" -ForegroundColor Green
Write-Host "   Deleted $deletedCount items" -ForegroundColor Yellow

# PART 4: Show what's left
Write-Host "`n📂 SURVIVORS (your actual code):" -ForegroundColor Cyan
Get-ChildItem -File | Where-Object { 
    $_.Extension -in @('.js', '.py', '.ps1', '.md', '.txt', '.json') -and
    $_.Name -notlike "*classification*" -and
    $_.Name -notlike "*analysis*" -and
    $_.Name -notlike "TOP*" -and
    $_.Name -notlike "*_parsed*"
} | Select-Object Name, @{N='Size (KB)';E={[math]::Round($_.Length/1KB, 2)}} | 
    Format-Table -AutoSize

Write-Host "`n💡 RECOMMENDATION:" -ForegroundColor Magenta
Write-Host "  Edit your content-hunter script to:" -ForegroundColor White
Write-Host "  1. Skip files with score > 400 (probably self-generated)" -ForegroundColor White
Write-Host "  2. Add .huntignore support if it doesn't have it" -ForegroundColor White
Write-Host "  3. Exclude its own output files" -ForegroundColor White
