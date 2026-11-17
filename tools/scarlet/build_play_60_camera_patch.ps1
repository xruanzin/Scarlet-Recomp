# Rebuild Scarlet's exact AOT Lua script loader with an in-memory 60-FPS
# camera scheduler fix inspired by KarPur's script timing adjustment.
# No mod files or game data are copied into the Git repository.
[CmdletBinding()]
param(
    [string]$Gen = '',
    [string]$Source = 'D:\Scarlet-Window-Playtest-20261112',
    [switch]$BuildOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..')).TrimEnd([char]'\', [char]'/')
Set-Location -LiteralPath $repo
$branch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -ne 'work/scarlet-indoor-camera-20261117') {
    throw 'Switch to the experimental camera branch before building.'
}
if (Get-Process scarlet -ErrorAction SilentlyContinue) {
    throw 'Close Scarlet normally before rebuilding the native EXE and game DLL.'
}

$py = Join-Path $repo '.venv-scarlet-aot-fixed\Scripts\python.exe'
$make = 'C:\msys64\usr\bin\make.exe'
$build = 'build/window-full-20261112'
$buildAbs = Join-Path $repo $build
$exe = Join-Path $buildAbs 'scarlet.exe'
$dll = Join-Path $buildAbs 'lasgame.dll'
$id = Join-Path $buildAbs 'lasgame.dll.id'
$game = Join-Path $Source 'scarlet-games\active'
$main = Join-Path $game 'exefs\main'
foreach ($item in @($py, $make, $exe, $dll, $id, $main)) {
    if (!(Test-Path -LiteralPath $item -PathType Leaf)) {
        throw "Required local file missing: $item"
    }
}
$env:PATH = 'C:\msys64\ucrt64\bin;C:\msys64\usr\bin;' + $env:PATH
Write-Host 'Checking Lua hook's synthetic guards...' -ForegroundColor Cyan
& $py tools/scarlet/test_lua_camera_native.py
if ($LASTEXITCODE -ne 0) { throw 'Lua hook guard tests failed.' }

$clang = (Get-Command clang -ErrorAction SilentlyContinue)
if (-not $clang) {
    $clang = Get-Command 'C:\msys64\ucrt64\bin\clang.exe' -ErrorAction SilentlyContinue
}
if (-not $clang) { throw 'clang not found; cannot verify the Lua camera constant guard.' }
$guardExe = Join-Path $buildAbs 'scarlet-camera-constant-guard.exe'
Write-Host 'Compiling the standalone C guard for the script constant...' -ForegroundColor Cyan
& $clang.Source '-std=c11' '-Wall' '-Wextra' '-O2' 'tools/scarlet/test_camera_script_patch.c' '-o' $guardExe
if ($LASTEXITCODE -ne 0) { throw 'Native Lua camera constant guard compilation failed.' }
& $guardExe
if ($LASTEXITCODE -ne 0) { throw 'Native Lua camera constant guard failed.' }

