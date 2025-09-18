<# SlayContactSheet_FFmpegOnly.ps1 — frame extraction + contact sheet in one tool
   - Uses FFmpeg select filter to keep every Nth decoded frame in [start,end)
   - Auto trims to grid capacity
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---- inputs (same defaults) ----
$videoDefault   = "D:\Golden_Wings_August_2025.mp4"
$outDirDefault  = "C:\Users\nobby.ONETRUESLAYSTAT\Pictures\vlc"
$startDefault   = 21
$endDefault     = 37
$everyNDefault  = 12
$ffmpegDefault  = "C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin\ffmpeg.exe"
$ffprobeDefault = "C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin\ffprobe.exe"
$prefixDefault  = "gw_"

$colsDefault    = "AUTO"
$rowsDefault    = "AUTO"
$thumbWDefault  = 320
$paddingDefault = 6
$marginDefault  = 8

$bgHexDefault   = "#0d0d0d"
$titleTextDef   = "GOLDEN WINGS — Contact Sheet"
$titleColorDef  = "white"
$titleBarPxDef  = 140
$titleSizeDef   = 64

$FontMap = @{
  "Arial"         = "C:\Windows\Fonts\arial.ttf"
  "Bahnschrift"   = "C:\Windows\Fonts\bahnschrift.ttf"
  "Calibri"       = "C:\Windows\Fonts\calibri.ttf"
  "Consolas"      = "C:\Windows\Fonts\consola.ttf"
  "CourierNew"    = "C:\Windows\Fonts\cour.ttf"
  "Georgia"       = "C:\Windows\Fonts\georgia.ttf"
  "Impact"        = "C:\Windows\Fonts\impact.ttf"
  "SegoeUI"       = "C:\Windows\Fonts\segoeui.ttf"
  "Tahoma"        = "C:\Windows\Fonts\tahoma.ttf"
  "TimesNewRoman" = "C:\Windows\Fonts\times.ttf"
  "TrebuchetMS"   = "C:\Windows\Fonts\trebuc.ttf"
  "Verdana"       = "C:\Windows\Fonts\verdana.ttf"
}
$fontDefaultKey = "Bahnschrift"

function Get-NiceGrid([int]$n) {
  $best = @{ rows = 1; cols = $n; blanks = 0; score = $n }
  $root = [int][math]::Sqrt([double]$n)
  for ($c = 1; $c -le $n; $c++) {
    $r = [int][math]::Ceiling($n / $c)
    $blanks = ($r * $c) - $n
    $score = [math]::Abs($c - $r) * 100 + $blanks
    if ($score -lt $best.score) { $best = @{ rows = $r; cols = $c; blanks = $blanks; score = $score } }
    if (($c -ge $root) -and ($blanks -eq 0) -and ([math]::Abs($c-$r) -le 1)) { break }
  }
  [PSCustomObject]$best
}

function Escape-FFText([string]$s) {
  $s = $s -replace '\\', '\\\\'
  $s = $s -replace ":", "\:"
  $s = $s -replace "'", "’"
  $s = $s -replace '%', '\%'
  return $s
}

# ---- prompts ----
$video   = Read-Host "Video path [$videoDefault]"; if (!$video) { $video = $videoDefault }
$outDir  = Read-Host "Output folder [$outDirDefault]"; if (!$outDir) { $outDir = $outDirDefault }
$startS  = Read-Host "Start time (s) [$startDefault]"; if (!$startS) { $startS = $startDefault } else { $startS = [int]$startS }
$endS    = Read-Host "End time (s) [$endDefault]"; if (!$endS) { $endS = $endDefault } else { $endS = [int]$endS }
$everyN  = Read-Host "Save every Nth frame [$everyNDefault]"; if (!$everyN) { $everyN = $everyNDefault } else { $everyN = [int]$everyN }
$ffmpeg  = Read-Host "FFmpeg exe name/path [$ffmpegDefault]"; if (!$ffmpeg) { $ffmpeg = $ffmpegDefault }
$ffprobe = Read-Host "FFprobe exe name/path [$ffprobeDefault]"; if (!$ffprobe) { $ffprobe = $ffprobeDefault }
$prefix  = Read-Host "Filename prefix [$prefixDefault]"; if (!$prefix) { $prefix = $prefixDefault }

