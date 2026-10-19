# Scripts auxiliares

Ferramentas manuais ficam separadas do código executado pelo aplicativo.

## Instalador Windows

Com Inno Setup 6 instalado, executar na raiz:

```powershell
./scripts/build-windows-installer.ps1 -AppVersion 0.0.0-dev
```

Para reutilizar um executável já compilado, adicionar `-SkipBuild`. Se necessário,
informar `-IsccPath` com o caminho do ISCC.exe. O instalador é gerado em
`dist/review/ArtFinder-Setup-<versão>.exe`, instala por usuário em
`%LOCALAPPDATA%\Programs\ArtFinder` e mantém dados em `%LOCALAPPDATA%\ArtFinder`.
Atualização e desinstalação não apagam configurações, cofre ou downloads.

Compilação validada em 19/10/2026 com Inno Setup 6.7.3 instalado pelo usuário.
Instalação inicial confirmada pelo usuário. Instalação, reinstalação da mesma
versão e desinstalação validadas em cópia isolada. Migração entre versões e
preservação de dados reais ainda precisam de validação.
O executável portátil tem validação própria.

## Verificação do pacote Windows

Antes de distribuir um executável, valide os recursos e a ausência de caminhos
comuns de dados pessoais (o instalador também executa esta verificação):

```powershell
venv\Scripts\python scripts/verify-windows-package.py dist/ArtFinder.exe
```

O comando exige categorias iniciais vazias, compara a interface empacotada com
o código atual e informa o SHA-256. Não substitui auditoria de segredos nem
teste de instalação em uma máquina limpa.

## Autenticação opcional

Execute a partir da raiz do projeto:

```powershell
venv\Scripts\python scripts/auth/get_pixiv_token.py
venv\Scripts\python scripts/auth/setup_tumblr_oauth.py
```

- `get_pixiv_token.py` abre o fluxo OAuth do Pixiv e imprime
  `PIXIV_REFRESH_TOKEN`.
- `setup_tumblr_oauth.py` completa o OAuth do Tumblr e imprime os dois tokens
  que devem ser adicionados ao `.env`.

Os scripts nunca gravam credenciais no repositório. Não copie a saída para
issues, commits ou logs públicos.
