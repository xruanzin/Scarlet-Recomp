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

# Scarlet stores most game resources in a small number of huge archives.
# Do NOT infer completeness from the number of loose files (24-30 is plausible).
$files = @(Get-ChildItem -LiteralPath $resolvedCandidate -File -Recurse -Force)
if (-not $files.Count) { throw "RECUSADO: pasta RomFS vazia." }
$totalBytes = ($files | Measure-Object -Property Length -Sum).Sum
$gb = [math]::Round($totalBytes / 1GB, 2)
Write-Host "Candidato: $resolvedCandidate"
Write-Host "Arquivos: $($files.Count); tamanho total: $gb GB"
Write-Host "Maiores arquivos:"
$files | Sort-Object Length -Descending | Select-Object -First 10 |
    ForEach-Object {
        $relative = $_.FullName.Substring($resolvedCandidate.TrimEnd('\').Length).TrimStart('\')
        Write-Host ("  {0,9:N1} MB  {1}" -f ($_.Length / 1MB), $relative)
    }

# Genuine Scarlet/Violet RomFS archives normally contain arc/data.trpfd
# (index) and arc/data.trpfs (archive). A partial update layer may have
# only one of them: never mislabel such a folder as a full merged game.
$descriptor = Join-Path $resolvedCandidate 'arc\data.trpfd'
$archive = Join-Path $resolvedCandidate 'arc\data.trpfs'
$hasDescriptor = (Test-Path -LiteralPath $descriptor -PathType Leaf) -and
                 ((Get-Item -LiteralPath $descriptor).Length -gt 0)
$hasArchive = (Test-Path -LiteralPath $archive -PathType Leaf) -and
              ((Get-Item -LiteralPath $archive).Length -gt 0)
Write-Host "arc/data.trpfd: $hasDescriptor"
Write-Host "arc/data.trpfs: $hasArchive"
if (-not ($hasDescriptor -and $hasArchive)) {
    Write-Warning "Sem o par data.trpfd + data.trpfs. Pode ser apenas um overlay de update/mod ou uma extracao incompleta."
    throw "RECUSADO: nao foi confirmado o arquivo principal do Scarlet. Preserve esta pasta e inspecione os dados."
}
Write-Warning "Arquivos-base presentes, mas nao e possivel verificar somente pela pasta se o update 4.0.0 foi aplicado."

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
