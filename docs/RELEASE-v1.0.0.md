# Scarlet-Recomp v1.0.0 — primeira versão para testes (rascunho)

> **PREPARAÇÃO, AINDA NÃO PUBLICADO.** Este texto será usado no Release quando o pacote e a instalação por jogadores forem validados.

## Sobre esta versão

O **Scarlet-Recomp** é um projeto comunitário de port de **Pokémon Scarlet 4.0.0** para Windows 11 (x64), com recompilação estática/AOT e gráficos em Vulkan.

### O que está disponível no runtime

- Launcher Scarlet com seleção de NSP/XCI, update 4.0.0, arquivos de keys locais e importação.
- Inicialização TLS/alocador automaticamente pelo `scarlet.exe`, sem ativar a antiga opção de inicialização experimental.
- Configurações de 30, 60, 120 e 240 FPS (a partir de 60 FPS, ainda experimental).
- Entrada por controle/teclado e teclado virtual.
- Correções gráficas específicas do Scarlet em desenvolvimento.

### Problemas conhecidos

- **Foto preta na ficha de matrícula:** a imagem original do personagem ainda não é produzida corretamente. A correção fica para uma versão posterior.
- **Bugs gráficos podem ocorrer** em personagens, efeitos, céu, algumas cutscenes e outras cenas.
- **Acima de 30 FPS é experimental:** podem ocorrer diferenças de velocidade, física, animações, temporização ou instabilidade.
- Compatibilidade com outros PCs e diferentes drivers Vulkan ainda exige testes.

### Downloads e requisitos

Veja [Requisitos e downloads oficiais](RELEASE-DEPENDENCIES-v1.0.0.md).

**Aviso importante:** o ZIP público preparado aqui contém apenas os arquivos redistribuíveis do runtime, launcher, importador e bibliotecas compatíveis. **Ele não inclui `lasgame.dll`** (código do jogo recompilado), nem NSP/XCI, RomFS/ExeFS ou keys. Para jogar, é necessário gerar a biblioteca AOT localmente dos arquivos legítimos do próprio usuário. O instalador/gerador automático dessa etapa ainda não está pronto; portanto o ZIP atual **não é plug-and-play** e não deve ser anunciado como completo.

### Créditos e agradecimentos

Projeto desenvolvido por **xruanzin**, com assistência do **ChatGPT (OpenAI)** em análise de bugs, implementação, revisão técnica e documentação.

Base arquitetural: [LASRecomp](https://github.com/peiikai/LASRecomp), [PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp) e seus colaboradores. Os direitos sobre Pokémon Scarlet e seus materiais pertencem aos respectivos titulares. Este projeto não tem associação oficial com Nintendo, Game Freak ou The Pokémon Company.

---

## English / test release summary

**Scarlet-Recomp v1.0.0** is a community-developed Windows/Vulkan AOT runtime for **Pokémon Scarlet 4.0.0**. It offers a custom launcher, local game importer, automatic early-start compatibility and experimental FPS settings above 30. **Known issues:** a black enrollment-form portrait and possible graphical artifacts. This is not yet a plug-and-play download: the game-derived `lasgame.dll` must be generated locally from the player's own legally obtained game. Developed by **xruanzin**, with technical assistance from **ChatGPT (OpenAI)**. Not affiliated with Nintendo or The Pokémon Company.
