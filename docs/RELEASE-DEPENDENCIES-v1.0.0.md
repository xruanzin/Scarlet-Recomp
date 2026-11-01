# Scarlet-Recomp v1.0.0 — requisitos, dependências e créditos

## Para jogadores no Windows

- **Windows 11 x64** e uma GPU com drivers atualizados e suporte a Vulkan.
- **Driver NVIDIA:** https://www.nvidia.com/Download/index.aspx
- **Driver AMD:** https://www.amd.com/en/support/download/drivers.html
- **Microsoft Visual C++ Redistributable (x64)**, se o Windows informar que faltam bibliotecas MSVC: https://aka.ms/vc14/vc_redist.x64.exe
- **Pokémon Scarlet base e update 4.0.0**, obtidos legalmente pelo usuário, e as próprias keys quando exigidas pelo importador.
- **AOT local:** a biblioteca `lasgame.dll` deve ser gerada a partir do jogo pertencente ao usuário. O ZIP público não fornece essa biblioteca, e a versão atual ainda precisa de um instalador/gerador AOT acessível ao jogador.

O pacote de runtime já inclui `scarlet.exe`, `ScarletLauncher.exe`, `scarletimport.exe` self-contained, SDL3, bibliotecas UCRT64/FFmpeg selecionadas e arte do launcher, condicionada à verificação das licenças de redistribuição.

**A meta é não exigir Python, .NET SDK, compiladores ou MSYS2 no PC do jogador.** O importador é self-contained e o ZIP inclui `lasgen/` e o compilador Zig. Isso estará confirmado apenas após testar a instalação e geração AOT num Windows limpo.

## Apenas para quem compila o projeto

- Python (oficial): https://www.python.org/downloads/windows/
- MSYS2/UCRT64: https://www.msys2.org/
- .NET 8 SDK: https://dotnet.microsoft.com/en-us/download/dotnet/8.0
- Microsoft Visual Studio / Build Tools: https://visualstudio.microsoft.com/downloads/
- Vulkan SDK (desenvolvimento): https://vulkan.lunarg.com/sdk/home
- GitHub CLI (somente para o mantenedor criar um Release): https://cli.github.com/

## Limitações da v1.0.0

- **A foto do personagem no formulário de matrícula aparece preta.**
- **Bugs gráficos podem ocorrer**, incluindo artefatos em cenas e efeitos.
- **30 FPS é a configuração recomendada.** Os alvos de 60, 120 e 240 FPS continuam experimentais e podem causar problemas de desempenho, física, animações e temporização.
- Não há garantia de compatibilidade com todos os computadores.

## Créditos

Desenvolvimento e integração do Scarlet-Recomp por **xruanzin**, com assistência do **ChatGPT (OpenAI)** em investigação de bugs, análise técnica, implementação, revisão de código e documentação.

Agradecimentos a **LASRecomp (Peiikai)**, **PokeZ-ARecomp (Hexveil404)** e demais autores e colaboradores dos projetos originais e das dependências utilizadas. Consulte os avisos e licenças do repositório.

Scarlet-Recomp é um projeto comunitário não oficial e não tem relação com a Nintendo, Game Freak ou The Pokémon Company. A distribuição de código do runtime não concede permissão para distribuir arquivos ou código derivados do jogo original.
