# Pokémon Scarlet 4.0.0 — relatório técnico cabelo e céu (Vulkan)
**30/10/2026 — investigação em branch experimental; nenhuma correção visual comprovada.**

## 1. Resumo executivo
As três capturas mostram 30 FPS, terreno e personagens desenhados, e faixas horizontais/repetições perceptíveis no céu e nas nuvens. A cor do cabelo aparece roxa e ciano; antes de classificá-la como erro é indispensável conhecer a cor selecionada no criador de personagem no mesmo save. Não foram forçadas cores nem filtros.
**Cabelo: NÃO CORRIGIDO. Céu: NÃO CORRIGIDO. Instrumentação: IMPLEMENTADA, ainda não compilada/testada no Windows.**
Foi adicionada rastreabilidade opt-in entre um shader fragment, o vertex shader, o render target e o tamanho/endereço dos constant buffers; o trace de texturas pré-existente agora aceita filtro por FS hash. Não houve alteração da saída gráfica padrão.

## 2. Preservação e proveniência
- Repositório: https://github.com/xruanzin/Scarlet-Recomp
- Funcional: scarlet/bootstrap-4.0.0-20261029; commit 45559ddb51f61a0599df9f0c4800de216b4a4f34.
- Diagnóstico anterior: diagnostic/scarlet-sky-bands-20261030; commit b5778e6a39c6176f87c872881dab5f0e19a78def, PR https://github.com/xruanzin/Scarlet-Recomp/pull/2 (3 commits e 3 arquivos à frente da funcional).
- Nova branch: diagnostic/scarlet-hair-sky-provenance-20261030, criada a partir da diagnóstica; funcional e PR #2 não foram modificados.
- Investigação restrita aos arquivos públicos do GitHub. Não é possível executar git status na pasta D:\Scarlet-Recomp, ver alterações locais, verificar diretamente AOT, lasgame.dll, caches ou o stderr da última sessão. Não houve hard reset, limpeza, regeneração ou upload de arquivos proprietários.

## 3. Cabelo: investigação
**Sintoma:** azul/roxo/ciano aparentemente saturados, porém não existe referência da opção escolhida, portanto nem a divergência em si está demonstrada.

**Caminho técnico localizado:**
1. runtime/nvn/vulkan/textures.c — fmt_of (NVN -> VkFormat, UNORM/sRGB/packed/BCn/ASTC), deswizzle/upload, vk_sample_view (swizzle, mip/layer, tipo de view) e sampler_make.
2. runtime/nvn/maxwell/translate.c — amostras de textura, IPL/IPA, operações half-float e referências de CBuffers.
3. runtime/nvn/vulkan/shaders.c — GLSL/SPIR-V, versão e cache de shader.
4. runtime/nvn/vulkan/exec.c — textura TIC/TSC em texture_info, bindings e CBuffers em stage_set, rasterização e render targets.

**Evidência:** esse caminho existe no código, mas não foi localizado um FS hash ou RT específico do cabelo. A existência de operações sRGB/FP16 não demonstra defeito. Não foi feito REA/Ghidra; nenhum endereço de função ARM64 do material foi comprovado. A amostragem do cabelo e os dados do material precisam ser medidos numa captura de GPU e comparados com a cor escolhida antes de qualquer correção.

**Instrumentação:** SCARLET_GRAPHICS_AUDIT=1 emite [gfxaudit], com frame, hash FS, VS/FS code addresses, quantidade de texturas, máscara de CBuffers FS, endereços/tamanhos dos buffers, render targets, formato/dimensões e viewport. Não lê conteúdo desses buffers nem mexe no shader. Para examinar conteúdo de CBuffer somente após identificar o shader, F9 e o diagnóstico existente LARECOMP_DEBUG_DATA=1 podem gerar detalhes para análise privada.

**Solução aplicada:** nenhuma. Forçar tint ou converter RGB/RGBA sem evidência poderia alterar cores intencionalmente selecionadas e outros materiais.

## 4. Céu: investigação
**Sintoma:** artefatos horizontais atravessam regiões do céu/nuvens; terreno e objetos mostram a melhora da correção anterior de feedback depth/stencil. As imagens não identificam o primeiro pass contaminado.

