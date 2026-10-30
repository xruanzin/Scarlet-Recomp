# Launcher original do Scarlet PC

Fonte: `xruanzin/scarlet_pc`, branch `perf/zen2-aot-production`,
arquivo `launcher/ScarletLauncher.cpp`.

A interface Win32/GDI+ foi copiada: janela 1280×760, cores,
painéis, tipografia, título interno e botão JOGAR.

A tela JOGO possui **somente uma pasta**: NSP/XCI.
Todos os `.nsp` e `.xci` diretamente na pasta são importados.
O update 4.0.0 e qualquer quantidade de DLCs são identificados
por título/conteúdo no `scarletimport.exe`. Não há dois slots fixos.

Coloque `prod.keys` na pasta escolhida ou em `keys` ao lado
do launcher. `title.keys` é opcional. A importação é feita apenas
na primeira vez ou quando os pacotes da pasta mudarem.
Os arquivos do jogo original não são modificados.

Executável de menu: `ScarletLauncher.exe` (Win32 puro).
Abrir `scarlet.exe` sem argumentos executa esse launcher.
JOGAR inicia `scarlet.exe --play <pasta ativa>`.
Voltar à tela inicial encerra o processo do jogo e restaura
o launcher original.

O build baixa o fundo original diretamente do commit fixo
`7cf8e933` do repositório antigo para `assets/`.
O ícone customizado é o mesmo do jogo, quando `icon.ico`
é fornecido na raiz do projeto.

## Build

```powershell
cd "D:\Scarlet-Recomp"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_next_version.ps1
```

## Testar só o launcher

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_next_version.ps1 -SkipImporter
& ".\build\scarlet\eb6deb908752b9c6\scarlet.exe"
```

Compilação/importação/60 FPS ainda precisam ser validados no
Windows com os arquivos locais do jogo. A AOT não é regenerada.
