# Collect the title-screen's own GPU-loaded textures for identifying the
# circular Nintendo A symbol. This does not patch icons, controls, RomFS or
# save files. Run Scarlet to the title screen only, then close the window.
# Windows PowerShell 5.1, no extra dependencies.
param(
    [string] $Source = 'D:\Scarlet-Window-Playtest-20261112',
    [int] $MaxTextures = 1200
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $repo
$exe = Join-Path $repo 'build\window-full-20261112\scarlet.exe'
$dll = Join-Path $repo 'build\window-full-20261112\lasgame.dll'
$game = Join-Path $Source 'scarlet-games\active'
if (Get-Process scarlet -ErrorAction SilentlyContinue) {
    throw 'Feche todas as instancias do Scarlet antes de iniciar a coleta.'
}
foreach ($p in @($exe,$dll,(Join-Path $game 'exefs\main'))) {
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "Arquivo necessario ausente: $p" }
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$report = Join-Path $repo ("build\scarlet-title-icon-survey-" + $stamp)
$dump = Join-Path $repo 'textures\dump'
$history = Join-Path $repo ("textures\dump-preserved-" + $stamp)
New-Item -ItemType Directory -Path $report -Force | Out-Null
$old = Test-Path -LiteralPath $dump -PathType Container
if ($old) { Move-Item -LiteralPath $dump -Destination $history -ErrorAction Stop }
New-Item -ItemType Directory -Path $dump -Force | Out-Null
$envBackup = @{}
$envNames = @('LARECOMP_TEX_DUMP','LARECOMP_DATA_ROOT','LARECOMP_GAME_LIB','SCARLET_TARGET_FPS','SCARLET_INDOOR_CAMERA_60','SCARLET_NORMALIZE_LSTICK','LARECOMP_GPU_OVERLAP')
foreach ($n in $envNames) { $envBackup[$n] = [Environment]::GetEnvironmentVariable($n, 'Process') }
$env:LARECOMP_TEX_DUMP = '1'
$env:LARECOMP_DATA_ROOT = $Source
$env:LARECOMP_GAME_LIB = $dll
$env:SCARLET_TARGET_FPS = '60'
$env:SCARLET_INDOOR_CAMERA_60 = '1'
$env:SCARLET_NORMALIZE_LSTICK = '1'
$env:LARECOMP_GPU_OVERLAP = '0'
try {
    Write-Host 'Abrindo Scarlet com captura de texturas (somente esta sessao).' -ForegroundColor Cyan
    Write-Host 'Fique na tela "PRESSIONE A PARA COMEÇAR" e feche a janela sem entrar no save.' -ForegroundColor Yellow
    & $exe --play $game
}
finally {
    foreach ($n in $envNames) { [Environment]::SetEnvironmentVariable($n, $envBackup[$n], 'Process') }
    $captured = Join-Path $report 'original-textures'
    if (Test-Path -LiteralPath $dump -PathType Container) {
        Move-Item -LiteralPath $dump -Destination $captured -ErrorAction Stop
    }
    if ($old -and (Test-Path -LiteralPath $history -PathType Container)) {
        Move-Item -LiteralPath $history -Destination $dump -ErrorAction Stop
    }
}
if (-not (Test-Path -LiteralPath $captured -PathType Container)) {
    throw 'A captura nao encontrou a pasta de texturas.'
}
$pics = @(Get-ChildItem -LiteralPath $captured -Filter '*.png' -File | Sort-Object Length -Descending)
if ($pics.Count -eq 0) {
    throw 'Nenhuma textura foi capturada. Confirme que o jogo chegou ate a tela de titulo.'
}
if ($MaxTextures -lt 1) { $MaxTextures = 1200 }
$picks = @($pics | Select-Object -First $MaxTextures)
Write-Host ("Texturas capturadas: {0} (relatorio de {1})" -f $pics.Count, $picks.Count) -ForegroundColor Cyan
Add-Type -AssemblyName System.Drawing
$rows = New-Object System.Collections.Generic.List[object]
$columns = 7
$perPage = 49
$cellW, $cellH = 206, 170
$pages = [int][Math]::Ceiling($picks.Count / [double]$perPage)
$font = New-Object System.Drawing.Font('Consolas', 10)
try {
    for ($page = 0; $page -lt $pages; $page++) {
        $sheet = New-Object System.Drawing.Bitmap ($columns * $cellW), (7 * $cellH)
        $g = [System.Drawing.Graphics]::FromImage($sheet)
        $g.Clear([System.Drawing.Color]::FromArgb(18,21,29))
        try {
            for ($index = $page*$perPage; $index -lt [Math]::Min(($page+1)*$perPage, $picks.Count); $index++) {
                $p = $picks[$index]
                $local = $index % $perPage
                $col = $local % $columns
                $line = [int][Math]::Floor($local / $columns)
                $xx = $col * $cellW
                $yy = $line * $cellH
                $img = $null
                try {
                    $img = [System.Drawing.Image]::FromFile($p.FullName)
                    $ratio = [Math]::Min(182.0/$img.Width, 130.0/$img.Height)
                    $ww = [float]($img.Width * $ratio)
                    $hh = [float]($img.Height * $ratio)
                    $rx = [float]($xx + ($cellW-$ww)/2)
                    $ry = [float]($yy + 4 + (132-$hh)/2)
                    $g.DrawImage($img, $rx, $ry, $ww, $hh)
                    $dim = "{0}x{1}" -f $img.Width,$img.Height
                    $rows.Add([pscustomobject]@{ hash=$p.BaseName; width=$img.Width; height=$img.Height; bytes=$p.Length; page=$page+1 })
                    $g.DrawString($p.BaseName, $font, [System.Drawing.Brushes]::White, [float]($xx+5), [float]($yy+137))
                    $g.DrawString($dim, $font, [System.Drawing.Brushes]::LightGray, [float]($xx+5), [float]($yy+153))
                } catch {
                    Write-Warning ("Falha ao ler: " + $p.Name + " -- " + $_.Exception.Message)
                } finally { if ($img) { $img.Dispose() } }
            }
            $out = Join-Path $report ("contato-{0:d3}.jpg" -f ($page+1))
            $sheet.Save($out, [System.Drawing.Imaging.ImageFormat]::Jpeg)
            Write-Host ("Preview: " + $out)
        }
        finally { $g.Dispose(); $sheet.Dispose() }
    }
}
finally { $font.Dispose() }
$rows | Export-Csv -LiteralPath (Join-Path $report 'texturas.csv') -NoTypeInformation -Encoding UTF8
$zip = $report + '-PREVIEWS.zip'
$contents = @(Get-ChildItem -LiteralPath $report -File | Where-Object { $_.Extension -in '.jpg','.csv' })
if ($contents.Count -gt 0) {
    Compress-Archive -LiteralPath $contents.FullName -DestinationPath $zip -Force
}
Write-Host ''
Write-Host 'COLETA CONCLUIDA: nenhum recurso do jogo foi alterado.' -ForegroundColor Green
Write-Host ("Previews/indice para enviar no chat: " + $zip) -ForegroundColor Yellow
Write-Host ("PNG originais preservados apenas localmente em: " + $captured)
Write-Host 'Envie tambem uma captura da tela do jogo mostrando o A original.'
