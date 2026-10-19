# ArtFinder

[![Build Windows](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml)
[![Build Linux](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml)
[![Build Android](https://github.com/GabiZips/findArts/actions/workflows/build-android.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-android.yml)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-desktop-0078D4?logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-AppImage-FCC624?logo=linux&logoColor=black)

[Português](README.md) · [English](README.en.md)

Aplicativo local para pesquisar, organizar e baixar artes e fan arts
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
- Biblioteca, coleções, visualizador com zoom e filtros de conteúdo.
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

Para gerar o instalador por usuário, instale Inno Setup 6 e execute
`./scripts/build-windows-installer.ps1 -AppVersion 0.10.1`.
O Setup fica em `dist/review/`. Instale atualizações sem desinstalar antes.
Consulte o [guia de atualização](docs/update-0.10.1.md). Gerar o pacote local
não publica uma release no GitHub.

O workflow `.github/workflows/build-windows.yml` também executa os testes e
gera o executável no GitHub Actions. Tags como `v0.2.0` acionam o workflow de
Release, que publica Windows, Linux, Android e seus checksums juntos.

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

Na busca, é possível escolher de 1 a 25 páginas por fonte, com padrão de 5,
filtrar por SFW/Sensível/NSFW, período e score. O bloqueio de arte marcada como IA é obrigatório. Buscas grandes
mostram o custo estimado e pedem confirmação entre 21 e 25 páginas. Conteúdo
NSFW fica borrado até ser revelado com um toque; qualquer resolução é aceita.
Depois da busca, os controles se recolhem para priorizar as imagens. Ao abrir
uma arte, deslize para os lados para navegar pelos resultados; toque para
ocultar os controles e use pinça ou toque duplo para ampliar.

### Parear o PC com o celular

Para levar as categorias, tags por fonte e chaves já configuradas no PC para o
Android, conecte os dois aparelhos à mesma rede Wi-Fi e abra
**Configurações > Parear com o PC** no Android e a área de pareamento no PC:

1. No PC, escolha o que deseja transferir e toque em **Criar pareamento**.
2. Copie o código completo exibido no PC e cole-o no Android.
3. Escolha **Mesclar** ou **Substituir** e toque em **Receber configuração**.

O código expira em cinco minutos e funciona uma única vez. O pacote trafega
cifrado com AES-256-GCM, a chave fica somente dentro do código e nenhum dado
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

Configure as fontes em **Configurações > Fontes e credenciais**. Novos valores
desktop usam o cofre nativo do sistema: Windows Credential Manager ou Secret
Service no Linux. No Linux, o serviço precisa estar disponível e desbloqueado.
Arquivos `.env` legados não são apagados automaticamente; use as ações explícitas
de migração e limpeza nas configurações. `.env.example` documenta os campos
para desenvolvimento e compatibilidade legada. O aplicativo informa apenas se um valor está
configurado e nunca exibe uma senha ou token salvo de volta na tela.

| Fonte | Configuração |
|---|---|
| Danbooru | `DANBOORU_LOGIN` e `DANBOORU_API_KEY` (opcionais) |
| Gelbooru | `GELBOORU_USER_ID` e `GELBOORU_API_KEY` |
| Pixiv | `PIXIV_REFRESH_TOKEN`; gere com `scripts/auth/get_pixiv_token.py` |
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

## Biblioteca, coleções e conteúdo sensível

- **Guardar** mantém a referência da arte na biblioteca do ArtFinder sem criar
  uma cópia no dispositivo.
- **Baixar** salva o arquivo no disco; no Android ele também aparece em
  `Pictures/ArtFinder`.
- Coleções organizam uma mesma arte em pastas sem duplicar a imagem.
- A proteção NSFW começa ligada. Clique/toque na área protegida para revelar,
  novamente para abrir e use **Ocultar imagem** para proteger de novo.
  Revelações são temporárias e não são sincronizadas.
- Arte identificada como gerada por IA é sempre removida dos resultados. Não há
  opção para desligar essa política.
- O visualizador interno aceita zoom e arrasto; o link da fonte continua sendo
  uma ação separada.

## Estrutura principal

```text
desktop.py              janela nativa e servidor privado
app.py                  composição da API FastAPI local
artfinder/api/          rotas separadas por recurso
artfinder/domain/       regras obrigatórias, como o bloqueio de IA
config.py               configurações e diretórios de dados
artfinder.spec          empacotamento desktop Windows/Linux
android-native/         cliente Kotlin/Compose, testes e Gradle do Android
docs/                   índice, guias e decisões de arquitetura
scripts/auth/            autenticação opcional de Pixiv e Tumblr
templates/index.html    interface
templates/i18n.js       tradução português/inglês
templates/viewer.*      zoom e proteção visual NSFW do desktop
sources/                conectores das plataformas
filters/                filtros de arquivo e cor
utils/database.py       banco SQLite
utils/downloader.py     download e deduplicação
utils/android_media.py  integração MediaStore no Android 10+
utils/tagmap.py         sugestões de tags por fonte
defaults/categories.json configuração inicial vazia
user_categories.json    categorias locais do usuário (ignorado pelo Git)
```

A documentação técnica possui um [índice próprio](docs/README.md), incluindo as
decisões de arquitetura, o [cliente Android](android-native/README.md) e o guia
de [contribuição](CONTRIBUTING.md).

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
