# ADR-0001: Shared web UI with platform-specific packages

**Status:** Superseded by ADR-0003
**Date:** 2026-08-06  
**Decider:** Project maintainer

## Context

ArtFinder already has a FastAPI backend, a responsive HTML/JavaScript interface
and a pywebview Windows launcher. The project needs Portuguese and English UI,
Linux distribution and a mobile application without maintaining three separate
search/download implementations.

## Decision

Keep FastAPI and the web interface as the shared application core.

- Windows: pywebview + PyInstaller `.exe`.
- Linux: pywebview with PySide6 + PyInstaller inside an AppImage.
- Android: this ADR originally selected a python-for-Android WebView package;
  ADR-0003 replaces that choice with a native Kotlin/Compose client.
- iOS: deferred until a macOS/Xcode build and an iOS-specific bridge can be
  maintained and tested.
- Localization: one runtime dictionary shared by browser, desktop and mobile.

All packages keep credentials and personal data outside bundled resources and
bind their internal HTTP server to loopback only.

## Options considered

### Rewrite in Flutter or another mobile-first toolkit

This would provide a conventional mobile UI but require rewriting every screen,
source integration, downloader and persistence flow. It was rejected for the
initial multiplatform release because of the high duplication and regression
risk.

### Thin mobile client connected to a hosted backend

This would produce a smaller APK, but introduces hosting costs and would move
credentials and downloaded artwork to a remote service. It was rejected to
preserve ArtFinder's local-first model.

### Shared local Python backend and WebView (chosen)

This maximizes reuse and keeps data local. The trade-off is larger packages and
more complex Android dependency builds.

## Consequences

- Search behavior, tags and fixes remain consistent across platforms.
- Each operating system still needs its own build and test job.
- Linux must be built on Linux; Windows artifacts cannot be converted.
- Android needs physical-device validation, scoped-storage export and lifecycle
  testing before it can be called stable.
- iOS remains a separate future project because Android packages cannot run on
  iPhone.
