# Single command for the maintainer to build and package the public runtime.
# NOT a complete player installer: the user's locally generated lasgame.dll
# exists only for build/test and is explicitly excluded from the public archive.
[CmdletBinding()]
param(
    [string]$BuildId = 'eb6deb908752b9c6',
    [switch]$CreateDraft
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$builder = Join-Path $root 'tools\scarlet\build_next_version.ps1'
$packager = Join-Path $root 'tools\scarlet\create_release_zip.ps1'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $builder -BuildId $BuildId
if ($LASTEXITCODE -ne 0) { throw 'Scarlet Windows build failed; release package not created.' }

# Build the game-code generator and pinned portable compiler ONCE on the maintainer
# machine, not on player PCs. The public ZIP includes both as with ZA Recomp.
$env:PATH = 'C:\msys64\ucrt64\bin;C:\msys64\usr\bin;' + $env:PATH
$make = Get-Command make.exe -ErrorAction SilentlyContinue
$bash = Get-Command bash.exe -ErrorAction SilentlyContinue
if (!(Test-Path -LiteralPath (Join-Path $root 'build\helper\lasgen\lasgen.exe'))) {
    if (!$make) { throw 'make.exe from MSYS2 required to build lasgen on the maintainer PC.' }
    Push-Location $root
    try {
        & $make.Source gen-helper
        if ($LASTEXITCODE -ne 0) { throw 'Bundled lasgen build failed' }
    } finally { Pop-Location }
}
if (!(Test-Path -LiteralPath (Join-Path $root 'build\zig-slim\zig.exe'))) {
    if (!$bash) { throw 'MSYS2 bash.exe required to prepare the bundled Zig compiler.' }
    Push-Location $root
    try {
        if (!(Test-Path -LiteralPath (Join-Path $root 'build\zig\zig.exe'))) {
            & $bash.Source 'tools/fetch_zig.sh'
            if ($LASTEXITCODE -ne 0) { throw 'Fetching pinned Zig compiler failed' }
        }
        & $bash.Source 'tools/zig_slim.sh' '-O1' '-march=x86-64-v3' '-fno-strict-aliasing' '-Wno-return-type' '-Wno-unused-label' '-fvisibility=hidden'
        if ($LASTEXITCODE -ne 0) { throw 'Preparing portable Zig compiler failed' }
    } finally { Pop-Location }
}
if ($CreateDraft) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $packager -BuildId $BuildId -CreateDraft
} else {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $packager -BuildId $BuildId
}
if ($LASTEXITCODE -ne 0) { throw 'Scarlet runtime ZIP packaging failed.' }
