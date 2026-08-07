[app]
title = ArtFinder
package.name = artfinder
package.domain = io.github.gabizips
version = 0.1.0

source.dir = .
source.include_exts = py,html,js,json,png,ico
source.include_patterns = templates/*,sources/*,filters/*,utils/*,palettes/*,assets/*,user_categories.json
source.exclude_dirs = .git,.github,.buildozer,venv,build,dist,tests,packaging

# Native packages must match the recipes shipped by the selected
# python-for-android release. Pure-Python packages can keep their normal
# versions. Do not use uvicorn[standard] here (uvloop is not needed).
requirements = python3==3.14.2,fastapi==0.118.3,uvicorn==0.38.0,pydantic==2.12.3,pydantic-core==2.41.4,starlette==0.48.0,annotated-types==0.7.0,typing-extensions==4.16.0,typing-inspection==0.4.2,anyio==4.14.2,idna==3.18,annotated-doc==0.0.4,sse-starlette==2.1.0,click==8.2.1,h11==0.16.0,requests==2.32.5,requests-oauthlib==2.0.0,aiohttp==3.8.3,aiofiles==25.1.0,pillow==11.3.0,colorthief==0.2.1,imagehash==4.3.2,colormath==3.0.0,beautifulsoup4==4.14.3,pixivpy3==3.7.5

icon.filename = assets/artfinder-icon.png
orientation = all
fullscreen = 0

# The app talks directly to artwork providers and runs its API on loopback.
android.permissions = INTERNET
android.api = 35
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a
android.private_storage = True
android.accept_sdk_license = True

# Native Android WebView + the local server started by main.py/mobile.py.
p4a.bootstrap = webview
p4a.branch = v2026.05.09
p4a.extra_args = --port=5000

[buildozer]
log_level = 2
warn_on_root = 1
