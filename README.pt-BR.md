<div align="center">

# Scarlet-Recomp

**Pokémon Scarlet 4.0.0 — versão nativa para Windows**

Recompilação estática (AOT) · Vulkan · Windows 11 x64

[English](README.md) · [Notas da v1.0.0](docs/RELEASE-v1.0.0.md) · [Compilação](docs/BUILD-windows.md) · [Reportar problema](https://github.com/xruanzin/Scarlet-Recomp/issues)

</div>

---

> [!IMPORTANT]
> **A v1.0.0 está em preparação.** O jogo funciona nos testes locais de desenvolvimento, mas o ZIP portátil e a preparação inicial **ainda não foram validados em uma instalação limpa do Windows**. Ainda não há uma release pública validada.

## Sobre o projeto

O Scarlet-Recomp é um **port nativo, comunitário e não oficial** de Pokémon Scarlet 4.0.0 para Windows. O projeto recompila antecipadamente o código dos arquivos do jogo do próprio usuário e utiliza um runtime Windows/Vulkan, sem recorrer a um emulador baseado no suyu.

A arquitetura parte de [PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp) e [LASRecomp](https://github.com/peiikai/LASRecomp), com adaptações e correções específicas para Scarlet.

## Estado atual

| Componente | Situação |
| --- | --- |
| Runtime nativo Windows/Vulkan | Inicializa e executa nos testes locais |
| Launcher e importação NSP/XCI | Implementados; instalação limpa ainda não validada |
| Pokémon Scarlet 4.0.0 | Versão-alvo |
| 30 FPS | Referência recomendada |
| 60 / 120 / 240 FPS | Metas experimentais; podem afetar física e temporização |
| ZIP público | Em preparação; nenhuma release validada publicada |

**Problemas conhecidos:** olhos e sobrancelhas podem desaparecer em algumas cenas; a foto da ficha de matrícula pode ficar preta; outros defeitos gráficos e de estabilidade podem ocorrer. A flutuação na animação da cadeira e as piscadas em tela cheia deixaram de ocorrer em builds locais específicas, mas ainda precisam ser verificadas no pacote v1.0.0.

**Temporização nativa adaptativa a 60 FPS (experimental):** selecionar **60 FPS** já utiliza o relógio adaptativo integrado ao runtime. Não precisa de mod, `.pchtxt`, nova opção no launcher nem refazer a DLL AOT por esse motivo. [Implementação e testes pendentes](docs/SCARLET-NATIVE-DYNAMIC-60FPS.md). A tremedeira do personagem ainda precisa de validação no jogo.

## Requisitos e instalação

É necessário ter **Windows 11 x64**, driver/GPU compatível com Vulkan, **sua própria cópia legítima do jogo base e da atualização 4.0.0**, além das chaves da sua instalação quando exigidas pela importação.

Quando estiver validado, o pacote será disponibilizado em [Releases](https://github.com/xruanzin/Scarlet-Recomp/releases). O launcher foi projetado para importar os arquivos do usuário e gerar localmente a biblioteca AOT específica do jogo.

> [!NOTE]
> O repositório **não distribui** o jogo, NSP/XCI, keys, RomFS, saves nem a `lasgame.dll` derivada do jogo. A preparação inicial pode demorar e ainda não foi validada em outro PC com Windows limpo.

## Desenvolvimento e documentação

Para mantenedores, o empacotamento no Windows utiliza:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_release_candidate.ps1
```

O comando pressupõe um ambiente de desenvolvimento configurado e uma build AOT existente. **Não é uma instrução de instalação para jogadores.**

[Guia de compilação](docs/BUILD-windows.md) · [Checklist da v1.0.0](docs/RELEASE-CHECKLIST-v1.0.0.md) · [Dependências](docs/RELEASE-DEPENDENCIES-v1.0.0.md) · [Notas de desenvolvimento](docs/SCARLET-BOOTSTRAP.md)

## Créditos

Desenvolvido por **xruanzin**, com assistência técnica do **ChatGPT (OpenAI)**. Agradecimentos aos autores e colaboradores de [PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp), [LASRecomp](https://github.com/peiikai/LASRecomp) e demais componentes usados no projeto.

Projeto independente, **sem vínculo oficial com Nintendo, Game Freak ou The Pokémon Company**. Consulte a [LICENSE](LICENSE); a licença do código-fonte não autoriza redistribuir conteúdo do jogo.
