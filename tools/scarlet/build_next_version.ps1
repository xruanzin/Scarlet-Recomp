# Build the existing Scarlet 4.0.0 AOT host and publish the NSP/XCI importer.
# No git reset or regeneration of lasgame.dll.
[CmdletBinding()]
param(
    [string]$BuildId = 'eb6deb908752b9c6',
    [switch]$SkipImporter,
    [switch]$SkipRuntime,
    [string]$IconPath = ''
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

# Optional user-supplied icon, shared by native Scarlet game + launcher.
# Users can save the exact icon from their ChatGPT upload as D:\Scarlet-Recomp\icon.ico,
# or pass -IconPath <their ico>. Never modify upstream docs/icon/icon.ico.
if (!$IconPath) {
    $candidate = Join-Path $repo 'icon.ico'
    if (Test-Path -LiteralPath $candidate) { $IconPath = $candidate }
}
if ($IconPath) {
    $source = (Resolve-Path -LiteralPath $IconPath -ErrorAction Stop).Path
    $bytes = [System.IO.File]::ReadAllBytes($source)
    if ($bytes.Length -lt 22 -or $bytes[0] -ne 0 -or $bytes[1] -ne 0 -or
        $bytes[2] -ne 1 -or $bytes[3] -ne 0) {
        throw "Arquivo nao e um icone Windows ICO valido: $source"
    }
    $targetIcon = Join-Path $repo 'docs\icon\scarlet.ico'
    if ($source -ne $targetIcon) { Copy-Item -LiteralPath $source -Destination $targetIcon -Force }
    Write-Host "Icone Scarlet instalado: $targetIcon"
} elseif (!(Test-Path -LiteralPath (Join-Path $repo 'docs\icon\scarlet.ico'))) {
    Write-Warning 'Icone nao encontrado. Salve o ICO enviado como D:\Scarlet-Recomp\icon.ico e execute novamente para incluir no scarlet.exe.'
}

# Recompile only the *host* objects when moving from the old ZA binary to
# Scarlet mode for the first time. Make does not otherwise track CFLAGS
# changed by SCARLET_AOT; stale objects can silently launch the old game.
$flavour = Join-Path $bin '.scarlet-native-launcher-mode'
if (!$SkipRuntime) {
    if (!(Test-Path -LiteralPath $flavour)) {
        Write-Host 'Primeira compilacao Scarlet: invalidando somente os objetos do host (AOT preservada).'
        foreach ($obj in @(
            'rt/main.o', 'rt/ui/launcher.o', 'rt/nvn/vulkan/device.o',
            'rt/nvn/vulkan/exec.o', 'rt/nvn/objects.o',
            'rt/platform/windows_rc.o'
        )) {
            $objPath = Join-Path $bin $obj
            if (Test-Path -LiteralPath $objPath) {
                Remove-Item -LiteralPath $objPath -Force
            }
        }
    }
    $env:PATH = "C:\msys64\ucrt64\bin;C:\msys64\usr\bin;" + $env:PATH
    $env:MSYSTEM = 'UCRT64'
    $build = "build/scarlet/$BuildId"
    & make -j2 SCARLET_AOT=1 "GEN=generated-scarlet/$BuildId" "B=$build" "$build/scarlet.exe" "$build/ScarletLauncher.exe"
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar Scarlet runtime/launcher Win32' }
    if (!(Test-Path -LiteralPath (Join-Path $bin 'ScarletLauncher.exe'))) {
        throw 'ScarletLauncher.exe nao foi gerado'
    }
    Set-Content -LiteralPath $flavour -Value 'SCARLET_AOT=1; launcher=ScarletPC-Win32-GDI; icon=Scarlet' -Encoding ASCII
    Write-Host 'Scarlet Win32 e runtime compilados. Abra scarlet.exe sem --play.'
}

# Copy the original background image from the owner's Scarlet PC launcher.
# It is downloaded directly from the specified GitHub branch, without changing
# the source repository. A missing network connection only affects the backdrop.
$assets = Join-Path $bin 'assets'
$background = Join-Path $assets 'scarlet_launcher_background.jpg'
if (!(Test-Path -LiteralPath $background)) {
    New-Item -ItemType Directory -Path $assets -Force | Out-Null
    $oldBgUrl = 'https://raw.githubusercontent.com/xruanzin/scarlet_pc/perf/zen2-aot-production/launcher/assets/scarlet_launcher_background.jpg'
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $oldBgUrl -OutFile $background -ErrorAction Stop
        Write-Host 'Fundo original do Scarlet PC copiado.'
    } catch {
        Write-Warning 'Nao foi possivel copiar o fundo original; a interface usa a cor base.'
    }
}

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
Write-Host "Pronto. Abra: $(Join-Path $bin 'scarlet.exe')"
