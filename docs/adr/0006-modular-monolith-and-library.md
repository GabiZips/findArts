# ADR 0006: Modular monolith and artwork library

- Status: Accepted
- Date: 2026-08-24

## Context

ArtFinder ships the same product as a Python desktop executable and a native Android application. The desktop entry point and its HTML currently contain several unrelated responsibilities, while Android already has useful data and UI boundaries but treats saving to the app and downloading to the device as one operation.

The next features need one consistent product model:

- AI-generated artwork is always excluded and is not a user option.
- NSFW blur is a persistent display preference, independent from whether NSFW results are included in a search.
- Opening artwork uses an in-app viewer with zoom; opening the source remains a separate action.
- Keeping artwork in the ArtFinder library does not download it. Downloading writes a copy to the operating-system gallery.
- Collections organize kept artwork without duplicating image files.

The application must remain easy to package as one desktop executable, one AppImage and one APK. A service split would add deployment and account requirements without solving a current need.

## Decision

ArtFinder remains a modular monolith on each platform.

New behavior is implemented in vertical slices with explicit model, repository/service and UI boundaries. Existing public routes and persisted data stay backward compatible while responsibilities are moved incrementally out of the large entry files.

The library uses stable source-qualified artwork IDs. A library item can be remote-only or downloaded, and collections reference those IDs instead of copying artwork. Persisted JSON is versioned and decoded with defaults so existing Android installations migrate in place. A database migration will only be introduced when library volume or query requirements justify it; changing storage now would increase release risk without changing user-visible behavior.

Display preferences are not search filters. NSFW blur is stored separately and defaults to enabled. Per-image reveal state is temporary and is never persisted. AI exclusion is enforced in the search domain layer so no UI or imported configuration can disable it.

Desktop viewer behavior is isolated in a small static module. Android viewer behavior is isolated in a reusable Compose component. This is the first incremental extraction; further routes and screens should follow the same boundary instead of growing `app.py` or the main HTML.

## Consequences

- Desktop and Android use the same meanings for Guardar, Baixar, blur and zoom.
- Existing Android gallery entries continue to load; missing new fields receive safe defaults.
- Collections and remote-only items do not consume device gallery storage.
- Packaging stays self-contained and offline state stays on the device.
- The Python and Kotlin implementations still need contract tests for shared policy because they cannot import one another directly.
- A future account/sync feature can synchronize the library model without redefining it.

## Alternatives considered

### Separate backend service

Rejected for now. It would require hosting, authentication, privacy controls and ongoing operations, while the current product is intentionally local-first.

### Immediate Room migration on Android

Deferred. Room is appropriate once the library needs relational queries at larger scale, but the current persisted list can support the approved collection model safely with less migration and build risk.

### Full repository rewrite

Rejected. Incremental extraction preserves the working release pipeline and makes each behavior independently testable.
