# Portable Windows loader smoke test for Scarlet-Recomp release archives.
# Does NOT import games, build AOT, or touch the developer's lasgame.dll.
[CmdletBinding()]
param(
    [string]$ZipPath = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if (!$ZipPath) { $ZipPath = Join-Path $root 'build\dist\Scarlet-Recomp-windows.zip' }
$ZipPath = (Resolve-Path -LiteralPath $ZipPath -ErrorAction Stop).Path
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$testDir = Join-Path $root "build\scarlet-portable-smoke\$stamp"
New-Item -ItemType Directory -Path $testDir -Force | Out-Null
Expand-Archive -LiteralPath $ZipPath -DestinationPath $testDir -ErrorAction Stop
$bundle = Join-Path $testDir 'Scarlet-Recomp'
$exe = Join-Path $bundle 'scarlet.exe'
if (!(Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw "ZIP is missing Scarlet-Recomp/scarlet.exe: $ZipPath"
}

# Use nonexistent game content deliberately: --prepare-aot MUST reach main,
# recognize the bundled tools, then reject the empty ExeFS with exit code 4.
# No NSP, XCI, keys, saves or game-derived DLLs are used.
$emptyGame = Join-Path $testDir 'empty-game-input'
$data = Join-Path $testDir 'test-data'
New-Item -ItemType Directory -Path $emptyGame, $data -Force | Out-Null
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $exe
$psi.Arguments = '--prepare-aot "' + $emptyGame + '"'
$psi.WorkingDirectory = $bundle
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true
$psi.EnvironmentVariables['LARECOMP_DATA_ROOT'] = $data
# Do not let C:\msys64\* or developer tools on PATH conceal a missing ZIP DLL.
$psi.EnvironmentVariables['PATH'] = "$env:SystemRoot\System32;$env:SystemRoot;$env:SystemRoot\System32\Wbem"
$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi
try {
    if (!$process.Start()) { throw 'Windows could not start the packaged scarlet.exe.' }
    $outTask = $process.StandardOutput.ReadToEndAsync()
    $errTask = $process.StandardError.ReadToEndAsync()
    if (!$process.WaitForExit(60000)) {
        $process.Kill()
        throw 'Packaged scarlet.exe did not complete the no-game loader smoke test.'
    }
    $stdoutText = $outTask.Result
    $stderrText = $errTask.Result
    $exitCode = $process.ExitCode
} finally {
    $process.Dispose()
}
$stdoutPath = Join-Path $testDir 'stdout.txt'
$stderrPath = Join-Path $testDir 'stderr.txt'
[System.IO.File]::WriteAllText($stdoutPath, $stdoutText)
[System.IO.File]::WriteAllText($stderrPath, $stderrText)
Write-Host "Portable smoke-test directory: $testDir"
Write-Host "Exit code: $exitCode"
Write-Host "Captured stderr: $stderrPath"
if ($stderrText -notmatch '\[scarlet-aot\] entered main') {
    throw 'Portable executable did not reach main(). Check stderr.txt and packaged DLLs (Windows loader failure suspected).'
}
if ($stderrText -match 'bundled lasgen/zig/gamelib-src are missing') {
    throw 'Packaged AOT tools are missing, even though the executable starts.'
}
if ($exitCode -ne 4) {
    throw "Unexpected smoke-test exit code $exitCode. Expected 4 (no game files); read stderr.txt."
}
Write-Host 'PASS: standalone ZIP reaches the native AOT entry point and detects bundled tools.'
Write-Host 'Expected: no game data was provided. This is NOT a full first-run AOT build test.'
