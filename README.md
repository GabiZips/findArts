# ArtFinder

[![Build Windows](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml)
[![Build Linux](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-desktop-0078D4?logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-AppImage-FCC624?logo=linux&logoColor=black)

[Português](README.md) · [English](README.en.md)

Aplicativo local para pesquisar, comparar, organizar e baixar artes e fan arts
de várias fontes em uma só interface.

> [!IMPORTANT]
> O ArtFinder é um projeto independente e não oficial. Ele não possui
> associação, aprovação ou patrocínio de Pixiv, Tumblr, Bluesky, DeviantArt,
> Danbooru, Gelbooru, Safebooru, e621 ou dos detentores das obras pesquisadas.

## Funcionalidades

- Busca unificada em Danbooru, Gelbooru, Safebooru, e621, Pixiv, Tumblr,
  Bluesky e DeviantArt.
- Tags específicas por fonte por meio de `source_tags`.
- Categorias personalizadas sem alterações no código.
- Favoritos, avaliações, blacklist e histórico armazenados localmente em
  SQLite.
- Galeria, comparação lado a lado e filtros de conteúdo.
- Download com limite de tamanho, validação do arquivo e deduplicação por hash
  perceptual.
- Preservação do autor e do link original quando a fonte fornece esses dados.
- Interface em português e inglês, com idioma salvo no dispositivo.

## Baixar para Windows

Os builds automáticos ficam na página
[GitHub Actions](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml):

1. Abra a execução mais recente que esteja com o indicador verde.
2. Na seção **Artifacts**, baixe `ArtFinder-Windows`.
3. Extraia o arquivo ZIP.
4. Execute `ArtFinder.exe`.

O Windows pode exibir um aviso do SmartScreen porque o executável ainda não
possui assinatura digital comercial.

Os dados do aplicativo ficam separados do executável:

```text
%LOCALAPPDATA%\ArtFinder\
├── .env
├── user_categories.json
├── webview\
└── downloads\
```

Atualizar ou substituir o `.exe` não apaga configurações, banco ou imagens.
Uma instalação nova começa sem personagens ou tags. As categorias criadas pelo
usuário ficam somente nessa pasta local e não são incluídas no executável.

## Executar pelo código

Requer Python 3.12.

```powershell
py -3.12 -m venv venv
venv\Scripts\python -m pip install -r requirements-desktop.txt
venv\Scripts\python desktop.py
```

Isso abre uma janela própria. O servidor interno da versão desktop usa uma
porta aleatória e aceita conexões somente do computador.

## Gerar o executável

```powershell
py -3.12 -m venv venv
venv\Scripts\python -m pip install -r requirements-dev.txt
venv\Scripts\python -m PyInstaller --noconfirm --clean artfinder.spec
```

O resultado será `dist\ArtFinder.exe`.

O workflow `.github/workflows/build-windows.yml` também executa os testes e
gera o executável no GitHub Actions. Ele pode ser iniciado manualmente ou ao
enviar uma tag como `v0.1.0`.

## Linux

O workflow [Build Linux](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml)
gera o artefato `ArtFinder-Linux-x86_64`, contendo um AppImage para computadores
Linux de 64 bits.

Depois de extrair o ZIP:

```bash
chmod +x ArtFinder-Linux-x86_64.AppImage
./ArtFinder-Linux-x86_64.AppImage
```

Os dados pessoais ficam em `~/.local/share/artfinder/`, ou no diretório
definido por `$XDG_DATA_HOME/artfinder/`. O executável Windows não funciona no
Linux; cada sistema recebe seu próprio build.

## Android e acesso pelo celular

O arquivo `.exe` funciona somente no Windows e não pode ser instalado
diretamente no Android ou iPhone.

Existe uma fundação experimental para gerar um APK Android nativo usando o
WebView do sistema e o mesmo backend Python local. O workflow
[Build Android](https://github.com/GabiZips/findArts/actions/workflows/build-android.yml)
é manual e gera `ArtFinder-Android-experimental`.

> [!CAUTION]
> O APK ainda precisa ser validado em aparelho físico. Nesta primeira etapa,
> downloads e configurações ficam no armazenamento privado do aplicativo; a
> exportação para a Galeria/Downloads pública do Android ainda será implementada.

As credenciais das fontes podem ser preenchidas dentro do próprio aplicativo
em **Stats > Fontes e credenciais**, sem incluir senhas no APK.

O iPhone não está incluído neste build. iOS exige um projeto e assinatura
próprios, além de um computador macOS com Xcode para gerar o `.ipa`.

Durante o desenvolvimento, o celular pode acessar o ArtFinder pelo navegador
quando estiver na mesma rede Wi-Fi do computador:

```powershell
$env:ARTFINDER_LAN="1"
venv\Scripts\python app.py
```

O terminal mostrará o endereço local que deve ser aberto no celular. Se o
Windows solicitar, permita o Python apenas em redes privadas.

> [!WARNING]
> Não exponha o ArtFinder diretamente à internet. O modo de rede local ainda
> não possui contas, senha ou controle de acesso.

## Credenciais opcionais

Copie `.env.example` para `.env` e preencha somente as fontes que pretende
usar. No executável, coloque esse arquivo em
`%LOCALAPPDATA%\ArtFinder\.env`.

Também é possível configurar esses campos pela interface em
**Stats > Fontes e credenciais**. O aplicativo informa apenas se um valor está
configurado e nunca exibe uma senha ou token salvo de volta na tela.

| Fonte | Configuração |
|---|---|
| Danbooru | `DANBOORU_LOGIN` e `DANBOORU_API_KEY` (opcionais) |
| Gelbooru | `GELBOORU_USER_ID` e `GELBOORU_API_KEY` |
| Pixiv | `PIXIV_REFRESH_TOKEN`; gere com `get_pixiv_token.py` |
| Tumblr | `TUMBLR_API_KEY`; OAuth completo melhora a busca |
| DeviantArt | `DEVIANTART_CLIENT_ID` e `DEVIANTART_CLIENT_SECRET` |
| Bluesky | `BSKY_HANDLE` e uma app password em `BSKY_PASSWORD` |

Danbooru, Safebooru e e621 podem funcionar sem credenciais. Nunca envie o
arquivo `.env` para o GitHub.

O suporte ao Pixiv usa um cliente de terceiros para a API do aplicativo e não
é uma integração oficial do Pixiv. Alterações na plataforma podem interromper
temporariamente essa fonte.

## Categorias e tags por fonte

As categorias começam vazias e ficam no `user_categories.json` privado de cada
dispositivo. Na tela de edição, o campo de tags aceita consultas específicas:

```text
vex_(league_of_legends);
pixiv: ヴェックス;
tumblr: vex league of legends;
bluesky: "vex" "league of legends"
```

O texto sem prefixo é a consulta-base dos boorus. Entradas `fonte: consulta`
são overrides e têm prioridade sobre sugestões automáticas.

## Estrutura principal

```text
desktop.py              janela nativa e servidor privado
app.py                  API FastAPI e interface local
config.py               configurações e diretórios de dados
artfinder.spec          empacotamento desktop Windows/Linux
mobile.py / main.py     servidor local usado pelo APK Android
buildozer.spec          empacotamento Android experimental
templates/index.html    interface
templates/i18n.js       tradução português/inglês
sources/                conectores das plataformas
filters/                filtros de arquivo e cor
utils/database.py       banco SQLite
utils/downloader.py     download e deduplicação
utils/tagmap.py         sugestões de tags por fonte
defaults/categories.json configuração inicial vazia
user_categories.json    categorias locais do usuário (ignorado pelo Git)
```

As decisões e limitações da arquitetura multiplataforma estão registradas em
[`docs/adr/0001-multiplatform-packaging.md`](docs/adr/0001-multiplatform-packaging.md).

## Aviso legal e de conteúdo

- Nenhuma fan art é incluída no repositório ou no executável.
- O conteúdo é consultado em serviços de terceiros por solicitação do usuário.
- Os nomes e marcas das plataformas pertencem aos respectivos titulares.
- O usuário é responsável por cumprir os termos de cada plataforma e respeitar
  os direitos dos artistas e demais titulares.
- O ArtFinder não remove marcas d'água nem tenta contornar conteúdo pago ou
  privado.
- Algumas fontes podem retornar conteúdo sensível ou adulto. Use os filtros de
  classificação e não disponibilize o aplicativo a menores sem supervisão.
- O filtro anti-IA depende dos metadados de cada fonte e não é infalível.

## Desenvolvimento

Contribuições, correções de conectores e melhorias no mapeamento de tags são
bem-vindas. Ao relatar um problema, não publique tokens, senhas, cookies ou o
conteúdo do seu arquivo `.env`.
