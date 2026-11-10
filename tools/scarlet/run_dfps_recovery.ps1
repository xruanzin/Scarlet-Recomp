# Visible, isolated DFPS validation. Never prepares AOT or writes source saves.
[CmdletBinding()]
param(
    [string]$Runtime = '',
    [string]$Experiment = 'D:\Scarlet-DFPS-Experiment',
    [string]$SourceData = '',
    [switch]$Probe,
    [switch]$FreshSave,
    [switch]$Baseline30,
    [switch]$Fullscreen,
    [switch]$GraphicsAudit,
    [switch]$RecordInput,
    [string]$InputScript = '',
    [ValidatePattern('^$|^[0-9a-fA-F]{1,16}(,[0-9a-fA-F]{1,16}){0,15}$')][string]$CaptureHashes = '',
    [ValidateRange(0,2147483647)][int]$CaptureFrame = 0,
    [ValidateRange(0,300)][int]$Seconds = 0
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'run_process.ps1')
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if ($Baseline30) {
    if ($Runtime) { throw 'Baseline30 uses the matching reference runtime and DLL; omit -Runtime.' }
    $Runtime = Join-Path $repo 'build\scarlet\eb6deb908752b9c6\scarlet.exe'
}
if (!$Runtime) { $Runtime = Join-Path $repo 'build\scarlet-dfps-recovery\scarlet.exe' }
$Runtime = (Resolve-Path -LiteralPath $Runtime).Path
if ([IO.Path]::GetFileName($Runtime) -ne 'scarlet.exe') { throw 'AOT imports require the executable name scarlet.exe.' }
if (Get-Process scarlet -ErrorAction SilentlyContinue) { throw 'Close the existing Scarlet before this isolated run.' }
$game = Join-Path $Experiment 'game'
$library = Join-Path $game 'lasgame.dll'
if (Test-Path -LiteralPath (Join-Path (Split-Path $Runtime -Parent) 'lasgame.dll')) {
    $library = Join-Path (Split-Path $Runtime -Parent) 'lasgame.dll'
}
if ($Baseline30) { $library = Join-Path $repo 'build\scarlet\eb6deb908752b9c6\lasgame.dll' }
$patch = Join-Path $Experiment 'mods\scarlet-dfps-v4.pchtxt'
if (!$SourceData) { $SourceData = Join-Path $Experiment 'runtime-data-intro-test' }
$sourceData = (Resolve-Path -LiteralPath $SourceData).Path
foreach ($f in @($library, ($library + '.id'), $patch, (Join-Path $game 'exefs\main'), $sourceData)) {
    if (!(Test-Path -LiteralPath $f)) { throw "Missing input: $f" }
}
$expectedId = if ($Baseline30) { '*-421C5411B487EB4D' } else { '*-421C5411B487EB4D-dfpsasm' }
if ((Get-Content -LiteralPath ($library + '.id') -Raw).Trim() -notlike $expectedId) { throw 'Wrong AOT variant.' }
if ($Baseline30 -and $Probe) { throw 'DFPS probe requires the experimental AOT.' }
$run = Join-Path $repo ('build\scarlet-recovery-runs\' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $run | Out-Null
$data = Join-Path $run 'userdata'
if ($FreshSave) {
    New-Item -ItemType Directory -Path $data | Out-Null
    foreach ($name in @('cache','larecomp.ini')) {
        $source = Join-Path $sourceData $name
        if (Test-Path -LiteralPath $source) { Copy-Item -LiteralPath $source -Destination $data -Recurse }
    }
} else { Copy-Item -LiteralPath $sourceData -Destination $data -Recurse }
$preserved = @(Get-Item -LiteralPath $library)
$preserved += @(Get-ChildItem -LiteralPath (Join-Path $sourceData 'save') -Recurse -File)
$before = @($preserved | Get-FileHash)
$before | Export-Csv (Join-Path $run 'preserved-before.csv') -NoTypeInformation
if ($Fullscreen) {
    # Only the new run's private copy. Original preferences remain untouched.
    $ini = Join-Path $data 'larecomp.ini'
    $settings = Get-Content -LiteralPath $ini -Raw
    if ($settings -notmatch '(?m)^fullscreen\s*=') { throw 'Fullscreen setting missing from copied configuration.' }
    $settings -replace '(?m)^fullscreen\s*=.*$', 'fullscreen = 1' | Set-Content -LiteralPath $ini
}
Get-FileHash -LiteralPath $Runtime,$patch | Export-Csv (Join-Path $run 'inputs.csv') -NoTypeInformation
# Environment belongs to this child PowerShell process. Identical source cache/settings for A/B.
Get-ChildItem Env: | Where-Object { $_.Name -like 'LARECOMP_*' -or $_.Name -like 'SCARLET_*' } |
    ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
$bin = Split-Path $Runtime -Parent
$env:PATH = $bin + ';C:\msys64\ucrt64\bin;C:\msys64\usr\bin;' + $env:PATH
$env:LARECOMP_DATA_ROOT = $data
$env:LARECOMP_GAME_LIB = $library
$env:LARECOMP_NO_LAUNCHER = '1'
if (!$Baseline30) { $env:SCARLET_DFPS_PCHTXT = $patch }
$env:SCARLET_TARGET_FPS = if ($Baseline30) { '30' } else { '60' }
if ($Probe) { $env:SCARLET_DFPS_INTRO_MODE = 'probe' }
if ($GraphicsAudit) {
    $env:SCARLET_GRAPHICS_AUDIT = '1'
    $env:SCARLET_GRAPHICS_FROM_FRAME = '600'
    $env:SCARLET_SKY_AUDIT = '1'
    $env:LARECOMP_LOG_WINDOW = '1'
}
if ($RecordInput) { $env:LARECOMP_RECORD_INPUT = Join-Path $run 'input.txt' }
if ($InputScript) {
    $env:LARECOMP_INPUT = $InputScript # existing guest input replay; never OS key injection
    $env:LARECOMP_NO_USER_INPUT = '0' # the user can still control/close this test
}
if ($CaptureHashes) { $env:SCARLET_CAPTURE_FSHASH = $CaptureHashes }
if ($CaptureFrame) {
    $env:LARECOMP_DEBUG_FRAME = [string]$CaptureFrame
    $env:LARECOMP_DEBUG_FRAMES = '1' # unique render-frame names, also for later F9 captures
    $env:LARECOMP_LOG_FSHASH = '1'
}
@{runtime=$Runtime; game=$game; library=$library; sourceData=$sourceData; freshSave=[bool]$FreshSave; probe=[bool]$Probe; baseline30=[bool]$Baseline30; fullscreen=[bool]$Fullscreen; graphicsAudit=[bool]$GraphicsAudit; recordInput=[bool]$RecordInput; inputScript=$InputScript; captureFrame=$CaptureFrame; captureHashes=$CaptureHashes; seconds=$Seconds; window='Normal'; started=(Get-Date).ToString('o')} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'run.json')
Write-Host "Logs and temporary save: $run"
# The user explicitly requests a visible window for valid performance comparison.
$p = Start-Process -FilePath $Runtime -ArgumentList @('--play', ('"' + $game + '"')) -WorkingDirectory $bin -WindowStyle Normal -RedirectStandardError (Join-Path $run 'stderr.log') -RedirectStandardOutput (Join-Path $run 'stdout.log') -PassThru
$p.Id | Set-Content -LiteralPath (Join-Path $run 'pid.txt')
$processHandle = $p.Handle # keep an open handle so PowerShell can report ExitCode after exit
$timedOut = $false
if ($Seconds -gt 0) {
    if (!$p.WaitForExit($Seconds * 1000)) {
        $timedOut = $true
        Stop-ScarletRunTree -Process $p -LogPath (Join-Path $run 'termination-process-tree.log')
        'Timed capture; owned process tree terminated, not a clean game exit or proof of stability.' | Set-Content (Join-Path $run 'termination.txt')
    }
} else { $p.WaitForExit() }
$outcome = if ($timedOut) { 'timed_capture' } elseif ($p.ExitCode -eq 0) { 'normal_exit' } else { 'game_error' }
@{exitCode=$p.ExitCode; outcome=$outcome; timedOut=$timedOut; ended=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $run 'result.json')
foreach ($entry in $before) {
    if ((Get-FileHash -LiteralPath $entry.Path).Hash -ne $entry.Hash) { throw "Preservation mismatch: $($entry.Path)" }
}
Write-Host "Preservation PASS. Exit=$($p.ExitCode). Logs: $run"
if (!$timedOut -and $p.ExitCode -ne 0) { exit 1 }
exit 0 # capture completed/preservation passed; inspect outcome, not this code, for game results
