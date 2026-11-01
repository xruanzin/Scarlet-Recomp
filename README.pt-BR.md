<div align="center">

# Scarlet-Recomp

**Runtime nativo para Pokémon Scarlet 4.0.0 no Windows, com recompilação estática e Vulkan.**

[English](README.md) · [Limitações](#limitações-conhecidas) · [Preparação da v1.0.0](docs/RELEASE-v1.0.0.md)

</div>

> **Preparação da v1.0.0 — ainda não é um instalador público validado.** O jogo executa no ambiente de desenvolvimento atual, mas a instalação em outro PC, o pacote de distribuição e a compatibilidade ampla ainda exigem testes. Não há garantia de que qualquer computador consiga iniciar o jogo com um simples download.

## Sobre o projeto

O Scarlet-Recomp é um projeto não oficial de **Pokémon Scarlet 4.0.0** no Windows, utilizando recompilação AOT do código extraído dos arquivos do próprio usuário. O runtime implementa serviços do Nintendo Switch e gráficos NVN por meio do Vulkan, com a proposta de executar o port sem um emulador baseado em suyu.

Utiliza como base arquitetural o [PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp) e o [LASRecomp](https://github.com/peiikai/LASRecomp), além das modificações específicas do Scarlet.

## Recursos implementados

- Runtime Windows 11 com Vulkan e módulos recompilados em AOT
- Launcher próprio com seleção de pasta/arquivos NSP/XCI e campos de keys locais
- Inicialização TLS/alocador automática para Scarlet 4.0.0: não é necessário marcar uma opção experimental nem configurar variáveis de ambiente
- Caminho de importação para jogo base e atualização **4.0.0**, com DLCs opcionais
- Controle, teclado e teclado virtual para inserir o nome do personagem
- Seleção de metas de **30 / 60 / 120 / 240 FPS**; 30 FPS é a referência, valores superiores são experimentais
- Correções gráficas Vulkan e opções de melhoria de imagem ainda em desenvolvimento

Os recursos acima descrevem implementações em desenvolvimento, **não um teste de compatibilidade completo**.

## Requisitos e arquivos do jogo

- Windows 11 de 64 bits e driver de vídeo compatível com Vulkan
- Sua própria cópia legítima de Pokémon Scarlet, com atualização **4.0.0**
- Keys de sua própria instalação/console, quando necessárias para a importação
- Uma `lasgame.dll` gerada **localmente** por recompilação AOT dos arquivos do jogo do próprio usuário

**Não incluir em commits nem em releases públicos:** NSP/XCI, dados extraídos, prod.keys, title.keys, tickets, saves ou `lasgame.dll` derivada do jogo.

## Compilação de desenvolvimento

O script incremental abaixo exige que a AOT já tenha sido produzida no computador:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_next_version.ps1
```

Ele **não gera** a `lasgame.dll` sozinho. Veja [Bootstrap do Scarlet](docs/SCARLET-BOOTSTRAP.md) e [documentação do launcher](docs/SCARLET-ORIGINAL-LAUNCHER.md). São documentos técnicos históricos; ainda não equivalem a um instalador pronto para um PC novo.

## Limitações conhecidas

- **A foto do personagem na ficha de matrícula fica preta.** A geração da foto pelo próprio jogo continua em investigação; não será usada uma imagem externa para disfarçar o problema.
- Alguns efeitos e passagens gráficas podem apresentar defeitos.
- 60, 120 e 240 FPS são metas experimentais, sem garantia de funcionamento correto da física ou temporização.
- A primeira instalação fora do ambiente de desenvolvimento precisa ser validada.

Veja o [rascunho do release v1.0.0](docs/RELEASE-v1.0.0.md) e o [checklist](docs/RELEASE-CHECKLIST-v1.0.0.md).

## Créditos e aviso legal

Projeto independente, sem vínculo com Nintendo, Game Freak ou The Pokémon Company. Os direitos sobre Pokémon Scarlet pertencem aos titulares respectivos.

O projeto deriva de trabalhos como [PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp) e [LASRecomp](https://github.com/peiikai/LASRecomp). Os créditos e licenças de terceiros precisam ser preservados. A [LICENSE](LICENSE) deste repositório **não** concede direitos de distribuição sobre o jogo original.
