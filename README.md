# ArtFinder

[![Validação](https://github.com/GabiZips/findArts/actions/workflows/ci.yml/badge.svg)](https://github.com/GabiZips/findArts/actions/workflows/ci.yml)

[Português](README.md) · [English](README.en.md)

Pesquise, organize e baixe artes do Danbooru, Gelbooru, Safebooru, e621, Pixiv, Tumblr, Bluesky e DeviantArt. O ArtFinder roda localmente no Windows em Rust e no Android em Kotlin com Jetpack Compose.

## Downloads

- [Instalador Windows x64](https://github.com/GabiZips/findArts/releases/latest/download/ArtFinder-Windows-Setup.exe)
- [Executável portátil Windows x64](https://github.com/GabiZips/findArts/releases/latest/download/ArtFinder-Windows.exe)
- [APK Android 10–16](https://github.com/GabiZips/findArts/releases/latest/download/ArtFinder-Android-10-16.apk)
- [Releases e SHA256SUMS](https://github.com/GabiZips/findArts/releases)

Os binários ficam em **Assets**. As builds de desenvolvimento ficam no [GitHub Actions](https://github.com/GabiZips/findArts/actions). Uma instalação começa com categorias vazias, e as credenciais ficam no cofre do sistema de cada dispositivo.

## Windows

A busca permite escolher as fontes, montar categorias com tags por fonte e carregar páginas até o fim. As artes aparecem conforme as fontes respondem. A grade tem prévias em três tamanhos, com filtros e ações de guardar, baixar e organizar em coleções.

O perfil Rust fica em `%LOCALAPPDATA%\ArtFinder-Rust`. Para trazer categorias, favoritos e downloads do desktop anterior, abra **Configurações → Importar categorias do ArtFinder instalado**. O novo perfil recebe uma cópia dos dados selecionados. Use o cofre de credenciais em **Configurações** para guardar os acessos de cada fonte.

Para compilar, instale Rust estável com a toolchain MSVC e as ferramentas de build do Visual Studio.

```powershell
cargo build --release --locked --manifest-path desktop-rust/Cargo.toml
cargo test --release --locked --manifest-path desktop-rust/Cargo.toml
```

O executável fica em `desktop-rust/target/release/artfinder-desktop.exe`. Com o Inno Setup 6 instalado, use `./scripts/build-windows-installer.ps1` para gerar o Setup. Consulte a [documentação do desktop](desktop-rust/README.md).

## Android

O APK usa Kotlin e Jetpack Compose e roda a partir do Android 10. A galeria usa o MediaStore para gravar em `Pictures/ArtFinder`. O visualizador tem navegação por gesto e zoom. Para transferir categorias e, opcionalmente, credenciais do PC, gere um código em **Configurações → Parear com outro dispositivo** e importe pelo Android na mesma rede.

O workflow de release usa o certificado estável do app para manter a compatibilidade de atualização do APK instalado. Consulte [build Android](android-native/README.md) e [assinatura do APK](docs/android-signing.md).

## Releases

Uma tag `v*` que corresponda às versões do Cargo e Gradle aciona os builds. O GitHub publica o instalador, o portátil, o APK assinado e os checksums após ambos os builds passarem.

O ArtFinder é um projeto independente e não tem associação oficial com as fontes de arte ou os detentores das obras. [Licença](LICENSE)
