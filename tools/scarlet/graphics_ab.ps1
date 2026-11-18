# Scarlet graphics A/B launcher. Does not rebuild game AOT or alter saves.
[CmdletBinding()]
param(
    [ValidateSet("baseline","mip2","half-exact","vertex-copy","vertex-audit")]
    [string]$Mode = "baseline",
    [string]$CacheId = "eb6deb908752b9c6",
    [string]$Repo = "D:\Scarlet-Recomp"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$dir = Join-Path $Repo ("build\scarlet\" + $CacheId)
$test = Join-Path $Repo "scarlet-boot-test"
$exe = Join-Path $dir "scarlet.exe"
$lib = Join-Path $dir "lasgame.dll"
if (!(Test-Path -LiteralPath $exe -PathType Leaf) -or !(Test-Path -LiteralPath $lib -PathType Leaf)) {
    throw "Native executable or existing AOT DLL missing. This script does not regenerate it."
}
if (!(Test-Path -LiteralPath (Join-Path $test "romfs") -PathType Container)) {
    throw "Test RomFS mount missing; set up merged Scarlet resources first."
}
if (Get-Process -Name "scarlet" -ErrorAction SilentlyContinue) {
    throw "Close the existing Scarlet window before starting an A/B case."
}
$env:MSYSTEM = "UCRT64"
$env:PATH = "C:\msys64\ucrt64\bin;C:\msys64\usr\bin;" + $env:PATH
$env:LARECOMP_GAME_LIB = $lib
$env:LARECOMP_NO_LAUNCHER = "1"
$env:LARECOMP_DATA_ROOT = Join-Path $test "userdata"
$env:SCARLET_EARLY_TLS_PROBE = "1"
$env:SCARLET_BOOTSTRAP_ALLOCATOR = "1"
@(
    "LARECOMP_VK_EQUAL_TOL",
    "LARECOMP_NO_DEPTH_TEST",
    "LARECOMP_NO_SHADOW",
    "LARECOMP_VK_XFB_MIRROR",
    "LARECOMP_VK_EXACT_H2F",
    "LARECOMP_NO_TRANSLATE_CACHE",
    "LARECOMP_VK_COPY_VERTICES",
    "LARECOMP_LOD_MIN",
    "LARECOMP_VK_VERTEX_AUDIT",
    "SCARLET_MAIN_INIT_FIRST"
) | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
switch ($Mode) {
    "mip2"         { $env:LARECOMP_LOD_MIN = "2" }
    "half-exact"   { $env:LARECOMP_VK_EXACT_H2F = "1" }
    "vertex-copy"  { $env:LARECOMP_VK_COPY_VERTICES = "1" }
    "vertex-audit" { $env:LARECOMP_VK_VERTEX_AUDIT = "1" }
}
$log = Join-Path $test ("scarlet-graphics-" + $Mode + "-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".stderr.log")
Write-Host ("Case: " + $Mode + " | log: " + $log)
Write-Host "Compare the SAME scene and camera (1x resolution, same F1 settings). Close game normally."
$quoted = '"' + $test + '"'
$p = Start-Process -FilePath $exe -ArgumentList @("--play", $quoted) -WorkingDirectory $dir -RedirectStandardError $log -PassThru -Wait
Write-Host ("Process exited: " + $p.ExitCode)
Get-Content -LiteralPath $log -Tail 35
if ($Mode -eq "vertex-audit") {
    Write-Host "--- Vertex layout warnings (first 25) ---"
    Select-String -LiteralPath $log -Pattern '\[vtxaudit\]' | Select-Object -First 25 | ForEach-Object { $_.Line }
}
Write-Host ("Log saved: " + $log)
