# utils/gallery.py
"""
Gerador de galeria HTML estática com layout Masonry (estilo Pinterest).
Varre as pastas de download e gera um arquivo gallery.html navegável.

Funcionalidades:
- Layout de 4 colunas responsivo (2 colunas no mobile)
- Filtros por categoria e fonte
- Badge com fonte e artista
- Link para a arte original
- Lightbox para visualização em tela cheia
"""

import json
import os
from pathlib import Path
from datetime import datetime

from config import DOWNLOAD_DIR

# Mapeamento de categorias para ícones/labels
CATEGORY_META = {
    "shadow_solo":  {"icon": "🖤", "label": "Shadow Solo"},
    "rouge_solo":   {"icon": "🦇", "label": "Rouge Solo"},
    "shadow_rouge": {"icon": "🖤🦇", "label": "Shadow & Rouge"},
    "shadow_sonic": {"icon": "🖤💙", "label": "Shadow & Sonic"},
}

SOURCE_COLORS = {
    "danbooru":   "#f06",
    "gelbooru":   "#0af",
    "tumblr":     "#36465d",
    "bluesky":    "#0085ff",
    "artstation": "#13aff0",
    "deviantart": "#05cc47",
    "twitter":    "#1da1f2",
    "reddit":     "#ff4500",
}

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🦔 Shadow & Rouge Art Finder — Galeria</title>
  <meta name="description" content="Galeria local de fan art de Shadow the Hedgehog e Rouge the Bat">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg:        #0d0d0f;
      --surface:   #16161a;
      --surface2:  #1f1f26;
      --accent:    #e02060;
      --accent2:   #6030d0;
      --text:      #e8e8f0;
      --muted:     #888899;
      --radius:    14px;
      --gap:       14px;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}

    /* ── Header ── */
    header {{
      background: linear-gradient(135deg, #1a0a20 0%, #0d0d1f 50%, #10101a 100%);
      border-bottom: 1px solid #ffffff10;
      padding: 28px 32px;
      display: flex;
      align-items: center;
      gap: 20px;
      position: sticky;
      top: 0;
      z-index: 100;
      backdrop-filter: blur(20px);
    }}

    .header-title {{
      font-size: 1.5rem;
      font-weight: 700;
      background: linear-gradient(90deg, #e02060, #a030f0);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .header-sub {{
      font-size: 0.78rem;
      color: var(--muted);
      margin-top: 2px;
    }}

    .header-stats {{
      margin-left: auto;
      text-align: right;
      font-size: 0.8rem;
      color: var(--muted);
    }}

    .header-stats strong {{
      color: var(--text);
      font-size: 1.1rem;
    }}

    /* ── Filters bar ── */
    .filters {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      padding: 20px 32px;
      background: var(--surface);
      border-bottom: 1px solid #ffffff08;
    }}

    .filter-group {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .filter-label {{
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      padding: 6px 0;
      margin-right: 4px;
    }}

    .filter-btn {{
      padding: 6px 14px;
      border-radius: 999px;
      border: 1px solid #ffffff18;
      background: var(--surface2);
      color: var(--muted);
      font-size: 0.8rem;
      cursor: pointer;
      transition: all 0.18s;
      font-family: 'Inter', sans-serif;
    }}

    .filter-btn:hover,
    .filter-btn.active {{
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }}

    /* ── Gallery ── */
    .gallery-wrap {{
      padding: 28px 32px;
    }}

    .gallery-container {{
      column-count: 4;
      column-gap: var(--gap);
    }}

    @media (max-width: 1200px) {{ .gallery-container {{ column-count: 3; }} }}
    @media (max-width: 800px)  {{ .gallery-container {{ column-count: 2; }} }}
    @media (max-width: 480px)  {{ .gallery-container {{ column-count: 1; }} }}

    .gallery-item {{
      break-inside: avoid;
      margin-bottom: var(--gap);
      border-radius: var(--radius);
      background: var(--surface);
      overflow: hidden;
      border: 1px solid #ffffff08;
      transition: transform 0.22s cubic-bezier(.34,1.56,.64,1), box-shadow 0.22s;
      cursor: pointer;
      position: relative;
    }}

    .gallery-item:hover {{
      transform: translateY(-4px) scale(1.01);
      box-shadow: 0 20px 60px rgba(0,0,0,0.6);
      z-index: 2;
    }}

    .gallery-item img {{
      width: 100%;
      display: block;
      object-fit: cover;
    }}

    .gallery-meta {{
      padding: 10px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
    }}

    .source-badge {{
      font-size: 0.68rem;
      font-weight: 600;
      padding: 3px 9px;
      border-radius: 999px;
      color: #fff;
      letter-spacing: 0.04em;
      text-transform: capitalize;
    }}

    .artist-name {{
      font-size: 0.72rem;
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      flex: 1;
      text-align: right;
    }}

    .score-badge {{
      font-size: 0.68rem;
      color: var(--muted);
    }}

    .open-link {{
      position: absolute;
      inset: 0;
      z-index: 1;
    }}

    /* ── Empty state ── */
    .empty {{
      text-align: center;
      padding: 80px 32px;
      color: var(--muted);
    }}

    .empty h2 {{ font-size: 1.3rem; margin-bottom: 8px; color: var(--text); }}
    .empty p  {{ font-size: 0.9rem; }}

    /* ── Lightbox ── */
    #lightbox {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.92);
      z-index: 999;
      cursor: zoom-out;
      justify-content: center;
      align-items: center;
    }}
    #lightbox.open {{ display: flex; }}
    #lightbox img {{
      max-width: 90vw;
      max-height: 90vh;
      border-radius: 8px;
      box-shadow: 0 40px 120px rgba(0,0,0,0.8);
      object-fit: contain;
    }}
    #lightbox-close {{
      position: absolute;
      top: 20px; right: 28px;
      font-size: 2rem;
      color: #fff;
      cursor: pointer;
      opacity: 0.7;
      transition: opacity 0.15s;
    }}
    #lightbox-close:hover {{ opacity: 1; }}
  </style>
