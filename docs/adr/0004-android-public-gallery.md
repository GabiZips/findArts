# ADR 0004: Android public gallery storage

**Status:** Accepted
**Date:** 2026-08-14
**Decider:** Project maintainer

## Context

ArtFinder needs downloaded images to remain available in its internal Gallery
and also appear in the Android photo gallery. The application only supports
Android 15 and newer, so legacy external-storage permissions and paths are not
required.

## Decision

- Require Android API 35+ for both the manifest and native libraries while
  continuing to target API 35. This covers Android 15 and 16.
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
