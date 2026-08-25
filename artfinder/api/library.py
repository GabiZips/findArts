"""Artwork collection routes, isolated from the desktop application entry point."""

import sqlite3

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from utils.database import (
    create_collection,
    delete_collection,
    get_collections,
    is_favorited,
    rename_collection,
    set_favorite_collections,
)


router = APIRouter(prefix="/api", tags=["library"])


@router.get("/collections")
async def list_collections():
    return {"collections": get_collections()}


@router.post("/collections")
async def add_collection(body: dict):
    try:
        return {"ok": True, "collection": create_collection(str(body.get("name") or ""))}
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    except sqlite3.IntegrityError:
        return JSONResponse({"error": "Já existe uma coleção com esse nome."}, status_code=409)


@router.patch("/collections/{collection_id}")
async def edit_collection(collection_id: int, body: dict):
    try:
        if not rename_collection(collection_id, str(body.get("name") or "")):
            return JSONResponse({"error": "Coleção não encontrada."}, status_code=404)
        return {"ok": True}
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    except sqlite3.IntegrityError:
        return JSONResponse({"error": "Já existe uma coleção com esse nome."}, status_code=409)


@router.delete("/collections/{collection_id}")
async def remove_collection(collection_id: int):
    return {"ok": delete_collection(collection_id)}


@router.put("/favorites/{source}/{post_id}/collections")
async def update_favorite_collections(source: str, post_id: str, body: dict):
    raw = body.get("collection_ids", [])
    if not isinstance(raw, list) or len(raw) > 100:
        return JSONResponse({"error": "collection_ids inválido"}, status_code=400)
    try:
        ids = [int(value) for value in raw]
    except (TypeError, ValueError):
        return JSONResponse({"error": "collection_ids inválido"}, status_code=400)
    if not is_favorited(source, post_id):
        return JSONResponse({"error": "Arte guardada não encontrada."}, status_code=404)
    return {"ok": True, "collection_ids": set_favorite_collections(source, post_id, ids)}
