# ArtFinder

[![Build Windows](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml)
[![Build Linux](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml)
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

Open the [Windows build workflow](https://github.com/GabiZips/findArts/actions/workflows/build-windows.yml),
choose the latest successful run and download `ArtFinder-Windows` from
**Artifacts**. Extract the ZIP and run `ArtFinder.exe`.

Personal data is stored separately under `%LOCALAPPDATA%\ArtFinder\`, so
replacing the executable does not delete settings, the database or images.
A fresh installation starts with no characters or tags. User-created
categories remain local to that device and are never bundled into the executable.

## Linux

Open the [Linux build workflow](https://github.com/GabiZips/findArts/actions/workflows/build-linux.yml)
and download `ArtFinder-Linux-x86_64` from a successful run. Extract it and run:

```bash
chmod +x ArtFinder-Linux-x86_64.AppImage
./ArtFinder-Linux-x86_64.AppImage
```

Linux data is stored under `$XDG_DATA_HOME/artfinder` or
`~/.local/share/artfinder`.

## Android (experimental)

The manual [Android build workflow](https://github.com/GabiZips/findArts/actions/workflows/build-android.yml)
uses python-for-android's native WebView bootstrap and creates an experimental
APK. It embeds the local Python backend; it does not require an ArtFinder cloud
server.

The APK has not yet been validated on a physical device. Downloads currently
remain in the application's private storage, and exporting them to Android's
public Gallery/Downloads storage is still planned. iOS is not part of this
build and requires a separate Xcode-based package and signing process.

Source credentials can be entered inside the application under
**Stats > Sources and credentials**, so secrets do not need to be embedded in
the APK.

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
