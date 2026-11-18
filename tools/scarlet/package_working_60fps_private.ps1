# Create a PRIVATE, local-only playable ZIP from the exact successful
# Scarlet-Recomp 60 FPS installation. Never publish this archive: it includes
# the player's own game files, AOT library and potentially saves/keys.
# Does not rebuild the runtime or modify the original installation.
[CmdletBinding()]
param(
    [string]$WorkingData = 'D:\Scarlet-Window-Playtest-20261112',
    [string]$WorkingBuild = 'build\window-full-20261112',
    [string]$BaseZip = 'build\dist\Scarlet-Recomp-Controls-RC-Windows-x64.zip'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
Push-Location -LiteralPath $repo
try {
    $working = (Resolve-Path -LiteralPath $WorkingBuild -ErrorAction Stop).Path
    $data = (Resolve-Path -LiteralPath $WorkingData -ErrorAction Stop).Path
    $base = (Resolve-Path -LiteralPath $BaseZip -ErrorAction Stop).Path

    $exe = Join-Path $working 'scarlet.exe'
    $aot = Join-Path $working 'lasgame.dll'
    $aotId = Join-Path $working 'lasgame.dll.id'
    $game = Join-Path $data 'scarlet-games\active\exefs\main'
    foreach ($file in @($exe, $aot, $aotId, $game)) {
        if (!(Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Arquivo da instalacao funcional nao encontrado: $file"
        }
    }
    $expected = '04C60A58A37F6D347AF78D7F4AECC0EBACB27D62C4A4E46AA384395B3074BF0B'
    $actual = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
    if ($actual -ne $expected) {
        throw ("O scarlet.exe foi alterado desde o teste funcional. " +
               "Esperado: $expected. Encontrado: $actual. " +
               "Nao vou criar um ZIP de uma build ainda nao confirmada.")
    }
    if (@(Get-Process -Name scarlet, ScarletLauncher -ErrorAction SilentlyContinue).Count -gt 0) {
        throw 'Feche Scarlet e ScarletLauncher antes de criar o snapshot.'
    }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $stage = Join-Path $repo ("build\scarlet-working-private-stage-$stamp")
    $bundle = Join-Path $stage 'Scarlet-Recomp'
    $dist = Join-Path $repo 'build\dist'
    $zip = Join-Path $dist ("Scarlet-Recomp-Working-60FPS-PRIVATE-DO-NOT-UPLOAD-$stamp.zip")

    Write-Warning 'ZIP PRIVADO: tera seu jogo, DLL AOT, saves e possivelmente chaves. NAO ENVIE AO GITHUB NEM A TERCEIROS.'
    Write-Host "Usando exatamente o scarlet.exe validado: $actual" -ForegroundColor Cyan
    Write-Host "Dados/saves da instalacao funcional: $data"
    Write-Host "ZIP base sem arquivos do jogo: $base"
    Write-Host "Preparando copia isolada em: $stage"
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    New-Item -ItemType Directory -Path $dist -Force | Out-Null

    $succeeded = $false
    try {
        # Use the original public bundle as the DLL/tool dependency base,
        # and replace ONLY its runtime executable with the working one.
        Expand-Archive -LiteralPath $base -DestinationPath $stage -ErrorAction Stop
        if (!(Test-Path -LiteralPath (Join-Path $bundle 'ScarletLauncher.exe') -PathType Leaf)) {
            throw 'O ZIP base nao contem Scarlet-Recomp/ScarletLauncher.exe.'
        }

        # Match the successful playtest's actual data root, including shader
        # caches and save files. Keep every original folder untouched.
        foreach ($entry in @(Get-ChildItem -LiteralPath $data -Force -ErrorAction Stop)) {
            if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Nao vou seguir links/junctions dentro dos dados: $($entry.FullName)"
            }
            Copy-Item -LiteralPath $entry.FullName -Destination $bundle -Recurse -Force -ErrorAction Stop
        }
        Copy-Item -LiteralPath $exe -Destination (Join-Path $bundle 'scarlet.exe') -Force
        Copy-Item -LiteralPath $aot -Destination (Join-Path $bundle 'lasgame.dll') -Force
        Copy-Item -LiteralPath $aotId -Destination (Join-Path $bundle 'lasgame.dll.id') -Force

        # This launch path mirrors build_play_f1_white.ps1 exactly, while
        # resolving the game library and save/data root to the ZIP folder.
        # Start directly in the already-prepared game: the import launcher
        # would otherwise use different first-run build and save paths.
        $cmd = @'
@echo off
setlocal
cd /d "%~dp0"
set "LARECOMP_DATA_ROOT=%~dp0"
set "LARECOMP_GAME_LIB=%~dp0lasgame.dll"
set "SCARLET_TARGET_FPS=60"
set "SCARLET_FPS60=1"
set "SCARLET_PHASE_LOCK=1"
set "SCARLET_INDOOR_CAMERA_60=1"
set "SCARLET_NORMALIZE_LSTICK=1"
set "LARECOMP_GPU_OVERLAP=0"
"%~dp0scarlet.exe" --play "%~dp0scarlet-games\active"
if errorlevel 1 pause
'@
        $cmdFile = Join-Path $bundle 'JOGAR-60FPS.cmd'
        [System.IO.File]::WriteAllText($cmdFile, $cmd,
            [System.Text.Encoding]::ASCII)
        $warning = @'
PRIVATE LOCAL BACKUP - DO NOT UPLOAD OR SHARE

This archive copies your own game files, compiled game library, data,
settings, caches, and saves for a local performance comparison.

Open JOGAR-60FPS.cmd to launch the already prepared installation.
Do not use the bundled import launcher for the first performance comparison.

This is not the distributable public release.
'@
        [System.IO.File]::WriteAllText(
            (Join-Path $bundle 'PRIVATE-LOCAL-ONLY.txt'), $warning,
            [System.Text.Encoding]::ASCII)

        $copied = (Get-FileHash -LiteralPath (Join-Path $bundle 'scarlet.exe') -Algorithm SHA256).Hash
        if ($copied -ne $expected) { throw 'O scarlet.exe copiado nao corresponde ao build validado.' }
        foreach ($required in @('lasgame.dll','lasgame.dll.id','scarlet-games\active\exefs\main','JOGAR-60FPS.cmd')) {
            if (!(Test-Path -LiteralPath (Join-Path $bundle $required) -PathType Leaf)) {
                throw "Snapshot incompleto: $required"
            }
        }

        Add-Type -AssemblyName System.IO.Compression
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::CreateFromDirectory(
            $stage, $zip,
            [System.IO.Compression.CompressionLevel]::Fastest,
            $false)
        $archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
        try {
            $names = @($archive.Entries | ForEach-Object { $_.FullName.Replace('\','/') })
            foreach ($required in @('Scarlet-Recomp/JOGAR-60FPS.cmd',
                                    'Scarlet-Recomp/scarlet.exe',
                                    'Scarlet-Recomp/lasgame.dll',
                                    'Scarlet-Recomp/scarlet-games/active/exefs/main')) {
                if ($names -notcontains $required) {
                    throw "O ZIP criado nao contem: $required"
                }
            }
        } finally { $archive.Dispose() }

        $zipHash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash
        Set-Content -LiteralPath ($zip + '.sha256') -Encoding ASCII -Value $zipHash
        $succeeded = $true
        Write-Host "ZIP LOCAL GERADO: $zip" -ForegroundColor Green
        Write-Host ("Tamanho: {0:N2} GB" -f ((Get-Item -LiteralPath $zip).Length / 1GB))
        Write-Host 'Extraia em outra pasta e abra JOGAR-60FPS.cmd. O save sera o mesmo da instalacao funcional.'
        Write-Warning 'Arquivo PRIVADO. Nao publique: ele contem dados privados/do jogo.'
    } finally {
        # Stage is our own uniquely-created directory. Leave it intact if
        # packaging fails, so nothing valuable is silently lost.
        if ($succeeded -and (Test-Path -LiteralPath $stage)) {
            Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction Continue
        }
    }
} finally {
    Pop-Location
}
