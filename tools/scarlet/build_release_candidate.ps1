# Single command for the maintainer to build and package the public runtime.
# NOT a complete player installer: the user's locally generated lasgame.dll
# exists only for build/test and is explicitly excluded from the public archive.
[CmdletBinding()]
param(
    [string]$BuildId = 'eb6deb908752b9c6',
    [switch]$CreateDraft
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

function Get-ScarletPython {
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    foreach ($ver in @('313','312','311','314')) {
        foreach ($base in @(
            (Join-Path $env:LOCALAPPDATA 'Programs\Python'),
            (Join-Path $env:LOCALAPPDATA 'Python'),
            'C:\Python'
        )) {
            if ($base -eq 'C:\Python') {
                $candidates.Add("C:\Python$ver\python.exe")
            } else {
                $candidates.Add((Join-Path $base "Python$ver\python.exe"))
            }
        }
    }
    # The Python launcher can resolve installations outside the usual path.
    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        foreach ($version in @('3.13','3.12','3.11','3.14')) {
            try {
                $resolved = & $pyLauncher.Source "-$version" -c 'import sys; print(sys.executable)' 2>$null
                if ($LASTEXITCODE -eq 0 -and $resolved) { $candidates.Add(("$resolved").Trim()) }
            } catch { }
        }
    }
    foreach ($command in @('python.exe','python3.exe')) {
        foreach ($item in @(Get-Command $command -All -ErrorAction SilentlyContinue)) {
            if ($item.Source) { $candidates.Add($item.Source) }
        }
    }
    foreach ($exe in ($candidates | Select-Object -Unique)) {
        if (!(Test-Path -LiteralPath $exe -PathType Leaf)) { continue }
        if ($exe -match '[\/]msys64[\/]') { continue }
        try {
            $info = & $exe -c 'import sys,struct; print(sys.version_info.major,sys.version_info.minor,struct.calcsize("P")*8,sys.platform)' 2>$null
            if ($LASTEXITCODE -ne 0 -or !$info) { continue }
        } catch { continue }
        $fields = ("$info").Trim().Split(' ')
        if ($fields.Count -eq 4 -and $fields[0] -eq '3' -and
            $fields[1] -in @('11','12','13','14') -and
            $fields[2] -eq '64' -and $fields[3] -eq 'win32') {
            Write-Host "Python detectado: $exe ($info)"
            return $exe
        }
    }
    throw ('CPython x64 3.11/3.12/3.13 nao encontrado. Instale Python de ' +
           'https://www.python.org/downloads/windows/ e tente novamente. ' +
           'So quem produz o ZIP precisa de Python; jogadores nao.')
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
