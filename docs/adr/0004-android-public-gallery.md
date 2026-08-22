# ADR 0004: Android public gallery storage

**Status:** Accepted
**Date:** 2026-08-14
**Decider:** Project maintainer

## Context

ArtFinder needs downloaded images to remain available in its internal Gallery
and also appear in the Android photo gallery. `MediaStore.RELATIVE_PATH` and
the pending-item lifecycle are available from Android 10 (API 29), allowing the
application to support Android 10 through 16 without legacy external-storage
permissions or raw public filesystem paths.

## Decision

- Use API 29 for the manifest and native-library floor, and target API 36. This
  covers Android 10 through Android 16 while opting into current platform
  behavior.
- Publish the image directly to `Pictures/ArtFinder` with `MediaStore`,
  `RELATIVE_PATH` and the pending-item lifecycle.
- Treat that MediaStore row as the single canonical copy and store the returned
  `content://` URI in local app preferences so ArtFinder can remove the
  MediaStore row it owns.
- Do not request broad or legacy storage permissions.
- Validate the downloaded byte signature and enforce a 100 MB limit before
  committing the pending MediaStore item.

## Consequences

- Images are visible to photo applications and survive an ArtFinder uninstall.
- A downloaded image uses one public copy shared by ArtFinder and photo apps.
- Removing an image outside ArtFinder can make the recorded public URI stale;
  ArtFinder treats a missing MediaStore row as already removed.
- Desktop and Linux behavior is unchanged; the MediaStore implementation lives
  only in the native Android project.
