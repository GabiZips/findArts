# ADR-0002: Authenticated LAN access and versioned release channels

**Status:** Accepted
**Date:** 2026-08-13
**Decider:** Project maintainer

## Context

ArtFinder normally runs a private HTTP server on loopback. Its optional LAN
mode previously bound to every interface without authentication, which made
write and delete endpoints reachable by other devices on the same network.
Build outputs were also distributed only as temporary GitHub Actions artifacts,
while GitHub Deployments contained obsolete Vercel history.

The Android package is still experimental: a successful cross-compilation does
not prove that its Python process and WebView start on a physical device.

## Decision

- Keep desktop and Android native packages bound to loopback by default.
- Require a high-entropy per-process token for non-loopback LAN clients. The
  initial URL exchanges the token for an HttpOnly, SameSite session cookie and
  removes it from the browser URL.
- Publish supported desktop binaries as versioned GitHub Release assets with a
  checksum file. Actions artifacts remain short-lived build evidence.
- Keep Android outside stable Releases until startup, lifecycle, storage and
  release-signing checks pass on physical devices.
- If Android's Python startup raises an exception, keep the WebView process
  alive with a local diagnostic page and save the traceback in private storage.

## Options considered

### Leave LAN mode unauthenticated

Rejected because browser origin checks do not authenticate direct HTTP clients
on a shared Wi-Fi network.

### Remove LAN mode

Safer but removes a useful development path. Token authentication keeps that
path while making accidental exposure less dangerous.

### Publish every successful build automatically

Rejected because a compiled but unlaunched Android APK would look stable. Tags
publish desktop Releases; Android stays explicitly experimental for now.

## Consequences

- A LAN URL changes each process start unless `ARTFINDER_LAN_TOKEN` is set.
- LAN traffic is still plain HTTP and therefore remains unsuitable for public
  or hostile networks even with a token.
- Desktop users receive stable, durable download links and checksums.
- Android startup failures become visible and actionable instead of appearing
  only as an immediate close.
