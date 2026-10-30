# Scarlet 4.0.0: correção das listras no feedback depth/stencil

## Estado preservado

Investigação iniciada em `scarlet/bootstrap-4.0.0-20261029`, commit `19f84d6`.
Não havia modificações rastreadas; `scarlet-boot-test/` era não rastreado.
Nenhum reset, checkout, geração de AOT ou link de `lasgame.dll` foi executado.
SHA-256 da DLL antes e depois:
`3E22220B9BA42B9B1D236A4D2A1CCBFBC5C0B93E9B82181ECCF8EA50132A0A32`.

## Causa e correção

`resolve_feedback()` deduplicava a cópia por `NvnTexture*` e também guardava
uma única `VkImageView` por textura. Para uma imagem depth/stencil escolhia
incondicionalmente `VK_IMAGE_ASPECT_DEPTH_BIT`. `texture_info()` substituía
a view correta do descritor por essa view, mesmo quando o slot solicitava
stencil e o shader declarava um `usampler2D`.

O fragment shader `74421cd200` (hash de diagnóstico `aa68a5939321c84a`)
lê a mesma textura `000001C0F967AB50` nos slots t0 e t2, com interpretações
distintas. A primeira leitura fornece flags: BFE com controle `0x106`
(bit 6, tamanho 1) decide um discard; outros campos de 3 bits selecionam
classes de material. A leitura de profundidade é usada separadamente.
Entregar profundidade ao slot de flags faz a classificação depender de bits
da profundidade, em vez dos valores do stencil. Isso explica a dependência
espacial das listras e a ausência do defeito na cor base.

A correção mantém uma única cópia da imagem, mas escolhe a view por descritor.
`vk_sample_view()` compartilha a lógica existente de `vk_view()` entre
texturas originais e snapshots: aspecto depth/stencil, formato, swizzle,
tipo de view e intervalos válidos de subrecursos. Arrays de uma camada usam
a imagem real, em vez do antigo fallback para uma textura dummy.
Não foram acrescentadas cópias de imagens, esperas GPU, filtros ou descartes.
As views continuam usando o cache existente de `vk_image_view()`.
Snapshots permitem formatos compatíveis com `VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT`,
necessário para manter as reinterpretações de formato dos descritores de cor.
Esse complemento foi compilado após a sessão visual; a sessão validou a
correção depth/stencil, não um caso de reinterpretação de formato de cor.

A especificação exige selecionar depth ou stencil, não ambos, numa view
amostrada de uma imagem depth/stencil:
https://docs.vulkan.org/spec/latest/chapters/descriptorsets.html

## Correlação da captura original

Fonte: `scarlet-boot-test/scarlet-graphics-baseline-20261029-231814.stderr.log`.
Os números abaixo são linhas desse arquivo, não do log novo.

Havia também um erro na captura: `CMD_SET_RENDER_TARGETS` altera `st.rt`
antes de `begin_pass()` encerrar o passe anterior. O capturador usava `st.rt`,
portanto podia salvar a imagem do próximo passe, inclusive conteúdo do frame
anterior, e omitir attachments do passe encerrado. Agora `debug_pass_rt`
registra os attachments efetivamente iniciados e o log `[pass]` identifica
cada textura capturada. A referência é invalidada quando a textura é destruída.

| PNG | Linha | Interpretação sustentada pelo log/código |
| --- | ---: | --- |
| 000–004 | 715–1573 | Etapas pequenas/layered e mapas anteriores à geometria; a atribuição retrospectiva exata é limitada pelo erro do capturador. |
| 005 | 1574 | Imagem com listras antes do prepass depth-only. Não prova que o prepass criou as listras: a captura pode conter o conteúdo anterior do próximo target. |
| 006 | 4804 | Cor base sRGB 1920×1080, visualmente limpa, após geometria MRT e antes do desenho `7441c9fd00` que lê profundidade. Não é a mesma imagem HDR de 017. |
| 007–015 | 4962–4989 | Targets 960×540, depth reduzido, iluminação auxiliar/oclusão; inclui `76e691d200`, `74421c2b00`, `74423f6200`. As imagens isoladas não recuperam todos os attachments perdidos. |
| 016 | 5002 | Snapshot do target HDR já selecionado, durante `debug_draw()` antes de executar o shader suspeito. |
| 017 | 5011 | Após o triângulo de composição `7442193000/74421cd200`, no target HDR 1920×1080 f0x3f: as listras estão presentes. |
| 018–103 | 6216–7460 | Etapas posteriores, transparência, redução/composição e pós-processamento. Não são a primeira introdução do defeito no target de iluminação. |

