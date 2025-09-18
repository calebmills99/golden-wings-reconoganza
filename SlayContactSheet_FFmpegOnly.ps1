<#
SlayContactSheet_FFmpegOnly.ps1

Generates a contact sheet (thumbnail grid) from video files using FFmpeg only
(optionally using ffprobe for metadata). Works on Windows PowerShell/PowerShell 7.

Features:
- Evenly-spaced frames between configurable start/end percentages, or every Nth frame in a time range
- Configurable columns/rows, cell width, padding, margins, background
- Optional per-frame timestamps and header text with file metadata
- Batch process files or folders
 - Interactive mode for prompts if you prefer not to pass flags

Requirements:
- ffmpeg in PATH (required)
- ffprobe in PATH (recommended for duration/resolution)

Examples:
  # Single file, default grid 6x4, 320px cells
  .\SlayContactSheet_FFmpegOnly.ps1 -Path .\video.mp4

  # Custom grid and output folder
  .\SlayContactSheet_FFmpegOnly.ps1 -Path .\clips -OutDir .\sheets -Cols 5 -Rows 5 -CellWidth 300

  # Disable timestamps and header
  .\SlayContactSheet_FFmpegOnly.ps1 -Path .\movie.mkv -NoTimestamps -NoHeader

  # Interactive prompts (no flags required)
  .\SlayContactSheet_FFmpegOnly.ps1 -Interactive

  # Every 12th frame from 16s to 37s (fills grid)
  .\SlayContactSheet_FFmpegOnly.ps1 -Path .\video.mp4 -StartTime 16 -EndTime 37 -EveryNthFrame 12
#>

[CmdletBinding()]
param(
  [Parameter(Position=0, Mandatory=$false, ValueFromPipeline=$true, ValueFromPipelineByPropertyName=$true)]
  [Alias('FullName')]
  [string[]]$Path,

  [string]$OutDir = (Join-Path -Path (Get-Location) -ChildPath 'contact_sheets'),

  [int]$Cols = 6,
  [int]$Rows = 5,
  [int]$CellWidth = 0,              # 0 = auto by TargetWidth
  [int]$TargetWidth = 1920,         # desired final sheet width
  [int]$Padding = 2,
  [int]$Margin = 10,
  [string]$Background = '#202020',

  [double]$StartPercent = 3.0,
  [double]$EndPercent = 97.0,

  # Optional explicit time range (seconds). If both set (>= 0), overrides Start/EndPercent
  [double]$StartTime = -1,
  [double]$EndTime = -1,

  # Optional: pick every Nth frame (within the chosen time range)
  [int]$EveryNthFrame = 0,

  [switch]$NoTimestamps,
  [int]$TimestampFontSize = 18,
  [string]$TimestampColor = '#EEEEEE',
  [string]$TimestampY = 'h-5-text_h',

  [switch]$NoHeader,
  [int]$HeaderFontSize = 22,
  [string]$HeaderColor = '#FFFFFF',

  [string]$Font = 'C:/Windows/Fonts/arial.ttf',
  [ValidateSet('jpg','png')]
  [string]$ImageFormat = 'jpg',

  [int]$JpegQuality = 2,            # 2(best)..31(worst)
  [ValidateRange(0,9)]
  [int]$PngCompression = 6,

  [switch]$SkipExisting,

  [switch]$Recurse,

  # Interactive mode: prompt for inputs if not provided
  [switch]$Interactive
)

