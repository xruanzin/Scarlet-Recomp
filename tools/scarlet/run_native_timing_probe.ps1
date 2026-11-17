[CmdletBinding()]
param(
    [ValidateSet(30,60)][int]$Fps = 30,
    [ValidateRange(10,600)][int]$Seconds = 60,
    [switch]$ForceReexec,
    [string]$InputScript = '',
    [string]$ShotAt = '',
    [string]$PositionFrames = '',
    [string]$SaveSource = '',
    [string]$Source = 'D:/Scarlet-Window-Playtest-20261112'
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$bin = Join-Path $repo 'build/window-full-20261112'
if (Get-Process scarlet -ErrorAction SilentlyContinue) { throw 'Scarlet is already running.' }
foreach ($name in @('scarlet.exe','lasgame.dll','lasgame.dll.id')) {
    if (!(Test-Path -LiteralPath (Join-Path $bin $name))) { throw "Missing $name" }
}
$run = Join-Path $repo ('build/native-timing-runs/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + "-$Fps")
$data = Join-Path $run 'userdata'
$sourceData = if ($SaveSource) { [IO.Path]::GetFullPath($SaveSource) } else { $Source }
if (!(Test-Path -LiteralPath (Join-Path $sourceData 'save'))) { throw "Missing diagnostic save source: $sourceData" }
New-Item -ItemType Directory -Path $data | Out-Null
foreach ($name in @('save','larecomp.ini')) {
    $path = Join-Path $sourceData $name
    if (Test-Path -LiteralPath $path) { Copy-Item -LiteralPath $path -Destination $data -Recurse }
}
$env:PATH = 'C:/msys64/ucrt64/bin;C:/msys64/usr/bin;' + $env:PATH
$env:LARECOMP_DATA_ROOT = $data
$env:LARECOMP_GAME_LIB = Join-Path $bin 'lasgame.dll'
$env:LARECOMP_GPU_OVERLAP = '0'
$env:SCARLET_TARGET_FPS = [string]$Fps
$env:SCARLET_TIMING_TRACE = '1'
if ($InputScript) { $env:LARECOMP_INPUT = $InputScript }
if ($ShotAt) { $env:LARECOMP_SHOT_AT = $ShotAt }
if ($PositionFrames) { $env:SCARLET_POSITION_TRACE = $PositionFrames }
if ($ForceReexec) { $env:LARECOMP_REEXEC_FORCE = '1' }
$game = Join-Path $Source 'scarlet-games/active'
& (Join-Path $repo '.venv-scarlet-aot-fixed/Scripts/python.exe') (Join-Path $PSScriptRoot 'launch_timing_process.py') --exe (Join-Path $bin 'scarlet.exe') --game $game --run $run --fps $Fps --seconds $Seconds --save-source $sourceData
if ($LASTEXITCODE -ne 0) { throw "Diagnostic launcher failed; inspect $run/result.json and logs before starting another run." }
