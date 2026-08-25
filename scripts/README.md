# Scripts auxiliares

Ferramentas manuais ficam separadas do código executado pelo aplicativo.

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
