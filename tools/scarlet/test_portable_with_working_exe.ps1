# Compare the installed portable ZIP with the developer's 60 FPS runtime
# without copying private game code, overwriting saves, or rebuilding AOT.
[CmdletBinding()]
param(
    [string]$PortableDirectory = '',
    [string]$SourceExe = '',
    [switch]$SkipLaunch
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
if (!$SourceExe) { $SourceExe = Join-Path $repo 'build\window-full-20261112\scarlet.exe' }
$SourceExe = (Resolve-Path -LiteralPath $SourceExe -ErrorAction Stop).Path

if (!(Test-Path -LiteralPath $PortableDirectory -PathType Container)) {
    if ($PortableDirectory) {
        throw "Pasta portable nao encontrada: $PortableDirectory"
    }
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.OpenFileDialog
    $picker.Title = 'Selecione ScarletLauncher.exe na pasta EXTRAIDA do ZIP'
    $picker.Filter = 'Scarlet launcher (ScarletLauncher.exe)|ScarletLauncher.exe'
    $picker.FileName = 'ScarletLauncher.exe'
    $picker.CheckFileExists = $true
    try {
        if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
            Write-Host 'Teste cancelado; nenhum arquivo modificado.'
            return
        }
        $PortableDirectory = Split-Path -Parent $picker.FileName
    } finally {
        $picker.Dispose()
    }
}
$PortableDirectory = (Resolve-Path -LiteralPath $PortableDirectory -ErrorAction Stop).Path
$launcher = Join-Path $PortableDirectory 'ScarletLauncher.exe'
$target = Join-Path $PortableDirectory 'scarlet.exe'
foreach ($file in @($launcher,$target)) {
    if (!(Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Pasta invalida: arquivo ausente: $file"
    }
}
if ([String]::Equals($SourceExe,$target,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Fonte e destino sao o mesmo executavel. Escolha a pasta extraida do ZIP.'
}
if (@(Get-Process -Name scarlet -ErrorAction SilentlyContinue).Count -gt 0) {
    throw 'Feche todas as instancias do Scarlet antes de copiar o runtime.'
}

# Verify that this source is the branch used for the successful phase-lock test.
# Source-specific SHA is intentionally not hardcoded: the build is made locally.
$fromHash = (Get-FileHash -LiteralPath $SourceExe -Algorithm SHA256).Hash
$oldHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
Write-Host "Runtime comprovado: $SourceExe"
Write-Host "Pasta extraida:     $PortableDirectory"
Write-Host "SHA256 fonte:       $fromHash"
Write-Host "SHA256 portable:    $oldHash"
$ini = Join-Path $PortableDirectory 'user\config\scarlet_launcher.ini'
if (Test-Path -LiteralPath $ini -PathType Leaf) {
    $selected = Select-String -LiteralPath $ini -Pattern '^target_fps\s*=' -ErrorAction SilentlyContinue
    if ($selected) { Write-Host "FPS salvo no launcher: $($selected.Line.Trim())" }
}
if ($fromHash -ne $oldHash) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup = Join-Path $PortableDirectory ("scarlet.exe.before-60fps-test-$stamp")
    Copy-Item -LiteralPath $target -Destination $backup -ErrorAction Stop
    Copy-Item -LiteralPath $SourceExe -Destination $target -Force -ErrorAction Stop
    $newHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
    if ($newHash -ne $fromHash) {
        Copy-Item -LiteralPath $backup -Destination $target -Force
        throw 'A copia do runtime falhou: o executavel original foi restaurado.'
    }
    Write-Host "Backup do EXE anterior: $backup" -ForegroundColor Cyan
    Write-Host 'Runtime de 60 FPS instalado na copia extraida.' -ForegroundColor Green
} else {
    Write-Host 'A pasta extraida ja tem o mesmo scarlet.exe; nao foi necessario copiar.' -ForegroundColor Yellow
}
Write-Host 'Os saves, larecomp.ini, scarlet-games, DLL AOT e preferencias do launcher NAO foram alterados.'
if ($SkipLaunch) { return }

# The working playtest used these settings. Apply them only to the child
# launcher process; do not change the saved config or user data root.
$env:SCARLET_PHASE_LOCK = '1'
$env:SCARLET_INDOOR_CAMERA_60 = '1'
$env:SCARLET_NORMALIZE_LSTICK = '1'
$env:LARECOMP_GPU_OVERLAP = '0'
Remove-Item Env:LARECOMP_DATA_ROOT -ErrorAction SilentlyContinue
Remove-Item Env:LARECOMP_GAME_LIB -ErrorAction SilentlyContinue
Write-Host 'Abrindo a mesma pasta portable, com o mesmo save dela. Selecione 60 FPS no launcher.' -ForegroundColor Green
Start-Process -FilePath $launcher -WorkingDirectory $PortableDirectory
Write-Host ("Log do jogo portable: " + (Join-Path $PortableDirectory 'user\log\scarlet-game.log'))
