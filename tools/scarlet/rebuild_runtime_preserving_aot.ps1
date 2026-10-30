# Rebuild only the Scarlet Windows runtime, keeping the existing lasgame.dll/AOT.
# The old game library's embedded ID is authoritative ONLY if its ABI and game
# version were previously validated (as in the running Scarlet 4.0.0 build).
[CmdletBinding()]
param(
    [string]$BuildDir = 'build/scarlet/eb6deb908752b9c6',
    [int]$Jobs = 2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $root
try {
    if ($BuildDir -match '^(?:[A-Za-z]:|\\|/)') {
        throw 'Use um BuildDir relativo ao repositorio.'
    }
    $lib = Join-Path $root ($BuildDir + '/lasgame.dll')
    $idPath = $lib + '.id'
    if (-not (Test-Path -LiteralPath $lib -PathType Leaf)) { throw "AOT nao encontrada: $lib" }
    if (-not (Test-Path -LiteralPath $idPath -PathType Leaf)) { throw "ID da AOT nao encontrado: $idPath" }

    $originalId = (Get-Content -LiteralPath $idPath -Raw).Trim()
    if ($originalId -notmatch '^([0-9a-fA-F]{16})-([0-9a-fA-F]{16})$') {
        throw "ID inesperado da AOT: $originalId"
    }
    $idPrefix = $Matches[1]
    $mainBuildId = $Matches[2].ToUpperInvariant()
    if ($mainBuildId -ne '421C5411B487EB4D') {
        throw "Esta AOT nao e de Scarlet 4.0.0 (main $mainBuildId). Abortando."
    }

    # These changes may alter the guest-code ABI even if they do not regenerate
    # lasgame.dll. An ID override would be unsafe if any is modified locally.
    $aotInputs = @(
        'runtime/cpu.h','runtime/simd.h','runtime/simd_fp.h','runtime/gamelib.h',
        'tools/gen.py','tools/lifter.py','tools/passes.py','tools/analyze.py',
        'tools/simd_c.py','tools/gamelib_entry.c','tools/flagfuse.py',
        'tools/regpromote.py','tools/patches.py','tools/nso.py',
        'tools/game_addresses.py','runtime/game_addresses/versions.h',
        'runtime/hle/hle_symbols.txt'
    )
    $dirty = @(& git diff --name-only -- $aotInputs)
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel verificar o Git.' }
    if ($dirty.Count -gt 0) {
        throw ('Entradas da AOT modificadas; nao e seguro reutilizar o ID: ' + ($dirty -join ', '))
    }

    $bin = Join-Path $root ($BuildDir + '/scarlet.exe')
    $backup = $null
    if (Test-Path -LiteralPath $bin) {
        $backup = "$bin.before-aot-preserving-build-$(Get-Date -Format yyyyMMdd-HHmmss).bak"
        Copy-Item -LiteralPath $bin -Destination $backup
    }
    $before = (Get-FileHash -LiteralPath $lib -Algorithm SHA256).Hash
    $pathPrefix = 'C:\msys64\ucrt64\bin;C:\msys64\usr\bin;'
    if (-not $env:PATH.StartsWith($pathPrefix)) { $env:PATH = $pathPrefix + $env:PATH }
    $env:MSYSTEM = 'UCRT64'

    $vars = @("-j$Jobs", 'SCARLET_AOT=1', "B=$BuildDir", "GAMELIB_ID=$idPrefix")
    Write-Host "[Scarlet] AOT ID: $originalId"
    Write-Host '[Scarlet] Rebuilding gamelib.o and gamebuild.o with the ORIGINAL AOT ID.'
    Write-Host '[Scarlet] No generated game objects or lasgame.dll will be compiled.'
    & make -B @vars "$BuildDir/rt/gamelib.o" "$BuildDir/rt/gamebuild.o"
    if ($LASTEXITCODE -ne 0) { throw "Falha ao recompilar verificacao da AOT (exit $LASTEXITCODE)." }

    & make @vars "$BuildDir/scarlet.exe"
    if ($LASTEXITCODE -ne 0) { throw "Falha ao recompilar runtime (exit $LASTEXITCODE)." }
    if (-not (Test-Path -LiteralPath $bin)) { throw "Executavel ausente apos build: $bin" }
    $after = (Get-FileHash -LiteralPath $lib -Algorithm SHA256).Hash
    if ($before -ne $after) { throw 'ALERTA: hash da lasgame.dll mudou. Verifique o ambiente.' }
    $afterId = (Get-Content -LiteralPath $idPath -Raw).Trim()
    if ($originalId -ne $afterId) { throw 'ALERTA: arquivo .id da AOT foi modificado.' }

    Write-Host "[Scarlet] OK: runtime atualizado e AOT intacta." -ForegroundColor Green
    Write-Host "[Scarlet] Executavel: $bin"
    if ($backup) { Write-Host "[Scarlet] Backup anterior: $backup" }
}
finally {
    Pop-Location
}
