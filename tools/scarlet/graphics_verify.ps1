# Run the existing runtime/AOT with private copies of settings, save and caches.
[CmdletBinding()]
param([switch]$NoWait)
$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$bin = Join-Path $repo 'build\scarlet\eb6deb908752b9c6'
$source = Join-Path $repo 'scarlet-boot-test'
if (Get-Process -Name scarlet -ErrorAction SilentlyContinue) { throw 'Close Scarlet before starting this test.' }
foreach ($file in @('scarlet.exe','lasgame.dll')) {
    if (!(Test-Path -LiteralPath (Join-Path $bin $file))) { throw "Missing $file; this script does not build AOT." }
}
$run = Join-Path $repo ('build\scarlet-graphics-runs\' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$data = Join-Path $run 'userdata'
New-Item -ItemType Directory -Path $data | Out-Null
foreach ($name in @('exefs','romfs')) {
    $link = Get-Item -LiteralPath (Join-Path $source $name)
    $target = if ($link.Target) { $link.Target[0] } else { $link.FullName }
    New-Item -ItemType Junction -Path (Join-Path $run $name) -Target $target | Out-Null
}
foreach ($name in @('save','cache','larecomp.ini')) {
    $path = Join-Path $source ('userdata\' + $name)
    if (Test-Path -LiteralPath $path) { Copy-Item -LiteralPath $path -Destination $data -Recurse }
}
# Changes are confined to this child PowerShell process and the new run directory.
Get-ChildItem Env: | Where-Object { $_.Name -like 'LARECOMP_*' -or $_.Name -like 'SCARLET_*' } |
    ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
$env:PATH = 'C:\msys64\ucrt64\bin;C:\msys64\usr\bin;' + $env:PATH
$env:LARECOMP_GAME_LIB = Join-Path $bin 'lasgame.dll'
$env:LARECOMP_NO_LAUNCHER = '1'
$env:LARECOMP_DATA_ROOT = $data
$env:SCARLET_EARLY_TLS_PROBE = '1'
$env:SCARLET_BOOTSTRAP_ALLOCATOR = '1'
$log = Join-Path $run 'stderr.log'
Write-Host "Isolated test: $run"
Write-Host 'Original save/settings/caches are preserved. F10 saves a screenshot in the private data folder.'
$p = Start-Process -FilePath (Join-Path $bin 'scarlet.exe') -ArgumentList @('--play', ('"' + $run + '"')) -WorkingDirectory $bin -RedirectStandardError $log -PassThru
$p.Id | Set-Content -LiteralPath (Join-Path $run 'process-id.txt')
if (!$NoWait) { $p.WaitForExit(); Write-Host "Exit: $($p.ExitCode) | Log: $log" }
