"""Android MediaStore bridge for publishing downloaded artwork.

Desktop and Linux never import PyJNIus. On Android 10+ the app owns the
MediaStore rows it creates, so publishing and deleting those rows does not
require broad storage permissions.
"""

from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PUBLIC_ALBUM = "Pictures/ArtFinder"


class AndroidMediaError(RuntimeError):
    """Raised when an Android MediaStore operation cannot be completed."""


def android_media_available() -> bool:
    """Return whether the current process is the packaged Android app."""
    return os.getenv("ARTFINDER_MOBILE", "").strip() == "1"


@dataclass(frozen=True)
class _AndroidRuntime:
    resolver: Any
    content_values: Any
    media_columns: Any
    images_media: Any
    media_store: Any
    uri: Any
    integer: Any


def _android_runtime() -> _AndroidRuntime:
    if not android_media_available():
        raise AndroidMediaError("A Galeria do Android só está disponível no aplicativo móvel")

    try:
        from jnius import autoclass

        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        return _AndroidRuntime(
            resolver=activity.getContentResolver(),
            content_values=autoclass("android.content.ContentValues"),
            media_columns=autoclass("android.provider.MediaStore$MediaColumns"),
            images_media=autoclass("android.provider.MediaStore$Images$Media"),
            media_store=autoclass("android.provider.MediaStore"),
            uri=autoclass("android.net.Uri"),
            integer=autoclass("java.lang.Integer"),
        )
    except Exception as exc:
        raise AndroidMediaError(f"Integração Android indisponível: {exc}") from exc


def _mime_type(path: Path) -> str:
    guessed, _encoding = mimetypes.guess_type(path.name)
    return guessed if guessed and guessed.startswith("image/") else "image/jpeg"


def publish_image(file_path: str | Path, display_name: str | None = None) -> str:
    """Copy an app-private image into ``Pictures/ArtFinder`` via MediaStore."""
    path = Path(file_path)
    if not path.is_file():
        raise AndroidMediaError("Arquivo privado não encontrado")

    runtime = _android_runtime()
    values = runtime.content_values()
    columns = runtime.media_columns
    values.put(columns.DISPLAY_NAME, display_name or path.name)
    values.put(columns.MIME_TYPE, _mime_type(path))
    values.put(columns.RELATIVE_PATH, PUBLIC_ALBUM)
    values.put(columns.IS_PENDING, runtime.integer(1))

    collection = runtime.images_media.getContentUri(
        runtime.media_store.VOLUME_EXTERNAL_PRIMARY
    )
    public_uri = None
    output = None
    published_ok = False
    try:
        public_uri = runtime.resolver.insert(collection, values)
        if public_uri is None:
            raise AndroidMediaError("O Android recusou a criação da imagem")

        output = runtime.resolver.openOutputStream(public_uri)
        if output is None:
            raise AndroidMediaError("O Android não abriu o arquivo da Galeria")

        # Pass byte arrays by value: copying Java's buffer back to Python after
        # every write is unnecessary and expensive for large images.
        with path.open("rb") as source:
            while chunk := source.read(64 * 1024):
                output.write(bytearray(chunk), pass_by_reference=False)
        output.flush()
        output.close()
        output = None

        published = runtime.content_values()
        published.put(columns.IS_PENDING, runtime.integer(0))
        runtime.resolver.update(public_uri, published, None, None)
        published_ok = True
        return str(public_uri.toString())
    except AndroidMediaError:
        raise
    except Exception as exc:
        raise AndroidMediaError(f"Não foi possível salvar na Galeria: {exc}") from exc
    finally:
        if output is not None:
            try:
                output.close()
            except Exception:
                pass
        if public_uri is not None and not published_ok:
            # Do not leave an invisible, pending MediaStore row after a failed
            # stream write. Successful rows remain in the public gallery.
            try:
                runtime.resolver.delete(public_uri, None, None)
            except Exception:
                pass


def delete_image(public_uri: str) -> bool:
    """Delete a MediaStore row previously created by ArtFinder.

    ``False`` means the row was already absent. Permission/provider failures
    raise ``AndroidMediaError`` so the caller can preserve the private copy and
    let the user retry.
    """
    if not public_uri:
        return False
    runtime = _android_runtime()
    try:
        uri = runtime.uri.parse(public_uri)
        return int(runtime.resolver.delete(uri, None, None)) > 0
    except Exception as exc:
        raise AndroidMediaError(f"Não foi possível remover da Galeria: {exc}") from exc
