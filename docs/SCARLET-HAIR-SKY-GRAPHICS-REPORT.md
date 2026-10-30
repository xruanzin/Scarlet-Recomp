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


## 10. Evidência F9 real e experimentos isolados (30/10/2026)

Este suplemento substitui a antiga pendência de identificar os shaders. As capturas fornecidas
pelo desenvolvedor ocorreram nos render frames **9231** e **14241**, com `[debug] F9 armed`,
`[debug] capturing render frame`, `[pass]` e `[vk] saved`.
O pacote analisado possui 249 PNGs; não se adiciona nenhum PNG, log completo,
shader gerado ou dado de jogo ao repositório.

**Identificação por draw trace e saída F9:**

| Fase | Fragment fingerprint | Prova |
|---|---|---|
| Deferred lighting / cabelo | `aa68a5939321c84a` | FS de 14 texturas com destino em RT 1920x1080; presente também no scarlet_pc |
| Céu intermediário | `9543b220d1d35f7b` | FS de 3 texturas com destino 480x270; `pass_017`/`pass_123` exibem degraus horizontais |
| Composição posterior | `2076c99beec00951` | Consome RT 480x270 como entrada (slot 3), desenha em 1920x1080 |

O primeiro input do shader `9543...` é uma textura **3D 32x128x32**,
não uma textura 2D 32x128; os outros dois são 2D 256x64 e 256x256.
É necessário conferir coordenadas de amostragem, slices e a aritmética no shader
traduzido antes de declarar a causa. O render target do céu é FP32 e o problema
precede a composição; um dither genérico de 8 bits **não é** correção justificada.

No repositório antigo, `docs/SCARLET-HAIR-CAPTURE.md` relata que a primeira
tentativa isotrópica não eliminou o defeito azul/roxo. Portanto a nova variante
é **uma repetição experimental do caminho anterior**, não correção confirmada.

### Nova instrumentação: source / material A/B

Esta branch preserva o comportamento baseline por padrão.
O material 3 só é marcado se o programa exato `aa68...` contiver a
instrução unsigned BFE conhecida `r62 = bfe_u(r47, 0x00000303u)`.
Qualquer outra assinatura exibe `[scarlet-hair] ... NOT FOUND` e não pinta pixels.

- `-HairMode baseline`: nenhum shader alterado.
- `-HairMode mask`: marca apenas os fragmentos que executarem o branch de material 3,
  em magenta. **Serve para provar a máscara, não como render final.**
- `-HairMode isotropic`: reaplica o redirecionamento simplificado do antigo experimento
  ao material 3; pode produzir alteração visual errada e só serve para comparação.
- `-DumpFocusShaders`: grava GLSL traduzido **somente** dos fingerprints de cabelo,
  céu e compositor em `userdata/build/scarlet-focus/fs_<hash>_<mode>.frag` e `fs_<hash>.nvasm` de cada run.

Os dois modos experimentais são isolados na identidade de programa e cache
(`ShaderKey.scarlet_hair_mode` espelhado na vertex key), sem tocar na AOT e
sem alterar shaders de outros materiais. O código de geração e os PNGs
ficam sob a pasta de execução isolada, não em commits públicos.

~~~powershell
cd "D:\Scarlet-Recomp"
$env:PATH = "C:\msys64\ucrt64\bin;C:\msys64\usr\bin;" + $env:PATH
$env:MSYSTEM = "UCRT64"
$build = "build/scarlet/eb6deb908752b9c6"
make -j2 SCARLET_AOT=1 GEN=generated-scarlet/eb6deb908752b9c6 B=$build "$build/scarlet.exe"
if ($LASTEXITCODE -ne 0) { throw "Falha ao compilar runtime" }

# Baseline: shader original e dump focado, sem precisar apertar F9
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -DumpFocusShaders

# Segundo run isolado: apenas material ID 3 em magenta
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -HairMode mask -DumpFocusShaders

# Opcional, somente apos avaliar mascara:
# powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -HairMode isotropic -DumpFocusShaders
~~~

No mesmo save, câmera e hora do jogo, use F10 para gerar um screenshot
se precisar comparar. F9 pesado não é necessário para o export GLSL.
Procure a última pasta em `build/scarlet-graphics-runs/<timestamp>/userdata/build/scarlet-focus`;
para a máscara, confira `[scarlet-hair]` no `stderr.log`.
**Limites:** estas mudanças não foram compiladas em Windows nem aprovadas
por comparação visual no instante do commit; nenhuma correção gráfica é reivindicada.


## 11. Follow-up with mask-mode F9 capture — expected pink and sky unchanged

The supplied `stderr(4).log` reports `[scarlet-hair] exact FS ... mode mask` and
`[scarlet-hair] mode 1 material-3 BFE extractor found`. The uploaded `build.zip`
shows the hair/hat region magenta in the mask test (e.g. pass_050),
so the diagnostic successfully tags that portion of the scene. The magenta
removes visible appearance by design; **it is NOT the new hair colour fix**.
Restoring `-HairMode baseline` reverts the diagnostic tint without a rebuild.

The same ZIP has sky stripes already in the 480x270 `pass_017` and in the
later composite (e.g. `pass_043`). No previous test modified the sky shader or
its sampler, therefore seeing unchanged stripes is expected.

The uploaded focus GLSL shows the sky shader uses TWO `texture(t0, vec3(...))`
samples from a 3D 32x128x32 texture. Its auxiliary textures t1 and t2 are 2D.
The previous focus `.nvasm` files were zero bytes because
`maxwell_disassemble()` is a no-op stub in this runtime. The diagnostic
export was corrected to save GLSL only rather than create empty files.

