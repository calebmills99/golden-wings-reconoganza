<#
Requires: Administrator (the script will self-elevate if needed)
Purpose: Grant Everyone Full Control on target drives, recursively
WARNING: Insecure on purpose. Use ONLY on disposable/wipe-target drives.

Examples:
  .\scripts\make-EF-world-writable.ps1 -Drives E,F -TakeOwnership -Force
  .\scripts\make-EF-world-writable.ps1 -Drives E:\,G: -Force

Tip: Use the companion .cmd wrapper to launch with execution policy bypass:
  scripts\make-EF-world-writable.cmd -Drives E,F -TakeOwnership -Force
#>

param(
  [Parameter(HelpMessage = "Drive letters or roots (e.g. E, E:, E:\\)")]
  [string[]]$Drives = @('E','F'),

  [Parameter(HelpMessage = "Also take ownership recursively before ACL changes")]
  [switch]$TakeOwnership,

  [Parameter(HelpMessage = "Do not prompt for confirmation")]
  [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info($msg)  { Write-Host $msg -ForegroundColor Cyan }
function Write-Good($msg)  { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host $msg -ForegroundColor Yellow }
function Write-Bad($msg)   { Write-Host $msg -ForegroundColor Red }

function Normalize-Drive([string]$d) {
  if ([string]::IsNullOrWhiteSpace($d)) { return $null }
  $d = $d.Trim()
  # Allow forms: E | E: | E:\ | E:\folder (we'll trim to root)
  if ($d.Length -eq 1) { $d = "$d:" }
  if ($d.Length -ge 2 -and $d[1] -eq ':') {
    # Strip any path beyond the root
    $d = ($d.Substring(0,2) + '\\')
  }
  return $d
}

function Ensure-Elevated {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($id)
  if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { return }

  Write-Warn "Elevation required. Relaunching as Administrator..."

  # Rebuild argument list from current bound parameters and args
  $argList = @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$PSCommandPath`"")
  foreach ($kvp in $PSBoundParameters.GetEnumerator()) {
    $name = $kvp.Key
    $value = $kvp.Value
    if ($null -eq $value) { continue }
    if ($value -is [switch]) {
      if ($value.IsPresent) { $argList += "-$name" }
      continue
    }
    if ($value -is [Array]) {
      foreach ($v in $value) { $argList += "-$name"; $argList += "`"$v`"" }
      continue
    }
    $argList += "-$name"; $argList += "`"$value`""
  }
  foreach ($a in $args) { $argList += "`"$a`"" }

  Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $argList | Out-Null
  exit
}

function Ensure-DriveExists($drive) {
  if (-not (Test-Path -LiteralPath $drive)) {
    Write-Warn "Skipping $drive (not found)."
    return $false
  }
  return $true
}

function Run-External($file, [string[]]$args) {
  & $file @args | Out-Null
  $code = $LASTEXITCODE
  if ($code -ne 0) { throw "$file exited with code $code" }
}

function Make-WorldWritable($drive) {
  if (-not (Ensure-DriveExists $drive)) { return }

  if ($TakeOwnership) {
    Write-Info "Taking ownership of $drive (recursively)..."
    try {
      Run-External 'takeown.exe' @('/F', $drive, '/R', '/D', 'Y')
    } catch { Write-Warn "takeown error on $drive: $_" }
  }

  Write-Info "Granting Everyone:(OI)(CI)F on $drive (this may take a while)..."
  try {
    Run-External 'icacls.exe' @($drive, '/grant', '*S-1-1-0:(OI)(CI)F', '/T', '/C')
    Write-Good "Done: $drive"
  } catch {
    Write-Bad "icacls error on $drive: $_"
  }
}

Ensure-Elevated

# Normalize and de-dup drives
$normalized = @()
foreach ($d in $Drives) {
  $n = Normalize-Drive $d
  if ($n -and -not ($normalized -contains $n)) { $normalized += $n }
}
if (-not $normalized -or $normalized.Count -eq 0) { throw "No valid drives specified." }

if (-not $Force) {
  $list = ($normalized -join ', ')
  Write-Warn "About to grant Everyone FULL CONTROL recursively on: $list"
  $confirm = Read-Host "Type YES to continue"
  if ($confirm -ne 'YES') { Write-Warn 'Aborted by user.'; exit 1 }
}

foreach ($drive in $normalized) { Make-WorldWritable $drive }

Write-Good "Completed ACL updates."
