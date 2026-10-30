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

# A runtime-only 'dotnet.exe' exists on many Windows PCs, but it cannot run
# 'dotnet publish'. Check actual SDK installations, not just Get-Command.
function Has-DotnetSdk([string]$Exe) {
    if (!$Exe -or !(Test-Path -LiteralPath $Exe)) { return $false }
    $installed = @(& $Exe --list-sdks 2>$null)
    return ($LASTEXITCODE -eq 0 -and $installed.Count -gt 0)
}

if (!$SkipImporter) {
    $sdkRoot = Join-Path $cache 'dotnet-sdk-8'
    $sdkExe = Join-Path $sdkRoot 'dotnet.exe'
    $dotnet = $null
    $systemDotnet = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($systemDotnet -and (Has-DotnetSdk $systemDotnet.Source)) {
        $dotnet = $systemDotnet.Source
    } elseif (Has-DotnetSdk $sdkExe) {
        $dotnet = $sdkExe
    } else {
        # Microsoft official non-admin bootstrap, installed only in this
        # repository's D: cache. It does not modify global PATH or registry.
        $installer = Join-Path $cache 'dotnet-install.ps1'
        $installerUrl = 'https://dot.net/v1/dotnet-install.ps1'
        Write-Host 'Nenhum .NET SDK encontrado. Instalando SDK .NET 8 no cache local do Scarlet (D:) ...'
        if (!(Test-Path -LiteralPath $installer)) {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -UseBasicParsing -Uri $installerUrl -OutFile $installer -ErrorAction Stop
        }
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer `
            -Channel 8.0 -Architecture x64 -InstallDir $sdkRoot -NoPath
        if ($LASTEXITCODE -ne 0 -or !(Has-DotnetSdk $sdkExe)) {
            throw 'Falha ao instalar o SDK .NET 8 no D:. Verifique rede/espaco livre.'
        }
        $dotnet = $sdkExe
    }

    if ($dotnet -eq $sdkExe) {
        $env:DOTNET_ROOT = $sdkRoot
        $env:PATH = "$sdkRoot;" + $env:PATH
    }
    $env:DOTNET_NOLOGO = '1'
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
    Write-Host "SDK selecionado: $dotnet"
    & $dotnet --list-sdks
    $project = Join-Path $repo 'tools\scarletimport\scarletimport.csproj'
    $target = Join-Path $bin 'scarletimport'
    & $dotnet publish $project -r win-x64 --self-contained true -c Release -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o $target
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
