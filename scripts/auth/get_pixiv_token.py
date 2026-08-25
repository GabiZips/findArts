#!/usr/bin/env python3
"""Obtain the Pixiv refresh token through gppt's browser OAuth flow.

Run from the project root:

    python scripts/auth/get_pixiv_token.py
"""

import asyncio
import inspect
import sys


def main() -> None:
    try:
        from gppt import GetPixivToken
    except ImportError:
        print("A ferramenta 'gppt' não está instalada. Rode:")
        print("    python -m pip install gppt")
        sys.exit(1)

    print("Abrindo o Pixiv no navegador para login...")
    print("(Se pedir, faça login normalmente. Não feche a janela até terminar.)")
    print("(Na primeira vez o gppt baixa o Chromium do Playwright — pode demorar.)\n")

    try:
        client = GetPixivToken(headless=False)
        result = client.login()
        if inspect.isawaitable(result):
            result = asyncio.run(result)
    except Exception as error:
        print(f"\nFalhou o login automático: {error}\n")
        print("Alternativa headless (sem abrir navegador):")
        print("    gppt login-headless -u SEU_LOGIN -p SUA_SENHA")
        print("\nOu veja o guia manual: https://github.com/eggplants/get-pixivpy-token")
        sys.exit(1)

    token = result.get("refresh_token", "")
    if not token:
        print("Não consegui extrair o refresh token da resposta.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  REFRESH TOKEN OBTIDO COM SUCESSO")
    print("=" * 60)
    print(f"\n{token}\n")
    print("Cole a linha abaixo no seu arquivo .env:\n")
    print(f"PIXIV_REFRESH_TOKEN={token}\n")


if __name__ == "__main__":
    main()