</head>
<body>

<header>
  <div>
    <div class="header-title">🦔 Shadow & Rouge Art Finder</div>
    <div class="header-sub">Galeria gerada em {generated_at}</div>
  </div>
  <div class="header-stats">
    <strong>{total_images}</strong> imagens
  </div>
</header>

<div class="filters">
  <span class="filter-label">Categoria:</span>
  <div class="filter-group" id="cat-filters">
    <button class="filter-btn active" data-cat="all" onclick="filterGallery()">Todas</button>
    {category_buttons}
  </div>
  <span class="filter-label" style="margin-left:16px">Fonte:</span>
  <div class="filter-group" id="src-filters">
    <button class="filter-btn active" data-src="all" onclick="filterGallery()">Todas</button>
    {source_buttons}
  </div>
</div>

<div class="gallery-wrap">
  <div class="gallery-container" id="gallery">
    {gallery_items}
  </div>
  <div class="empty" id="empty-state" style="display:none">
    <h2>Nenhuma imagem encontrada</h2>
    <p>Tente outros filtros ou execute o script para baixar mais artes.</p>
  </div>
</div>

<!-- Lightbox -->
<div id="lightbox">
  <span id="lightbox-close" onclick="closeLightbox()">✕</span>
  <img id="lightbox-img" src="" alt="Arte em tela cheia">
</div>

<script>
  let activeCat = 'all';
  let activeSrc = 'all';

  function filterGallery() {{
    const catBtns = document.querySelectorAll('#cat-filters .filter-btn');
    const srcBtns = document.querySelectorAll('#src-filters .filter-btn');

    catBtns.forEach(b => {{ if (b.classList.contains('active')) activeCat = b.dataset.cat; }});
    srcBtns.forEach(b => {{ if (b.classList.contains('active')) activeSrc = b.dataset.src; }});

    const items = document.querySelectorAll('.gallery-item');
    let visible = 0;
    items.forEach(item => {{
      const matchCat = activeCat === 'all' || item.dataset.cat === activeCat;
      const matchSrc = activeSrc === 'all' || item.dataset.src === activeSrc;
      item.style.display = (matchCat && matchSrc) ? '' : 'none';
      if (matchCat && matchSrc) visible++;
    }});

    document.getElementById('empty-state').style.display = visible === 0 ? '' : 'none';
  }}

  // Toggle de filtros (só um ativo por vez em cada grupo)
  document.querySelectorAll('.filter-btn').forEach(btn => {{
    btn.addEventListener('click', function() {{
      const group = this.closest('.filter-group');
      group.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      filterGallery();
    }});
  }});

  // Lightbox
  function openLightbox(src) {{
    document.getElementById('lightbox-img').src = src;
    document.getElementById('lightbox').classList.add('open');
  }}

  function closeLightbox() {{
    document.getElementById('lightbox').classList.remove('open');
    document.getElementById('lightbox-img').src = '';
  }}

  document.getElementById('lightbox').addEventListener('click', function(e) {{
    if (e.target === this) closeLightbox();
  }});

  document.addEventListener('keydown', e => {{
    if (e.key === 'Escape') closeLightbox();
  }});
