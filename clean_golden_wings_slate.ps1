# GOLDEN WINGS CLEAN SLATE SCRIPT
# Time to blow away all the old bullshit!

Write-Host "`n🧹 GOLDEN WINGS CLEAN SLATE OPERATION" -ForegroundColor Yellow
Write-Host "=" * 50 -ForegroundColor DarkGray
Write-Host "Destroying all old scan results..." -ForegroundColor Cyan

$targetDir = "D:\golden-wings-reconoganza"

# Files to DELETE (old results)
$filesToDelete = @(
    "golden-wings-content-inventory.json",
    "CONTENT-SUMMARY.md", 
    "content-inventory.csv",
    "content_classification_results.json",
    "rename_mappings.json",
    "rename_plan_*.json",
    "execute_renames_*.py",
    "README_Step_1_4_RUN.txt",
    "top*_parsed_data_*.json",
    "TOP*.md",
    "digital_empire.json",
    "empire_report.txt",
    "golden_wings_files.txt",
    "PathShortener.db",
    "*.log"
)

# Navigate to the directory
if (Test-Path $targetDir) {
    Push-Location $targetDir
    
    Write-Host "`n📁 Cleaning in: $targetDir" -ForegroundColor Green
    
    $deletedCount = 0
    foreach ($pattern in $filesToDelete) {
        $files = Get-ChildItem -Path . -Filter $pattern -ErrorAction SilentlyContinue
        if ($files) {
            Write-Host "  ❌ Deleting: $pattern ($($files.Count) files)" -ForegroundColor Red
            Remove-Item $pattern -Force -ErrorAction SilentlyContinue
            $deletedCount += $files.Count
        }
    }
    
    # Clean up any logs directory
    if (Test-Path "logs") {
        Write-Host "  ❌ Deleting: logs directory" -ForegroundColor Red
        Remove-Item "logs" -Recurse -Force -ErrorAction SilentlyContinue
        $deletedCount++
    }
    
    # Clean up any backup directories
    $backupDirs = Get-ChildItem -Directory -Filter "backup_*" -ErrorAction SilentlyContinue
    if ($backupDirs) {
        Write-Host "  ❌ Deleting: $($backupDirs.Count) backup directories" -ForegroundColor Red
        $backupDirs | Remove-Item -Recurse -Force
        $deletedCount += $backupDirs.Count
    }
    
    Write-Host "`n✨ CLEAN SLATE ACHIEVED!" -ForegroundColor Green
    Write-Host "   Deleted $deletedCount items total" -ForegroundColor Yellow
    
    # Show what's left
    Write-Host "`n📂 What's still here (your actual code):" -ForegroundColor Cyan
    Write-Host "-" * 40 -ForegroundColor DarkGray
    
    Get-ChildItem -File | Where-Object { 
        $_.Extension -in @('.js', '.py', '.ps1', '.md', '.json') -and 
        $_.Name -notlike 'rename_*' -and 
        $_.Name -notlike 'top*' -and
        $_.Name -notlike 'golden-wings-content*' -and
        $_.Name -notlike 'content_*'
    } | Select-Object Name, @{N='Size (KB)';E={[math]::Round($_.Length/1KB, 2)}} | 
        Format-Table -AutoSize
    
    Write-Host "`n🚀 NEXT STEP:" -ForegroundColor Magenta
    Write-Host "   Run: npm run workflow" -ForegroundColor White
    Write-Host "   Or:  npm run hunt" -ForegroundColor White
    Write-Host ""
    
    Pop-Location
    
} else {
    Write-Host "❌ ERROR: Can't find $targetDir" -ForegroundColor Red
    Write-Host ""
    Write-Host "Current location: $(Get-Location)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Try one of these:" -ForegroundColor Cyan
    Write-Host "  1. cd to where you moved golden-wings-reconoganza" -ForegroundColor White
    Write-Host "  2. Update the `$targetDir variable in this script" -ForegroundColor White
    Write-Host "  3. Run this script from inside the project directory" -ForegroundColor White
}
