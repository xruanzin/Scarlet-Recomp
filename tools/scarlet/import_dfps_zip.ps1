# Import the original Fl4sh Dynamic FPS ASM patch into a local Scarlet installation.
# Only the user's own verified patch is copied; it is never committed or
# bundled with Scarlet-Recomp. The existing launcher 60 FPS option auto-detects it.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $ModZip,
    [Parameter(Mandatory = $true)] [string] $RuntimeDir
)
$ErrorActionPreference = 'Stop'
$expected = '3C9038E42DDA33848D40FB1B4D850C16AE22FCC206901924E9497C31BC00A5BB'
$entryName = '[Dynamic FPS Scarlet v4.0.0][ASM] Final Release/exefs/3.0.1-4.0.0.pchtxt'
$zipPath = (Resolve-Path -LiteralPath $ModZip -ErrorAction Stop).Path
$runtime = (Resolve-Path -LiteralPath $RuntimeDir -ErrorAction Stop).Path
if (-not (Test-Path -LiteralPath (Join-Path $runtime 'scarlet.exe') -PathType Leaf)) {
    throw "RuntimeDir must contain scarlet.exe: $runtime"
}
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    $entries = @($archive.Entries | Where-Object { $_.FullName -ceq $entryName })
    if ($entries.Count -ne 1) { throw 'Expected exactly one Scarlet 4.0.0 Dynamic FPS ASM patch in the ZIP.' }
    $entry = $entries[0]
    if ($entry.Length -lt 1000 -or $entry.Length -gt 65536) {
        throw 'Unexpected Dynamic FPS ASM patch size.'
    }
    $stream = $entry.Open()
    $memory = New-Object System.IO.MemoryStream
    try { $stream.CopyTo($memory); $bytes = $memory.ToArray() }
    finally { $memory.Dispose(); $stream.Dispose() }
}
finally { $archive.Dispose() }
$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    $hash = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '')
}
finally { $sha.Dispose() }
if ($hash -cne $expected) {
    throw 'The mod does not match the reviewed Scarlet 4.0.0 ASM build. No files were changed.'
}
$dir = Join-Path $runtime 'user\mods'
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$target = Join-Path $dir 'scarlet-dfps-v4.pchtxt'
$temp = Join-Path $dir ('scarlet-dfps-' + [guid]::NewGuid().ToString('N') + '.tmp')
try {
    [System.IO.File]::WriteAllBytes($temp, $bytes)
    Move-Item -LiteralPath $temp -Destination $target -Force
}
finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Force }
}
Write-Host 'Verified Fl4sh Scarlet 4.0.0 Dynamic FPS ASM patch installed locally.' -ForegroundColor Green
Write-Host "Path: $target"
Write-Host 'Use the regular 60 FPS launcher selection. No additional mode or environment variable is required.'
Write-Host 'The next 60 FPS launch may recompile the AOT library to avoid mixing static and dynamic code.'
