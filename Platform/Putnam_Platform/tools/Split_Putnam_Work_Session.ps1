param(
    [string]$InputVideo
)

$ErrorActionPreference = "Stop"

if (-not $env:USERENVIRONMENT -or -not (Test-Path $env:USERENVIRONMENT)) {
    $env:USERENVIRONMENT = Join-Path $env:USERPROFILE "OneDrive\PutnamCollectibles"
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "FFmpeg is required."
    Write-Host "Install with:"
    Write-Host "winget install Gyan.FFmpeg"
    pause
    exit 1
}

if (-not $InputVideo) {
    $InputVideo = Read-Host "Paste or drag the raw OBS recording path"
}

$InputVideo = $InputVideo.Trim('"')
if (-not (Test-Path $InputVideo)) {
    Write-Host "File not found: $InputVideo"
    pause
    exit 1
}

$sessionDate = Get-Date -Format "yyyy-MM-dd"
$outDir = Join-Path $env:USERENVIRONMENT "Work Sessions\$sessionDate\Segments"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$outPattern = Join-Path $outDir "Putnam_Work_Session_%03d.mp4"

Write-Host "Splitting video into 15-minute copy-only segments..."
Write-Host "Input: $InputVideo"
Write-Host "Output: $outDir"

ffmpeg -hide_banner -i "$InputVideo" -map 0 -c copy -f segment -segment_time 900 -reset_timestamps 1 "$outPattern"

Write-Host ""
Write-Host "Done."
Write-Host "Segments saved to:"
Write-Host $outDir
pause

