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
$zip = Join-Path $out 'Scarlet-Recomp-v1.0.0-Windows-x64-runtime.zip'
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
$archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
try {
  $entries = @($archive.Entries | Where-Object { $_.Name } | ForEach-Object { $_.FullName.Replace('\','/') })
  if (@($entries | Where-Object { $_ -match $deny }).Count -gt 0) { throw 'ZIP safety audit failed.' }
  foreach ($name in @('Scarlet-Recomp/scarlet.exe','Scarlet-Recomp/ScarletLauncher.exe',
                      'Scarlet-Recomp/scarletimport/scarletimport.exe','Scarlet-Recomp/LEIA-ME.md')) {
    if ($entries -notcontains $name) { throw "ZIP is missing: $name" }
  }
} finally { $archive.Dispose() }
$sha = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
$shaFile = $zip + '.sha256'
Set-Content -LiteralPath $shaFile -Encoding ASCII -Value "$sha  $(Split-Path -Leaf $zip)"
Write-Host "Created $zip"
Write-Host "SHA256 $sha"
Write-Warning 'Runtime only. lasgame.dll is game-derived and excluded. This ZIP alone cannot run the game; players need to produce their own game-derived AOT library from their own game.'
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