$colsInp = Read-Host "Columns (or AUTO) [$colsDefault]"; if (!$colsInp) { $colsInp = $colsDefault }
$rowsInp = Read-Host "Rows (or AUTO)    [$rowsDefault]"; if (!$rowsInp) { $rowsInp = $rowsDefault }
$thumbW  = Read-Host "Thumb width px [$thumbWDefault]"; if (!$thumbW) { $thumbW = $thumbWDefault } else { $thumbW = [int]$thumbW }
$padding = Read-Host "Tile padding px [$paddingDefault]"; if (!$padding) { $padding = $paddingDefault } else { $padding = [int]$padding }
$margin  = Read-Host "Mosaic margin px [$marginDefault]"; if (!$margin) { $margin = $marginDefault } else { $margin = [int]$margin }

$bgHex   = Read-Host "Background hex color [$bgHexDefault]"; if (!$bgHex) { $bgHex = $bgHexDefault }
$title   = Read-Host "Title text [`"$titleTextDef`"]"; if (!$title) { $title = $titleTextDef }
$titleCol= Read-Host "Title color [$titleColorDef]"; if (!$titleCol) { $titleCol = $titleColorDef }
$titleBar= Read-Host "Title bar height px [$titleBarPxDef]"; if (!$titleBar) { $titleBar = $titleBarPxDef } else { $titleBar = [int]$titleBar }
$fontSize= Read-Host "Title font size [$titleSizeDef]"; if (!$fontSize) { $fontSize = $titleSizeDef } else { $fontSize = [int]$fontSize }

Write-Host "`nPick a font key:" -ForegroundColor Magenta
$FontMap.Keys | ForEach-Object { Write-Host " - $_" }
$fontKey = Read-Host "Font key [$fontDefaultKey]"; if (!$fontKey) { $fontKey = $fontDefaultKey }
if (-not $FontMap.ContainsKey($fontKey)) { throw "Unknown font key: $fontKey" }
$fontFile = $FontMap[$fontKey]