# Use an existing generated AOT source directory for the exact Scarlet
# build. Never silently create or compile an unrelated game version.
if (-not $Gen) {
    $candidates = New-Object System.Collections.Generic.List[object]
    $roots = @(Get-ChildItem -LiteralPath $repo -Directory -Filter 'generated*')
    foreach ($root in $roots) {
        $options = @($root) + @(Get-ChildItem -LiteralPath $root.FullName -Directory)
        foreach ($opt in $options) {
            $identity = Join-Path $opt.FullName 'main\main_build_id.txt'
            if (!(Test-Path -LiteralPath $identity -PathType Leaf)) { continue }
            $buildId = (Get-Content -LiteralPath $identity -TotalCount 1).Trim()
            if (-not $buildId.ToLowerInvariant().StartsWith('421c5411b487eb4d')) { continue }
            $mainTable = Join-Path $opt.FullName 'main\main_table.c'
            $sdk = Join-Path $opt.FullName 'sdk'
            $subsdk = Join-Path $opt.FullName 'subsdk0'
            if (!(Test-Path -LiteralPath $mainTable -PathType Leaf) -or
                !(Test-Path -LiteralPath $sdk -PathType Container) -or
                !(Test-Path -LiteralPath $subsdk -PathType Container)) { continue }
            $candidates.Add([PSCustomObject]@{
                Folder = $opt.FullName
                Modified = (Get-Item -LiteralPath $mainTable).LastWriteTimeUtc
            })
        }
    }
    if ($candidates.Count -eq 0) {
        throw 'No existing Scarlet 4.0.0 generated AOT directory found. Provide -Gen <relative-folder>; no files changed.'
    }
    $Gen = ($candidates | Sort-Object Modified -Descending | Select-Object -First 1).Folder
    if ($candidates.Count -gt 1) {
        Write-Warning 'Several generated directories match this build; choosing the most recently generated. Override with -Gen if needed.'
        $candidates | ForEach-Object { Write-Host "AOT candidate: $($_.Folder)" }
    }
}
$genFull = if ([IO.Path]::IsPathRooted($Gen)) {
    [IO.Path]::GetFullPath($Gen)
} else {
    [IO.Path]::GetFullPath((Join-Path $repo $Gen))
}
if (-not $genFull.StartsWith($repo + [IO.Path]::DirectorySeparatorChar,
                            [StringComparison]::OrdinalIgnoreCase)) {
    throw 'AOT generated source must stay inside this repository.'
}
$identity = Join-Path $genFull 'main\main_build_id.txt'
if (!(Test-Path -LiteralPath $identity -PathType Leaf)) {
    throw "Generated main build identity missing: $identity"
}
if (-not (Get-Content -LiteralPath $identity -TotalCount 1).Trim().ToLowerInvariant().StartsWith('421c5411b487eb4d')) {
    throw 'Generated AOT main does not match Scarlet 4.0.0.'
}
$genRel = $genFull.Substring($repo.Length + 1).Replace('\', '/')
Write-Host "Using generated AOT: $genRel" -ForegroundColor Cyan

$backup = Join-Path $repo ('build/scarlet-60-camera-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Item -LiteralPath $exe, $dll, $id -Destination $backup -ErrorAction Stop
Write-Host "Previous playable build backed up: $backup" -ForegroundColor Cyan
try {
    Write-Host 'Regenerating only Scarlet main AOT code (exact NSO signature required)...' -ForegroundColor Cyan
    & $py tools/gen.py main $main '0x7000000000' "$genRel/main" --simd c --game scarlet
    if ($LASTEXITCODE -ne 0) {
        throw "AOT generation rejected the exact Lua call-site guard (exit $LASTEXITCODE)."
    }
    Write-Host 'Compiling AOT changes, EXE and DLL. Do not remove the existing backup.' -ForegroundColor Cyan
    $makeArgs = @(
        '-j4', 'SCARLET_AOT=1', "GEN=$genRel", "B=$build",
        "$build/scarlet.exe", "$build/lasgame.dll"
    )
    & $make @makeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Incremental Scarlet rebuild failed (exit $LASTEXITCODE)."
    }
} catch {
    Write-Warning "Native build did not complete: $_"
    Copy-Item -LiteralPath (Join-Path $backup 'scarlet.exe') -Destination $exe -Force
    Copy-Item -LiteralPath (Join-Path $backup 'lasgame.dll') -Destination $dll -Force
    Copy-Item -LiteralPath (Join-Path $backup 'lasgame.dll.id') -Destination $id -Force
    throw 'Previous EXE/DLL/ID restored; the generated source may contain the new hook. Read the failure log.'
}

if ($BuildOnly) {
    Write-Host "Compiled successfully; saved previous build in $backup" -ForegroundColor Green
    return
}

foreach ($key in @(
    'LARECOMP_INPUT', 'LARECOMP_HOST_INPUT', 'LARECOMP_NO_USER_INPUT',
    'LARECOMP_SHOT_AT', 'LARECOMP_REEXEC_FORCE', 'LARECOMP_REEXEC',
    'SCARLET_POSITION_TRACE', 'LARECOMP_DOORJUMP_TEST',
    'LARECOMP_PLACE', 'LARECOMP_BIND_TEST'
)) { Remove-Item "Env:$key" -ErrorAction SilentlyContinue }

$env:SCARLET_TARGET_FPS = '60'
$env:SCARLET_INDOOR_CAMERA_60 = '1'
$env:SCARLET_NORMALIZE_LSTICK = '1'
$env:LARECOMP_DATA_ROOT = $Source
$env:LARECOMP_GAME_LIB = $dll
$env:LARECOMP_GPU_OVERLAP = '0'

Write-Host 'Launching native Scarlet 60 FPS; normal user input remains enabled.' -ForegroundColor Green
Write-Host 'Look for [scarlet-camera] applied in-memory camera script step 1/30 -> 1/60'
Write-Host 'This is an experimental camera change; verify animation speed in interiors.'
& $exe --play $game
