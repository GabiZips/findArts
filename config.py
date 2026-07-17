# ================================================================
# config.py — Configuração centralizada do Shadow & Rouge Art Finder
# ================================================================

import os
from pathlib import Path

# --- Carrega variáveis de um arquivo .env (se existir) ---
# Loader leve, sem dependência externa. Não sobrescreve variáveis já
# definidas no ambiente do sistema.
def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

_load_dotenv(Path(__file__).parent / ".env")

# --- Diretórios ---
# Sempre relativos à pasta do projeto (não ao cwd), para o app funcionar
# mesmo quando iniciado de outro diretório.
BASE_DIR     = Path(__file__).resolve().parent
DOWNLOAD_DIR = str(BASE_DIR / "downloads")
PALETTE_DIR  = str(BASE_DIR / "palettes")
DB_PATH      = str(BASE_DIR / "downloads" / "artfinder.db")

# ----------------------------------------------------------------
# FILTROS DE ARQUIVO (verificados antes/durante o download)
# ----------------------------------------------------------------
MIN_WIDTH       = 800
MIN_HEIGHT      = 600
MIN_FILE_KB     = 5
MAX_FILE_MB     = 100
ALLOWED_FORMATS = ["jpg", "jpeg", "png", "webp"]
SAFE_ONLY       = True        # True = somente SFW
MIN_SCORE       = 0           # 0 = sem mínimo de score/likes

# ----------------------------------------------------------------
# FILTROS DE COR (verificados após o download)
# ----------------------------------------------------------------

# Ativar/desativar o filtro de cor
USE_COLOR_FILTER = False

# Modo de comparação: "rgb" (mais rápido) ou "lab" (mais preciso perceptualmente)
COLOR_MODE = "rgb"

# Tolerância: quanto cada cor pode variar e ainda ser aceita
# 0 = exato, 80 = tolerante, 150 = muito flexível
COLOR_THRESHOLD = 80

# Quantas das cores-alvo precisam aparecer na paleta da imagem
# 1 = basta ter uma, 3 = precisa ter pelo menos 3
MIN_COLOR_MATCHES = 1

# Cores-alvo (em RGB). Deixe vazio [] para não filtrar por cor.
# Paleta padrão do Shadow: preto profundo, vermelho vivo, branco
TARGET_COLORS = [
    (15,  15,  15),    # preto profundo (corpo do Shadow)
    (180,  0,   0),    # vermelho vivo (detalhes)
    (240, 240, 240),   # branco (luvas, peito)
]

# Cores a EXCLUIR (imagem rejeitada se tiver estas cores como dominantes)
EXCLUDE_COLORS = []

# Filtro de brilho (0 = preto puro, 255 = branco puro)
BRIGHTNESS_MIN = 0
BRIGHTNESS_MAX = 255

# Saturação mínima (0.0 = escala de cinza, 1.0 = totalmente saturado)
SATURATION_MIN = 0.0

# ----------------------------------------------------------------
# FILTRO DE ORIENTAÇÃO
# ----------------------------------------------------------------
# Opções: "all", "landscape", "portrait", "square"
TARGET_ASPECT_RATIO = "all"

# ----------------------------------------------------------------
# CATEGORIAS E TAGS
# ----------------------------------------------------------------
CATEGORIES = ["shadow_solo", "rouge_solo", "shadow_rouge", "shadow_sonic"]

# ----------------------------------------------------------------
# CREDENCIAIS DE API
# ----------------------------------------------------------------

# Danbooru — conta em: https://danbooru.donmai.us
# My Account > Profile > API Key
DANBOORU_LOGIN   = os.getenv("DANBOORU_LOGIN",   "")
DANBOORU_API_KEY = os.getenv("DANBOORU_API_KEY", "")

# Tumblr — registrar em: https://www.tumblr.com/oauth/apps
# Para busca por POPULARIDADE (artes mais curtidas) rode: python setup_tumblr_oauth.py
TUMBLR_API_KEY            = os.getenv("TUMBLR_API_KEY",             "")
TUMBLR_CONSUMER_SECRET    = os.getenv("TUMBLR_CONSUMER_SECRET",     "")  # OAuth
TUMBLR_OAUTH_TOKEN        = os.getenv("TUMBLR_OAUTH_TOKEN",         "")  # OAuth
TUMBLR_OAUTH_TOKEN_SECRET = os.getenv("TUMBLR_OAUTH_TOKEN_SECRET",  "")  # OAuth

# Gelbooru — conta gratuita em: https://gelbooru.com
# My Account > Options > API Access Credentials
GELBOORU_USER_ID  = os.getenv("GELBOORU_USER_ID",  "")
GELBOORU_API_KEY  = os.getenv("GELBOORU_API_KEY",  "")

# Twitter/X — registrar em: https://developer.twitter.com
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")

# DeviantArt — registrar em: https://www.deviantart.com/developers/
# App pode ficar Unpublished para uso pessoal (client_credentials nao requer publicar)
DEVIANTART_CLIENT_ID     = os.getenv("DEVIANTART_CLIENT_ID",     "")
DEVIANTART_CLIENT_SECRET = os.getenv("DEVIANTART_CLIENT_SECRET", "")

# Pixiv — precisa de um refresh token (gere com: python get_pixiv_token.py)
PIXIV_REFRESH_TOKEN = os.getenv("PIXIV_REFRESH_TOKEN", "")


# ----------------------------------------------------------------
# RATE LIMITS (segundos entre requisições para cada API)
# ----------------------------------------------------------------
DANBOORU_DELAY   = 0.6
GELBOORU_DELAY   = 0.3
TUMBLR_DELAY     = 0.5
TWITTER_DELAY    = 2.0
ARTSTATION_DELAY = 1.0
DEVIANTART_DELAY = 0.5

# ----------------------------------------------------------------
# DOWNLOAD
# ----------------------------------------------------------------
# Número máximo de workers para download assíncrono
MAX_DOWNLOAD_WORKERS = 8

# Timeout em segundos para cada requisição HTTP
REQUEST_TIMEOUT = 30

# Como organizar as subpastas dentro de downloads/:
#   "category" = por tag/categoria (shadow_solo, rouge_solo, ...)  [padrão]
#   "artist"   = por artista (cheersonlyy, copperisbald, ...)
ORGANIZE_BY = "category"


# --- BLUESKY CONFIGURATION ---
BSKY_HANDLE   = os.getenv("BSKY_HANDLE", "")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD", "")
BSKY_DELAY    = 1.0
