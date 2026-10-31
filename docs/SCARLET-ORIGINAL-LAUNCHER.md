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

## Falha de inicialização resolvida: dependências UCRT64

O teste no Windows mostrou que `ScarletLauncher.exe` não iniciava
porque não encontrava `libstdc++-6.dll` e `libgcc_s_seh-1.dll`.
Essas DLLs são dependências dinâmicas do launcher original (C++/MSYS2),
não são arquivos do jogo nem da AOT.

`build_next_version.ps1` passa a copiar automaticamente o runtime do
compilador a partir de `C:\msys64\ucrt64\bin`, incluindo
`libwinpthread-1.dll`, e inspeciona dependências transitivas usando
`objdump.exe` quando disponível. Nunca procura DLLs em sites
de terceiros, não sobrescreve DLLs existentes nem altera o PATH global.

Para reparar **sem recompilar**, caso os dois executáveis já existam:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_next_version.ps1 -SkipRuntime -SkipImporter
```

Para recompilar o runtime e atualizar as DLLs:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_next_version.ps1 -SkipImporter
```

A verificação final de inicialização é necessária no Windows do usuário.

## Revisão visual e importação sem limite (30/10/2026)

O fundo foi substituído pela arte Scarlet/Violet enviada pelo usuário,
agora versionada como `launcher/assets/scarlet_launcher_background.jpg`
em 1280×720. A build copia essa arte sobre o JPG antigo em todas as
compilações, inclusive com `-SkipRuntime -SkipImporter`.
Não baixa mais o fundo do projeto anterior.

O texto de status e as legendas foram movidos dos controles Win32 STATIC
transparentes para o desenho próprio GDI+ do painel, corrigindo a
sobreposição observada na captura. A janela agora se chama `Scarlet`.
O fundo ocupa todo o espaço disponível, com painéis escuros e detalhes
dourados.

Controles novos, sem limite fixo:
- Pasta principal, incluindo subpastas (NSP/XCI)
- `+ ADICIONAR NSP` (quantas vezes desejar)
- `+ ADICIONAR PASTA` (quantas vezes desejar)
- `REMOVER` (somente itens adicionados manualmente)

Os extras são lembrados em `user/config/scarlet_extra_packages.txt`.
Todos os pacotes são deduplicados por caminho antes de criar o manifest
para o importador. Nenhuma modificação em keys, AOT, céu ou cabelo.

Para compilar e abrir a interface:
```powershell
cd D:\Scarlet-Recomp
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_next_version.ps1 -SkipImporter
& '.\build\scarlet\eb6deb908752b9c6\scarlet.exe'
```

Compilação e teste visual no Windows do usuário ainda pendentes.

## Campos de keys e seletor de FPS (30/10/2026)

A tela única **JOGO** contém agora:
- Pasta do jogo NSP/XCI e lista de pacotes adicionais sem limite.
- `prod.keys` com botão PROCURAR. `title.keys` opcional com botão PROCURAR.
  A seleção é persistida em `user/config/scarlet_launcher.ini`.
  O caminho indicado é passado diretamente ao importador; não exige
  colocar as keys junto aos NSPs. Quando o campo fica vazio, permanecem
  os diretórios de keys automaticamente pesquisados antes.
- Seletor de FPS: **30 / 60 / 120 / 240**, persistido e passado ao
  processo `scarlet.exe` por `SCARLET_TARGET_FPS`.

O runtime aplica o valor ao período de frame do Scarlet 4.0.0 somente
após conferir program ID, limite do módulo e constante esperada. O
NVN apresenta com intervalo 2 (modo 30 original), 1 (60), ou 0 (120/240).
120 e 240 possuem limite de apresentação host correspondente.
**Essas são metas de FPS, não desempenho garantido.** O patch de
120/240 é extrapolado e ainda não tem validação de física,
temporização, animações e batalhas. No caso de falha na identificação
do jogo, o runtime mantém 30 FPS.

As keys são utilizadas para a importação e não são incluídas no GitHub.
Os campos novos são controles reais; os rótulos são desenhados na
superfície GDI+ existente, sem os antigos STATIC transparentes.

Teste local:

```powershell
cd D:\Scarlet-Recomp
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_next_version.ps1 -SkipImporter
& .\build\scarlet\eb6deb908752b9c6\ScarletLauncher.exe
```

Para importar os NSP/XCI, execute build_next_version.ps1 sem
`-SkipImporter` antes de clicar JOGAR. A versão ainda requer
compilação/validação no Windows do proprietário.

## Correção da rejeição incorreta do NSP 4.0.0

Log anterior: `error: no update Control NACP with display version 4.0.0`.

A checagem antiga exigia que o `Control NCA` usasse
`0100A3D008C5C800` (Patch Title ID), porém esse tipo de conteúdo
pode registrar `0100A3D008C5C000` (Application Title ID).
O importador agora examina os dois IDs do Scarlet e lê o campo
`DisplayVersion` de `control.nacp` no offset `0x3060`.
A validação estrita `4.0.0` e a verificação do Build ID do NSO
continuam ativas, sem aceitar versões incorretas.

O novo `import.log` registra:
`control: <pacote/NCA> title <id> display version '<versão>'`.
Quando não detectar 4.0.0, a mensagem de erro lista as versões
encontradas para diferenciar pacote errado de falha de leitura.

Para atualizar só o importador (sem recompilar Scarlet ou AOT):

```powershell
cd D:\Scarlet-Recomp
git fetch https://github.com/xruanzin/Scarlet-Recomp.git refs/heads/feature/scarlet-original-launcher-folder-import-20261030
git merge --ff-only FETCH_HEAD
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\scarlet\build_next_version.ps1 -SkipRuntime
```

Em seguida execute `ScarletLauncher.exe` e clique JOGAR.
A nova execução deve reconhecer o `Control` da atualização
ou indicar quais versões realmente foram encontradas.
