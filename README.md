# ArtFinder

Aplicativo local para descobrir, comparar, organizar e baixar fan arts de
várias fontes em uma só interface.

## O que ele faz

- Busca em Danbooru, Gelbooru, Safebooru, e621, Pixiv, Tumblr, Bluesky e
  DeviantArt.
- Combina tags diferentes por fonte por meio de `source_tags`.
- Permite criar e editar categorias sem alterar o código.
- Mantém favoritos, avaliações, blacklist e histórico em SQLite.
- Baixa imagens com limite de tamanho, validação do conteúdo e deduplicação por
  hash perceptual.
- Oferece galeria, comparação lado a lado e filtros de conteúdo.

## Usar como aplicativo no Windows

O executável ainda precisa ser gerado. Para testar a versão desktop pelo código:

```powershell
py -3.12 -m venv venv
venv\Scripts\python -m pip install -r requirements-desktop.txt
venv\Scripts\python desktop.py
```

Isso abre uma janela própria. O servidor interno usa uma porta aleatória e
aceita conexões somente deste computador.

Os dados da versão empacotada ficam em:

```text
%LOCALAPPDATA%\ArtFinder\
├── .env
├── user_categories.json
├── webview\
└── downloads\
```

Assim, atualizar ou trocar o `.exe` não apaga configurações, banco ou imagens.

## Gerar o executável

```powershell
py -3.12 -m venv venv
venv\Scripts\python -m pip install -r requirements-dev.txt
venv\Scripts\python -m PyInstaller --noconfirm --clean artfinder.spec
```

O resultado será `dist\ArtFinder.exe`.

O workflow `.github/workflows/build-windows.yml` também gera o executável no
GitHub Actions. Ele pode ser iniciado manualmente na aba Actions ou ao enviar
uma tag como `v0.1.0`.

## Usar no navegador durante o desenvolvimento

```powershell
py -3.12 -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python app.py
```

Por padrão, `app.py` abre `http://127.0.0.1:7860` somente neste computador.
Para liberar temporariamente o acesso na rede local:

```powershell
$env:ARTFINDER_LAN="1"
venv\Scripts\python app.py
```

Não exponha esse modo à internet: o ArtFinder é uma ferramenta pessoal e não
possui sistema de contas.

## Credenciais opcionais

Copie `.env.example` para `.env` e preencha apenas as fontes que pretende usar.
No executável, coloque esse arquivo em `%LOCALAPPDATA%\ArtFinder\.env`.

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

## Categorias e tags por fonte

As categorias ficam em `user_categories.json`. Na tela de edição, o campo de
tags aceita consultas específicas:

```text
vex_(league_of_legends);
pixiv: ヴェックス;
tumblr: vex league of legends;
bluesky: "vex" "league of legends"
```

O texto sem prefixo é a consulta-base dos boorus. Entradas `fonte: consulta`
são overrides e têm prioridade sobre qualquer sugestão automática.

## Estrutura principal

```text
desktop.py              janela nativa e servidor privado
app.py                  API FastAPI e interface local
config.py               configurações e diretórios de dados
artfinder.spec          empacotamento do Windows
templates/index.html    interface
sources/                conectores das plataformas
filters/                filtros de arquivo e cor
utils/database.py       banco SQLite
utils/downloader.py     download e deduplicação
utils/tagmap.py         sugestões de tags por fonte
user_categories.json    categorias iniciais
```

## Observações

- Respeite os termos de uso das plataformas e os direitos dos artistas.
- O ArtFinder preserva links e autores quando a fonte fornece esses dados.
- O filtro anti-IA depende dos metadados de cada fonte e não é infalível.
