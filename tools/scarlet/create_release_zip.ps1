# Scarlet-Recomp v1.0.0: public runtime-only ZIP (no proprietary game code).
# Requires a prebuilt Windows developer output. Does not alter the game/AOT.
[CmdletBinding()]
param(
  [string]$BuildId = 'eb6deb908752b9c6',
  [switch]$CreateDraft
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$bin = Join-Path $root "build\scarlet\$BuildId"
$out = Join-Path $root 'build\dist'
$stageRoot = Join-Path $root 'build\scarlet-release-staging'
$stage = Join-Path $stageRoot 'Scarlet-Recomp'
$zip = Join-Path $out 'Scarlet-Recomp-windows.zip'
if (!(Test-Path -LiteralPath $bin -PathType Container)) { throw "No local Windows build: $bin" }
function CopySafe([string]$source, [string]$target) {
  if (!(Test-Path -LiteralPath $source -PathType Leaf)) { throw "Required file missing: $source" }
  $destination = Join-Path $stage $target
  $destdir = Split-Path -Parent $destination
  New-Item -ItemType Directory -Path $destdir -Force | Out-Null
  Copy-Item -LiteralPath $source -Destination $destination -ErrorAction Stop
}
New-Item -ItemType Directory -Path $out -Force | Out-Null
if (Test-Path -LiteralPath $stageRoot) { Remove-Item -LiteralPath $stageRoot -Recurse -Force }
New-Item -ItemType Directory -Path $stage -Force | Out-Null

function CopyBundleDirectory([string]$source, [string]$targetName, [string]$requiredExe) {
  if (!(Test-Path -LiteralPath $source -PathType Container)) {
    throw "Bundled AOT prerequisite missing: $source. Build the local generator/compiler first."
  }
  if (!(Test-Path -LiteralPath (Join-Path $source $requiredExe) -PathType Leaf)) {
    throw "Bundled AOT prerequisite executable missing: $(Join-Path $source $requiredExe)"
  }
  $target = Join-Path $stage $targetName
  New-Item -ItemType Directory -Path $target -Force | Out-Null
  Copy-Item -Path (Join-Path $source '*') -Destination $target -Recurse -Force
}
# ZA Recomp's release model: the generator + compiler ship with the runtime,
# and compile the player's OWN game code at first startup.
CopyBundleDirectory (Join-Path $root 'build\helper\lasgen') 'lasgen' 'lasgen.exe'
CopyBundleDirectory (Join-Path $root 'build\zig-slim') 'zig' 'zig.exe'
foreach ($required in @('rt\link.rsp', 'rt-v2\link.rsp')) {
  if (!(Test-Path -LiteralPath (Join-Path $stage ('zig\' + $required)) -PathType Leaf)) {
    throw "Slim Zig toolchain missing required link recipe: $required"
  }
}
foreach ($file in @('runtime\cpu.h','runtime\simd.h','runtime\simd_fp.h',
                   'runtime\gamelib.h','tools\gamelib_entry.c','runtime\hle\hle_symbols.txt')) {
  CopySafe (Join-Path $root $file) ('gamelib-src\' + (Split-Path -Leaf $file))
}
CopySafe (Join-Path $bin 'lasrecomp.dll.a') 'lasrecomp.dll.a'

foreach ($file in @('scarlet.exe','ScarletLauncher.exe','assets\scarlet_launcher_background.jpg')) {
  CopySafe (Join-Path $bin $file) $file
}
# Copy self-contained .NET importer files, but no generated game data.
$importer = Join-Path $bin 'scarletimport'
if (!(Test-Path (Join-Path $importer 'scarletimport.exe'))) {
  throw 'Missing self-contained scarletimport.exe; rebuild without -SkipImporter'
}
Get-ChildItem -LiteralPath $importer -File | Where-Object {
  $_.Extension -in @('.exe','.dll','.json','.dat')
} | ForEach-Object {
  CopySafe $_.FullName ('scarletimport\' + $_.Name)
}
# Explicit allowlist; NEVER copy every DLL from the runtime build folder.
foreach ($dll in @('libstdc++-6.dll','libgcc_s_seh-1.dll',
                   'libwinpthread-1.dll','SDL3.dll','avutil-61.dll',
                   'avcodec-63.dll','avformat-63.dll')) {
  CopySafe (Join-Path $bin $dll) $dll
}
foreach ($dll in @('libiconv-2.dll','swscale-10.dll','libshaderc_shared.dll')) {
  $src = Join-Path $bin $dll
  if (Test-Path -LiteralPath $src -PathType Leaf) { CopySafe $src $dll }
}

# Copy the COMPLETE PE dependency closure, not only the fixed fallback list.
# The developer's scarlet.exe may work because C:\msys64\ucrt64\bin is on PATH,
# while an extracted public ZIP fails in the Windows loader before main() runs.
# Scan the developer's lasgame.dll for dependencies too, but NEVER ship that DLL.
$peReader = $null
foreach ($candidate in @('C:\msys64\ucrt64\bin\objdump.exe',
                         'C:\msys64\usr\bin\objdump.exe')) {
  if (Test-Path -LiteralPath $candidate -PathType Leaf) { $peReader = $candidate; break }
}
if (!$peReader) {
  $command = Get-Command objdump.exe -ErrorAction SilentlyContinue
  if ($command) { $peReader = $command.Source }
}
if (!$peReader) {
  throw 'Cannot audit the portable ZIP: objdump.exe is missing. Install MSYS2 binutils and retry.'
}

$pendingPE = New-Object 'System.Collections.Generic.Queue[string]'
foreach ($file in @('scarlet.exe','ScarletLauncher.exe')) {
  $pendingPE.Enqueue((Join-Path $stage $file))
}
$localAot = Join-Path $bin 'lasgame.dll'
if (Test-Path -LiteralPath $localAot -PathType Leaf) {
  $pendingPE.Enqueue($localAot) # inspect imports only; never include game-derived DLL
}
$seenPE = @{}
$resolvedDLLs = @{}
while ($pendingPE.Count -gt 0) {
  $pe = $pendingPE.Dequeue()
  if ($seenPE.ContainsKey($pe)) { continue }
  $seenPE[$pe] = $true
  $report = @(& $peReader -p $pe 2>$null)
  if ($LASTEXITCODE -ne 0) { throw "Cannot inspect PE imports of $pe" }
  foreach ($line in $report) {
    if ($line -notmatch '^\s*DLL Name:\s*([^\s]+)') { continue }
    $dll = $Matches[1]
    if ($dll -match '[\\/]') { throw "Unexpected DLL name in $pe : $dll" }
    if ($resolvedDLLs.ContainsKey($dll)) { continue }
    $resolvedDLLs[$dll] = $true

    $inStage = Join-Path $stage $dll
    if (!(Test-Path -LiteralPath $inStage -PathType Leaf)) {
      # Prefer the already-vetted runtime copied by build_next_version.ps1.
      $fromBuild = Join-Path $bin $dll
      $fromMsys = Join-Path 'C:\msys64\ucrt64\bin' $dll
      if (Test-Path -LiteralPath $fromBuild -PathType Leaf) {
        CopySafe $fromBuild $dll
      } elseif (Test-Path -LiteralPath $fromMsys -PathType Leaf) {
        CopySafe $fromMsys $dll
      }
    }
    if (Test-Path -LiteralPath $inStage -PathType Leaf) {
      $pendingPE.Enqueue($inStage)
      continue
    }

    # Windows DLLs are supplied by the OS. The Vulkan loader comes with the
    # installed GPU driver, and VC runtimes are documented as prerequisites.
    $system = Join-Path $env:SystemRoot "System32\$dll"
    $external = $dll -match '^(?i:api-ms-win-|ext-ms-win-|vulkan-1\.dll$|vcruntime\d+(_\d+)?\.dll$|msvcp\d+(_\d+)?\.dll$)'
    if (!(Test-Path -LiteralPath $system -PathType Leaf) -and !$external) {
      throw "Portable ZIP missing dependent DLL '$dll' (imported by $pe). Check the UCRT64 toolchain and rebuild."
    }
  }
}
Write-Host "Portable ZIP dependency audit completed: $($resolvedDLLs.Count) DLL names resolved."
foreach ($copy in @(
  @('LICENSE','LICENSE'),
  @('README.md','README.md'),
  @('README.pt-BR.md','README.pt-BR.md'),
  @('README.pt-BR.md','LEIA-ME.md'),
  @('docs\RELEASE-v1.0.0.md','docs\RELEASE-v1.0.0.md'),
  @('docs\RELEASE-DEPENDENCIES-v1.0.0.md','docs\RELEASE-DEPENDENCIES-v1.0.0.md'),
  @('docs\RELEASE-DEPENDENCIES-v1.0.0.md','REQUISITOS-E-CREDITOS.md'),
  @('docs\RELEASE-CHECKLIST-v1.0.0.md','docs\RELEASE-CHECKLIST-v1.0.0.md'),
  @('docs\SCARLET-BOOTSTRAP.md','docs\SCARLET-BOOTSTRAP.md'),
  @('docs\SCARLET-ORIGINAL-LAUNCHER.md','docs\SCARLET-ORIGINAL-LAUNCHER.md')
)) {
  CopySafe (Join-Path $root $copy[0]) $copy[1]
}
# Protect users and developers from publishing compiled game code or their keys.
$deny = '(?i)(^|[\\/])(lasgame\.dll(\.id)?|prod\.keys|title\.keys|[^\\/]*\.(nsp|xci|nca|tik)|romfs(\.bin)?|exefs|scarlet-games|save|saves|logs|user|extracted|generated-scarlet)([\\/]|$)'
$bad = @(Get-ChildItem -LiteralPath $stage -Recurse -File | Where-Object { $_.FullName -match $deny })
if ($bad.Count -gt 0) { throw ('Forbidden game/private files found: ' + ($bad.FullName -join ', ')) }
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -LiteralPath $stage -DestinationPath $zip -CompressionLevel Optimal
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
try {
  $entries = @($archive.Entries | Where-Object { $_.Name } | ForEach-Object { $_.FullName.Replace('\','/') })
  if (@($entries | Where-Object { $_ -match $deny }).Count -gt 0) { throw 'ZIP safety audit failed.' }
  foreach ($name in @('Scarlet-Recomp/scarlet.exe','Scarlet-Recomp/ScarletLauncher.exe',
                      'Scarlet-Recomp/scarletimport/scarletimport.exe','Scarlet-Recomp/LEIA-ME.md',
                      'Scarlet-Recomp/zig/zig.exe','Scarlet-Recomp/lasgen/lasgen.exe',
                      'Scarlet-Recomp/lasrecomp.dll.a','Scarlet-Recomp/gamelib-src/gamelib_entry.c')) {
    if ($entries -notcontains $name) { throw "ZIP is missing: $name" }
  }
} finally { $archive.Dispose() }
$sha = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
$shaFile = $zip + '.sha256'
Set-Content -LiteralPath $shaFile -Encoding ASCII -Value "$sha  $(Split-Path -Leaf $zip)"
Write-Host "Created $zip"
Write-Host "SHA256 $sha"
Write-Host 'Portable setup tools bundled: Zig compiler, lasgen AOT generator, SDK header inputs, Scarlet importer.'
Write-Warning 'lasgame.dll is game-derived and excluded. At first start the launcher prepares the game and compiles the AOT library from each player own files.'
Write-Warning 'Review the licenses of the wallpaper and redistributable DLLs before publishing.'
if ($CreateDraft) {
  $gh = Get-Command gh.exe -ErrorAction SilentlyContinue
  if (!$gh) { throw 'GitHub CLI not installed on maintainer PC.' }
  $arguments = @('release','create','v1.0.0',$zip,$shaFile,
    '--repo','xruanzin/Scarlet-Recomp',
    '--target','release/v1.0.0-preparation-20261101',
    '--title','Scarlet-Recomp v1.0.0',
    '--notes-file',(Join-Path $root 'docs\RELEASE-v1.0.0.md'),'--draft')
  & $gh.Source @arguments
  if ($LASTEXITCODE -ne 0) { throw 'Could not create GitHub draft release.' }
  Write-Host 'Draft created, NOT published.'
}
