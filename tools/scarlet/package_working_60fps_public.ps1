# Create a public-safe experimental portable ZIP using the exact scarlet.exe
# that was verified at ~60 FPS. No game files, keys, saves or AOT DLL.
# Builds nothing and never overwrites the previous RC ZIP.
[CmdletBinding()]
param(
    [string]$WorkingBuild = 'build\window-full-20261112',
    [string]$BaseZip = 'build\dist\Scarlet-Recomp-Controls-RC-Windows-x64.zip'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
Push-Location -LiteralPath $repo
try {
    $working = (Resolve-Path -LiteralPath $WorkingBuild -ErrorAction Stop).Path
    $base = (Resolve-Path -LiteralPath $BaseZip -ErrorAction Stop).Path
    $exe = Join-Path $working 'scarlet.exe'
    $expected = '04C60A58A37F6D347AF78D7F4AECC0EBACB27D62C4A4E46AA384395B3074BF0B'
    if (!(Test-Path -LiteralPath $exe -PathType Leaf)) { throw "EXE nao encontrado: $exe" }
    $hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
    if ($hash -ne $expected) {
        throw "O scarlet.exe nao e o executavel validado. SHA encontrado: $hash; esperado: $expected"
    }
    if (@(Get-Process -Name scarlet,ScarletLauncher -ErrorAction SilentlyContinue).Count -gt 0) {
        throw 'Feche o jogo e o launcher antes de empacotar.'
    }

    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $stage = Join-Path $repo ("build\scarlet-working-public-stage-$stamp")
    $bundle = Join-Path $stage 'Scarlet-Recomp'
    $outDir = Join-Path $repo 'build\dist'
    $output = Join-Path $outDir ("Scarlet-Recomp-Working-60FPS-PUBLIC-EXPERIMENTAL-$stamp.zip")
    New-Item -ItemType Directory -Path $stage,$outDir -Force | Out-Null
    $success = $false
    try {
        Expand-Archive -LiteralPath $base -DestinationPath $stage -ErrorAction Stop
        if (!(Test-Path -LiteralPath (Join-Path $bundle 'ScarletLauncher.exe') -PathType Leaf)) {
            throw 'ZIP base nao contem ScarletLauncher.exe.'
        }
        Copy-Item -LiteralPath $exe -Destination (Join-Path $bundle 'scarlet.exe') -Force
        $cmd = @'
@echo off
setlocal
cd /d "%~dp0"
set "SCARLET_PHASE_LOCK=1"
set "SCARLET_INDOOR_CAMERA_60=1"
set "SCARLET_NORMALIZE_LSTICK=1"
set "LARECOMP_GPU_OVERLAP=0"
set "LARECOMP_DATA_ROOT="
set "LARECOMP_GAME_LIB="
"%~dp0ScarletLauncher.exe"
'@
        [System.IO.File]::WriteAllText(
            (Join-Path $bundle 'ABRIR-LAUNCHER-60FPS.cmd'), $cmd,
            [System.Text.Encoding]::ASCII)
        $note = @'
Scarlet-Recomp | experimental 60 FPS portable candidate

Use ABRIR-LAUNCHER-60FPS.cmd to launch the bundled ScarletLauncher
with the same runtime flags used during the successful developer test.

Game files, keys, saves and lasgame.dll are NOT included.
You must prepare your own Scarlet 4.0.0 locally through the launcher.
The first-time AOT process on a clean Windows PC is not fully tested.
This archive is experimental and not yet a validated release.
'@
        [System.IO.File]::WriteAllText(
            (Join-Path $bundle 'WORKING-60FPS-README.txt'), $note,
            [System.Text.Encoding]::ASCII)

        # Release safety: never ship the compiled game DLL, keys or dumps.
        $denied = '(?i)(^|[\\/])(lasgame\.dll(\.id)?|prod\.keys|title\.keys|[^\\/]*\.(nsp|xci|nca|tik)|romfs(\.bin)?|exefs|scarlet-games|save|saves|user)([\\/]|$)'
        $bad = @(Get-ChildItem -LiteralPath $bundle -File -Recurse -Force |
                 Where-Object { $_.FullName -match $denied })
        if ($bad.Count -gt 0) {
            throw ("Arquivos privados encontrados no ZIP publico: " + ($bad.FullName -join ', '))
        }

        Add-Type -AssemblyName System.IO.Compression
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::CreateFromDirectory(
            $stage, $output,
            [System.IO.Compression.CompressionLevel]::Optimal,
            $false)
        $archive = [System.IO.Compression.ZipFile]::OpenRead($output)
        try {
            $entries = @($archive.Entries | ForEach-Object { $_.FullName.Replace('\','/') })
            foreach ($name in @('Scarlet-Recomp/scarlet.exe',
                                 'Scarlet-Recomp/ScarletLauncher.exe',
                                 'Scarlet-Recomp/ABRIR-LAUNCHER-60FPS.cmd',
                                 'Scarlet-Recomp/lasgen/lasgen.exe',
                                 'Scarlet-Recomp/zig/zig.exe')) {
                if ($entries -notcontains $name) { throw "Arquivo nao encontrado no ZIP: $name" }
            }
        } finally { $archive.Dispose() }
        $newHash = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash
        Set-Content -LiteralPath ($output + '.sha256') -Encoding ASCII -Value $newHash
        $testScript = Join-Path $repo 'tools\scarlet\test_release_zip.ps1'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $testScript -ZipPath $output
        if ($LASTEXITCODE -ne 0) { throw 'Smoke test falhou. NAO publique este ZIP.' }
        $success = $true
        Write-Host "ZIP EXPERIMENTAL GERADO: $output" -ForegroundColor Green
        Write-Host "SHA256: $newHash"
        Write-Host 'Para abrir, extraia em outra pasta e use ABRIR-LAUNCHER-60FPS.cmd.'
        Write-Warning 'O primeiro AOT e a estabilidade de 60 FPS em uma instalacao limpa ainda precisam ser testados.'
    } finally {
        if ($success -and (Test-Path -LiteralPath $stage)) {
            Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction Continue
        }
    }
} finally {
    Pop-Location
}
