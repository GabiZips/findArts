# 💎 ArtFinder

Ferramenta local de **descoberta e curadoria de fan art**. Busca em várias
plataformas ao mesmo tempo, junta tudo numa interface só e ajuda você a
**escolher** o que presta — com um fluxo de triagem rápido em vez de só acumular.

Roda no seu PC e abre no navegador. Nada sai da sua máquina.

## ✨ O que faz

- **Busca unificada** em Danbooru, Gelbooru, Safebooru, e621, Tumblr, Bluesky e DeviantArt — resultados mesclados e deduplicados numa grade só.
- **Tumblr por popularidade**: amostra várias épocas e ordena por número de notas (acha as artes famosas, não só as recentes).
- **Triagem rápida**: no zoom, teclas `1` Usar · `2` Talvez · `3` Rever depois · `4` Não gostei, com auto-avanço. Nada é apagado — tudo vira uma pilha revisável.
- **Modo comparação**: 2 a 4 finalistas lado a lado em tela cheia para escolher a melhor.
- **Galeria** com miniaturas geradas sob demanda, filtros por fonte/categoria/pilha e busca por texto.
- **Filtro anti-IA** em todas as fontes, filtro por rating (SFW/Sensível/NSFW), score, período e resolução.
- **Deduplicação** por perceptual hash (evita a mesma imagem vinda de fontes diferentes).
- **Categorias personalizadas** com autocomplete de tags do Danbooru.

## 📦 Instalação

Requer **Python 3.10+**.

```bash
# 1. Clonar
git clone <url-do-seu-repo>
cd findArts

# 2. Ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows (PowerShell)
source venv/bin/activate     # Linux / macOS

# 3. Dependências
python -m pip install -r requirements.txt

# 4. (opcional) Credenciais de API
cp .env.example .env         # depois edite o .env

# 5. Rodar
python app.py                # abre http://localhost:7860
```

> Dica: use sempre `python -m pip` (não só `pip`) para garantir que a
> instalação vá para o ambiente virtual ativo.

## 🔑 Credenciais (opcional)

Danbooru, Gelbooru, Safebooru e e621 funcionam **sem nada configurado**.
As demais fontes só aparecem se você preencher as chaves no `.env`
(copie de `.env.example`):

| Fonte | O que precisa | Onde obter |
|---|---|---|
| Danbooru | login + API key (opcional, sobe o limite para 200/pág) | conta gratuita em danbooru.donmai.us |
| Gelbooru | user_id + API key | My Account → Options → API Access |
| Tumblr | API key (+ OAuth para popularidade) | tumblr.com/oauth/apps |
| DeviantArt | client_id + secret | deviantart.com/developers |
| Bluesky | handle + app password | configurações do Bluesky |

O `.env` **nunca** é versionado (está no `.gitignore`).

## ⚠️ Segurança — leia antes de compartilhar

Este é um app **pessoal, para rodar na sua própria máquina**. Ele **não tem
login nem senha** e, por padrão, escuta em todas as interfaces de rede
(`0.0.0.0:7860`) para permitir acesso pelo celular no mesmo Wi-Fi.

Consequências importantes:

- **Qualquer pessoa na mesma rede** (Wi-Fi de casa, república, café) consegue
  abrir a interface e usar tudo — inclusive **apagar imagens** e **limpar o
  banco**. Só rode em redes em que você confia.
- **Nunca exponha a porta 7860 à internet** (não faça port-forward no roteador
  nem coloque atrás de um domínio público sem autenticação).
- Se quiser restringir só à sua máquina, troque o host no final do `app.py`
  de `"0.0.0.0"` para `"127.0.0.1"` — aí o celular deixa de acessar, mas
  ninguém na rede acessa também.

Proteções já embutidas: o proxy de imagens só aceita `http/https` e **bloqueia
endereços internos** (anti-SSRF), e nomes de artista/tags vindos das APIs são
**escapados** antes de irem para a tela (anti-XSS). Ainda assim, o modelo de
ameaça é "ferramenta de rede local confiável", não "serviço público".

## 🗂️ Estrutura

```
findArts/
├── app.py              # Servidor web (FastAPI) + todas as rotas da API
├── config.py           # Configurações; carrega segredos do .env
├── requirements.txt
├── .env.example        # Modelo de credenciais (copie para .env)
├── templates/
│   └── index.html      # Toda a interface (HTML + CSS + JS num arquivo só)
├── sources/            # Um módulo por plataforma (fetch_posts padronizado)
├── filters/            # Qualidade (resolução/tamanho) e cor dominante
├── utils/
│   ├── database.py     # SQLite: posts, downloads, favoritos, blacklist, ratings
│   ├── downloader.py   # Download assíncrono + pHash
│   └── gallery.py      # Gerador de galeria HTML estática (legado)
├── palettes/           # Paletas de cor em JSON
└── downloads/          # Imagens + banco (gerado; fora do git)
```

## ⚙️ Ajustes rápidos (`config.py`)

| Configuração | Descrição |
|---|---|
| `MIN_WIDTH` / `MIN_HEIGHT` | Resolução mínima aceita (padrão 800×600) |
| `MAX_DOWNLOAD_WORKERS` | Downloads simultâneos (padrão 8) |
| `USE_COLOR_FILTER` / `TARGET_COLORS` | Filtro opcional por cor dominante |
| `ORGANIZE_BY` | Organizar downloads por `"category"` ou `"artist"` |

## 📝 Licença

Uso pessoal. Respeite os Termos de Serviço de cada plataforma e os direitos
dos artistas — a ferramenta preserva o link original e o autor de cada arte
para facilitar creditar e apoiar quem criou.