begin {
  function Assert-Tool($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
      throw "Required tool '$name' not found in PATH. Please install and try again."
    }
  }

  function Try-Tool($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
  }

  function Get-VideoMeta {
    param([string]$File)
    $hasFfprobe = Try-Tool 'ffprobe'
    $duration = $null
    $dim = $null
    if ($hasFfprobe) {
      try {
        $durationStr = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 -- "$File" 2>$null
        if ($durationStr) { [double]::TryParse($durationStr, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$duration) | Out-Null }
      } catch { }
      try {
        $dim = & ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 -- "$File" 2>$null
      } catch { }
    }
    [pscustomobject]@{
      Duration = $duration  # seconds (double) or $null if unknown
      Dimensions = $dim     # e.g. "1920x1080" or $null
    }
  }

  function Escape-DrawText([string]$s) {
    if ($null -eq $s) { return '' }
    $s = $s -replace '\\','\\\\'   # escape backslashes
    $s = $s -replace "'","\\'"        # escape single quotes
    $s = $s -replace ':','\:'          # escape colons
    return $s
  }

  function Normalize-FontPath([string]$p) {
    if ([string]::IsNullOrWhiteSpace($p)) { return $p }
    $p = $p -replace '\\','/'
    # Escape the drive letter colon (e.g., C:/ -> C\:/)
    $p = [regex]::Replace($p, '^(?<drive>[A-Za-z]):', { param($m) $m.Groups['drive'].Value + '\:' })
    return $p
  }

  function Start-Interactive {
    Write-Host "Interactive mode — press Enter to accept defaults." -ForegroundColor Cyan
    $p = Read-Host ("Path to file or folder [${PWD}]")
    if ([string]::IsNullOrWhiteSpace($p)) { $p = (Get-Location).Path }

    $recurseAns = Read-Host "Recurse into subfolders? (y/N)"
    if ($recurseAns -match '^(?i)y(es)?$') { $script:Recurse = $true } else { $script:Recurse = $false }

    $od = Read-Host ("Output folder [$OutDir]")
    if (-not [string]::IsNullOrWhiteSpace($od)) { $script:OutDir = $od }

    $colsIn = Read-Host ("Columns [$Cols]")
    if (-not [string]::IsNullOrWhiteSpace($colsIn) -and [int]::TryParse($colsIn, [ref]([int]$null))) { $script:Cols = [int]$colsIn }
    $rowsIn = Read-Host ("Rows [$Rows]")
    if (-not [string]::IsNullOrWhiteSpace($rowsIn) -and [int]::TryParse($rowsIn, [ref]([int]$null))) { $script:Rows = [int]$rowsIn }

    $mode = Read-Host "Sampling mode: 1=Even spacing, 2=Every Nth frame [2]"
    if ([string]::IsNullOrWhiteSpace($mode)) { $mode = '2' }
    if ($mode -eq '2') {
      $st = Read-Host "Start time in seconds [$StartTime] (default 16)"
      if ([string]::IsNullOrWhiteSpace($st)) { $st = '16' }
      $et = Read-Host "End time in seconds [$EndTime] (default 37)"
      if ([string]::IsNullOrWhiteSpace($et)) { $et = '37' }
      $nth = Read-Host "Every Nth frame [${EveryNthFrame}] (default 12)"
      if ([string]::IsNullOrWhiteSpace($nth)) { $nth = '12' }

      $script:StartTime = [double]$st
      $script:EndTime = [double]$et
      $script:EveryNthFrame = [int]$nth
    } else {
      $sp = Read-Host "Start percent [$StartPercent]"
      if (-not [string]::IsNullOrWhiteSpace($sp)) { $script:StartPercent = [double]$sp }
      $ep = Read-Host "End percent [$EndPercent]"
      if (-not [string]::IsNullOrWhiteSpace($ep)) { $script:EndPercent = [double]$ep }
    }

    $tsAns = Read-Host "Show per-frame timestamps? (Y/n)"
    if ($tsAns -match '^(?i)n(o)?$') { $script:NoTimestamps = $true } else { $script:NoTimestamps = $false }

    $hdrAns = Read-Host "Show header metadata? (Y/n)"
    if ($hdrAns -match '^(?i)n(o)?$') { $script:NoHeader = $true } else { $script:NoHeader = $false }

    $fmtAns = Read-Host "Image format jpg/png [$ImageFormat]"
    if (-not [string]::IsNullOrWhiteSpace($fmtAns)) { $script:ImageFormat = ($fmtAns.ToLower()) }

    $script:Path = @($p)
  }

  function New-ContactSheet {
    param(
      [string]$File
    )

    $base = [System.IO.Path]::GetFileNameWithoutExtension($File)
    $ext = '.' + $ImageFormat.ToLowerInvariant()
    if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
    $outPath = Join-Path $OutDir ("${base}_sheet${ext}")

    if ($SkipExisting -and (Test-Path -LiteralPath $outPath)) {
      Write-Host "Skip existing: $outPath"
      return
    }

    $meta = Get-VideoMeta -File $File
    $duration = $meta.Duration
    if (-not $duration -or $duration -le 0) {
      Write-Warning "Could not determine duration via ffprobe. Falling back to approximate sampling."
      # As a conservative fallback, assume 10 minutes to compute fps. This only affects sampling density.
      $duration = 600.0
    }

    $startPct = [Math]::Max(0.0, [Math]::Min(100.0, $StartPercent))
    $endPct = [Math]::Max(0.0, [Math]::Min(100.0, $EndPercent))
    if ($endPct -le $startPct) { $startPct = 0.0; $endPct = 100.0 }

    if ($StartTime -ge 0 -and $EndTime -gt $StartTime) {
      $tStart = $StartTime
      $tEnd = $EndTime
      $tLen = [Math]::Max(0.1, $tEnd - $tStart)
    } else {
      $tStart = $duration * ($startPct/100.0)
      $tEnd = $duration * ($endPct/100.0)
      $tLen = [Math]::Max(0.1, $tEnd - $tStart)
    }

    $frames = [Math]::Max(1, $Cols * $Rows)
    $fpsStr = $null
    if ($EveryNthFrame -le 0) {
      $fps = [Math]::Max(0.0001, $frames / $tLen)
      $fpsStr = $fps.ToString([System.Globalization.CultureInfo]::InvariantCulture)
    }

    $tStartStr = $tStart.ToString([System.Globalization.CultureInfo]::InvariantCulture)
    $tLenStr = $tLen.ToString([System.Globalization.CultureInfo]::InvariantCulture)

    $fontPath = Normalize-FontPath $Font
    $fontFileOpt = ''
    if ($Font -and (Test-Path -LiteralPath $Font)) { $fontFileOpt = "fontfile='$fontPath':" }

    $vfParts = @()
    if ($EveryNthFrame -gt 0) {
      # Select every Nth frame within the time window (input is already trimmed by -ss/-t)
      $vfParts += "select='not(mod(n,$EveryNthFrame))'"
      # Keep only the first N frames to fill the tile grid
      $vfParts += "select='lte(n,$([Math]::Max(0,$frames-1)))'"
    } else {
      $vfParts += "fps=$fpsStr"
    }

    # Compute cell width if auto
    $cellW = $CellWidth
    if ($cellW -le 0) {
      $usable = $TargetWidth - (($Cols - 1) * $Padding) - (2 * $Margin)
      if ($usable -le 0) { $usable = $TargetWidth }
      $cellW = [Math]::Max(64, [Math]::Floor($usable / [Math]::Max(1,$Cols)))
    }
    $vfParts += "scale=${cellW}:-2"

    if (-not $NoTimestamps) {
      # Use a single backslash to escape the colon for FFmpeg's drawtext
      # so the option separator ':' inside the %{pts\:hms} spec is treated as text.
      $ts = "drawtext=${fontFileOpt}text='%{pts\:hms}':x=5:y=${TimestampY}:fontsize=${TimestampFontSize}:fontcolor=${TimestampColor}:box=1:boxcolor=black@0.5:boxborderw=5:shadowcolor=black@0.6:shadowx=1:shadowy=1"
      $vfParts += $ts
    }

    $vfParts += "tile=${Cols}x${Rows}:padding=${Padding}:margin=${Margin}:color=${Background}"

    if (-not $NoHeader) {
      $headerH = [Math]::Max(0, $HeaderFontSize + 16)
      $vfParts += "pad=iw:ih+${headerH}:0:${headerH}:color=${Background}"

      # Build header text: filename · duration · dims · size · date
      $fi = Get-Item -LiteralPath $File
      $niceSize = [Math]::Round($fi.Length / 1MB, 2).ToString([System.Globalization.CultureInfo]::InvariantCulture) + ' MB'
      $dims = if ($meta.Dimensions) { $meta.Dimensions } else { '' }
      $durTS = [TimeSpan]::FromSeconds($duration)
      $durStr = ('{0:hh}:{0:mm}:{0:ss}' -f $durTS)
      $dateStr = (Get-Item -LiteralPath $File).LastWriteTime.ToString('yyyy-MM-dd HH:mm')

      $headerText = "$($fi.Name) · $durStr · $dims · $niceSize · $dateStr"
      $headerTextEsc = Escape-DrawText $headerText
      $vfParts += "drawtext=${fontFileOpt}text='$headerTextEsc':x=(w-text_w)/2:y=(${headerH}-text_h)/2:fontsize=${HeaderFontSize}:fontcolor=${HeaderColor}:shadowcolor=black@0.6:shadowx=1:shadowy=1"
    }

    $vf = ($vfParts -join ',')

    $argsList = @(
      '-hide_banner','-y',
      '-ss', $tStartStr,
      '-t', $tLenStr,
      '-i', $File,
      '-vf', $vf,
      '-frames:v','1',
      $outPath
    )

    if ($ImageFormat -eq 'jpg') {
      $argsList = @('-hide_banner','-y','-ss',$tStartStr,'-t',$tLenStr,'-i',$File,'-vf',$vf,'-frames:v','1','-q:v', ($JpegQuality.ToString()), $outPath)
    } elseif ($ImageFormat -eq 'png') {
      $argsList = @('-hide_banner','-y','-ss',$tStartStr,'-t',$tLenStr,'-i',$File,'-vf',$vf,'-frames:v','1','-compression_level', ($PngCompression.ToString()), $outPath)
    }

    Write-Host "[FFmpeg] $([System.IO.Path]::GetFileName($File)) -> $([System.IO.Path]::GetFileName($outPath))"
    # Invoke ffmpeg
    & ffmpeg @argsList
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "ffmpeg failed for '$File' (exit $LASTEXITCODE)"
    } else {
      Write-Host "Saved: $outPath"
    }
  }

  # Validate tools early
  Assert-Tool 'ffmpeg'
  if (-not (Try-Tool 'ffprobe')) {
    Write-Warning 'ffprobe not found; duration/dimensions will be approximated or omitted.'
  }
}

