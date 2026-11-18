# Scarlet-Recomp Controls RC: build/package/test a public Windows ZIP.
# Runs on the maintainer's Windows machine with the project's toolchain.
# Does not publish a GitHub release, include a game DLL or modify saves.
[CmdletBinding()]
param(
    [string]$BuildId = 'eb6deb908752b9c6',
    [switch]$UsePreparedBuild,
    [switch]$SkipSmokeTest
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $root
$expected = 'release/scarlet-stable-controls-rc-20261117'
$actual = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $actual -ne $expected) {
    throw "Incorrect branch '$actual'. Check out '$expected' first."
}
$dirty = @(& git status --porcelain --untracked-files=normal)
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the Git working tree.' }
if ($dirty.Count -gt 0) {
    throw "Working tree is not clean. Commit or stash changes before packaging:`n$($dirty -join [Environment]::NewLine)"
}
if ((Get-Process scarlet,ScarletLauncher -ErrorAction SilentlyContinue)) {
    throw 'Close Scarlet and ScarletLauncher before building the release ZIP.'
}
$zip = Join-Path $root 'build\dist\Scarlet-Recomp-Controls-RC-Windows-x64.zip'
$hashFile = $zip + '.sha256'
$builder = Join-Path $root 'tools\scarlet\build_release_candidate.ps1'
$packager = Join-Path $root 'tools\scarlet\create_release_zip.ps1'
$test = Join-Path $root 'tools\scarlet\test_release_zip.ps1'

Write-Host 'Scarlet-Recomp Controls RC (Windows x64) — pacote publico' -ForegroundColor Cyan
Write-Host 'Branch verificada; compilacao AOT do jogo permanece particular.' -ForegroundColor Cyan
if ($UsePreparedBuild) {
    $compiled = Join-Path $root ("build\scarlet\" + $BuildId + "\scarlet.exe")
    if (!(Test-Path -LiteralPath $compiled -PathType Leaf)) {
        throw "No prepared build: $compiled. Run without -UsePreparedBuild to compile."
    }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $packager -BuildId $BuildId -ControlsRC
} else {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $builder -BuildId $BuildId -ControlsRC
}
if ($LASTEXITCODE -ne 0) {
    throw 'Build or ZIP packaging failed. Nothing has been published.'
}
if (!(Test-Path -LiteralPath $zip -PathType Leaf)) { throw "ZIP missing after packaging: $zip" }
if (!(Test-Path -LiteralPath $hashFile -PathType Leaf)) { throw "SHA256 missing after packaging: $hashFile" }
if (-not $SkipSmokeTest) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $test -ZipPath $zip
    if ($LASTEXITCODE -ne 0) {
        throw 'Portable ZIP smoke test failed. DO NOT publish this file.'
    }
} else {
    Write-Warning 'Smoke test deliberately skipped. Do not label the archive stable without testing it.'
}
$sha = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
$stamp = (Get-Content -LiteralPath $hashFile -Raw).Trim()
if (-not $stamp.StartsWith($sha, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'ZIP SHA256 does not match checksum file. Do not distribute.'
}
$size = [math]::Round((Get-Item -LiteralPath $zip).Length / 1MB, 2)
Write-Host ''
Write-Host "ZIP GERADO: $zip" -ForegroundColor Green
Write-Host ("Tamanho: {0:N2} MB" -f $size) -ForegroundColor Green
Write-Host "SHA256: $sha" -ForegroundColor Cyan
Write-Host 'Nao publicado. Revise creditos/licencas e teste importacao AOT em uma pasta limpa antes da release publica.'
