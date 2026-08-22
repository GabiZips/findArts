# ArtFinder

[![Build Windows](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml)
[![Build Linux](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml)
[![Build Android](https://github.com/GabiZips/findArts/actions/workflows/build-android.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-android.yml)
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

Versões estáveis ficam em
[GitHub Releases](https://github.com/GabiZips/findArts/releases), acompanhadas
do arquivo `SHA256SUMS.txt`:

1. Abra a versão mais recente.
2. Baixe `ArtFinder-Windows.exe`.
3. Execute o arquivo.

Builds de desenvolvimento continuam disponíveis temporariamente em
[GitHub Actions](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml).

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
gera o executável no GitHub Actions. Tags como `v0.2.0` acionam o workflow de
Release, que publica Windows, Linux e seus checksums juntos.

## Linux

Releases incluem `ArtFinder-Linux-x86_64.AppImage` para computadores Linux de
64 bits. O workflow [Build Linux](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml)
continua gerando builds temporários para desenvolvimento.

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

As Releases incluem `ArtFinder-Android-10-16.apk`, um cliente Android nativo
feito em Kotlin e Jetpack Compose. Ele não abre um site, não incorpora Python e
não depende de um servidor do ArtFinder. O mesmo APK atende Android 10 (API 29)
até Android 16 (API 36), inclusive Android 14.

O aplicativo começa sem personagens. Tags, credenciais e galeria ficam no
próprio aparelho; credenciais são cifradas com uma chave do Android Keystore.
Quem atualiza o antigo APK Python recebe uma migração única das categorias e
credenciais compatíveis, quando os dados antigos ainda estiverem acessíveis.

Ao tocar em **Salvar na galeria**, a imagem é publicada em
`Pictures/ArtFinder` pelo MediaStore, visível no Google Fotos e em outros
aplicativos. Não é solicitada permissão ampla de armazenamento. A Galeria do
ArtFinder referencia essa mesma cópia, evitando duplicar o arquivo. Apagar no
aplicativo remove a imagem que ele criou e o registro local.

O leitor de QR Code é nativo, usa a câmera e processa o código no aparelho. O
modelo do leitor vem embutido no APK; ele não precisa baixar um scanner depois
da instalação.

### Parear o PC com o celular

Para levar as categorias, tags por fonte e chaves já configuradas no PC para o
Android, conecte os dois aparelhos à mesma rede Wi-Fi e abra
**Configurações > Parear com o PC** no Android e a área de pareamento no PC:

1. No PC, escolha o que deseja transferir e toque em **Criar pareamento**.
2. No Android, toque em **Ler QR Code** e aponte a câmera, ou cole o código.
3. Escolha **Mesclar** ou **Substituir** e toque em **Receber configuração**.

O código expira em cinco minutos e funciona uma única vez. O pacote trafega
cifrado com AES-256-GCM, a chave fica somente dentro do QR/código e nenhum dado
é enviado para uma nuvem. Trate o código como uma senha temporária e feche a
tela ao terminar. O pareamento não transfere artes, banco de dados ou histórico.

Redes de faculdade, empresa ou Wi-Fi público podem impedir que aparelhos se
enxerguem. Nesse caso, use uma rede doméstica ou o ponto de acesso de outro
aparelho. Se o Firewall do Windows perguntar, permita o ArtFinder apenas em
redes privadas.

O iPhone não está incluído neste build. iOS exige um projeto e assinatura
próprios, além de um computador macOS com Xcode para gerar o `.ipa`.

Durante o desenvolvimento, o celular pode acessar o ArtFinder pelo navegador
quando estiver na mesma rede Wi-Fi do computador:

```powershell
$env:ARTFINDER_LAN="1"
venv\Scripts\python app.py
```

O terminal mostrará um endereço com um token temporário. Abra o link completo
no celular; o token é removido da barra de endereços e guardado em um cookie de
sessão. Se o Windows solicitar, permita o Python apenas em redes privadas.

> [!WARNING]
> Não exponha o ArtFinder diretamente à internet. O modo de rede local usa
> HTTP e deve ser usado somente numa rede privada confiável, mesmo com o token
> de sessão.

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
android-native/         cliente Kotlin/Compose, testes e Gradle do Android
mobile.py / main.py     bootstrap legado do antigo APK Python
buildozer.spec          empacotamento Android legado, não publicado
scripts/                inspeção de artefatos e controles de empacotamento
templates/index.html    interface
templates/i18n.js       tradução português/inglês
sources/                conectores das plataformas
filters/                filtros de arquivo e cor
utils/database.py       banco SQLite
utils/downloader.py     download e deduplicação
utils/android_media.py  integração MediaStore no Android 10+
utils/tagmap.py         sugestões de tags por fonte
defaults/categories.json configuração inicial vazia
user_categories.json    categorias locais do usuário (ignorado pelo Git)
```

As decisões e limitações da arquitetura multiplataforma estão registradas em
[`docs/adr/0001-multiplatform-packaging.md`](docs/adr/0001-multiplatform-packaging.md).
O acesso em rede e os canais de Release estão registrados em
[`docs/adr/0002-local-access-and-release-channels.md`](docs/adr/0002-local-access-and-release-channels.md).
A decisão da interface Android nativa está em
[`docs/adr/0003-mobile-implementation-strategy.md`](docs/adr/0003-mobile-implementation-strategy.md).

## Licença e segurança

O código-fonte usa a [licença MIT](LICENSE). Ela se aplica ao software, não às
artes, marcas ou conteúdo retornado pelas plataformas. Vulnerabilidades devem
ser relatadas seguindo [SECURITY.md](SECURITY.md), sem publicar credenciais ou
dados pessoais.

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
