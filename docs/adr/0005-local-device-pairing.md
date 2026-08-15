# ADR 0005: Local encrypted device pairing

**Status:** Accepted
**Date:** 2026-08-15
**Decider:** Project maintainer

## Context

People using ArtFinder on Windows and Android need a practical way to reuse
their source credentials and custom category/tag mappings without typing every
value again. The project does not operate a cloud backend or user-account
service, and adding one would substantially expand its privacy, security and
maintenance responsibilities.

## Decision

- Pair devices directly on the same local network, with no account or cloud
  dependency.
- Let the desktop create a random 256-bit AES key, a random 96-bit nonce and a
  high-entropy one-time endpoint.
- Encrypt the selected configuration with AES-256-GCM and bind it to the
  protocol version using authenticated additional data.
- Put the endpoint and decryption key in the QR/pairing code. Never include the
  key in the HTTP request, response, server logs or persistent files.
- Serve only the encrypted envelope, once, from a temporary HTTP server that
  listens for at most five minutes.
- Decrypt in the Android WebView using the Web Crypto API, then submit the
  plaintext only to the app's loopback backend for strict validation and local
  persistence.
- Allow category merge or replacement. Accept only the existing credential
  allowlist and bounded category fields. Do not transfer downloads, SQLite
  data, history or caches.

## Security properties and limitations

- A passive observer on the Wi-Fi can see the endpoint and encrypted envelope,
  but not the configuration plaintext or the key.
- AES-GCM detects modification of the envelope or use of the wrong key.
- Anyone who sees or copies the QR/pairing code before it is used can retrieve
  and decrypt the package. The UI therefore treats it as a temporary secret.
- The endpoint can be consumed by another LAN client as a denial of service;
  creating a new pairing invalidates the previous session.
- A compromised source or destination device is outside this protocol's threat
  model. Imported values retain the existing device-local storage behavior.
- Client isolation on public, corporate or campus Wi-Fi can block pairing even
  though both devices appear to use the same network.

## Consequences

- The common PC-to-phone setup requires no external server, subscription or
  project-operated credential database.
- The desktop executable needs the `cryptography` and `qrcode` packages.
- The Android WebView bootstrap must keep cleartext traffic enabled for its
  loopback server and the temporary LAN endpoint; CI verifies the generated
  manifest before publishing the APK.
- Windows Firewall may request permission for private-network access while a
  pairing session is active.
- Cross-network synchronization and automatic multi-device updates remain out
  of scope; those would require an authenticated backend and a separate design.
