# Rebuild ONLY the Scarlet Windows runtime executable, keep the old files
# for rollback, and launch an interactive 60-FPS session with normal controls.
[CmdletBinding()]
param([switch]$BuildOnly)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
Set-Location -LiteralPath $repo

$build = Join-Path $repo 'build/window-full-20261112'
$exe = Join-Path $build 'scarlet.exe'
$dll = Join-Path $build 'lasgame.dll'
$id = Join-Path $build 'lasgame.dll.id'
$source = 'D:\Scarlet-Window-Playtest-20261112'
$game = Join-Path $source 'scarlet-games/active'
$make = 'C:\msys64\usr\bin\make.exe'
if (!(Test-Path -LiteralPath $make -PathType Leaf)) { throw "Missing MSYS2 make: $make" }
foreach ($file in @($exe, $dll, $id)) {
    if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing existing compiled file: $file" }
}
if (!(Test-Path -LiteralPath (Join-Path $game 'exefs/main') -PathType Leaf)) {
    throw "Missing installed Scarlet ExeFS in $game"
}
if (Get-Process scarlet -ErrorAction SilentlyContinue) {
    throw 'Close Scarlet normally before relinking the runtime executable.'
}
$branch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -ne 'work/scarlet-indoor-camera-20261117') {
    throw 'Switch to work/scarlet-indoor-camera-20261117 first.'
}

$backup = Join-Path $repo ('build/scarlet-runtime-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Item -LiteralPath $exe,$dll,$id -Destination $backup
Write-Host "Backup: $backup" -ForegroundColor Cyan

$env:PATH = 'C:\msys64\ucrt64\bin;C:\msys64\usr\bin;' + $env:PATH
$makeArgs = @(
    'SCARLET_AOT=1',
    'GEN=generated-scarlet/window-full-20261112',
    'B=build/window-full-20261112',
    '-j4',
    'build/window-full-20261112/scarlet.exe'
)
Write-Host 'Building runtime EXE only; game AOT objects and game library are left untouched.'
& $make @makeArgs
if ($LASTEXITCODE -ne 0) {
    Copy-Item -LiteralPath (Join-Path $backup 'scarlet.exe') -Destination $exe -Force
    throw "Runtime build failed (exit $LASTEXITCODE). Original executable restored."
}

if ($BuildOnly) {
    Write-Host "Runtime built. Old files: $backup" -ForegroundColor Green
    return
}
foreach ($key in @(
    'LARECOMP_INPUT', 'LARECOMP_HOST_INPUT', 'LARECOMP_NO_USER_INPUT',
    'LARECOMP_REEXEC_FORCE', 'LARECOMP_SHOT_AT',
    'SCARLET_POSITION_TRACE', 'LARECOMP_DOORJUMP_TEST',
    'LARECOMP_PLACE', 'LARECOMP_BIND_TEST', 'LARECOMP_FORCE_LAUNCHER'
)) { Remove-Item -Path "Env:$key" -ErrorAction SilentlyContinue }

$env:SCARLET_TARGET_FPS = '60'
$env:SCARLET_NORMALIZE_LSTICK = '1'
$env:LARECOMP_GPU_OVERLAP = '0'
$env:LARECOMP_DATA_ROOT = $source
$env:LARECOMP_GAME_LIB = $dll

Write-Host 'Launching interactive Scarlet 60 FPS with circular left stick.' -ForegroundColor Green
Write-Host 'Expected: [scarlet-input] circular left-stick limit enabled'
Write-Host 'Camera shake and animation timing remain uncorrected in this build.'
& $exe --play $game