A transição relevante é 016→017 no target de composição, não 006→017
como se fossem a mesma imagem. A operação executada entre elas é o desenho
de iluminação. O defeito está na preparação de seu descritor, não numa
operação aritmética comprovadamente incorreta do shader.

## Entradas da iluminação e produtores anteriores

O MRT da geometria aparece, por exemplo, nas linhas 3114, 4218 e 4791:
cor sRGB f0x38, dois RGBA8 UNORM f0x25, HDR f0x3f, depth/stencil f0x35.
Vários shaders de materiais produzem esses buffers; não há um único produtor
da geometria. O capturador antigo não preservou os três attachments auxiliares
nesse ponto, portanto não é possível validar seus pixels retrospectivamente.

| Slot | Textura (sufixo do ponteiro) | Formato / tamanho | Uso/observação |
| --- | --- | --- | --- |
| t0 | F967AB50 | D24S8, 1920×1080 | Stencil/flags, mesmo recurso de t2, view distinta |
| t1 | F9679A40 | RGBA8 UNORM, 1920×1080 | Buffer auxiliar do MRT |
| t2 | F967AB50 | D24S8, 1920×1080 | Profundidade |
| t3 | F9679D80 | B10G11R11 UFLOAT, 1920×1080 | Buffer HDR do MRT |
| t4 | F9678AD0 | RGBA8 sRGB, 1920×1080 | Cor base |
| t5 | F9679CB0 | RGBA8 UNORM, 1920×1080 | Buffer auxiliar do MRT |
| t6 | F9678C70 | D24S8, 960×540 | Profundidade reduzida |
| t7 | F9678040 | R8 UNORM, 960×540 | Saída de etapa auxiliar; bytes CPU zerados não provam que a imagem GPU esteja zerada |
| t8 | F967A810 | RGBA8 UNORM, 960×540 | Entrada auxiliar |
| t9/t10 | 8EE197F0 / 8EE1BAE0 | BC6H SFLOAT, 64×64 | Cubemaps, 1 e 7 níveis respectivamente |
| t11/t12 | F96792F0 / F9679630 | RGBA16 FLOAT, 960×540 | Entradas auxiliares |
| t13 | F9677EA0 | B10G11R11 UFLOAT, 960×540 | Iluminação auxiliar |

Não se atribuiu arbitrariamente o significado normal/material a cada canal
dos dois RGBA8: falta uma captura válida dos seus dados. Os fetches iniciais
t0–t5 usam coordenadas inteiras derivadas de `gl_FragCoord` e mip 0; o log
registra escala 1. Os cubemaps usam amostragem/LOD separadamente.
`stencil_slots()` já distinguia o tipo inteiro e `vk_view()` já respeitava
`ds_mode`; a substituição posterior por feedback perdia essa distinção.
Layouts permanecem GENERAL; a cópia e os passes mantêm as barreiras existentes.

## Tradutor e SPIR-V

O shader foi extraído em modo somente leitura de `cache/shader_code.bin`,
identificado recalculando o hash dos 0x200 bytes a partir de +0x30.
Seu hash de arquivo de shaders é `1f2a11a80c71db36`, diferente do hash de
diagnóstico. São 1504 instruções, 14 texturas, máscara de cbuf `0x823a`.
Na tradução com o slot de stencil 28 (handle 0x100), t0 é `usampler2D` e
t2 é `sampler2D`. Essa tradução compila e passa em `spirv-val` Vulkan 1.3.
Os artefatos privados estão em `build/graphics-investigation/` e não foram
adicionados ao Git.

