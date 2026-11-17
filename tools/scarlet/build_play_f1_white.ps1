# Rebuild only the Scarlet native F1 overlay, preserving the working game AOT DLL.
# Does not run gen.py, change save data, or alter the original FPS/camera patch.
[CmdletBinding()]
param(
    [string]$Source = 'D:\Scarlet-Window-Playtest-20261112',
    [switch]$BuildOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $repo
$branch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -notin @(
    'work/scarlet-indoor-camera-20261117',
    'fix/scarlet-xbox-playstation-prompts-20261117',
    'fix/scarlet-native-controller-layout-title-prompt-20261117',
    'fix/scarlet-native-title-glyph-no-overlay-20261117'
)) {
    throw 'Open the Scarlet camera branch or the controller-prompt fix branch before rebuilding the F1 UI.'
}
if (Get-Process scarlet -ErrorAction SilentlyContinue) {
    throw 'Close Scarlet before linking the updated F1 menu.'
}

$make = 'C:\msys64\usr\bin\make.exe'
$build = 'build/window-full-20261112'
$exe = Join-Path $repo 'build\window-full-20261112\scarlet.exe'
$dll = Join-Path $repo 'build\window-full-20261112\lasgame.dll'
$id = Join-Path $repo 'build\window-full-20261112\lasgame.dll.id'
$game = Join-Path $Source 'scarlet-games\active'
foreach ($item in @($make, $exe, $dll, $id, (Join-Path $game 'exefs\main'))) {
    if (!(Test-Path -LiteralPath $item -PathType Leaf)) {
        throw "Required local file not found: $item"
    }
}

$backup = Join-Path $repo ('build/scarlet-f1-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Item -LiteralPath $exe -Destination $backup -ErrorAction Stop
Write-Host "Previous Scarlet executable saved at: $backup" -ForegroundColor Cyan

$env:PATH = 'C:\msys64\ucrt64\bin;C:\msys64\usr\bin;' + $env:PATH
Write-Host 'Rebuilding only the Scarlet F1 overlay and runtime EXE; keeping AOT DLL unchanged.' -ForegroundColor Cyan
& $make '-j4' 'SCARLET_AOT=1' "B=$build" "$build/scarlet.exe"
if ($LASTEXITCODE -ne 0) {
    Copy-Item -LiteralPath (Join-Path $backup 'scarlet.exe') -Destination $exe -Force
    throw "F1 UI build failed; previous executable restored."
}
Write-Host 'Scarlet F1 white theme compiled. The existing game DLL remains intact.' -ForegroundColor Green
# Scarlet's native title/button font: no fake panel drawn over the original game.
# Build a separate host-style font from the bundled OFL font, leaving existing
# Nintendo system font dumps and game resources untouched.
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    throw 'Python not found. Install Python or make it available on PATH to build the native title glyphs.'
}
$fontTool = Join-Path $repo 'tools\scarlet\native_title_glyphs.py'
& $py.Source $fontTool --repo $repo --settings (Join-Path $repo 'larecomp.ini')
if ($LASTEXITCODE -ne 0) {
    throw 'Native Scarlet title button font generation failed. The previous game DLL and saves are unchanged.'
}
Write-Host 'Scarlet native title glyphs prepared for Xbox / PlayStation / keyboard. No large overlay.' -ForegroundColor Green
if ($BuildOnly) { return }

foreach ($key in @('LARECOMP_INPUT', 'LARECOMP_HOST_INPUT', 'LARECOMP_SHOT_AT',
                   'LARECOMP_REEXEC_FORCE', 'LARECOMP_NO_USER_INPUT',
                   'SCARLET_POSITION_TRACE')) {
    Remove-Item -Path "Env:$key" -ErrorAction SilentlyContinue
}
$env:SCARLET_TARGET_FPS = '60'
$env:SCARLET_INDOOR_CAMERA_60 = '1'
$env:SCARLET_NORMALIZE_LSTICK = '1'
$env:LARECOMP_GPU_OVERLAP = '0'
$env:LARECOMP_DATA_ROOT = $Source
$env:LARECOMP_GAME_LIB = $dll

Write-Host 'Opening Scarlet at 60 FPS. Press F1 to see the new white menu.' -ForegroundColor Green
& $exe --play $game
