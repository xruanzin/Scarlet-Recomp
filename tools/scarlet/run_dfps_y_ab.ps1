# Scarlet Dynamic FPS vertical-gain A/B runner.
# Uses an isolated save root on every run; no game, DLL, or save files modified.
[CmdletBinding()]
param(
    [ValidateSet("neutral", "original")]
    [string]$Mode = "neutral",
    [string]$Experiment = "D:\Scarlet-DFPS-Experiment",
    [string]$Runtime = ""
)

$ErrorActionPreference = "Stop"
$repo = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
if (-not $Runtime) {
    $Runtime = Join-Path $repo "build\scarlet-dfps-test\scarlet.exe"
}
$game = Join-Path $Experiment "game"
$patch = Join-Path $Experiment "mods\scarlet-dfps-v4.pchtxt"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$run = Join-Path $Experiment ("y-gain-ab-" + $Mode + "-" + $stamp)

foreach ($file in @(
    $Runtime,
    (Join-Path $game "lasgame.dll"),
    (Join-Path $game "lasgame.dll.id"),
    (Join-Path $game "exefs\main"),
    $patch
)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Missing required file: $file"
    }
}
New-Item -Path $run -ItemType Directory -Force | Out-Null
$env:PATH = "C:\msys64\ucrt64\bin;C:\msys64\usr\bin;$env:PATH"
$env:LARECOMP_GAME_LIB = Join-Path $game "lasgame.dll"
$env:LARECOMP_DATA_ROOT = Join-Path $run "data"
$env:SCARLET_DFPS_PCHTXT = $patch
$env:SCARLET_TARGET_FPS = "60"
$env:SCARLET_EARLY_TLS_PROBE = "1"
$env:SCARLET_BOOTSTRAP_ALLOCATOR = "1"
$env:LARECOMP_SCALE = "1"
$env:LARECOMP_VK_PRESENT = "fifo"
# Disable the expensive per-present investigation: compare only Y gain.
Remove-Item Env:SCARLET_DFPS_INTRO_MODE -ErrorAction SilentlyContinue
$env:SCARLET_DFPS_NEUTRAL_Y = if ($Mode -eq "neutral") { "1" } else { "0" }

$stderr = Join-Path $run "stderr.log"
$stdout = Join-Path $run "stdout.log"
Write-Host ("Scarlet Dynamic FPS Y A/B: " + $Mode) -ForegroundColor Cyan
Write-Host ("Game library (unchanged): " + $env:LARECOMP_GAME_LIB)
Write-Host ("Isolated data: " + $env:LARECOMP_DATA_ROOT) -ForegroundColor Green
Write-Host ("Logs: " + $stderr)
Write-Host "Observe the initial bedroom scene, then close the game."

$p = Start-Process -FilePath $Runtime `
    -ArgumentList @("--play", ('"' + $game + '"')) `
    -WorkingDirectory $repo `
    -RedirectStandardError $stderr `
    -RedirectStandardOutput $stdout `
    -WindowStyle Normal -PassThru -Wait

Write-Host ("Exit code: " + $p.ExitCode)
Write-Host ("Log: " + $stderr)
$hits = Select-String -LiteralPath $stderr -Pattern "\[scarlet-dfps\]|\[vk\] t=" -ErrorAction SilentlyContinue
if ($hits) {
    $hits | Select-Object -First 6 | ForEach-Object { Write-Host $_.Line }
}
