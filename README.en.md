# ArtFinder

[![Build Windows](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml)
[![Build Linux](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml)
[![Build Android](https://github.com/GabiZips/findArts/actions/workflows/build-android.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-android.yml)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)

[Português](README.md) · [English](README.en.md)

A local application for searching, comparing, organizing and downloading
artwork and fan art from multiple sources in one interface.

> [!IMPORTANT]
> ArtFinder is an independent, unofficial project. It is not associated with,
> approved by or sponsored by Pixiv, Tumblr, Bluesky, DeviantArt, Danbooru,
> Gelbooru, Safebooru, e621 or any rights holder whose works may be searched.

## Features

- Unified search across Danbooru, Gelbooru, Safebooru, e621, Pixiv, Tumblr,
  Bluesky and DeviantArt.
- Source-specific tags and custom categories without editing Python code.
- Local SQLite favorites, review groups, blacklist and download history.
- Gallery, side-by-side comparison and content filters.
- Size validation and perceptual-hash deduplication during downloads.
- Portuguese and English interface with a saved language preference.

## Windows

Stable binaries are published under
[GitHub Releases](https://github.com/GabiZips/findArts/releases). Download
`ArtFinder-Windows.exe`; `SHA256SUMS.txt` can be used to verify it. Temporary
development builds remain available from the
[Windows build workflow](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml).

Personal data is stored separately under `%LOCALAPPDATA%\ArtFinder\`, so
replacing the executable does not delete settings, the database or images.
A fresh installation starts with no characters or tags. User-created
categories remain local to that device and are never bundled into the executable.

## Linux

Stable Releases include `ArtFinder-Linux-x86_64.AppImage`. The
[Linux build workflow](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml)
also provides temporary development builds. Run it with:

```bash
chmod +x ArtFinder-Linux-x86_64.AppImage
./ArtFinder-Linux-x86_64.AppImage
```

Linux data is stored under `$XDG_DATA_HOME/artfinder` or
`~/.local/share/artfinder`.

## Android 10 through 16

Releases include `ArtFinder-Android-10-16.apk`, a native Kotlin and Jetpack
Compose client. It does not open a website, embed Python or depend on an
ArtFinder cloud server. One APK supports Android 10 (API 29) through Android 16
(API 36), including Android 14.

A fresh install starts without characters. Tags, credentials and Gallery
metadata stay on the device; credentials are encrypted with an Android
Keystore key. Updating from the former Python APK performs a one-time migration
of compatible categories and credentials when the old private data is still
available.

**Save to Gallery** publishes one copy under `Pictures/ArtFinder` through
MediaStore, without broad storage permissions. ArtFinder's Gallery references
that same copy. Search supports 1–25 pages per source (default 5), content
rating, age, score and AI filters. Very large searches require confirmation,
and NSFW thumbnails stay blurred until tapped. PC pairing uses only the
temporary full code copied into Android; the app does not request camera access.

iOS is not part of this build and requires a separate Xcode-based package and
signing process.

## Browser access from another device

For development on a trusted private Wi-Fi network:

```powershell
$env:ARTFINDER_LAN="1"
venv\Scripts\python app.py
```

Open the complete tokenized URL printed by the process. The token is exchanged
for an HttpOnly session cookie and removed from the address bar. LAN mode still
uses HTTP: never expose it to the internet or use it on a public or hostile
network.

## Run from source

Python 3.12 is recommended.

```powershell
py -3.12 -m venv venv
venv\Scripts\python -m pip install -r requirements-desktop.txt
venv\Scripts\python desktop.py
```

On Linux, use the equivalent `python3` and `venv/bin/python` commands. The
Linux dependency selects the PySide6 backend for pywebview.

## Optional credentials

Copy `.env.example` to `.env` and configure only the sources you intend to use.
Never commit or share this file.

The same fields can be configured in **Stats > Sources and credentials**. The
application reports only whether a value exists and never displays a saved
password or token back to the interface.

| Source | Configuration |
|---|---|
| Danbooru | Optional `DANBOORU_LOGIN` and `DANBOORU_API_KEY` |
| Gelbooru | `GELBOORU_USER_ID` and `GELBOORU_API_KEY` |
| Pixiv | `PIXIV_REFRESH_TOKEN`, generated with `get_pixiv_token.py` |
| Tumblr | `TUMBLR_API_KEY`; full OAuth improves search |
| DeviantArt | `DEVIANTART_CLIENT_ID` and `DEVIANTART_CLIENT_SECRET` |
| Bluesky | `BSKY_HANDLE` and an app password in `BSKY_PASSWORD` |

## Source-specific tags

Categories start empty and are stored in a private `user_categories.json` on
each device. The tag editor accepts source-specific queries:

```text
vex_(league_of_legends);
pixiv: ヴェックス;
tumblr: vex league of legends;
bluesky: "vex" "league of legends"
```

Unprefixed text is the booru query. `source: query` overrides take precedence
over automatic suggestions.

The native Android architecture decision is documented in
[`docs/adr/0003-mobile-implementation-strategy.md`](docs/adr/0003-mobile-implementation-strategy.md).

## Legal and content notice

- No fan art is bundled in the repository or application packages.
- Content is requested from third-party services by the user.
- Platform names and trademarks belong to their respective owners.
- Users are responsible for complying with each platform's terms and the
  rights of artists and other rights holders.
- ArtFinder does not remove watermarks or bypass paid or private content.
- Sources may return sensitive or adult content. Use the rating filters.
- Metadata-based AI filtering is not infallible.

Contributions are welcome. Do not include tokens, passwords, cookies or `.env`
contents in issues or pull requests.

The source code is available under the [MIT license](LICENSE). The license does
not grant rights to third-party artwork, trademarks or platform content. Follow
[SECURITY.md](SECURITY.md) when reporting a vulnerability.
