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
- Keep the app-private downloaded file as the canonical copy used by ArtFinder.
- Publish a second copy to `Pictures/ArtFinder` with `MediaStore`,
  `RELATIVE_PATH` and the pending-item lifecycle.
- Store the returned `content://` URI in SQLite so ArtFinder can remove the
  MediaStore row it owns.
- Do not request broad or legacy storage permissions.
- Treat public export failure as partial success: keep the private download and
  expose a retry button. Treat public deletion failure as a failed deletion and
  preserve the private copy and URI for retry.

## Consequences

- Images are visible to photo applications and survive an ArtFinder uninstall.
- A downloaded image uses storage twice while both copies exist.
- Removing an image outside ArtFinder can make the recorded public URI stale;
  ArtFinder treats a missing MediaStore row as already removed.
- Desktop and Linux behavior is unchanged because PyJNIus is loaded only in the
  packaged Android process.
