[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SaveSource,
    [string]$Source = 'D:\Scarlet-Window-Playtest-20261112',
    [ValidateRange(50,300)][int]$Seconds = 85,
    [ValidateRange(5,25)][int]$ShotFrames = 16
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runner = Join-Path $PSScriptRoot 'run_native_timing_probe.ps1'
$save = [IO.Path]::GetFullPath($SaveSource)
if (!(Test-Path -LiteralPath (Join-Path $save 'save') -PathType Container)) {
    throw "SaveSource must contain a 'save' directory. Do not supply the original game files."
}
if (!(Get-ChildItem -LiteralPath (Join-Path $save 'save') -Force -ErrorAction Stop | Select-Object -First 1)) {
    throw "SaveSource/save is empty. Need an existing private gameplay save from inside a house."
}
if (!(Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw 'Native timing probe launcher not found'
}
if ((Get-Process scarlet -ErrorAction SilentlyContinue)) {
    throw 'Stop any active Scarlet process before this comparison.'
}
$active = (& git -C $repo branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $active -ne 'work/scarlet-indoor-camera-20261117') {
    throw 'Use the dedicated experimental camera work branch for reproducible comparisons.'
}
$dirty = @(& git -C $repo status --porcelain)
if ($dirty.Count -gt 0) {
    throw 'Tracked/untracked source changes detected; commit or preserve them before testing.'
}

# Match elapsed game time: at 30 FPS begin at frame 1200, 60 FPS at frame 2400.
# Capture consecutive frames to expose 60 FPS hold/jump alternation.
# The native probe copies the save to a new private run folder each time.
$specs = @(
    @{ Fps = 30; Start = 1200; Move = 30 },
    @{ Fps = 60; Start = 2400; Move = 60 }
)
$report = Join-Path $repo ('build/interior-camera-ab-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $report -Force | Out-Null
$manifest = [ordered]@{
    branch = $active
    repo = $repo
    save_source = $save
    source = $Source
    note = 'A/B static camera test. Game saving stays isolated to each probe run.'
    seconds = $Seconds
    result_runs = @()
}
foreach ($spec in $specs) {
    $fps = [int]$spec.Fps
    $start = [int]$spec.Start
    $end = $start + $ShotFrames - 1
    $shots = ($start..$end) -join ','
    $inputSpec = ('{0}:STICK_UP:{1}' -f $start, $spec.Move)
    $probeArgs = @{
        Fps = $fps; Seconds = $Seconds; ForceReexec = $true
        SaveSource = $save; Source = $Source; ShotAt = $shots
        PositionFrames = ('{0},{1}' -f $start, $end)
    }
    $probeArgs['InputScript'] = $inputSpec
    Write-Host "Starting an isolated $fps FPS test with same saved scene..." -ForegroundColor Cyan
    $runsFolder = Join-Path $repo 'build/native-timing-runs'
    $before = @(Get-ChildItem -LiteralPath $runsFolder -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { $_.FullName })
    & $runner @probeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "$fps FPS probe stopped with exit code $LASTEXITCODE. Check build/native-timing-runs."
    }
    $created = @(Get-ChildItem -LiteralPath $runsFolder -Directory -ErrorAction Stop |
        Where-Object { $before -notcontains $_.FullName })
    if ($created.Count -ne 1) {
        throw "Expected one new private run directory for $fps FPS; found $($created.Count). Inspect build/native-timing-runs."
    }
    $runPath = $created[0].FullName
    $manifest.result_runs += [ordered]@{
        fps = $fps; shot_frames = "$start..$end"
        input_script = $inputSpec
        run_directory = $runPath
        result = (Join-Path $runPath 'result.json')
        screenshots = (Join-Path $runPath 'userdata/build/frames')
    }
    if ((Get-Process scarlet -ErrorAction SilentlyContinue)) {
        throw "$fps FPS Scarlet still running; abort next test to preserve process isolation."
    }
}
$dest = Join-Path $report 'comparison-manifest.json'
$manifest | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $dest -Encoding UTF8
Write-Host "Both runs completed. Manifest: $dest" -ForegroundColor Green
Write-Host 'Check each private run folder for result.json, screenshots and stderr.log.'
Write-Host 'Do not upload user data, saves, ROM files or game keys to GitHub.'