`translate.c` e `shaders.c` foram inspecionados, mas não modificados: não
houve evidência para alterar precisão, interpolação, operações half ou
aritmética. Os testes semânticos existentes passaram em 34 casos e suas
102 variantes GLSL/SPIR-V passaram na validação. Isso não constitui prova
exaustiva de todas as instruções Maxwell.

## DEVICE_LOST: investigação separada

O log original termina em `vkWaitSemaphores: -4`, após 103 PNGs, com leitura
GPU inválida `0x35fe98000` e IP `0x2005906f0`. O backtrace foi simbolizado
usando a cópia do executável anterior: a espera ocorre durante o fechamento
e readback de um passe (`vk_end_pass_at`, caminho de flush/overlap), vindo
de clear/exec_list. O endereço GPU não é um endereço guest ou host que se
possa resolver com `addr2line`.

Sem mapa de alocações/checkpoints GPU da execução que falhou, não há como
atribuir esse acesso inválido a uma imagem/buffer específico. Não foi
introduzido um workaround de sincronização nem declarado que essa falha
foi corrigida. A sessão nova normal, sem captura completa de passes, não
reproduziu a perda de dispositivo. O capturador corrigido ainda precisa de
validação sob a mesma carga de captura completa.

## Validação em Windows

- Build incremental do alvo `build/scarlet/eb6deb908752b9c6/scarlet.exe`:
  sucesso. A mudança de header recompilou seus dependentes do runtime;
  nenhum objeto AOT ou `lasgame.dll` foi reconstruído.
- `test_vulkan_feedback.py`: depth/stencil compartilhados, override da view,
  D24/D32, array, swizzle e limites de subrecursos passaram.
- `test_vulkan_sync_errors.py`, `test_vulkan_validation.py`,
  `test_vulkan_overlap.py`, `test_vulkan_overlay.py`: passaram.
- Os simuladores de validation/overlap precisaram acompanhar dependências
  já presentes no runtime (enumeração de extensões, settings/vendor e limite
  de extração anterior a `xm_on`). Nenhuma política de overlap foi alterada.
- Sessão isolada: `build/scarlet-graphics-runs/20261030-000229-839/stderr.log`.
  Chegou ao frame 5690, ~212 segundos, e terminou em `window closed`.
  Inspeção visual da cena do caminho/cerca/personagem: sem as listras pretas.
  Imagem observada arquivada em `build/graphics-investigation/verified-scene.png`.
- Vários intervalos registraram 30,0 FPS e máximo de 34 ms por frame.
  Houve hitches durante carregamento e alguns intervalos posteriores;
  não se afirma uma medição longa ou comparação estatística de desempenho.
- 1716 arquivos (save, caches, ini e DLL originais) comparados por SHA-256:
  **zero alterações**. Manifesto em `build/graphics-investigation/preserved-before.csv`.

## Arquivos e funções

- `runtime/nvn/vulkan/exec.c`: `resolve_feedback`, `texture_info`,
  `begin_pass`, `vk_end_pass_at`, `vk_exec_texture_destroyed`.
- `runtime/nvn/vulkan/textures.c`: extração de `vk_sample_view` de `vk_view`.
- `runtime/nvn/vulkan/vk.h`: declaração da função compartilhada.
- `tools/test_vulkan_feedback.py`: novo teste de regressão.
- `tools/test_vulkan_validation.py`, `tools/test_vulkan_overlap.py`: simuladores atualizados.
- `tools/scarlet/graphics_verify.ps1`: teste isolado, sem escrever nos dados originais.

Comando PowerShell (o progresso nesta cópia de teste não substitui seu save):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Scarlet-Recomp\tools\scarlet\graphics_verify.ps1
```
