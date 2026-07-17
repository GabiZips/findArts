import webbrowser
from requests_oauthlib import OAuth1Session

# Credenciais lidas do .env via config.py (não hardcodar segredos aqui)
from config import TUMBLR_API_KEY, TUMBLR_CONSUMER_SECRET

CONSUMER_KEY    = TUMBLR_API_KEY
CONSUMER_SECRET = TUMBLR_CONSUMER_SECRET

if not CONSUMER_KEY or not CONSUMER_SECRET:
    print("Defina TUMBLR_API_KEY e TUMBLR_CONSUMER_SECRET no arquivo .env primeiro.")
    exit(1)

REQUEST_TOKEN_URL = "https://www.tumblr.com/oauth/request_token"
AUTHORIZE_URL     = "https://www.tumblr.com/oauth/authorize"
ACCESS_TOKEN_URL  = "https://www.tumblr.com/oauth/access_token"

print("\n[1/3] Obtendo request token...")
try:
    oauth = OAuth1Session(CONSUMER_KEY, client_secret=CONSUMER_SECRET)
    fetch_response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
except Exception as e:
    print("Erro ao conectar com o Tumblr:", e)
    exit(1)

resource_owner_key = fetch_response.get("oauth_token")
resource_owner_secret = fetch_response.get("oauth_token_secret")

auth_url = oauth.authorization_url(AUTHORIZE_URL)
print(f"\n[2/3] Abrindo browser para autorizar o app...")
print(f"URL: {auth_url}")
webbrowser.open(auth_url)

verifier = input("\nCole o PIN/verifier que o Tumblr mostrou: ").strip()

print("\n[3/3] Obtendo access token...")
try:
    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier
    )
    oauth_tokens = oauth.fetch_access_token(ACCESS_TOKEN_URL)
except Exception as e:
    print("Erro ao validar o PIN:", e)
    exit(1)

access_token = oauth_tokens.get("oauth_token")
access_token_secret = oauth_tokens.get("oauth_token_secret")

print("\n" + "="*60)
print("Tokens obtidos! Copie isso para o config.py:")
print("="*60)
print(f'TUMBLR_OAUTH_TOKEN       = "{access_token}"')
print(f'TUMBLR_OAUTH_TOKEN_SECRET= "{access_token_secret}"')
print("="*60 + "\n")
