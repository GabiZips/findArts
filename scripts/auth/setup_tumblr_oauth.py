#!/usr/bin/env python3
"""Complete Tumblr OAuth 1.0 and print the values expected by ``.env``."""

import sys
import webbrowser
from pathlib import Path

from requests_oauthlib import OAuth1Session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import TUMBLR_API_KEY, TUMBLR_CONSUMER_SECRET  # noqa: E402

REQUEST_TOKEN_URL = "https://www.tumblr.com/oauth/request_token"
AUTHORIZE_URL = "https://www.tumblr.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://www.tumblr.com/oauth/access_token"


def main() -> None:
    if not TUMBLR_API_KEY or not TUMBLR_CONSUMER_SECRET:
        print("Defina TUMBLR_API_KEY e TUMBLR_CONSUMER_SECRET no arquivo .env primeiro.")
        sys.exit(1)

    print("\n[1/3] Obtendo request token...")
    try:
        oauth = OAuth1Session(TUMBLR_API_KEY, client_secret=TUMBLR_CONSUMER_SECRET)
        response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
    except Exception as error:
        print(f"Erro ao conectar com o Tumblr: {error}")
        sys.exit(1)

    oauth = OAuth1Session(
        TUMBLR_API_KEY,
        client_secret=TUMBLR_CONSUMER_SECRET,
        resource_owner_key=response.get("oauth_token"),
        resource_owner_secret=response.get("oauth_token_secret"),
    )
    auth_url = oauth.authorization_url(AUTHORIZE_URL)
    print("\n[2/3] Abrindo o navegador para autorizar o app...")
    print(f"URL: {auth_url}")
    webbrowser.open(auth_url)
    verifier = input("\nCole o PIN/verifier que o Tumblr mostrou: ").strip()

    print("\n[3/3] Obtendo access token...")
    try:
        oauth = OAuth1Session(
            TUMBLR_API_KEY,
            client_secret=TUMBLR_CONSUMER_SECRET,
            resource_owner_key=response.get("oauth_token"),
            resource_owner_secret=response.get("oauth_token_secret"),
            verifier=verifier,
        )
        tokens = oauth.fetch_access_token(ACCESS_TOKEN_URL)
    except Exception as error:
        print(f"Erro ao validar o PIN: {error}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Tokens obtidos. Adicione estas linhas ao arquivo .env:")
    print("=" * 60)
    print(f'TUMBLR_OAUTH_TOKEN={tokens.get("oauth_token", "")}')
    print(f'TUMBLR_OAUTH_TOKEN_SECRET={tokens.get("oauth_token_secret", "")}')
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
