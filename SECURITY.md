# Security policy

## Supported versions

Only the latest GitHub Release is supported. Android builds remain experimental
until a release-signed APK has passed physical-device startup and lifecycle
tests.

## Reporting a vulnerability

Do not open a public issue containing credentials, tokens, private artwork or a
copy of `.env`. Use GitHub's private vulnerability reporting when it is enabled,
or contact the repository owner privately.

Include the affected version, operating system, reproduction steps and the
smallest safe log excerpt. Remove passwords, refresh tokens, API keys, cookies
and personal file paths before sending logs.

## Deployment guidance

- Keep the default loopback-only server mode.
- LAN mode is intended only for a trusted private network and requires the
  tokenized URL printed by the desktop process.
- Never port-forward ArtFinder or expose it directly to the internet.
- Do not distribute Android debug builds as stable releases.