### Targeted sky 3D filtering A/B, disabled by default

To test whether 3D texel/layer interpolation is responsible for the banding,
the Vulkan sampler for the **exact shader hash** `9543b220d1d35f7b`,
fragment slot `t0`, and **3D texture only** may be overridden.
This leaves all shader math, texture data, other draw programs and the AOT
unchanged. It makes a copied sampler descriptor and never changes the
guest descriptor. The modes intentionally preserve the nearest-mip class.

- `-Sky3DFilter baseline`: guest sampler, default/no change
- `-Sky3DFilter linear`: linear within the sampled 3D texture/mip
- `-Sky3DFilter nearest`: point sampling (negative A/B control)

~~~powershell
cd "D:\Scarlet-Recomp"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -HairMode baseline -Sky3DFilter linear
~~~

Compare F10 screenshots on the same save/camera and inspect `[scarlet-sky]`
for the original min/mag filter values. If the sky looks the same **and the
original sampler was already linear**, then texture point sampling is unlikely
to explain the stripes; investigate missing 3D layers/upload, coordinates and
shader arithmetic instead. This is an **experiment, not a verified visual fix**.


### Hair material-3 colour restoration candidate (opt-in, not a confirmed fix)

After the mask A/B identified the affected hair pixels, a separate
`-HairMode albedo` was introduced for the *exact* deferred-lighting FS
`aa68a5939321c84a`. It retains the **guest-computed lighting luminance**
and restores **G-buffer albedo chroma from t4** only for pixels whose
stencil BFE has material ID 3. It reuses the method in
`xruanzin/scarlet_pc`, with the guard that the shader really contains
the fingerprinted BFE extraction.

The original isotropic experiment was not a proven visual solution,
so this new mode does **not** change the guest's material branch. The
normal `-HairMode baseline` and the magenta `mask` remain unchanged.
Because this is a chroma-reconstruction approximation, directional
highlights and hues may still differ from original Switch output.
Only compare on the same scene/save with F10 screenshots.

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -HairMode albedo -Sky3DFilter linear
~~~

This test applies two independent, *fingerprint-scoped* experiments to
different shaders in the same isolated run. If one improves and the
other doesn't, A/B them separately before enabling either by default.
Neither is a verified permanent fix. Do not change the functional branch.

## 12. Hair visually confirmed; sky 3D memory provenance (user test follow-up)

User reported `-HairMode albedo` fixes the observed hair colour. This is visual
confirmation in their scene, not proof that it is pixel-perfect in all scenes.
**Do not replace or delete this opt-in hair mode while diagnosing sky.**

Actual captured sky sampler `[skyaudit]` for FS `9543b220d1d35f7b`,
fragment t0, was `min_filter=3`, `mag_filter=1`, wrap `7/7/7`;
`runtime/nvn/vulkan/textures.c` maps those to linear filter for both min
and mag. Therefore `-Sky3DFilter linear` was equivalent to the original guest
sampling and is not evidence of a fix. The severe horizontal dark bands in
`pass_017` are much larger than the 10-/11-bit quantization at the end of
the GLSL, so removing the final `floor()` blindly is not supported.

A separate candidate root cause is the default Tegra 3D GOB block depth:
`runtime/nvn/tegra.c` currently sets `block_depth_log2=5` (32 stacked
slices) for 32x128x32. Tegra descriptors can represent different Z block
depths, so an incorrect assumption might shuffle data among 3D slices.
**Not yet proved.** The new opt-in `-SkyVolumeDepth baseline|0|1|2|3|4|5`
substitutes the deswizzle block depth only for
3D `32x128x32` format `0x29`, not for any hair or other textures.
The default baseline remains untouched. A single experiment with
`-SkyVolumeDump` saves the raw guest-tiled 1MiB input and the resulting
RGBA16F linear volume for offline inspection. No F9 or full frame dumps needed.

IMPORTANT: the volumetric texture could be **GPU-generated** instead of
CPU-uploaded. The focused `[scarlet-sky] volume binding` log now records
`gpu_owned` and `uploaded`. If `gpu_owned=1` and no raw file is
produced, the CPU deswizzle experiment cannot affect it; next inspect
GPU rendering/compute writes to the volume, not the Tegra upload path.

### Local validation (Windows 11)

After `git fetch` / `git merge --ff-only FETCH_HEAD` on this diagnostic
branch and an incremental `scarlet.exe` build:

~~~powershell
# Preserve the hair improvement while probing ONLY the sky volume:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\graphics_verify.ps1 -HairMode albedo -SkyVolumeDepth 0 -SkyVolumeDump

# The run path is printed by graphics_verify.ps1. When the game closes:
$run = Get-ChildItem '.\build\scarlet-graphics-runs' -Directory |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
$focus = Join-Path $run.FullName 'userdata\build\scarlet-focus'
Select-String (Join-Path $run.FullName 'stderr.log') -Pattern '\[scarlet-sky\]'
if (Test-Path (Join-Path $focus 'sky_volume_tiled_rgba16f_32x128x32.bin')) {
  python '.\tools\scarlet\analyze_sky_volume.py' (Join-Path $focus 'sky_volume_tiled_rgba16f_32x128x32.bin') --png (Join-Path $focus 'sky_volume_layouts.png')
}
~~~

Keep F10 screenshots at same camera for visually comparing with the
baseline. The offline analyzer compares block-depth `0..5` numerically
and creates one contact sheet; smoother scores are **diagnostic clues,
not proof**, and should never automatically select a production fix.
If depth 0 corrupts the sky, revert with `-SkyVolumeDepth baseline`;
the original shader and hair-albedo mode remain unchanged.
