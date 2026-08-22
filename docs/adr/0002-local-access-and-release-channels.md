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

The original Android package was experimental and embedded Python in a WebView.
ADR-0003 replaced that package with a native client and native build checks.

## Decision

- Keep the desktop package bound to loopback by default. The native Android
  client talks directly to the selected providers and runs no local server.
- Require a high-entropy per-process token for non-loopback LAN clients. The
  initial URL exchanges the token for an HttpOnly, SameSite session cookie and
  removes it from the browser URL.
- Publish supported desktop binaries as versioned GitHub Release assets with a
  checksum file. Actions artifacts remain short-lived build evidence.
- Publish the signed native Android APK in tagged Releases after tests, lint,
  package inspection and certificate verification pass.

## Options considered

### Leave LAN mode unauthenticated

Rejected because browser origin checks do not authenticate direct HTTP clients
on a shared Wi-Fi network.

### Remove LAN mode

Safer but removes a useful development path. Token authentication keeps that
path while making accidental exposure less dangerous.

### Publish every successful build automatically

Rejected. Tagged releases publish the three supported packages only after each
platform's build checks pass.

## Consequences

- A LAN URL changes each process start unless `ARTFINDER_LAN_TOKEN` is set.
- LAN traffic is still plain HTTP and therefore remains unsuitable for public
  or hostile networks even with a token.
- Desktop users receive stable, durable download links and checksums.
- Android no longer depends on Python startup or a system WebView.
