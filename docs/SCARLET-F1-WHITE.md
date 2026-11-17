# Scarlet-Recomp — Menu F1 branco

Esta personalização altera a interface sobreposta de F1 no build nativo
`SCARLET_AOT=1` sem tocar no jogo, no save ou no AOT já compilado.

## Identidade visual

- **Branco** como superfície principal: janela quase branca, painéis brancos,
  controles cinza-claro e bordas cinza suaves.
- Texto em carvão escuro, legível sobre superfícies claras.
- Vermelho escarlate (`#CA2738`, aproximadamente) nos destaques, barras,
  marcadores ativos e cabeçalho. Sem paleta vinho.
- Emblema próprio: monograma geométrico inspirado em "S", num bloco vermelho;
  substitui o antigo hexágono com "Z".
- Cabeçalho `SCARLET RECOMP` com identificação `CONFIGURAÇÕES / F1`.
- Créditos no menu **Jogo → Créditos → Menu F1 original**.
- Textos visíveis de saída e retorno ao jogo mencionam Scarlet-Recomp.
  Não há marca Z-A visível fora da atribuição aos autores anteriores.

## Créditos

Menu F1 adaptado a partir das bases de **PokeZ-ARecomp (Hexveil404)** e
**LASRecomp (Peiikai)**. Interface construída com **Dear ImGui**
(Omar Cornut e colaboradores). A atribuição original continua visível.
O novo tema é uma adaptação do projeto Scarlet-Recomp.

Arquivos principais:
- `runtime/ui/menu.mm`: painel, cabeçalho, ícone, textos e créditos.
- `runtime/ui/option_rows.mm`: cartões de opção e indicação de foco.

As mudanças de cor são condicionadas ao build Scarlet onde necessário, para
preservar o funcionamento dos demais componentes do projeto.

## Aplicar ao build existente do Windows

Não é necessário regenerar o código do jogo. Após atualizar a branch
`work/scarlet-indoor-camera-20261117`, feche Scarlet e execute:

```powershell
cd "D:\Scarlet-Recomp-Window-Test"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\scarlet\build_play_f1_white.ps1"
```

O script compila o **runtime executável somente**, mantém a DLL AOT
`lasgame.dll` intacta, faz um backup do EXE anterior em `build/`
e inicia uma sessão manual com 60 FPS. Se a compilação falhar, restaura o
EXE antigo. Com `-BuildOnly`, apenas compila.

Critérios de verificação: painel claro; texto escuro legível; abas e
realces em vermelho; ícone com S, sem hexágono/Z; créditos acessíveis;
controle de F1 e navegação intactos; jogo e câmera funcionando como
antes da alteração visual.

**Validação:** a revisão estática do código e dos blocos condicionais
foi realizada. A compilação Windows e a inspeção visual final precisam
ser confirmadas no computador do usuário.
