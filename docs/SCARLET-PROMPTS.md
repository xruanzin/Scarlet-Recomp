# Ícones nativos do Pokémon Scarlet 4.0.0

## O problema

A opção **F1 → Controles → Ícones dos botões** já guardava as
escolhas **Automático / Nintendo / Xbox / PlayStation / Teclado / Steam Deck**.
Os mapeamentos físicos já funcionavam e **não precisam ser refeitos**.

As implementações antigas de ícones reconheciam `BtnA_00` e outras
texturas de LASRecomp, ou montavam as fontes de Z-A pelo `zaprompts`.
Pokémon Scarlet/Violet utiliza **máscaras de botão BC4/BC5 distintas**,
por isso mudar a seleção no F1 não substituía suas texturas de jogo.

## Correção na branch experimental

`runtime/nvn/texpatch.c` agora possui um caminho específico para o
**Title ID 0100A3D008C5C000** (Scarlet), protegido por
`SCARLET_AOT`:

1. Identifica as 16 máscaras conhecidas dos prompts de Scarlet/Violet
   4.0.0 por **dimensão, formato BC4/BC5 e hash FNV-1a dos blocos
   deswizzled**; uma textura diferente permanece intacta.
2. Substitui somente máscaras reconhecidas na hora da transferência
   para a GPU, com **arte gerada pelo próprio runtime**. Os arquivos
   originais do jogo não são alterados nem distribuídos.
3. Usa **a seleção já existente**, `g_settings.prompts`:
   - Xbox: letras A/B/X/Y e LB/RB/LT/RT, Menu/View conforme
     `g_bind_pad` (a tecla física ligada ao comando Switch);
   - PlayStation: cruz, círculo, quadrado e triângulo, além
     de L1/R1/L2/R2, Options/Create conforme `g_bind_pad`;
   - Teclado e mouse: teclas já definidas em `g_bind_key` e
     botões em `g_bind_mouse`, desenhados como keycaps/mouse;
   - Nintendo: conserva exatamente os ícones originais;
   - Automático: conserva a escolha existente de
     `bind_prompts_auto()`; Steam Deck usa os nomes da família
     Xbox para as ações compatíveis.
4. Atualiza `texpatch_generation()` para invalidar os ícones
   reconhecidos quando a família ou um mapeamento muda, **sem
   alterar o código de input**. Não cria opção nova no F1.

**Limitação:** 16 imagens conhecidas estão cobertas (A/B/X/Y,
ZL/ZR, L/R, Plus/Minus, câmera e analógico, incluindo algumas
versões ampliadas). Outros prompts podem ser textos de fonte,
imagens fixas ou texturas cujo hash difere, e continuar mostrando
símbolos do Switch até serem identificados. O runtime registra
`[scarlet-prompts] matched` e `[scarlet-prompts] replaced`
para conferir as correspondências reais. **Não foi realizado
ainda teste visual dentro do jogo no computador do usuário.**

A fonte usada para as letras é a que o runtime já carregava para o
sistema antigo. Se a fonte não estiver disponível, os prompts não
são reescritos, evitando ícones vazios. A identificação exige
conteúdo original exato, evitando falsos positivos no HUD.

Referência independente das máscaras e dimensões:
[Tera-recomp, runtime/prompt_icons.c](https://github.com/tukidev-lgtm/Tera-recomp/blob/main/runtime/prompt_icons.c)
(MIT, copyright 2026 Valiantsin Dzerakh). A implementação
de renderização nesta branch é específica do Scarlet-Recomp e
reutiliza o renderizador de letras original de `texpatch.c`.

## Compilar sem perder o 60 FPS e o save

Com o Scarlet fechado e na branch
`work/scarlet-indoor-camera-20261117`, execute:

```powershell
cd "D:\Scarlet-Recomp-Window-Test"
git fetch origin "refs/heads/work/scarlet-indoor-camera-20261117:refs/remotes/origin/work/scarlet-indoor-camera-20261117"
git merge --ff-only "refs/remotes/origin/work/scarlet-indoor-camera-20261117"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\scarlet\build_play_f1_white.ps1"
```

O script já existente faz backup de `scarlet.exe` e compila
apenas o **runtime**. `lasgame.dll` e o save são preservados.

No jogo, abra F1 → Controles → Ícones dos botões e selecione
Xbox, PlayStation ou Teclado. Confirme visualmente em um menu
do próprio jogo e procure os marcadores `[scarlet-prompts]`
no terminal. Se não aparecerem, isso significa que as texturas
encontradas no jogo não coincidiram com as máscaras cobertas
pela primeira implementação; não afirmar sucesso sem testar.
