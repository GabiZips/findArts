# ArtFinder

[![Validation](https://github.com/GabiZips/findArts/actions/workflows/ci.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/ci.yml)

[Português](README.md) · [English](README.en.md)

Search, organize, and download artwork from Danbooru, Gelbooru, Safebooru, e621, Pixiv, Tumblr, Bluesky, and DeviantArt. ArtFinder runs locally on Windows with Rust and on Android with Kotlin and Jetpack Compose.

## Downloads

- [Windows x64 installer](https://github.com/GabiZips/findArts/releases/latest/download/ArtFinder-Windows-Setup.exe)
- [Windows x64 portable executable](https://github.com/GabiZips/findArts/releases/latest/download/ArtFinder-Windows.exe)
- [APK for Android 10–16](https://github.com/GabiZips/findArts/releases/latest/download/ArtFinder-Android-10-16.apk)
- [Releases and SHA256SUMS](https://github.com/GabiZips/findArts/releases)

Find the binaries under **Assets**. Development builds are available in [GitHub Actions](https://github.com/GabiZips/findArts/actions). A fresh installation starts with no categories, and credentials are stored in the device's system vault.

## Windows

Search across selected sources, assign source-specific tags to categories, and follow each query through its last page. Artwork appears as sources respond. Choose among three preview sizes, filter the results, and save, download, or organize artwork in collections.

The Rust profile lives under `%LOCALAPPDATA%\ArtFinder-Rust`. Use **Settings → Import categories from installed ArtFinder** to copy categories, favorites, and downloads from the previous desktop version. Source credentials can be saved to the system vault from **Settings**.

To build, install stable Rust with the MSVC toolchain and the Visual Studio build tools.

```powershell
cargo build --release --locked --manifest-path desktop-rust/Cargo.toml
cargo test --release --locked --manifest-path desktop-rust/Cargo.toml
```

The executable is under `desktop-rust/target/release/artfinder-desktop.exe`. With Inno Setup 6 installed, run `./scripts/build-windows-installer.ps1` to generate the installer. See the [desktop documentation](desktop-rust/README.md).

## Android

The native app uses Kotlin and Jetpack Compose and runs on Android 10 and newer. Downloads are saved to `Pictures/ArtFinder` through MediaStore. The viewer supports swipe navigation and zoom. To transfer categories and optional credentials, generate a pairing code in the Windows settings and import it on Android over the same local network.

The release workflow signs the APK with the stable ArtFinder certificate so users can update their installation. See the [Android build guide](android-native/README.md) and [signing details](docs/android-signing.md).

## Releases

A `v*` tag matching the Cargo and Gradle versions triggers a release. GitHub publishes the Windows installer, the portable executable, the signed APK, and their checksums after both builds succeed.

ArtFinder is an independent project with no official affiliation with the artwork providers or rights holders. [License](LICENSE)