process {
  if ($Interactive -or -not $Path -or $Path.Count -eq 0) {
    Start-Interactive
  }
  # Expand provided paths to files
  $targets = New-Object System.Collections.Generic.List[string]
  foreach ($p in $Path) {
    if ([string]::IsNullOrWhiteSpace($p)) { continue }
    if (Test-Path -LiteralPath $p -PathType Leaf) {
      $targets.Add((Resolve-Path -LiteralPath $p).Path) | Out-Null
    } elseif (Test-Path -LiteralPath $p -PathType Container) {
      $search = if ($Recurse) { Get-ChildItem -LiteralPath $p -Recurse -File } else { Get-ChildItem -LiteralPath $p -File }
      foreach ($f in $search) {
        # Basic video extension filter
        if ($f.Extension -match '^(?i)\.(mp4|mkv|mov|avi|wmv|webm|m4v|flv)$') {
          $targets.Add($f.FullName) | Out-Null
        }
      }
    } else {
      Write-Warning "Path not found: $p"
    }
  }

  if ($targets.Count -eq 0) {
    Write-Warning 'No video files found to process.'
    return
  }

  foreach ($file in $targets) {
    try {
      New-ContactSheet -File $file
    } catch {
      Write-Warning "Error processing '$file': $($_.Exception.Message)"
    }
  }
}

end {
  # Done
}
