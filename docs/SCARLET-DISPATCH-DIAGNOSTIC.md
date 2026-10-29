# Diagnóstico de 0x7000026ca4 e listras — 2026-10-29

Branch: `scarlet/bootstrap-4.0.0-20261029`, checkout `D:\Scarlet-Recomp`.
Base inspecionada: `d936550`. Alteração local inicial: somente `?? scarlet-boot-test/`, preservada.

## Crash: conclusão e limite da evidência

`0x7000026ca4` é uma continuação interna de `setjmp`, não uma entrada ausente de função.
A AOT contém o rótulo e a captura host em `main/main_006.c`, dentro de `f_7000026c60`.
`tools/gen.py` emite a captura e desativa promoção de registradores nessa função.
`tools/lifter.py` distingue BR, BLR e RET; não foi necessário alterar a tradução.

A função SDK `f_70085ae034` (`sdk/sdk_181.c`) restaura LR de `buf+0x58`,
SP de `buf+0x68`, registradores e despacha LR. O log `no-depth-test.stderr.log`
termina após o relatório do frame 366, com PC=LR=7000026ca4, SP=x2=723fffefb0,
x17=70085ae034 e x0=x1=1: evidência consistente com esse longjmp.

O runtime guardava apenas 32 contextos por thread. Registrar outro buffer distinto
sobrescrevia o mais antigo, mesmo que seu frame host ainda estivesse vivo. Sem esse
contexto, dispatch trata a continuação como função desconhecida e aborta.
O log não contém a tabela de contextos: a expulsão é uma causa fortemente sustentada,
mas ainda não foi confirmada numa reprodução instrumentada do jogo.

Correção em `runtime/dispatch.c`: alocações estáveis por buffer e por thread,
sem expulsão circular; destrutor pthread libera a lista ao encerrar a thread.
`jmp_buf` capturado nunca é movido. A busca continua exigindo retorno e SP iguais;
destinos desconhecidos continuam no caminho FATAL. ABI, lifter, cpu.h e AOT intactos.
Custo: memória proporcional aos buffers distintos de cada thread e busca linear;
não introduz coleta especulativa de frames, pois poderia invalidar contextos vivos.

## Testes executados no Windows / UCRT64

```powershell
cd D:\Scarlet-Recomp
python tools\test_dispatch_jmp.py
```

PASS: 256 buffers com longjmp real ao primeiro contexto; 96 níveis recursivos;
reutilização estável; rejeição de retorno/SP divergentes; isolamento entre quatro
threads; liberação de todas as alocações ao término. Modelo do registro antigo
reproduz deterministicamente a perda do contexto externo. O teste extrai o registro
real de dispatch.c, mas não executa o jogo nem o dispatch completo.

Rebuild somente do executável (executado, sucesso):

```powershell
$env:MSYSTEM = 'UCRT64'
$env:PATH = 'C:\msys64\ucrt64\bin;C:\msys64\usr\bin;' + $env:PATH
make -j2 GEN=generated-scarlet/eb6deb908752b9c6 B=build/scarlet/eb6deb908752b9c6 GENOPT=-O1 GENARCH=-march=x86-64-v3 SCARLET_AOT=1 build/scarlet/eb6deb908752b9c6/scarlet.exe
```

Dry-run verificou apenas compilação de dispatch.c e relincagem. Não usar `all`,
`gen-scarlet` ou limpeza para aplicar esta correção.
`git diff --check` passou.

Preservação: 233.286 funções (main 180.337, sdk 39.287, subsdk0 13.662).
Os 1.727 arquivos em `obj/` mantiveram nomes, tamanhos e timestamps.
SHA-256 de `lasgame.dll` antes/depois:
`3E22220B9BA42B9B1D236A4D2A1CCBFBC5C0B93E9B82181ECCF8EA50132A0A32`.
Nenhuma AOT foi regenerada; nenhum reset ou limpeza foi executado.

## Listras: investigação e próximos testes

A captura examinada mostra listras no personagem e em superfícies estáticas.
O log de EQUAL_TOL registra RTX 5060, D24_UNORM_S8_UINT e mirror XFB ativo.
Não há evidência suficiente para declarar shadow acne ou aplicar uma correção
permanente no renderizador.

- EQUAL_TOL altera somente EQUAL para LESS_OR_EQUAL e bias -8 (`vulkan/exec.c`).
- NO_DEPTH_TEST também desativa escrita de profundidade; não isola sombras.
- Não foi disponibilizada captura do teste sem profundidade, portanto seu log
  não confirma se as listras mudaram.

Testar uma linha por execução, reiniciando o jogo, na mesma cena e câmera:

| Caso | Variáveis |
| --- | --- |
| Baseline | todas as opções de diagnóstico abaixo ausentes |
| Comparação de sombras | `LARECOMP_NO_SHADOW=1` |
| Mirror de transform feedback | `LARECOMP_VK_XFB_MIRROR=0` |
| Conversão half exata | `LARECOMP_VK_EXACT_H2F=1` e `LARECOMP_NO_TRANSLATE_CACHE=1` |

NO_SHADOW força ALWAYS somente em samplers de comparação (`textures.c`);
não cobre comparação manual no shader. EXACT_H2F muda GLSL, mas não participa da
chave de cache de tradução (`maxwell/translate.c`): sem NO_TRANSLATE_CACHE o teste
pode reutilizar código antigo. Não apagar o cache; a variável evita essa reutilização.

Exemplo de execução manual, depois de limpar variáveis dos casos anteriores:

```powershell
$dir = 'D:\Scarlet-Recomp\build\scarlet\eb6deb908752b9c6'
$test = 'D:\Scarlet-Recomp\scarlet-boot-test'
$env:LARECOMP_GAME_LIB = "$dir\lasgame.dll"
$env:LARECOMP_NO_LAUNCHER = '1'
$env:LARECOMP_DATA_ROOT = "$test\userdata"
$env:SCARLET_EARLY_TLS_PROBE = '1'
$env:SCARLET_BOOTSTRAP_ALLOCATOR = '1'
# Exemplo: caso sombras. Para baseline, omitir esta linha.
$env:LARECOMP_NO_SHADOW = '1'
$log = "$test\diag-shadow-$(Get-Date -Format yyyyMMdd-HHmmss).stderr.log"
Start-Process "$dir\scarlet.exe" -ArgumentList "--play `"$test`"" -WorkingDirectory $dir -RedirectStandardError $log -Wait
Remove-Item Env:LARECOMP_NO_SHADOW -ErrorAction SilentlyContinue
```

Antes de cada caso remover EQUAL_TOL, NO_DEPTH_TEST, NO_SHADOW, VK_XFB_MIRROR,
VK_EXACT_H2F e NO_TRANSLATE_CACHE, além de SCARLET_MAIN_INIT_FIRST, quando presentes.
Usar os prefixos completos `LARECOMP_` indicados na tabela/código.
Esse teste interativo usa os dados habituais do jogo; não foi iniciado automaticamente.
F10 captura a cena; F9 coleta passes para localizar a primeira corrupção caso nenhum
A/B mude as listras. Depois investigar GMEM_FAST/sincronização isoladamente.

Pendente: repetir a situação do crash e uma sessão longa com o novo executável;
comparar imagens dos quatro casos. Compilação e regressão passaram no Windows,
mas não houve nova execução visual do jogo nesta investigação. Não afirmar que o
crash observado ou as listras foram eliminados até essa validação.
