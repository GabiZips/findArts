# ADR-0003: Mobile implementation strategy

**Status:** Accepted
**Date:** 2026-08-21
**Decider:** Project maintainer

## Context

ArtFinder's desktop application remains implemented in Python. The former
Android package embedded that code with python-for-android and opened the HTML
interface in a local WebView. Dependency failures, lifecycle behavior, inset
handling and camera integration made that package unreliable on real devices.

The application also stores provider credentials and artwork metadata locally.
Moving the Python backend to a public server would add hosting cost, a new
security boundary and responsibility for other users' credentials.

## Decision

- Do not move provider credentials or the search backend to a hosted service by
  default.
- Maintain Android as a native Kotlin and Jetpack Compose client with one
  activity, unidirectional UI state, repositories for persistence/search and
  provider-specific source clients.
- Port the eight source connectors to Kotlin instead of embedding Python or
  Chaquopy. Keep the category and source-tag data contract compatible with the
  desktop pairing protocol.
- Store credentials with an Android Keystore-backed encryption key, download
  through MediaStore and scan QR codes with CameraX and the bundled ML Kit
  barcode model.
- Support Android 10 through 16 with `minSdk 29` and `targetSdk 36`.
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

**Disadvantages:** introduces a fragile cross-language boundary and still ships
a large Python runtime. Rejected after the native ports remained small enough
to test independently.

### Native Kotlin/Compose client (chosen)

**Advantages:** conventional Android lifecycle, edge-to-edge layout, camera,
MediaStore and secure local credential storage without Python packaging.

**Disadvantages:** provider connector fixes must sometimes be applied once in
Python and once in Kotlin. Contract tests and explicit tag overrides reduce the
risk of divergence.

### Flutter rewrite

**Advantages:** one modern UI can target Android, iOS, Windows and Linux.

**Disadvantages:** the Python connectors and business logic cannot be reused
directly across every target. A rewrite or remote backend would be required.

## Consequences

- Android builds run Kotlin unit tests, lint, R8, APK metadata inspection and
  stable signing-certificate verification before publication.
- The old Buildozer files remain only as migration history and are not used by
  the release workflow.
- Desktop and Android share configuration over the existing local encrypted
  pairing protocol, not by sharing executable code or sending secrets to a
  cloud service.
- Supporting iOS natively remains a separate future decision requiring macOS,
  Xcode and Apple signing.
