(() => {
  "use strict";

  const BLUR_KEY = "artfinder.blurNsfw";
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
    document.body.classList.toggle("no-nsfw-blur", !enabled);
    const toggle = document.getElementById("globalBlurToggle");
    if (toggle) toggle.checked = enabled;
    try { localStorage.setItem(BLUR_KEY, enabled ? "1" : "0"); } catch (_) {}
  };

  window.revealNsfwCard = function revealNsfwCard(button) {
    button.closest(".card,.gal-card")?.classList.add("nsfw-revealed");
  };

  window.setLightboxNsfw = function setLightboxNsfw(enabled) {
    const lightbox = document.getElementById("lightbox");
    if (!lightbox) return;
    lightbox.classList.toggle("nsfw-blur", enabled);
    lightbox.classList.remove("nsfw-revealed");
  };

  window.revealLightboxNsfw = function revealLightboxNsfw() {
    document.getElementById("lightbox")?.classList.add("nsfw-revealed");
  };

  document.addEventListener("DOMContentLoaded", () => {
    let enabled = true;
    try { enabled = localStorage.getItem(BLUR_KEY) !== "0"; } catch (_) {}
    window.setNsfwBlur(enabled);

    const stage = document.getElementById("lbMediaStage");
    const img = image();
    if (!stage || !img) return;

    stage.addEventListener("wheel", event => {
      if (img.style.display === "none") return;
      event.preventDefault();
      window.lbZoomBy(event.deltaY < 0 ? .25 : -.25);
    }, { passive: false });

    stage.addEventListener("dblclick", event => {
      event.stopPropagation();
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
