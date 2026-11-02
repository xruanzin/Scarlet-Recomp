# Scarlet 4.0.0 — diagnóstico das faixas horizontais no céu

## Estado e evidência

Base: `scarlet/bootstrap-4.0.0-20261029`, commit `45559dd`
(`Fix Scarlet Vulkan feedback views and graphics validation`).

A sessão `20261030-044530-438` iniciou normalmente, carregou a `lasgame.dll`
(180337 funções main e 39287 sdk), apresentou geometria e cenário e ficou a
30 FPS após o carregamento. O log termina em `window closed`, sem falha fatal
nem `DEVICE_LOST`. As capturas enviadas mostram terreno e objetos sem as antigas
listras pretas, mas **ainda há bandas horizontais nas nuvens e no horizonte**.

Essas imagens **não comprovam** que o defeito restante seja um cubemap, shader,
mip incorreto ou reutilização de feedback; não substituir heurísticas por
mudanças de cor ou filtros no caminho padrão.

## Instrumentação passiva

`SCARLET_SKY_AUDIT=1` escreve `[skyaudit]` para, no máximo, **512 bindings
distintos** de texturas de fragment shaders, a partir do frame 600. Não troca
shaders, views, samplers, estados ou comandos Vulkan; executa somente logs
descritivos de tipo solicitado, formato NVN/Vulkan, dimensão, níveis, camadas,
view efetiva, faixa da view e sampler (filtros, wrap, bias, LOD).

`SCARLET_SKY_FROM_FRAME` altera o primeiro frame coletado. Os dados são
amostrados em momento de preparação do descriptor, não inferem o valor de
pixels ou qual shader desenhou a faixa; a atribuição exige correlação com
capturas isoladas/fragment shader.

## Teste no Windows 11

Todos os comandos abaixo partem de `D:\Scarlet-Recomp`. Compile somente o
runtime; **não rode** `make gen-scarlet`, `make clean` ou regenere a AOT:

```powershell
$env:PATH = "C:\msys64\ucrt64\bin;C:\msys64\usr\bin;" + $env:PATH
$env:MSYSTEM = "UCRT64"
make -j2 SCARLET_AOT=1 GEN=generated-scarlet/eb6deb908752b9c6 B=build/scarlet/eb6deb908752b9c6 build/scarlet/eb6deb908752b9c6/scarlet.exe
```

Verifique que `lasgame.dll` e o executável ainda são compatíveis antes de
executar. A execução usa cópias isoladas de `save`, `cache` e
`larecomp.ini`; nenhum original é substituído.

```powershell
# Controle: sem mudar amostragem, apenas observar bindings.
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -SkyAudit

# A/B 1: LOD mínimo 1 (isola artefatos de mip 0, também afeta outras texturas).
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -SkyAudit -SkyMode lod1

# A/B 2 (somente se necessário): desabilita memo de views no mesmo frame.
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -SkyAudit -SkyMode no-tex-memo

# A/B 3 (somente se necessário): desabilita a reutilização de feedback.
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -SkyAudit -SkyMode fresh-feedback
```

Faça capturas da **mesma posição de câmera e horário no jogo** para comparar;
a alteração de LOD não é uma correção permanente. Para extrair os registros:

```powershell
$run = Get-ChildItem .\build\scarlet-graphics-runs -Directory | Sort-Object Name -Descending | Select-Object -First 1
Select-String -LiteralPath (Join-Path $run.FullName 'stderr.log') -Pattern '\[skyaudit\]|\[tex\] type mismatch|\[vk\] view failed|FATAL|DEVICE_LOST' |
    Select-Object -First 600
```

Se uma execução não alcançar frame 600, rode `-SkyFromFrame 50`.
Na análise, distinguir as linhas `[skyaudit]` do descriptor efetivamente
utilizado do shader responsável pela faixa: a primeira sozinha não prova a
segunda. Se nenhum A/B mudar o céu, investigar produtor do pass e tradutor
Maxwell/GLSL com capturas direcionadas, não aplicar um workaround global.

## Limitações

Nenhum teste visual/compilação do novo código foi executado no computador do
usuário por esta alteração no GitHub; branch de diagnóstico até validação.
O teste visual já concluído continua sendo o da correção de feedback,
não a eliminação destas faixas.
