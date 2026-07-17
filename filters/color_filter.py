# filters/color_filter.py
"""
Filtro de cor dominante para imagens.
Suporta comparação em espaço RGB (rápido) ou CIE LAB (mais preciso perceptualmente).
"""

import math
from io import BytesIO
from typing import Optional

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    from colorthief import ColorThief
    _COLORTHIEF_AVAILABLE = True
except ImportError:
    _COLORTHIEF_AVAILABLE = False

from config import (
    COLOR_THRESHOLD,
    MIN_COLOR_MATCHES,
    TARGET_COLORS,
    EXCLUDE_COLORS,
    BRIGHTNESS_MIN,
    BRIGHTNESS_MAX,
    SATURATION_MIN,
    COLOR_MODE,
    USE_COLOR_FILTER,
)


# ----------------------------------------------------------------
# DISTÂNCIA ENTRE CORES
# ----------------------------------------------------------------

def rgb_distance(c1: tuple, c2: tuple) -> float:
    """Distância euclidiana no espaço RGB (0–441)."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def lab_distance(c1: tuple, c2: tuple) -> float:
    """
    Distância perceptual no espaço CIE LAB usando Delta E CIE2000.
    Requer a biblioteca `colormath`. Faz fallback para RGB se ausente.
    """
    try:
        from colormath.color_objects import sRGBColor, LabColor
        from colormath.color_conversions import convert_color
        from colormath.color_diff import delta_e_cie2000

        rgb1 = sRGBColor(c1[0] / 255, c1[1] / 255, c1[2] / 255)
        rgb2 = sRGBColor(c2[0] / 255, c2[1] / 255, c2[2] / 255)
        lab1 = convert_color(rgb1, LabColor)
        lab2 = convert_color(rgb2, LabColor)
        return float(delta_e_cie2000(lab1, lab2))
    except Exception:
        # ImportError (colormath ausente) OU AttributeError — colormath 3.0
        # usa numpy.asscalar, removido no numpy >= 1.23. Fallback para RGB.
        return rgb_distance(c1, c2)


def color_distance(c1: tuple, c2: tuple) -> float:
    """Escolhe o modo de comparação de acordo com COLOR_MODE."""
    if COLOR_MODE == "lab":
        return lab_distance(c1, c2)
    return rgb_distance(c1, c2)


# ----------------------------------------------------------------
# EXTRAÇÃO DE PALETA
# ----------------------------------------------------------------

def extract_palette(
    image_path: Optional[str] = None,
    image_data: Optional[bytes] = None,
    n_colors: int = 8,
) -> list[tuple]:
    """
    Extrai as N cores dominantes de uma imagem usando ColorThief.

    Args:
        image_path: caminho para o arquivo de imagem (opcional)
        image_data: bytes da imagem (opcional, tem prioridade)
        n_colors: quantas cores extrair

    Returns:
        Lista de tuplas RGB, ex: [(15, 15, 15), (180, 0, 0), ...]
    """
    if not _COLORTHIEF_AVAILABLE:
        print("  [ColorFilter] colorthief não instalado. Instale com: pip install colorthief")
        return []

    try:
        if image_data:
            ct = ColorThief(BytesIO(image_data))
        elif image_path:
            ct = ColorThief(image_path)
        else:
            return []

        palette = ct.get_palette(color_count=n_colors, quality=3)
        return palette or []
    except Exception as e:
        print(f"  [ColorFilter] Erro ao extrair paleta: {e}")
        return []


# ----------------------------------------------------------------
# ANÁLISE DE BRILHO E SATURAÇÃO
# ----------------------------------------------------------------

def image_brightness(image_path: Optional[str] = None, image_data: Optional[bytes] = None) -> float:
    """Retorna o brilho médio da imagem (0–255)."""
    if not _PIL_AVAILABLE:
        return 128.0

    try:
        if image_data:
            img = Image.open(BytesIO(image_data)).convert("L")
        else:
            img = Image.open(image_path).convert("L")

        pixels = list(img.getdata())
        return sum(pixels) / len(pixels)
    except Exception:
        return 128.0


def image_saturation(image_path: Optional[str] = None, image_data: Optional[bytes] = None) -> float:
    """Retorna a saturação média da imagem (0.0–1.0)."""
    if not _PIL_AVAILABLE:
        return 0.5

    try:
        if image_data:
            img = Image.open(BytesIO(image_data)).convert("HSV")
        else:
            img = Image.open(image_path).convert("HSV")

        pixels = list(img.getdata())
        # Canal S está em 0–255; normalizar para 0.0–1.0
        return sum(p[1] for p in pixels) / (len(pixels) * 255)
    except Exception:
        return 0.5


# ----------------------------------------------------------------
# FILTRO PRINCIPAL
# ----------------------------------------------------------------

def passes_color_filter(
    image_path: Optional[str] = None,
    image_data: Optional[bytes] = None,
) -> bool:
    """
    Verifica se a imagem passa nos filtros de cor configurados.

    Lógica:
    1. Extrai paleta dominante (top 8 cores)
    2. Conta quantas TARGET_COLORS estão presentes (dentro do threshold)
    3. Verifica se alguma EXCLUDE_COLOR está presente
    4. Verifica brilho e saturação médios

    Returns:
        True se a imagem passa em todos os filtros, False caso contrário.
    """
    if not USE_COLOR_FILTER:
        return True

    palette = extract_palette(image_path=image_path, image_data=image_data)
    if not palette:
        return True     # sem paleta = não filtra (evita falsos negativos)

    # --- Verificar cores-alvo ---
    if TARGET_COLORS:
        matches = 0
        for target in TARGET_COLORS:
            for palette_color in palette:
                if color_distance(target, palette_color) <= COLOR_THRESHOLD:
                    matches += 1
                    break  # essa target_color já foi encontrada

        if matches < MIN_COLOR_MATCHES:
            return False

    # --- Verificar cores excluídas ---
    for exc in EXCLUDE_COLORS:
        for palette_color in palette:
            if color_distance(exc, palette_color) <= COLOR_THRESHOLD:
                return False   # cor indesejada encontrada

    # --- Verificar brilho ---
    if BRIGHTNESS_MIN > 0 or BRIGHTNESS_MAX < 255:
        brightness = image_brightness(image_path=image_path, image_data=image_data)
        if not (BRIGHTNESS_MIN <= brightness <= BRIGHTNESS_MAX):
            return False

    # --- Verificar saturação ---
    if SATURATION_MIN > 0:
        saturation = image_saturation(image_path=image_path, image_data=image_data)
        if saturation < SATURATION_MIN:
            return False

    return True
