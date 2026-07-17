# filters/quality.py
"""
Filtros de qualidade de arquivo — resolução, tamanho e formato.
Aplicados tanto antes (via metadados da API) quanto após o download.
"""

from config import MIN_WIDTH, MIN_HEIGHT, MIN_FILE_KB, MAX_FILE_MB, ALLOWED_FORMATS, TARGET_ASPECT_RATIO


def passes_resolution(width: int, height: int) -> bool:
    """Verifica se as dimensões atendem ao mínimo configurado."""
    if width and height:
        return width >= MIN_WIDTH and height >= MIN_HEIGHT
    return True     # dimensões desconhecidas: passa (vai verificar depois)


def passes_aspect_ratio(width: int, height: int) -> bool:
    """Verifica se a proporção (landscape/portrait/square) é a desejada."""
    if TARGET_ASPECT_RATIO == "all" or not (width and height):
        return True

    ratio = width / height
    if TARGET_ASPECT_RATIO == "landscape":
        return ratio >= 1.2
    if TARGET_ASPECT_RATIO == "portrait":
        return ratio <= (1 / 1.2)
    if TARGET_ASPECT_RATIO == "square":
        return 0.83 <= ratio <= 1.2     # ±20%
    return True


def passes_format(url: str) -> bool:
    """Verifica se a extensão do arquivo está na lista de formatos permitidos."""
    ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_FORMATS


def passes_file_size(size_bytes: int) -> bool:
    """Verifica se o tamanho do arquivo está dentro dos limites configurados."""
    if size_bytes <= 0:
        return True     # tamanho desconhecido: passa

    size_kb = size_bytes / 1024
    size_mb = size_kb / 1024
    return MIN_FILE_KB <= size_kb and size_mb <= MAX_FILE_MB


def passes_all_pre_download(post: dict) -> bool:
    """
    Verificações rápidas antes de baixar (usando metadados da API).
    Evita downloads desnecessários.
    """
    w = post.get("width", 0)
    h = post.get("height", 0)
    url = post.get("url", "")

    if not passes_resolution(w, h):
        return False
    if not passes_aspect_ratio(w, h):
        return False
    if url and not passes_format(url):
        return False
    return True
