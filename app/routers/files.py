from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.services import s3_service

# Images Lylo (choix, moodboards, logo) d'un bucket privé : redirection vers une URL signée.
# Volontairement sans authentification, comme les anciennes URL S3 publiques (affichées sur
# le site, dans les emails et à l'impression). Les autres préfixes sont refusés.
router = APIRouter(tags=["files"])


@router.get("/files/{key:path}")
async def get_file(key: str):
    url = s3_service.public_file_signed_url(unquote(key))
    if not url:
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    # Cache court : l'URL signée expire au bout d'une heure.
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "public, max-age=600"})