**Pontos inspecionados no código:** vk_sample_view (mip/layer, cubemap/array, swizzle/format), vk_image_view (cache e criação), sampler_make (filter/wrap/LOD), upload/deswizzle Tegra, texture_info (descritores e feedback) e translate.c (coordenadas/texture ops). Hipóteses abertas: textura 2D, 3D, cubemap, mip, deswizzle, imagem intermediária, precisão ou composição. Nenhuma foi demonstrada.

**Diagnóstico existente:** SCARLET_SKY_AUDIT=1 registra [skyaudit], até 512 bindings distintos desde frame 600 ou SCARLET_SKY_FROM_FRAME, preservando comportamento padrão. Experimentos isolados existentes: baseline, lod1, no-tex-memo e fresh-feedback. Nunca tratar uma melhoria visual isolada em lod1 como correção definitiva.

**Nova correlação:** SCARLET_GRAPHICS_AUDIT=1 registra [gfxaudit] após início do pass, com hashes e render targets associados ao draw. SCARLET_GRAPHICS_FSHASH=HASH_HEX, opcional, filtra **ambos** [gfxaudit] e [skyaudit] pelo mesmo fragment shader, para não esgotar o limite de 512 bindings em shaders irrelevantes. SCARLET_GRAPHICS_FROM_FRAME controla frame inicial; logs têm limite de 512 combinações distintas de FS/VS/primeiro RT. Instrumentação passiva: nenhum novo comando Vulkan, filtro de cor ou textura substituta. O RT registrado é do estado do draw; só captura F9/RenderDoc permite provar qual pass introduziu a faixa.

**Causa / solução aplicada:** pass responsável não identificado; nenhuma correção visual. Próximo experimento deve relacionar F9 do primeiro pass com a faixa aos hashes [gfxaudit], bindings [skyaudit], texturas amostradas e saída do pass.

## 5. Comparação com ports de referência
Consultados arquivos públicos de textura do LASRecomp, PokeZ-ARecomp e letsgo-recomp. Todos apresentam estrutura de conversão fmt_of e mapeamento de tipos de view, refletindo ancestralidade comum. A compatibilidade de uma rotina em outro título **não prova** equivalência dos descritores e dados do Scarlet. Não foi copiada nenhuma mudança especulativa nem testada equivalência de pixels.
- https://github.com/peiikai/LASRecomp
- https://github.com/Hexveil404/PokeZ-ARecomp
- https://github.com/raulzrrs/letsgo-recomp

## 6. Arquivos alterados
| Arquivo | Finalidade |
|---|---|
| runtime/nvn/vulkan/exec.c | Opt-in draw provenance [gfxaudit], filtro por FS hash também em [skyaudit], limite de mensagens, sem mudar GPU state. |
| tools/scarlet/graphics_verify.ps1 | Parâmetros -GraphicsAudit, -GraphicsFromFrame e -GraphicsShaderHash, validando hex e mantendo execução isolada. |
| docs/SCARLET-HAIR-SKY-GRAPHICS-REPORT.md | Relatório, hipóteses, testes e pendências. |

Nenhum game binary, imagem de jogo, save, cache, shader extraído ou AOT foi incluído.

## 7. Testes e comandos
**Executados:** leitura e comparação dos branches no GitHub, leitura dos caminhos de textura/shader/exec, consulta estática de implementations de referência, criação de branch e commits remotos. **Não executados:** compilação Windows, git status local, teste visual A/B, captura F9/F10, teste GPU/device lost e medição de FPS após patch.

Antes de checkout, confirme que as modificações locais estão preservadas. Se git status apresentar mudanças, não faça switch até decidir como salvá-las. No PowerShell:

~~~powershell
cd "D:\Scarlet-Recomp"
git status --short
git fetch origin
git switch --track origin/diagnostic/scarlet-hair-sky-provenance-20261030
# Se a branch local ja existir: git switch diagnostic/scarlet-hair-sky-provenance-20261030