</script>
</body>
</html>
"""

ITEM_TEMPLATE = """\
<div class="gallery-item" data-cat="{category}" data-src="{source}">
  <img src="{rel_path}" alt="{alt}" loading="lazy" onclick="openLightbox('{rel_path}')">
  <div class="gallery-meta">
    <span class="source-badge" style="background:{source_color}">{source}</span>
    <span class="artist-name" title="{artist}">{artist_display}</span>
    <span class="score-badge">⭐ {score}</span>
  </div>
  {open_link}
</div>
"""


def build_gallery(output_path: str = None) -> str:
    """
    Varre o diretório de downloads e gera o arquivo gallery.html.

    Args:
        output_path: caminho do HTML de saída (padrão: DOWNLOAD_DIR/gallery.html)

    Returns:
        Caminho do arquivo gerado
    """
    if output_path is None:
        output_path = str(Path(DOWNLOAD_DIR) / "gallery.html")

    download_root = Path(DOWNLOAD_DIR)
    items_html = []
    total = 0
    seen_sources: set[str] = set()
    seen_categories: set[str] = set()

    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    for cat_dir in sorted(download_root.iterdir()):
        if not cat_dir.is_dir():
            continue
        category = cat_dir.name
        if category.startswith(".") or category in ("matched_colors", "metadata"):
            continue

        for img_path in sorted(cat_dir.iterdir()):
            if img_path.suffix.lower() not in image_exts:
                continue

            # Carregar metadados: o downloader salva em metadata/<categoria>/<nome>.json
            # (fallback: JSON ao lado da imagem, formato antigo)
            meta_path = download_root / "metadata" / category / (img_path.stem + ".json")
            if not meta_path.exists():
                meta_path = img_path.with_suffix(".json")
            meta: dict = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

            source  = meta.get("source", img_path.stem.split("_")[0])
            artist  = meta.get("artist", "")
            score   = meta.get("score", 0)
            orig_url = meta.get("url", "")

            # Caminho relativo ao HTML
            rel_path = os.path.relpath(str(img_path), str(download_root)).replace("\\", "/")

            source_color = SOURCE_COLORS.get(source, "#666")
            artist_display = artist[:20] + "…" if len(artist) > 20 else artist
            alt = f"{category} art by {artist or 'unknown'}"

            open_link = f'<a class="open-link" href="{orig_url}" target="_blank" title="Ver original"></a>' if orig_url else ""

            items_html.append(ITEM_TEMPLATE.format(
                category=category,
                source=source,
                rel_path=rel_path,
                alt=alt,
                source_color=source_color,
                artist=artist,
                artist_display=artist_display or "—",
                score=score,
                open_link=open_link,
            ))

            seen_sources.add(source)
            seen_categories.add(category)
            total += 1

    # Botões de filtro
    cat_btns = ""
    for cat in sorted(seen_categories):
        meta_cat = CATEGORY_META.get(cat, {"icon": "🖼️", "label": cat})
        cat_btns += (
            f'<button class="filter-btn" data-cat="{cat}" onclick="filterGallery()">'
            f'{meta_cat["icon"]} {meta_cat["label"]}</button>\n    '
        )

    src_btns = ""
    for src in sorted(seen_sources):
        color = SOURCE_COLORS.get(src, "#666")
        src_btns += (
            f'<button class="filter-btn" data-src="{src}" onclick="filterGallery()"'
            f' style="border-color:{color}40">{src.capitalize()}</button>\n    '
        )

    html = HTML_TEMPLATE.format(
        generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
        total_images=total,
        category_buttons=cat_btns,
        source_buttons=src_btns,
        gallery_items="\n    ".join(items_html) if items_html else "",
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html, encoding="utf-8")

    print(f"  [OK] Galeria gerada: {output_path} ({total} imagens)")
    return output_path
