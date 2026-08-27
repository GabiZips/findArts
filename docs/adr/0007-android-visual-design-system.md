# ADR-0007: Android visual design system

**Status:** Accepted  
**Date:** 2026-08-26  
**Deciders:** ArtFinder maintainers

## Context

The native Android client is functionally complete enough to search, manage
tags, organize saved artwork, configure credentials and pair with desktop. Its
screens, however, still expose Material components with mostly default visual
hierarchy. Local color changes do not create a coherent product identity, and
screen-specific styling would make future interface work inconsistent.

The redesign must preserve Android 10 through 16 support, accessibility,
offline startup, current data formats and the native Kotlin/Compose codebase.

## Decision

Maintain Kotlin and Jetpack Compose, and add a reusable ArtFinder visual layer
above Material 3. The layer owns color tokens, surface hierarchy, typography,
spacing, branded navigation, panels, pills, action buttons, artwork treatment
and screen backdrops.

Manrope is bundled as the interface typeface under the SIL Open Font License.
The application does not download fonts at runtime. Screens may continue using
Material primitives for behavior and accessibility, but shared presentation
belongs in `ui/theme` and `ui/component`.

Artwork remains the visual priority. Controls use compact surfaces and reveal
progressively; decorative gradients remain subtle and never reduce contrast.

## Options Considered

### Option A: Continue styling Material components per screen

| Dimension | Assessment |
|-----------|------------|
| Complexity | Low initially |
| Cost | Low initially, higher maintenance |
| Scalability | Poor |
| Team familiarity | High |

**Pros:** Small diffs and fast isolated changes.  
**Cons:** Repeats styling, keeps the prototype appearance and encourages drift.

### Option B: Reusable Compose design system

| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium |
| Cost | Moderate one-time investment |
| Scalability | High for the Android client |
| Team familiarity | High |

**Pros:** Native behavior, coherent identity, reusable components and gradual
migration.  
**Cons:** Requires discipline around tokens and component boundaries.

### Option C: Rewrite the interface in Flutter or React Native

| Dimension | Assessment |
|-----------|------------|
| Complexity | High |
| Cost | High |
| Scalability | Potential cross-platform benefit |
| Team familiarity | Lower |

**Pros:** A future shared mobile UI could target more than Android.  
**Cons:** Reimplements working search, secure storage, MediaStore and lifecycle
integration without directly improving the current product.

## Trade-off Analysis

Option B gives the app a distinct identity while retaining the stable native
implementation. It also allows screens to migrate independently. A rewrite is
only justified if a shared iOS interface becomes a higher priority than Android
iteration speed.

## Consequences

- Shared visual decisions become easier to change and test.
- New screens must use ArtFinder tokens and components before adding local
  styling.
- Material 3 remains an implementation foundation, not the visible identity.
- The bundled font slightly increases APK size and requires its license to stay
  in the repository.
- Physical-device visual and accessibility checks remain part of release QA.

## Action Items

1. [x] Add the ArtFinder color, typography and shape tokens.
2. [x] Add reusable branded surfaces, pills, buttons and backgrounds.
3. [x] Migrate every main screen to the shared layer.
4. [ ] Add screenshot tests for compact and expanded phone layouts.
5. [ ] Revisit adaptive two-pane layouts when tablet support is prioritized.
