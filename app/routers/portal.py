from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
from app.template_utils import make_templates
from datetime import date

from app.database import get_db
from app.auth_utils import tpl

router = APIRouter()
templates = make_templates(str(Path(__file__).parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def hub(request: Request):
    conn = get_db()

    total_base      = conn.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0]
    total_digitales = conn.execute("SELECT COUNT(*) FROM exp_digitales").fetchone()[0]

    hoy = date.today().isoformat()
    prox_sala = conn.execute(
        "SELECT fecha, franja, titulo, estado FROM sala_agenda WHERE fecha >= ? ORDER BY fecha, franja LIMIT 1",
        (hoy,)
    ).fetchone()

    total_control_autos = conn.execute("SELECT COUNT(*) FROM control_autos_sustanciacion").fetchone()[0]

    total_corr = conn.execute("SELECT COUNT(*) FROM correspondencia").fetchone()[0]
    corr_rojos = conn.execute("""
        SELECT COUNT(*) FROM correspondencia
        WHERE (fecha_radicado_salida IS NULL OR fecha_radicado_salida = '')
        AND (tipo_respuesta IS NULL OR UPPER(TRIM(tipo_respuesta)) NOT IN ('ANEXO EXPEDIENTE', 'ANEXO AL EXPEDIENTE'))
        AND fecha_ingreso IS NOT NULL
        AND CAST(julianday('now','localtime') - julianday(substr(fecha_ingreso,1,10)) AS INTEGER) >= 9
    """).fetchone()[0]

    conn.close()

    return templates.TemplateResponse("portal.html", tpl(request, None,
        total_base=total_base, total_digitales=total_digitales,
        prox_sala=dict(prox_sala) if prox_sala else None,
        total_corr=total_corr, corr_rojos=corr_rojos,
        total_control_autos=total_control_autos,
    ))
