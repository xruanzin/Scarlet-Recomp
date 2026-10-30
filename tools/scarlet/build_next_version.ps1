# Build the existing Scarlet 4.0.0 AOT host and publish the NSP/XCI importer.
# No git reset or regeneration of lasgame.dll.
[CmdletBinding()]
param(
    [string]$BuildId = 'eb6deb908752b9c6',
    [switch]$SkipImporter,
    [switch]$SkipRuntime
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $repo
$bin = Join-Path $repo "build\scarlet\$BuildId"
if (!(Test-Path $bin)) { throw "Nao achei a pasta AOT: $bin" }
if (!(Test-Path (Join-Path $bin 'lasgame.dll'))) {
    throw 'lasgame.dll ausente; este script so atualiza o runtime, nao recompila a AOT.'
}

# Avoid filling C: with NuGet temporary caches.
$cache = Join-Path $repo 'build\scarlet-tools-cache'
New-Item -ItemType Directory -Force $cache | Out-Null
$env:DOTNET_CLI_HOME = $cache
$env:NUGET_PACKAGES = Join-Path $cache 'nuget-packages'
$env:TMP = Join-Path $cache 'tmp'
$env:TEMP = $env:TMP
New-Item -ItemType Directory -Force $env:TMP | Out-Null

if (!$SkipImporter) {
    if (!(Get-Command dotnet -ErrorAction SilentlyContinue)) {
        throw 'Para compilar o importador NSP/XCI, instale o .NET 8 SDK (dotnet).'
    }
    $project = Join-Path $repo 'tools\scarletimport\scarletimport.csproj'
    $target = Join-Path $bin 'scarletimport'
    & dotnet publish $project -r win-x64 --self-contained true -c Release -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o $target
    if ($LASTEXITCODE -ne 0) { throw 'Falha no dotnet publish scarletimport' }
    if (!(Test-Path (Join-Path $target 'scarletimport.exe'))) {
        throw 'scarletimport.exe nao foi gerado'
    }
    Write-Host "Importer: $(Join-Path $target 'scarletimport.exe')"
}
if (!$SkipRuntime) {
    $env:PATH = "C:\msys64\ucrt64\bin;C:\msys64\usr\bin;" + $env:PATH
    $env:MSYSTEM = 'UCRT64'
    $build = "build/scarlet/$BuildId"
    & make -j2 SCARLET_AOT=1 "GEN=generated-scarlet/$BuildId" "B=$build" "$build/scarlet.exe"
    if ($LASTEXITCODE -ne 0) { throw 'Falha na compilacao incremental do Scarlet runtime' }
}
Write-Host "Pronto. Abra: $(Join-Path $bin 'scarlet.exe')"
