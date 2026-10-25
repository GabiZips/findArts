(() => {
  "use strict";

  const BLUR_KEY = "artfinder.blurNsfw";
  const revealedIds = new Set(); // Memory only; never synchronize or persist.
  const cards = '.card,.gal-card,.cmp-item';
  const zoom = { scale: 1, x: 0, y: 0, dragging: false, px: 0, py: 0 };

  function image() { return document.getElementById("lbImg"); }

  function applyZoom() {
    const img = image();
    if (!img) return;
    img.style.transform = `translate(${zoom.x}px, ${zoom.y}px) scale(${zoom.scale})`;
    img.style.cursor = zoom.scale > 1 ? (zoom.dragging ? "grabbing" : "grab") : "default";
    const label = document.getElementById("lbZoomLabel");
    if (label) label.textContent = `${Math.round(zoom.scale * 100)}%`;
  }

  function clampOffset() {
    const stage = document.getElementById("lbMediaStage");
    const img = image();
    if (!stage || !img || zoom.scale <= 1) {
      zoom.x = 0;
      zoom.y = 0;
      return;
    }
    const maxX = Math.max(0, (img.clientWidth * zoom.scale - stage.clientWidth) / 2);
    const maxY = Math.max(0, (img.clientHeight * zoom.scale - stage.clientHeight) / 2);
    zoom.x = Math.max(-maxX, Math.min(maxX, zoom.x));
    zoom.y = Math.max(-maxY, Math.min(maxY, zoom.y));
  }

  window.resetLbZoom = function resetLbZoom() {
    zoom.scale = 1;
    zoom.x = 0;
    zoom.y = 0;
    applyZoom();
  };

  window.lbZoomBy = function lbZoomBy(delta) {
    zoom.scale = Math.max(1, Math.min(6, zoom.scale + delta));
    clampOffset();
    applyZoom();
  };

  window.setNsfwBlur = function setNsfwBlur(enabled) {
    // Turning protection back on must hide previously revealed artwork too.
    if (enabled) {
      revealedIds.clear();
      document.getElementById('lbVideo')?.pause?.();
      document.querySelectorAll(".nsfw-revealed").forEach(element => {
        element.classList.remove("nsfw-revealed");
      });
    }
    document.body.classList.toggle("no-nsfw-blur", !enabled);
    const toggle = document.getElementById("globalBlurToggle");
    if (toggle) toggle.checked = enabled;
    try { localStorage.setItem(BLUR_KEY, enabled ? "1" : "0"); } catch (_) {}
  };

  window.revealNsfwCard = function revealNsfwCard(button) {
    const card = button.closest(cards);
    if (!card) return;
    setRevealed(card.dataset.uid, true);
    card.querySelector?.('.nsfw-hide')?.focus?.({preventScroll: true});
  };

  window.hideNsfwCard = function hideNsfwCard(button) {
    const card = button.closest(cards);
    if (!card) return;
    setRevealed(card.dataset.uid, false);
    card.querySelector?.('.nsfw-reveal')?.focus?.({preventScroll: true});
  };

  window.syncNsfwCards = function syncNsfwCards(root = document) {
    const found = Array.from(root.querySelectorAll(cards));
    if (root.matches?.(cards)) found.push(root);
    found.forEach(card => card.classList.toggle('nsfw-revealed', revealedIds.has(card.dataset.uid)));
  };

  function setRevealed(uid, revealed) {
    if (!uid) return;
    if (revealed) revealedIds.add(uid); else revealedIds.delete(uid);
    window.syncNsfwCards();
    const lightbox = document.getElementById('lightbox');
    if (lightbox?.dataset.uid === uid) {
      lightbox.classList.toggle('nsfw-revealed', revealed);
      if (!revealed) {
        document.getElementById('lbVideo')?.pause?.();
        window.resetLbZoom();
      }
    }
  }

  window.setLightboxNsfw = function setLightboxNsfw(enabled, uid = "") {
    const lightbox = document.getElementById("lightbox");
    if (!lightbox) return;
    lightbox.classList.toggle("nsfw-blur", enabled);
    lightbox.dataset.uid = uid;
    lightbox.classList.toggle("nsfw-revealed", enabled && revealedIds.has(uid));
  };

  window.revealLightboxNsfw = function revealLightboxNsfw() {
    const lightbox = document.getElementById("lightbox");
    if (!lightbox) return;
    setRevealed(lightbox.dataset.uid, true);
    document.getElementById('lbNsfwHide')?.focus?.({preventScroll: true});
  };

  window.hideLightboxNsfw = function hideLightboxNsfw() {
    setRevealed(document.getElementById('lightbox')?.dataset.uid, false);
    document.getElementById('lbNsfwReveal')?.focus?.({preventScroll: true});
  };

  document.addEventListener("DOMContentLoaded", () => {
    let enabled = true;
    try { enabled = localStorage.getItem(BLUR_KEY) !== "0"; } catch (_) {}
    window.setNsfwBlur(enabled);

    // Native details provides keyboard activation; capture also handles cards
    // whose individual controls stop click propagation.
    document.addEventListener('click', event => {
      document.querySelectorAll('.art-menu[open]').forEach(menu => {
        if (!menu.contains(event.target)) menu.removeAttribute('open');
      });
    }, true);
    document.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      const menu = document.querySelector('.art-menu[open]');
      if (!menu) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      menu.removeAttribute('open');
      menu.querySelector('summary')?.focus();
    }, true);

    const stage = document.getElementById("lbMediaStage");
    const img = image();
    if (!stage || !img) return;

    const video = document.getElementById('lbVideo');
    video?.addEventListener('error', () => {
      if (video.getAttribute('src') && document.getElementById('lightbox')?.classList.contains('open')) {
        toast(t('Não foi possível reproduzir o vídeo. Tente abrir na fonte.'), 'error');
      }
    });

    stage.addEventListener("wheel", event => {
      if (img.style.display === "none") return;
      event.preventDefault();
      window.lbZoomBy(event.deltaY < 0 ? .25 : -.25);
    }, { passive: false });

    stage.addEventListener("dblclick", event => {
      event.stopPropagation();
      if (event.target.closest?.('button')) return;
      if (zoom.scale > 1) window.resetLbZoom(); else window.lbZoomBy(1);
    });

    stage.addEventListener("pointerdown", event => {
      if (zoom.scale <= 1 || event.target !== img) return;
      zoom.dragging = true;
      zoom.px = event.clientX;
      zoom.py = event.clientY;
      stage.setPointerCapture(event.pointerId);
      applyZoom();
    });
    stage.addEventListener("pointermove", event => {
      if (!zoom.dragging) return;
      zoom.x += event.clientX - zoom.px;
      zoom.y += event.clientY - zoom.py;
      zoom.px = event.clientX;
      zoom.py = event.clientY;
      clampOffset();
      applyZoom();
    });
    const stopDrag = event => {
      if (!zoom.dragging) return;
      zoom.dragging = false;
      if (stage.hasPointerCapture(event.pointerId)) stage.releasePointerCapture(event.pointerId);
      applyZoom();
    };
    stage.addEventListener("pointerup", stopDrag);
    stage.addEventListener("pointercancel", stopDrag);
  });
})();
