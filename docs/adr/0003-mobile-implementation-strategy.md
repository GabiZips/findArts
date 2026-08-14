# ADR-0003: Mobile implementation strategy

**Status:** Proposed
**Date:** 2026-08-14
**Decider:** Project maintainer

## Context

ArtFinder's search connectors, filtering, database and download behavior are
implemented in Python. The experimental Android package currently embeds that
code with python-for-android and opens the existing HTML interface in a local
WebView. This maximizes reuse, but Android dependency packaging and lifecycle
behavior are less predictable than in a conventional Android project.

The application also stores provider credentials and artwork metadata locally.
Moving the Python backend to a public server would add hosting cost, a new
security boundary and responsibility for other users' credentials.

## Proposed decision

- Keep the python-for-android package as an experimental path while the current
  startup, dependency and storage behavior is stabilized.
- Do not move provider credentials or the search backend to a hosted service by
  default.
- For a production-quality Android application, create a native Kotlin and
  Jetpack Compose shell. Initially reuse the Python search core through
  Chaquopy, with an explicit interface between the native UI and Python.
- Consider Flutter only if shipping Android and iOS from one UI codebase becomes
  an immediate requirement. That path requires replacing or separately hosting
  most of the current Python application core.

## Options considered

### Continue only with python-for-android

**Advantages:** smallest change and maximum reuse of the current application.

**Disadvantages:** fragile transitive dependency packaging, WebView-oriented UI
and weaker integration with Android lifecycle, storage and sharing APIs.

### Kotlin/Compose with an embedded Python core

**Advantages:** native Android UI and lifecycle while retaining the existing
connectors and local credential model.

**Disadvantages:** introduces a Kotlin project and a cross-language boundary;
Android remains a separate UI from desktop.

### Flutter rewrite

**Advantages:** one modern UI can target Android, iOS, Windows and Linux.

**Disadvantages:** the Python connectors and business logic cannot be reused
directly across every target. A rewrite or remote backend would be required.

## Consequences

- The current APK remains explicitly experimental.
- Android packaging tests must inspect the actual Python runtime bundle, not
  only verify that an APK file was generated.
- A native mobile migration can happen incrementally without blocking desktop
  releases or moving personal credentials to a server.
- Supporting iOS natively remains a separate future decision requiring macOS,
  Xcode and Apple signing.
