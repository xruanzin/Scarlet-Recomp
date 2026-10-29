# Validate and optionally repoint the test RomFS junction. No AOT build.
# Never remove original game files; changing junctions requires -Apply.
[CmdletBinding()]
param(
    [string]$Candidate,
    [switch]$Apply,
    [string]$TestRoot = "D:\Scarlet-Recomp\scarlet-boot-test"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$junction = Join-Path $TestRoot "romfs"
$exefs = Join-Path $TestRoot "exefs"

function IsExeFs([string]$folder) {
    if (Test-Path -LiteralPath (Join-Path $folder "main.npdm")) { return $true }
    $main = Join-Path $folder "main"
    if (Test-Path -LiteralPath $main -PathType Leaf) {
        $f = [System.IO.File]::OpenRead($main)
        try {
            $signature = New-Object byte[] 4
            if ($f.Read($signature, 0, 4) -eq 4) {
                return [Text.Encoding]::ASCII.GetString($signature) -eq "NSO0"
            }
        } finally { $f.Dispose() }
    }
    return $false
}

$existing = Get-Item -LiteralPath $junction -Force -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "RomFS atual: $($existing.FullName) [$($existing.LinkType)]"
    Write-Host "Destino atual: $($existing.Target)"
} else {
    Write-Host "RomFS atual: ausente"
}

if (-not $Candidate) {
    Write-Host ""
    Write-Host "Buscando pastas RomFS candidatas (nao altera arquivos):"
    $parents = @("D:\Pokemon Scarlet\Extracted", "D:\Pokemon Scarlet", "D:\ScarletNativeCache")
    $found = @()
    foreach ($parent in $parents) {
        if (-not (Test-Path -LiteralPath $parent -PathType Container)) { continue }
        $dirs = Get-ChildItem -LiteralPath $parent -Directory -Recurse -Depth 3 -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -ieq "romfs" } | Select-Object -First 30
        foreach ($dir in $dirs) {
            if ($found -notcontains $dir.FullName) { $found += $dir.FullName }
        }
    }
    if ($found.Count -gt 0) { $found | ForEach-Object { Write-Host " - $_" } }
    else { Write-Host "Nenhuma pasta RomFS encontrada. Extraia o RomFS real da base e da atualizacao." }
    Write-Host ""
    Write-Host "Verificar: .\tools\scarlet\romfs_link.ps1 -Candidate 'D:\CAMINHO\RomFS'"
    Write-Host "Aplicar:   .\tools\scarlet\romfs_link.ps1 -Candidate 'D:\CAMINHO\RomFS' -Apply"
    exit 0
}

if (-not (Test-Path -LiteralPath $Candidate -PathType Container)) {
    throw "A candidata deve ser uma pasta RomFS extraida: $Candidate"
}
$resolvedCandidate = (Resolve-Path -LiteralPath $Candidate).ProviderPath
$resolvedExeFS = if (Test-Path -LiteralPath $exefs) {
    (Resolve-Path -LiteralPath $exefs).ProviderPath
} else { "" }
if ($resolvedCandidate -eq $resolvedExeFS -or (IsExeFs $resolvedCandidate)) {
    throw "RECUSADO: caminho ExeFS, nao RomFS. Nao use main/sdk/subsdk0."
}

# Only sample 101 files to avoid traversing a giant extracted RomFS.
$sample = @(Get-ChildItem -LiteralPath $resolvedCandidate -File -Recurse |
    Select-Object -First 101)
if ($sample.Count -lt 101) {
    throw "RECUSADO: apenas $($sample.Count) arquivos. Nao parece um RomFS completo."
}
Write-Host "Candidato: $resolvedCandidate"
Write-Host "Mais de 100 arquivos e sem NSO/NPDM do ExeFS."
Write-Warning "Esta checagem NAO comprova o merge correto da base com update 4.0.0."

if (-not $Apply) {
    Write-Host "Somente validacao. Use -Apply para trocar a junction de teste."
    exit 0
}
if (Get-Process -Name "scarlet" -ErrorAction SilentlyContinue) {
    throw "Feche o scarlet.exe antes de trocar a junction."
}
if ($existing -and $existing.LinkType -ne "Junction") {
    throw "RECUSADO: o romfs atual nao e junction; nao vou apagar arquivos reais."
}
$previousTarget = if ($existing) { [string]@($existing.Target)[0] } else { $null }
if ($existing) {
    # cmd.exe rmdir on a junction removes ONLY the link, not its target.
    & $env:ComSpec /D /C ('rmdir "' + $junction + '"')
    if ($LASTEXITCODE -ne 0) { throw "Falha ao remover a junction antiga." }
}
try {
    $null = New-Item -ItemType Junction -Path $junction -Target $resolvedCandidate
    $actual = Get-Item -LiteralPath $junction -Force
    if ($actual.LinkType -ne "Junction") {
        throw "O novo link nao e uma junction."
    }
    Write-Host "OK: $junction -> $($actual.Target)"
} catch {
    if ($previousTarget -and -not (Test-Path -LiteralPath $junction)) {
        $null = New-Item -ItemType Junction -Path $junction -Target $previousTarget
        Write-Warning "Junction anterior restaurada."
    }
    throw
}
