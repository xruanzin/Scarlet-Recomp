<div align="center">

<img src="https://raw.githubusercontent.com/xruanzin/Scarlet-Recomp/main/launcher/assets/scarlet_launcher_background.jpg" width="850" alt="Arte do Scarlet-Recomp">

# Scarlet-Recomp

### Pokémon Scarlet recompilado para Windows.

Port nativo independente de **Pokémon Scarlet 4.0.0** para PC.

**Windows 11** · **Vulkan** · **Compilação nativa** · **Teclado e controles**

[Download](https://github.com/xruanzin/Scarlet-Recomp/releases) · [Funcionalidades](#funcionalidades) · [Como jogar](#como-jogar) · [Problemas conhecidos](#problemas-conhecidos) · [English](README.md)

</div>

---

## Sobre

O Scarlet-Recomp leva Pokémon Scarlet ao Windows por meio de recompilação nativa, usando um runtime próprio com Vulkan em vez de emular o sistema original do Switch.

O projeto trabalha com os arquivos do próprio jogador, na versão **4.0.0**, e reúne launcher para PC, controles adaptados, opções de FPS e correções visuais específicas para Scarlet.

## Funcionalidades

### Experiência nativa no Windows

- **Execução nativa:** biblioteca do jogo recompilada e runtime Windows com Vulkan.
- **Launcher dedicado:** seleção do jogo base, atualização, DLCs opcionais e arquivos necessários para a preparação local.
- **Importação de NSP/XCI:** os arquivos são fornecidos pelo próprio jogador; nenhum conteúdo original acompanha o port.
- **Configurações salvas:** preferências de imagem, controles e inicialização.

### FPS e desempenho

- **30 FPS:** opção tradicional do jogo.
- **60 FPS:** modo funcional, testado durante a jogabilidade, embora alguns problemas pontuais ainda possam acontecer.
- **120 / 240 FPS:** disponíveis no launcher, mas **experimentais**, sem garantia de estabilidade ou de física e animações corretas.
- **Contador de FPS, controle de quadros, tela cheia e modo janela.**
- **Resolução interna ajustável** e opções de apresentação portátil ou na base.

### Gráficos

- **Resolução e escala:** opções para aumentar a nitidez, reduzir a resolução e ajustar o enquadramento.
- **Upscaling, sharpening e anti-aliasing**, incluindo SMAA e caminhos opcionais de AMD FSR.
- **Sombras e iluminação:** resolução e nitidez das sombras, oclusão ambiente, iluminação indireta e reflexos na água.
- **Filtros de textura, resolução dinâmica e HDR**, conforme o suporte da placa e da tela.
- **Correções específicas do Scarlet:** melhorias no cabelo, céu e outros problemas visuais encontrados durante o desenvolvimento.

Algumas opções avançadas continuam experimentais.

### Controles

- **Xbox, PlayStation, Nintendo, Steam Deck, teclado e mouse.**
- **Remapeamento** de botões, teclas, mouse, gatilhos e analógicos.
- **Confirmação e cancelamento adaptados:** A/B no padrão Xbox e ×/○ no padrão PlayStation.
- **Ícones de botões no jogo**, nas imagens reconhecidas, incluindo equivalentes de Start e Select.
- **Câmera com mouse e vibração dos controles.**

### Outros ajustes

- Interface em **inglês e português brasileiro**, com detecção do idioma do Windows.
- Seleção de idioma do jogo entre os idiomas presentes nos arquivos do usuário.
- Volume, áudio das cenas e reverberação.
- Ajustes de compatibilidade e acesso aos logs.

## Desempenho

O port alcançou **60 FPS** nos seguintes testes informados:

| Placa de vídeo | Resultado |
| :--- | :--- |
| **NVIDIA GeForce RTX 5060** | **60 FPS** — testes locais |
| **NVIDIA GeForce RTX 3050** | **60 FPS** — testes informados |

Os resultados não representam um benchmark nem garantem FPS constantes. Processador, resolução, drivers e região do jogo também influenciam. O caminho de 60 FPS já foi usado em testes de jogabilidade, mas ainda exige validação contínua.

**120 e 240 FPS são experimentais** e podem apresentar problemas de física, animação ou ritmo do jogo.

## Como jogar

**Requisitos:** Windows 11 (64 bits), GPU compatível com Vulkan e drivers atualizados, arquivos próprios do jogo base e da atualização **4.0.0** e as chaves da própria instalação quando necessárias.

1. Baixe o pacote de Windows pela página de [Releases](https://github.com/xruanzin/Scarlet-Recomp/releases), assim que for publicado.
2. Extraia o ZIP e abra **ScarletLauncher.exe**.
3. Selecione seus NSP/XCI, atualização, DLCs opcionais e as chaves necessárias.
4. Deixe o launcher preparar o jogo localmente e inicie.

A preparação inicial pode demorar. O pacote portátil **passou em um teste básico de inicialização isolada**, mas a instalação completa em outro Windows limpo **ainda não foi validada**. Até lá, o projeto permanece candidato a lançamento.

O repositório **não distribui arquivos do jogo, NSP/XCI, chaves, saves, RomFS nem DLLs compiladas a partir do jogo**.

## Problemas conhecidos

- **Retrato do jogador:** a foto pode ficar preta ou não aparecer no formulário de matrícula no começo do jogo. **É um bug visual conhecido e ainda será corrigido.**
- **Falhas gráficas pontuais:** olhos, sobrancelhas e alguns efeitos ou texturas podem aparecer incorretamente.
- **Botão na tela inicial:** o símbolo **A** do Switch pode continuar aparecendo na frase para começar, mesmo escolhendo outro controle.
- **FPS experimentais:** os modos de 120 e 240 FPS não são estáveis; certos problemas de ritmo, câmera ou animação também podem surgir em 60 FPS.
- **Primeira instalação:** o fluxo completo de preparação em outros computadores ainda precisa de mais testes.

Encontrou um problema reproduzível? [Abra uma issue](https://github.com/xruanzin/Scarlet-Recomp/issues).

## Desenvolvimento

O código inclui runtime Windows, launcher, importador, remapeamento dos controles, ajustes gráficos e ferramentas de distribuição.

Consulte o [guia de compilação](docs/BUILD-windows.md), os [requisitos da versão](docs/RELEASE-DEPENDENCIES-v1.0.0.md) ou explore o [código-fonte](https://github.com/xruanzin/Scarlet-Recomp).

## Créditos

**Scarlet-Recomp** é desenvolvido e mantido por **[xruanzin](https://github.com/xruanzin)**.

Baseado no trabalho de **[PokeZ-ARecomp](https://github.com/Hexveil404/PokeZ-ARecomp)**, **[LASRecomp](https://github.com/peiikai/LASRecomp)** e seus colaboradores, com adaptações próprias para Scarlet. O desenvolvimento contou com auxílio do ChatGPT.

Projeto de fãs **não oficial**, sem vínculo com Nintendo, Game Freak ou The Pokémon Company. Todo o conteúdo Pokémon pertence aos seus respectivos proprietários. Consulte [LICENSE](LICENSE) e as licenças das dependências.
