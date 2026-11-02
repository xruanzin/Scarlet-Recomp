# Scarlet-Recomp v1.0.0

**First public test release candidate · Windows x64 · Pokémon Scarlet 4.0.0**

## English

Scarlet-Recomp is an unofficial Windows/Vulkan port of **Pokémon Scarlet 4.0.0**, using ahead-of-time static recompilation. This is the **first version for community testing** and graphical or stability issues may occur.

### Installation

1. Download **`Scarlet-Recomp-windows.zip`** from Assets, extract the **`Scarlet-Recomp`** folder, then open **`scarlet.exe`**. Do not run the game from inside the ZIP.
2. In the built-in launcher, choose a folder containing **your own legally obtained base game NSP/XCI, update 4.0.0 NSP**, and optional DLC packages. Choose your own `prod.keys` and optional `title.keys` if required.
3. Press **Play**. On first setup, the bundled importer extracts the updated game data, and the bundled **lasgen** and **Zig** tools prepare the game-specific AOT `lasgame.dll` **on your PC**. Subsequent launches reuse the local compilation when compatible.
4. Once setup is complete, the game starts through the native Vulkan runtime. Keep the extracted installation folder writable.

**No game or game-derived library is included.** No NSP/XCI, keys, ROM assets, saves or precompiled `lasgame.dll` are shipped. The player must provide their own legally acquired files. The automatic first-run workflow is implemented but **still requires an end-to-end test on a clean Windows machine** before publication.

### Features

- Native Scarlet launcher with local NSP/XCI import, update 4.0.0 support and optional DLC selection
- Bundled standalone AOT generator, Zig compiler and self-contained importer — no separate Python, .NET SDK or MSYS2 should be necessary on player PCs, subject to verification
- Automatic TLS/early allocator startup without the old experimental checkbox
- Controller and keyboard input with in-game virtual keyboard support
- FPS targets of **30 / 60 / 120 / 240** (higher modes are experimental)

### Known issues

- The enrollment form's character photo is **black**. The original in-game portrait generation remains unresolved.
- **Graphical glitches may occur**, including in characters, sky, shaders, effects and cutscenes.
- **30 FPS is recommended. Anything above 30 FPS is experimental**, and may affect performance, game timing, animations or physics.
- Compatibility and the full first-run setup have not yet been verified across different Windows PCs and GPU drivers.

### Requirements

- Windows 11 64-bit with a Vulkan-capable graphics driver
- Own Pokémon Scarlet base game and update **4.0.0**, and your own keys when required
- [NVIDIA drivers](https://www.nvidia.com/Download/index.aspx) · [AMD drivers](https://www.amd.com/en/support/download/drivers.html) · [Microsoft Visual C++ Redistributable x64](https://aka.ms/vc14/vc_redist.x64.exe) (only if Windows requires it)
- Full notes: [Requirements, dependencies and credits](https://github.com/xruanzin/Scarlet-Recomp/blob/release/v1.0.0-preparation-20261101/docs/RELEASE-DEPENDENCIES-v1.0.0.md)

### Credits

Developed by **xruanzin**, with technical assistance from **ChatGPT (OpenAI)** in debugging, coding, code review and documentation. Based on and inspired by **LASRecomp** (Peiikai), **PokeZ-ARecomp** (Hexveil404), and upstream contributors.

This project is unofficial and is **not affiliated with Nintendo, Game Freak, or The Pokémon Company**.

---

## Português (Brasil)

O **Scarlet-Recomp** é um port comunitário e não oficial de **Pokémon Scarlet 4.0.0** para Windows, usando recompilação estática AOT e Vulkan. Esta é a **primeira versão para testes da comunidade**: podem ocorrer problemas de estabilidade e bugs gráficos.

### Instalação

1. Baixe **`Scarlet-Recomp-windows.zip`** em *Assets*, extraia a pasta **`Scarlet-Recomp`** e abra **`scarlet.exe`**. Não execute o jogo diretamente de dentro do ZIP.
2. No launcher, escolha uma pasta com os **seus próprios arquivos NSP/XCI do jogo base e a atualização 4.0.0 em NSP**, além dos DLCs opcionais. Se necessário, selecione suas `prod.keys` e `title.keys`.
3. Clique em **JOGAR**. Na primeira configuração, o importador organiza os arquivos do jogo e o **lasgen** e o compilador **Zig**, incluídos no ZIP, geram a biblioteca AOT `lasgame.dll` **localmente no seu computador**.
4. Ao concluir a preparação, o jogo inicia pelo runtime nativo Vulkan. Mantenha a pasta de instalação em um local com permissão de escrita.

**O ZIP não inclui o jogo nem código recompilado do jogo**: nada de NSP/XCI, keys, RomFS, saves ou `lasgame.dll` pronta. Cada jogador usa seus próprios arquivos legítimos. A preparação automática foi implementada, mas **ainda precisa ser testada de ponta a ponta num Windows limpo** antes da publicação.

### Recursos desta versão

- Launcher próprio com importação de NSP/XCI, update 4.0.0 e DLCs opcionais
- Gerador AOT e compilador Zig portáteis incluídos, sem necessidade planejada de instalar Python, .NET SDK ou MSYS2 no PC do jogador (pendente de validação)
- Inicialização TLS/alocador integrada, sem ativar opção experimental
- Controles, teclado e teclado virtual
- Opções de **30 / 60 / 120 / 240 FPS**

### Problemas conhecidos

- **A foto do personagem na ficha de matrícula aparece preta.** A correção ficará para uma atualização futura.
- **Bugs gráficos podem acontecer** em personagens, cabelo, céu, shaders, efeitos e cutscenes.
- **Acima de 30 FPS ainda é experimental** e pode provocar problemas de desempenho, física, animações e sincronização. Recomenda-se iniciar em **30 FPS**.
- Alguns PCs e drivers ainda não foram testados; a instalação inicial fora do ambiente de desenvolvimento exige validação.

### Requisitos

Windows 11 x64, GPU e driver compatíveis com Vulkan, sua própria cópia de Pokémon Scarlet e atualização **4.0.0**. Downloads oficiais: [drivers NVIDIA](https://www.nvidia.com/Download/index.aspx), [drivers AMD](https://www.amd.com/en/support/download/drivers.html) e [Visual C++ x64](https://aka.ms/vc14/vc_redist.x64.exe) (caso seja solicitado pelo Windows).

### Créditos

Projeto desenvolvido por **xruanzin**, com assistência técnica do **ChatGPT (OpenAI)** durante a implementação, investigação de bugs, revisão de código e documentação. Agradecimentos aos autores de **LASRecomp**, **PokeZ-ARecomp** e demais colaboradores.

Projeto independente, sem qualquer vínculo oficial com a Nintendo, Game Freak ou The Pokémon Company.
