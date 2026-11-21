# Scripts auxiliares

## Instalador Windows

Com Inno Setup 6 e Rust instalados, execute na raiz do projeto.

```powershell
./scripts/build-windows-installer.ps1
```

Adicione `-SkipBuild` para reaproveitar o executável compilado ou `-IsccPath` para indicar o caminho do `ISCC.exe`. A versão vem de `desktop-rust/Cargo.toml`. O instalador é gerado em `dist/review/` e instala por usuário em `%LOCALAPPDATA%\Programs\ArtFinder`.

`verify-windows-package.py` verifica artefatos da distribuição Python antiga. O workflow atual compila e testa o executável Rust em um perfil temporário.

## Autenticação de fontes

Os scripts em [auth/](auth/) auxiliam na configuração manual de Pixiv e Tumblr.
