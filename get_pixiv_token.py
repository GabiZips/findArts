#!/usr/bin/env python3
"""
get_pixiv_token.py — obtém o REFRESH TOKEN do Pixiv (necessário uma única vez).

O Pixiv não permite mais login por usuário/senha na API, então usamos o fluxo
OAuth pelo navegador. Rode:

    python get_pixiv_token.py

Ele abre o Pixiv no navegador; faça login normalmente. O token aparece no
terminal — copie e cole em PIXIV_REFRESH_TOKEN no arquivo .env.

Requer a ferramenta 'gppt' (Get Pixiv Token):
    python -m pip install gppt
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
        g = GetPixivToken(headless=False)
        res = g.login()
        # gppt >= 4 usa Playwright e login() é assíncrono; versões antigas
        # (Selenium) retornam o dict diretamente.
        if inspect.isawaitable(res):
            res = asyncio.run(res)
    except Exception as e:
        print(f"\nFalhou o login automático: {e}\n")
        print("Alternativa headless (sem abrir navegador):")
        print("    gppt login-headless -u SEU_LOGIN -p SUA_SENHA")
        print("\nOu veja o guia manual: https://github.com/eggplants/get-pixivpy-token")
        sys.exit(1)

    token = res.get("refresh_token", "")
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
