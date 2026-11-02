# Single command for the maintainer to build and package the public runtime.
# NOT a complete player installer: the user's locally generated lasgame.dll
# exists only for build/test and is explicitly excluded from the public archive.
[CmdletBinding()]
param(
    [string]$BuildId = 'eb6deb908752b9c6',
    [switch]$CreateDraft,
    [string]$PythonExe = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$builder = Join-Path $root 'tools\scarlet\build_next_version.ps1'
$packager = Join-Path $root 'tools\scarlet\create_release_zip.ps1'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $builder -BuildId $BuildId
if ($LASTEXITCODE -ne 0) { throw 'Scarlet Windows build failed; release package not created.' }

# Build the game-code generator and pinned portable compiler ONCE on the maintainer
# machine, not on player PCs. The public ZIP includes both as with ZA Recomp.
$env:PATH = 'C:\msys64\ucrt64\bin;C:\msys64\usr\bin;' + $env:PATH
$make = Get-Command make.exe -ErrorAction SilentlyContinue
$bash = Get-Command bash.exe -ErrorAction SilentlyContinue
# Build Scarlet's standalone generator in its own Python venv. Unlike the
# upstream 'make gen-helper', this does not demand py -3.12 or install
# Link's Awakening randomizer dependencies that are irrelevant to Scarlet.
$cache = Join-Path $root 'build\scarlet-tools-cache'
$venv = Join-Path $root 'build\scarlet-gen-venv'
$pyExe = Join-Path $venv 'Scripts\python.exe'
$pythonTemp = Join-Path $cache 'python-temp'
New-Item -ItemType Directory -Force -Path $pythonTemp | Out-Null
$env:TMP = $pythonTemp
$env:TEMP = $pythonTemp
$env:TMPDIR = $pythonTemp
$env:PIP_CACHE_DIR = Join-Path $cache 'pip-cache'
$env:PYINSTALLER_CONFIG_DIR = Join-Path $cache 'pyinstaller-config'

# Python's official NuGet package is designed for CI/build systems and does
# not require a system-wide install or the Windows py launcher. Pin this build
# dependency; it remains on the maintainer's D: drive and is NOT in the ZIP.
function Install-ScarletPortablePython {
    $version = '3.13.16'
    $target = Join-Path $cache "python-nuget-$version"
    $exe = Join-Path $target 'tools\python.exe'
    if (Test-Path -LiteralPath $exe -PathType Leaf) {
        Write-Host "Reutilizando Python isolado no projeto: $exe"
        return $exe
    }
    $pkg = Join-Path $cache "python.$version.nupkg"
    $shaPath = $pkg + '.sha512'
    $url = "https://api.nuget.org/v3-flatcontainer/python/$version/python.$version.nupkg"
    Write-Host "Baixando CPython oficial para builds: $version (NuGet; sem instalacao global)..."
    $oldSecurity = [Net.ServicePointManager]::SecurityProtocol
    try {
        [Net.ServicePointManager]::SecurityProtocol = $oldSecurity -bor [Net.SecurityProtocolType]::Tls12
        if (!(Test-Path -LiteralPath $pkg -PathType Leaf)) {
            Invoke-WebRequest -Uri $url -OutFile $pkg -UseBasicParsing -ErrorAction Stop
        }
        Invoke-WebRequest -Uri ($url + '.sha512') -OutFile $shaPath -UseBasicParsing -ErrorAction Stop
    } catch {
        throw ("Falha ao obter Python NuGet pela rede: $($_.Exception.Message). " +
               "Confira sua conexao e o acesso a api.nuget.org, ou informe -PythonExe.")
    } finally {
        [Net.ServicePointManager]::SecurityProtocol = $oldSecurity
    }

    # Verify package integrity before running any downloaded executable.
    $expected = (Get-Content -LiteralPath $shaPath -Raw).Trim()
    $stream = [System.IO.File]::OpenRead($pkg)
    try {
        $sha = [System.Security.Cryptography.SHA512]::Create()
        try { $actual = [Convert]::ToBase64String($sha.ComputeHash($stream)) }
        finally { $sha.Dispose() }
    } finally { $stream.Dispose() }
    if ($expected -cne $actual) {
        throw "O SHA512 do pacote Python nao confere com o publicado no NuGet. Arquivo: $pkg"
    }
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (!(Test-Path -LiteralPath $target -PathType Container)) {
        New-Item -ItemType Directory -Force -Path $target | Out-Null
    }
    [System.IO.Compression.ZipFile]::ExtractToDirectory($pkg, $target)
    if (!(Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "NuGet Python extraido, mas tools\python.exe nao foi localizado em $target"
    }
    & $exe -c 'import sys,venv,ensurepip,ssl; assert sys.version_info[:2] == (3,13)'
    if ($LASTEXITCODE -ne 0) { throw "Python NuGet nao passou no teste de venv/ensurepip: $exe" }
    Write-Host "Python isolado pronto: $exe"
    return $exe
}

function Get-ScarletPython {
    # The previous search only handled a few default installer paths.
    # Scarlet has already used local Python virtual environments; reuse them.
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    if ($PythonExe) {
        $resolvedPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($PythonExe)
        if (!(Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
            throw "Python informado nao existe: $resolvedPath"
        }
        $candidates.Add($resolvedPath)
    } else {
        foreach ($candidate in @(
            (Join-Path $root 'tools\venv\Scripts\python.exe'),
            (Join-Path $root '.venv\Scripts\python.exe'),
            (Join-Path $root 'venv\Scripts\python.exe'),
            (Join-Path $root 'build\scarlet-python\Scripts\python.exe'),
            (Join-Path $root 'build\scarlet-tools-cache\python\python.exe')
        )) { $candidates.Add($candidate) }

        $localDirs = New-Object 'System.Collections.Generic.List[string]'
        if ($env:LOCALAPPDATA) {
            $localDirs.Add((Join-Path $env:LOCALAPPDATA 'Programs\Python'))
            $localDirs.Add((Join-Path $env:LOCALAPPDATA 'Python'))
        }
        if ($env:USERPROFILE) {
            $localDirs.Add((Join-Path $env:USERPROFILE '.pyenv\pyenv-win\versions'))
        }
        $localDirs.Add('C:\Program Files')
        $localDirs.Add('C:\')
        foreach ($base in $localDirs) {
            if (!(Test-Path -LiteralPath $base -PathType Container)) { continue }
            foreach ($dir in @(Get-ChildItem -LiteralPath $base -Directory -ErrorAction SilentlyContinue |
                               Where-Object { $_.Name -match '^(Python|pythoncore-3\.|3\.(11|12|13|14))' })) {
                $candidates.Add((Join-Path $dir.FullName 'python.exe'))
            }
        }
        # PEP 514 registry entries also cover non-default Windows installations.
        foreach ($registry in @(
            'HKCU:\Software\Python\PythonCore',
            'HKLM:\Software\Python\PythonCore',
            'HKLM:\Software\WOW6432Node\Python\PythonCore'
        )) {
            foreach ($version in @(Get-ChildItem -Path $registry -ErrorAction SilentlyContinue)) {
                try {
                    $installKey = Get-Item -LiteralPath (Join-Path $version.PSPath 'InstallPath') -ErrorAction Stop
                    $exe = $installKey.GetValue('ExecutablePath')
                    if ($exe) { $candidates.Add([string]$exe) }
                    $folder = $installKey.GetValue('')
                    if ($folder) { $candidates.Add((Join-Path ([string]$folder) 'python.exe')) }
                } catch { }
            }
        }
        # Newer Python installations may be discoverable only through py.exe.
        $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($pyLauncher) {
            foreach ($version in @('3.13','3.12','3.11','3.14')) {
                try {
                    $resolved = & $pyLauncher.Source "-$version" -c 'import sys; print(sys.executable)' 2>$null
                    if ($LASTEXITCODE -eq 0 -and $resolved) { $candidates.Add(("$resolved").Trim()) }
                } catch { }
            }
        }
        foreach ($command in @('python.exe','python3.exe','python3.13.exe','python3.12.exe','python3.11.exe')) {
            foreach ($item in @(Get-Command $command -All -ErrorAction SilentlyContinue)) {
                if ($item.Source) { $candidates.Add($item.Source) }
            }
        }
    }

    $checked = 0
    foreach ($exe in ($candidates | Select-Object -Unique)) {
        if (!(Test-Path -LiteralPath $exe -PathType Leaf)) { continue }
        if ($exe -match '[\\/]msys64[\\/]') { continue }
        $checked++
        try {
            $info = & $exe -c 'import sys,struct;print("SCARLET_PY",sys.version_info.major,sys.version_info.minor,struct.calcsize("P")*8,sys.platform)' 2>$null
            if ($LASTEXITCODE -ne 0 -or !$info) { continue }
            $fields = (("$info").Trim() -split '\s+')
            if ($fields.Count -eq 5 -and $fields[0] -eq 'SCARLET_PY' -and
                $fields[1] -eq '3' -and
                $fields[2] -in @('11','12','13','14') -and
                $fields[3] -eq '64' -and $fields[4] -eq 'win32') {
                Write-Host "Python Windows x64 encontrado: $exe ($info)"
                return $exe
            }
        } catch { }
    }
    if ($PythonExe) {
        throw "O executavel -PythonExe informado nao corresponde a CPython x64 compativel: $PythonExe"
    }
    Write-Host "Nenhum Python Windows valido encontrado nos $checked candidatos. Instalando fallback isolado..."
    return Install-ScarletPortablePython
}
Push-Location $root
try {
    if (!(Test-Path -LiteralPath $pyExe -PathType Leaf)) {
        $python = Get-ScarletPython
        & $python -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente Python do lasgen.' }
    }
    & $pyExe -m pip install --disable-pip-version-check --no-cache-dir 'pyinstaller==6.22.3' 'capstone==5.0.9' 'unicorn==2.1.4' 'lz4==4.4.5'
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias do gerador Scarlet.' }
    & $pyExe -m PyInstaller --noconfirm --clean --log-level WARN --distpath 'build/helper' --workpath 'build/scarlet-pyinstaller-work' 'tools/lasgen.spec'
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar lasgen.exe com PyInstaller.' }
    & $pyExe 'tools/pe_no_cfg.py' 'build/helper/lasgen/lasgen.exe'
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao ajustar CFG de lasgen.exe.' }
    & (Join-Path $root 'build\helper\lasgen\lasgen.exe') --help
    if ($LASTEXITCODE -ne 0) { throw 'lasgen.exe nao iniciou corretamente.' }
    Write-Host 'lasgen.exe Scarlet gerado e testado com sucesso.'
} finally {
    Pop-Location
}
if (!(Test-Path -LiteralPath (Join-Path $root 'build\zig-slim\zig.exe'))) {
    if (!$bash) { throw 'MSYS2 bash.exe required to prepare the bundled Zig compiler.' }
    Push-Location $root
    try {
        if (!(Test-Path -LiteralPath (Join-Path $root 'build\zig\zig.exe'))) {
            & $bash.Source 'tools/fetch_zig.sh'
            if ($LASTEXITCODE -ne 0) { throw 'Fetching pinned Zig compiler failed' }
        }
        & $bash.Source 'tools/zig_slim.sh' '-O1' '-march=x86-64-v3' '-fno-strict-aliasing' '-Wno-return-type' '-Wno-unused-label' '-fvisibility=hidden'
        if ($LASTEXITCODE -ne 0) { throw 'Preparing portable Zig compiler failed' }
    } finally { Pop-Location }
}
if ($CreateDraft) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $packager -BuildId $BuildId -CreateDraft
} else {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $packager -BuildId $BuildId
}
if ($LASTEXITCODE -ne 0) { throw 'Scarlet runtime ZIP packaging failed.' }