# ---- prep ----
if (!(Test-Path $video)) { throw "Video not found: $video" }
if (!(Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$work = Join-Path $outDir ("ff_frames_{0:yyyyMMdd_HHmmss}" -f (Get-Date))
New-Item -ItemType Directory -Path $work -Force | Out-Null

# ---- Stage 1: extract every Nth frame in window ----
# select filter: keep frames where n%everyN==0, after trimming by -ss/-to
$sel = "select='not(mod(n\,${everyN}))',setpts=N/FRAME_RATE/TB"
$ffArgsGrab = @(
  '-y',
  '-ss', $startS, '-to', $endS,
  '-i', $video,
  '-vf', $sel,
  '-vsync','vfr',
  (Join-Path $work ($prefix + '%06d.png'))
)
$g = Start-Process -FilePath $ffmpeg -ArgumentList $ffArgsGrab -NoNewWindow -PassThru -Wait
if ($g.ExitCode -ne 0) { throw "FFmpeg extraction failed with exit code $($g.ExitCode)" }

$frames = Get-ChildItem -Path $work -Filter "$prefix*.png" | Sort-Object Name
$actual = $frames.Count
if ($actual -eq 0) { throw "No frames created. Check times / everyN." }

# ---- grid ----
if ($colsInp -eq 'AUTO' -or $rowsInp -eq 'AUTO') {
  $gAuto = Get-NiceGrid $actual
  if ($colsInp -eq 'AUTO') { $cols = $gAuto.cols } else { $cols = [int]$colsInp }
  if ($rowsInp -eq 'AUTO') { $rows = $gAuto.rows } else { $rows = [int]$rowsInp }
} else {
  $cols = [int]$colsInp; $rows = [int]$rowsInp
}
$capacity = $cols*$rows
if ($actual -gt $capacity) {
  Write-Host "Trimming $actual → $capacity to fit grid." -ForegroundColor Yellow
  # Delete extras to keep concat clean
  $toDelete = $frames | Select-Object -Skip $capacity
  $toDelete | Remove-Item -Force
  $frames = Get-ChildItem -Path $work -Filter "$prefix*.png" | Sort-Object Name
  $actual = $frames.Count
}
Write-Host "Grid: ${cols}x${rows} (capacity $capacity, using $actual)" -ForegroundColor Cyan

# ---- Stage 2: mosaic ----
$listFile = Join-Path $work "inputs.txt"
$frames | ForEach-Object { "file '$($_.FullName.Replace('\','/'))'" } | Set-Content -Path $listFile -Encoding ASCII
$mosaicPng = Join-Path $outDir ("mosaic_{0}x{1}.png" -f $cols,$rows)
$vfMosaic  = "scale=${thumbW}:-1,tile=${cols}x${rows}:margin=${margin}:padding=${padding}"

$ffArgsMos = @(
  '-y','-safe','0',
  '-f','concat','-i',$listFile,
  '-vf', $vfMosaic,
  '-frames:v','1',
  $mosaicPng
)
$m = Start-Process -FilePath $ffmpeg -ArgumentList $ffArgsMos -NoNewWindow -PassThru -Wait
if ($m.ExitCode -ne 0) { throw "FFmpeg mosaic failed: $($m.ExitCode)" }

# ---- Stage 3: canvas + title + overlay ----
# Probe size
$tmp = Join-Path $env:TEMP ("dims_{0}.txt" -f ([Guid]::NewGuid()))
$p = Start-Process -FilePath $ffprobe -ArgumentList @('-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','csv=s=x:p=0', $mosaicPng) -NoNewWindow -PassThru -Wait -RedirectStandardOutput $tmp
if ($p.ExitCode -ne 0) { throw "ffprobe failed for mosaic." }
$wh = (Get-Content $tmp -Raw).Trim() -split 'x'
Remove-Item $tmp -Force -ErrorAction SilentlyContinue
$canvasW = [int]$wh[0]; $canvasH = [int]$wh[1] + $titleBar

$finalOut = Join-Path $outDir ("contact-sheet_{0}x{1}.png" -f $cols,$rows)
$tText = Escape-FFText $title
$fontEsc = $fontFile -replace '\\','/

# Add soft shadow for title legibility
$filter = @(
  "`[1:v`]"drawtext=fontfile='$fontEsc':text='$tText':fontsize=$fontSize:fontcolor=$titleCol:x=(w-text_w)/2:y=(($titleBar-text_h)/2):",
  "shadowcolor=black:shadowx=3:shadowy=3:borderw=0[title];",
  "[title][0:v]overlay=x=(W-w)/2:y=$titleBar:format=auto[out]"
) -join ""

$ffArgsOut = @(
  '-y',
  '-loop','1','-i', $mosaicPng,
  '-f','lavfi','-i', 'color=c=$bgHex:size=${canvasW}x${canvasH}:d=1',
  '-filter_complex', $filter,
  '-map','[out]',
  '-frames:v','1',$finalOut
)
$o = Start-Process -FilePath $ffmpeg -ArgumentList $ffArgsOut -NoNewWindow -PassThru -Wait
if ($o.ExitCode -ne 0) { throw "FFmpeg compose failed: $($o.ExitCode)" }

Write-Host "`n✨ Done: $finalOut" -ForegroundColor Green
# optional cleanup
# Remove-Item -LiteralPath $work -Recurse -Force
