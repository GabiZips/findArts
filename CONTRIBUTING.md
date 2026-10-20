# Contribuindo com o ArtFinder

Obrigado por ajudar. Antes de abrir um pull request, mantenha a mudança pequena,
explique o comportamento afetado e não inclua artes, credenciais ou dados locais.

## Ambiente

```powershell
py -3.12 -m venv venv
venv\Scripts\python -m pip install -r requirements-dev.txt
venv\Scripts\python -m unittest discover -s tests -v
venv\Scripts\python -m ruff check .
```

Para alterações Android, use Java 17 e um Android SDK atual:

```powershell
cd android-native
.\gradlew.bat testDebugUnitTest lintDebug assembleRelease
```

## Organização

- `artfinder/`: regras e API do aplicativo desktop.
- `sources/`: integrações com serviços externos.
- `android-native/`: cliente Android Kotlin/Compose.
- `templates/`: interface desktop.
- `tests/`: testes Python.
- `docs/`: decisões e documentação técnica.
- `scripts/`: ferramentas de desenvolvimento e autenticação opcional.

Atualize português e inglês juntos quando alterar textos visíveis. Novas decisões
arquiteturais relevantes devem ser registradas em `docs/adr/`.

## Segurança e privacidade

Nunca envie `.env`, tokens, cookies, bancos, tags pessoais ou imagens baixadas.
Falhas de segurança devem seguir o processo descrito em [SECURITY.md](SECURITY.md).
