# Scarlet-Recomp — release candidate: controles e ícones multiplataforma

**Branch:** `release/scarlet-stable-controls-rc-20261117`  
**Status:** candidata para validação local, **não** release final publicada.  
**Base:** `fix/scarlet-xbox-playstation-prompts-20261117` com o remapeamento nativo das faces.  

## Entregas desta versão

- F1 do Scarlet em tema branco e com identidade Scarlet-Recomp; preservar o crédito ao projeto de menu original.
- Opção de ícones Nintendo, Xbox, PlayStation, teclado/mouse e Steam Deck no F1.
- Ícones nativos de Start/Select (equivalentes a +/−), gatilhos e faces em texturas conhecidas.
- Xbox: A (sul) confirma, B (leste) volta, X (oeste), Y (norte).
- PlayStation: × (sul) confirma, ○ (leste) volta, □ (oeste), △ (norte).
- Nintendo: A (leste) confirma, B (sul) volta, mantendo a convenção original.
- Mapeamentos personalizados continuam salvos; os padrões nativos só entram automaticamente quando as quatro faces permanecem nos defaults.
- A opção de golpes por posição, enquanto ZL é mantido, não reverte os layouts Xbox/PlayStation.
- O runtime conserva o caminho já existente para o modo nativo de 60 FPS; a compilação local mantém a DLL AOT existente.

## Exclusões intencionais

- **Não** inclui o painel grande na tela inicial de jogo.
- **Não** inclui o experimento de fonte NintendoExt para trocar o botão da tela inicial.
- O símbolo **A** em “PRESSIONE A PARA COMEÇAR” poderá continuar sendo o do Switch; a textura exata ainda não foi identificada. Esta é uma limitação conhecida, não uma correção concluída.
- A substituição de outras texturas não reconhecidas pelo matcher de 16 máscaras não é prometida.

## Validação antes da publicação

1. Fechar `scarlet.exe`, confirmar `git status --short` limpo, mudar para esta branch.
2. Compilar com `tools/scarlet/build_play_f1_white.ps1` no Windows usando a instalação AOT já testada.
3. Iniciar o jogo e abrir um save; confirmar ~60 FPS sem piscadas/regressões no perfil já validado.
4. F1 Nintendo: confirmar A leste / cancelar B sul.
5. F1 Xbox: A sul confirma e B leste cancela; conferir X/Y, Start e Select exibidos e funcionais.
6. F1 PlayStation: × confirma e ○ cancela; conferir □/△, Start e Select exibidos e funcionais.
7. F1 Teclado: conferir os prompts das teclas mapeadas e entrada no save.
8. Testar batalhas, menus e trocas de estilo no F1; configurações personalizadas mantidas.
9. Voltar à tela de título: garantir que não exista mais o retângulo/sobreposição experimental; registrar a limitação do símbolo A original.
10. Criar o pacote de distribuição e testar a partir de uma pasta limpa, sem depender de caminhos locais de desenvolvimento. Conferir créditos/licenças e não incluir NSP/XCI, arquivos do jogo, chaves ou outro conteúdo proprietário.

## Comandos locais (clone existente)

```powershell
cd "D:\Scarlet-Recomp-Window-Test"
git status --short
git fetch origin "refs/heads/release/scarlet-stable-controls-rc-20261117"
git switch -c release/scarlet-stable-controls-rc-20261117 FETCH_HEAD
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\prepare_stable_controls_zip.ps1
```

O empacotador da RC chama a compilação de release, inclui `ScarletLauncher.exe`, `scarlet.exe`, o importador, gerador AOT e Zig para que cada jogador prepare a própria cópia legalmente obtida, incorpora estas notas no arquivo, fecha a auditoria de dependências e realiza um teste portátil. Ele **não distribui** `lasgame.dll`, NSP/XCI, keys, saves ou game data.

**Arquivos gerados no PC do mantenedor:**

- `build/dist/Scarlet-Recomp-Controls-RC-Windows-x64.zip`
- `build/dist/Scarlet-Recomp-Controls-RC-Windows-x64.zip.sha256`

Se as ferramentas e a build completa em `build/scarlet/eb6deb908752b9c6` já estiverem prontas, use `-UsePreparedBuild` para apenas empacotar; não use esse modo quando os executáveis forem de uma branch anterior. O teste automático confirma que o executável abre numa pasta isolada e reconhece o ambiente de compilação, mas **não** substitui o teste de importação e jogo num Windows limpo.

Não crie tag `stable` nem publique uma release até passar pela validação acima.

## Changelog público sugerido

**Scarlet-Recomp — nova candidata com controles multiplataforma**

Interface F1 personalizada, ícones para Nintendo, Xbox, PlayStation e teclado/mouse, Start/Select e remapeamento nativo dos botões de confirmação/cancelamento para Xbox e PlayStation. Mantém o trabalho anterior em 60 FPS. A troca do botão Nintendo na frase da tela inicial ainda está em desenvolvimento e não faz parte desta versão.
