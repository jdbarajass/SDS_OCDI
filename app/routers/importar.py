from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.auth_utils import ROLES_SUPERUSUARIO

from app.database import get_db

router = APIRouter()


def _puede_importar_exp(request: Request) -> bool:
    user = getattr(request.state, "user", None)
    if not user:
        return False
    if user["rol"] in ROLES_SUPERUSUARIO:
        return True
    return getattr(request.state, "permisos", {}).get("expedientes", {}).get("puede_importar", False)


# Nota: las rutas GET/POST "/importar" (carga y mapeo de Excel) viven en
# app/routers/expedientes.py, registrado antes que este router en main.py.
# Este archivo solo conserva "/importar/limpiar-bd", usada por el botón
# "Zona de Peligro" de importar.html.

@router.post("/importar/limpiar-bd")
async def limpiar_base_datos(request: Request):
    if not _puede_importar_exp(request):
        return RedirectResponse("/expedientes?msg=sin_permiso", status_code=303)
    conn = get_db()
    conn.execute("DELETE FROM expedientes")
    conn.execute("DELETE FROM sqlite_sequence WHERE name = 'expedientes'")
    conn.commit()
    conn.close()
    return RedirectResponse("/importar?msg=bd_limpiada", status_code=303)
