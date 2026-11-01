# Temporary Scarlet enrollment photo replacement. Requires a PNG/JPEG/BMP of
# the *selected character*, because the game's original producer is still broken.
# No changes to AOT, saves, game content, or installed settings.
[CmdletBinding()]
param(
    [string]$ImagePath = "",
    [string]$BinDir = ""
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
if (-not $BinDir) {
    $bins = @(Get-ChildItem -LiteralPath (Join-Path $repo "build\scarlet") -Filter "scarlet.exe" -File -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending)
    if ($bins.Count -lt 1) { throw "scarlet.exe nao encontrado em build\scarlet. Compile primeiro." }
    $BinDir = $bins[0].DirectoryName
}
$BinDir = (Resolve-Path -LiteralPath $BinDir).Path
if (-not $ImagePath) { $ImagePath = Join-Path $BinDir "user\scarlet-portrait.png" }
if (-not (Test-Path -LiteralPath $ImagePath -PathType Leaf)) {
    throw "Salve primeiro uma imagem real do seu personagem em: $ImagePath"
}
$ImagePath = (Resolve-Path -LiteralPath $ImagePath).Path
$exe = Join-Path $BinDir "scarlet.exe"
$game = Join-Path $BinDir "scarlet-games\active"
if (-not (Test-Path -LiteralPath $game)) { throw "Jogo nao encontrado: $game" }
$logdir = Join-Path $BinDir "user\log"
New-Item -ItemType Directory -Force -Path $logdir | Out-Null
$log = Join-Path $logdir "scarlet-portrait-fallback.log"
$keys = @("SCARLET_EARLY_TLS_PROBE", "SCARLET_BOOTSTRAP_ALLOCATOR", "SCARLET_PORTRAIT_IMAGE",
          "SCARLET_MAIN_INIT_FIRST", "SCARLET_PORTRAIT_GPU_COPY", "SCARLET_PORTRAIT_SOURCE_READBACK",
          "SCARLET_PORTRAIT_SOURCE_LINEAGE")
$previous = @{}
foreach ($key in $keys) { $previous[$key] = [Environment]::GetEnvironmentVariable($key, "Process") }
try {
    $env:SCARLET_EARLY_TLS_PROBE = "1"
    $env:SCARLET_BOOTSTRAP_ALLOCATOR = "1"
    $env:SCARLET_PORTRAIT_IMAGE = $ImagePath
    foreach ($key in @("SCARLET_MAIN_INIT_FIRST", "SCARLET_PORTRAIT_GPU_COPY",
                       "SCARLET_PORTRAIT_SOURCE_READBACK", "SCARLET_PORTRAIT_SOURCE_LINEAGE")) {
        [Environment]::SetEnvironmentVariable($key, $null, "Process")
    }
    Write-Host "Imagem: $ImagePath"
    Write-Host "Jogo: $game"
    $p = Start-Process -FilePath $exe -ArgumentList @("--play", ('"' + $game + '"')) `
        -WorkingDirectory $BinDir -RedirectStandardError $log -PassThru -Wait
    Write-Host "Exit code: $($p.ExitCode)"
    Write-Host "Log: $log"
    Select-String -LiteralPath $log -Pattern '\[scarlet-portrait-fallback\]'
}
finally {
    foreach ($key in $keys) {
        [Environment]::SetEnvironmentVariable($key, $previous[$key], "Process")
    }
}
