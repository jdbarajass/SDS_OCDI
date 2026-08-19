"""
Búsqueda global — un solo cuadro de texto que busca por número o nombre a
través de los módulos de casos (Expedientes, SDQS, Correspondencia,
Expedientes Digitales), sin duplicar la lógica de filtro de cada lista.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pathlib import Path

from app.template_utils import make_templates
from app.database import get_db
from app.auth_utils import tpl

router = APIRouter()
templates = make_templates(str(Path(__file__).parent.parent / "templates"))

_LIMITE = 20


def _puede_ver(request: Request, modulo: str) -> bool:
    user = getattr(request.state, "user", None)
    if user and user.get("rol") in ("admin", "jefe"):
        return True
    permisos = getattr(request.state, "permisos", {})
    return permisos.get(modulo, {}).get("puede_ver", True)


@router.get("/buscar", response_class=HTMLResponse)
async def buscar(request: Request, q: str = ""):
    q = (q or "").strip()
    resultados = {"expedientes": [], "sdqs": [], "correspondencia": [], "digitales": []}

    if len(q) >= 2:
        like = f"%{q}%"
        conn = get_db()

        if _puede_ver(request, "expedientes"):
            rows = conn.execute("""
                SELECT id, n_expediente, anio, nombre_investigado, quejoso, etapa_actual
                FROM expedientes
                WHERE n_expediente LIKE ? OR nombre_investigado LIKE ? OR quejoso LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (like, like, like, _LIMITE)).fetchall()
            resultados["expedientes"] = [dict(r) for r in rows]

        if _puede_ver(request, "sdqs"):
            rows = conn.execute("""
                SELECT id, sdqs, quejoso, tema, mes
                FROM sdqs
                WHERE sdqs LIKE ? OR quejoso LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (like, like, _LIMITE)).fetchall()
            resultados["sdqs"] = [dict(r) for r in rows]

        if _puede_ver(request, "correspondencia"):
            rows = conn.execute("""
                SELECT id, n_radicado, origen, asunto, anio
                FROM correspondencia
                WHERE n_radicado LIKE ? OR origen LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (like, like, _LIMITE)).fetchall()
            resultados["correspondencia"] = [dict(r) for r in rows]

        if _puede_ver(request, "digitales"):
            rows = conn.execute("""
                SELECT id, n_expediente, anio, abogado, etapa
                FROM exp_digitales
                WHERE n_expediente LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (like, _LIMITE)).fetchall()
            resultados["digitales"] = [dict(r) for r in rows]

        conn.close()

    total = sum(len(v) for v in resultados.values())
    return templates.TemplateResponse("buscar.html", tpl(request, None,
        q=q, resultados=resultados, total=total, active="buscar",
    ))