Test-Path .\build\scarlet\eb6deb908752b9c6\lasgame.dll
Test-Path .\build\scarlet\eb6deb908752b9c6\scarlet.exe
$env:PATH = "C:\msys64\ucrt64\bin;C:\msys64\usr\bin;" + $env:PATH
$env:MSYSTEM = "UCRT64"
make -j2 SCARLET_AOT=1 GEN=generated-scarlet/eb6deb908752b9c6 B=build/scarlet/eb6deb908752b9c6 build/scarlet/eb6deb908752b9c6/scarlet.exe
~~~

NÃO executar make clean, make gen-scarlet, nem recompilar lasgame.dll. Se os caminhos de AOT não existirem, interromper e localizar o build real antes de compilar. Em seguida, executar com o mesmo save/câmera/horário:

~~~powershell
# Sem trace (controle)
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1

# Trace observacional (nenhuma mudança de rendering)
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -SkyAudit -GraphicsAudit -SkyFromFrame 50 -GraphicsFromFrame 50

# Com um FS hash real identificado previamente nos logs (1 a 16 dígitos hex sem 0x)
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -SkyAudit -GraphicsAudit -SkyFromFrame 50 -GraphicsFromFrame 50 -GraphicsShaderHash "A1B2C3D4"

# Um experimento por vez; não são fixes
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -SkyAudit -GraphicsAudit -SkyMode lod1 -SkyFromFrame 50 -GraphicsFromFrame 50
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -SkyAudit -GraphicsAudit -SkyMode no-tex-memo -SkyFromFrame 50 -GraphicsFromFrame 50
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -SkyAudit -GraphicsAudit -SkyMode fresh-feedback -SkyFromFrame 50 -GraphicsFromFrame 50
~~~

A1B2C3D4 é exemplo de sintaxe, **não** é um hash real identificado. F9: salvar passes intermediários; F10: screenshot final em armazenamento isolado. Observar console e logs [gfxaudit]/[skyaudit], FATAL, DEVICE_LOST e mensagens de view. Extrair:

~~~powershell
$run = Get-ChildItem .\build\scarlet-graphics-runs -Directory | Sort-Object Name -Descending | Select-Object -First 1
Select-String -LiteralPath (Join-Path $run.FullName 'stderr.log') -Pattern '\[gfxaudit\]|\[skyaudit\]|\[tex\] type mismatch|\[vk\] view failed|FATAL|DEVICE_LOST' | Select-Object -First 1000
~~~

**Critérios de regressão:** nova execução baseline com trace OFF visualmente idêntica à funcional; trace ON visualmente idêntico ao baseline; sem novo crash, DEVICE_LOST ou queda significativa no frame time; somente depois testar hipóteses isoladas e confirmar eventual fix em A/B com screenshots.

## 8. Desempenho
Overlays das três capturas: 30 FPS; GPU 21–26%, CPU 32–43%, RAM aproximadamente 12,8–13,1 GB. Leituras instantâneas, não perfil de frametime. A documentação do PR #2 descreve sessão anterior de cerca de 30 FPS terminada em window closed, sem DEVICE_LOST. **Após esta branch:** FPS, frametime, CPU, GPU e GPU específica não foram medidos. O novo trace é desativado por padrão; seu overhead quando ligado precisa ser medido.

## 9. Pendências e resultado final
1. Confirmar escolha de cabelo e um screenshot de referência sem mudança de iluminação/horário.
2. F9/RenderDoc: descobrir primeiro pass com faixas e seu RT/FS hash.
3. Executar [gfxaudit]+[skyaudit] focando os hashes de cabelo/céu. Comparar textura de entrada, CBuffer, amostra e saída do pass.
4. Localizar a causa com dados e só então criar fix mínimo, teste de regressão de formato/shader e medir A/B Vulkan.
5. Rodar build incremental e validar em cada GPU utilizada; não atribuir o bug à RTX 5060 apenas com um log passado.

| Bug | Classificação | Razão |
|---|---|---|
| Cabelo | **NÃO CORRIGIDO** | Falta referência da cor escolhida e shader/material isolado. |
| Céu | **NÃO CORRIGIDO** | Origem/pass ainda não identificados; nenhum workaround aplicado. |
| Instrumentação | **IMPLEMENTADA, validação pendente** | Código publicado em branch separada; sem compilação ou GPU nesta sessão. |
