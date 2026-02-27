from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import date

from app.database import get_db, calcular_alerta, row_to_dict

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

MESES_CORTO = {
    "ENERO": "Ene", "FEBRERO": "Feb", "MARZO": "Mar", "ABRIL": "Abr",
    "MAYO": "May", "JUNIO": "Jun", "JULIO": "Jul", "AGOSTO": "Ago",
    "SEPTIEMBRE": "Sep", "OCTUBRE": "Oct", "NOVIEMBRE": "Nov", "DICIEMBRE": "Dic",
}
MESES_NUM = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
    "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12,
}


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = get_db()
    hoy = date.today().isoformat()

    total = conn.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0]

    por_etapa = [{"etapa": r[0] or "Sin etapa", "cantidad": r[1]}
        for r in conn.execute("SELECT etapa, COUNT(*) FROM expedientes GROUP BY etapa ORDER BY COUNT(*) DESC").fetchall()]

    por_estado = [{"estado": r[0] or "Sin estado", "cantidad": r[1]}
        for r in conn.execute("SELECT estado_proceso, COUNT(*) FROM expedientes GROUP BY estado_proceso ORDER BY COUNT(*) DESC").fetchall()]

    por_abogado = [{"abogado": r[0] or "Sin asignar", "cantidad": r[1]}
        for r in conn.execute("SELECT nombre_abogado, COUNT(*) FROM expedientes GROUP BY nombre_abogado ORDER BY COUNT(*) DESC").fetchall()]

    por_anio = [{"anio": r[0] or "Sin año", "cantidad": r[1]}
        for r in conn.execute("SELECT anio, COUNT(*) FROM expedientes GROUP BY anio ORDER BY anio DESC").fetchall()]

    por_origen = [{"origen": r[0] or "Sin especificar", "cantidad": r[1]}
        for r in conn.execute("SELECT origen_proceso, COUNT(*) FROM expedientes GROUP BY origen_proceso ORDER BY COUNT(*) DESC LIMIT 10").fetchall()]

    por_tipologia = [{"tipologia": r[0] or "Sin especificar", "cantidad": r[1]}
        for r in conn.execute("SELECT tipologia, COUNT(*) FROM expedientes WHERE tipologia IS NOT NULL GROUP BY tipologia ORDER BY COUNT(*) DESC LIMIT 8").fetchall()]

    filas_tendencia = conn.execute("""
        SELECT anio, mes, COUNT(*) as cantidad FROM expedientes
        WHERE anio IS NOT NULL AND mes IS NOT NULL GROUP BY anio, mes
    """).fetchall()
    tendencia_raw = []
    for r in filas_tendencia:
        mes_num = MESES_NUM.get(str(r[1]).upper(), 0)
        tendencia_raw.append({
            "anio": r[0], "mes_num": mes_num,
            "etiqueta": f"{MESES_CORTO.get(str(r[1]).upper(), str(r[1])[:3])} {r[0]}",
            "cantidad": r[2],
        })
    tendencia_raw.sort(key=lambda x: (x["anio"], x["mes_num"]))
    tendencia = tendencia_raw[-24:]
    tendencia_max = max((t["cantidad"] for t in tendencia), default=1)

    # Alertas: excluyen archivados y valores no-fecha como "#VALUE!" usando date()
    vencidos = conn.execute("""
        SELECT COUNT(*) FROM expedientes
        WHERE estado_proceso NOT IN ('AUTO DE ARCHIVO','ARCHIVADO')
          AND ((date(fecha_vencimiento_ind) IS NOT NULL AND date(fecha_vencimiento_ind) < ?)
            OR (date(fecha_vencimiento_inv) IS NOT NULL AND date(fecha_vencimiento_inv) < ?))
    """, (hoy, hoy)).fetchone()[0]

    prox30 = conn.execute("""
        SELECT COUNT(*) FROM expedientes
        WHERE estado_proceso NOT IN ('AUTO DE ARCHIVO','ARCHIVADO')
          AND ((date(fecha_vencimiento_ind) IS NOT NULL AND date(fecha_vencimiento_ind) BETWEEN ? AND date(?, '+30 days'))
            OR (date(fecha_vencimiento_inv) IS NOT NULL AND date(fecha_vencimiento_inv) BETWEEN ? AND date(?, '+30 days')))
    """, (hoy, hoy, hoy, hoy)).fetchone()[0]

    prox60 = conn.execute("""
        SELECT COUNT(*) FROM expedientes
        WHERE estado_proceso NOT IN ('AUTO DE ARCHIVO','ARCHIVADO')
          AND ((date(fecha_vencimiento_ind) IS NOT NULL AND date(fecha_vencimiento_ind) BETWEEN date(?, '+31 days') AND date(?, '+60 days'))
            OR (date(fecha_vencimiento_inv) IS NOT NULL AND date(fecha_vencimiento_inv) BETWEEN date(?, '+31 days') AND date(?, '+60 days')))
    """, (hoy, hoy, hoy, hoy)).fetchone()[0]

    proximos_lista = [_enriquecer_simple(row_to_dict(r)) for r in conn.execute("""
        SELECT * FROM expedientes WHERE (
            (date(fecha_vencimiento_ind) IS NOT NULL AND date(fecha_vencimiento_ind) BETWEEN ? AND date(?, '+60 days'))
            OR (date(fecha_vencimiento_inv) IS NOT NULL AND date(fecha_vencimiento_inv) BETWEEN ? AND date(?, '+60 days'))
            OR (date(fecha_vencimiento_ind) IS NOT NULL AND date(fecha_vencimiento_ind) < ? AND estado_proceso NOT IN ('AUTO DE ARCHIVO','ARCHIVADO'))
            OR (date(fecha_vencimiento_inv) IS NOT NULL AND date(fecha_vencimiento_inv) < ? AND estado_proceso NOT IN ('AUTO DE ARCHIVO','ARCHIVADO'))
        )
        ORDER BY CASE WHEN date(fecha_vencimiento_ind) < ? THEN fecha_vencimiento_ind
                      WHEN date(fecha_vencimiento_inv) < ? THEN fecha_vencimiento_inv
                      ELSE MIN(COALESCE(fecha_vencimiento_ind,'9999'),COALESCE(fecha_vencimiento_inv,'9999'))
                 END ASC LIMIT 15
    """, (hoy, hoy, hoy, hoy, hoy, hoy, hoy, hoy)).fetchall()]

    recientes = [row_to_dict(r) for r in conn.execute(
        "SELECT * FROM expedientes ORDER BY created_at DESC LIMIT 10"
    ).fetchall()]

    conn.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request, "active": "dashboard",
        "total": total, "por_etapa": por_etapa, "por_estado": por_estado,
        "por_abogado": por_abogado, "por_anio": por_anio,
        "por_origen": por_origen, "por_tipologia": por_tipologia,
        "tendencia": tendencia, "tendencia_max": tendencia_max,
        "vencidos": vencidos, "prox30": prox30, "prox60": prox60,
        "proximos_lista": proximos_lista, "recientes": recientes, "hoy": hoy,
    })


def _enriquecer_simple(exp: dict) -> dict:
    from app.database import calcular_alerta
    exp["alerta_ind"] = calcular_alerta(exp.get("fecha_vencimiento_ind"))
    exp["alerta_inv"] = calcular_alerta(exp.get("fecha_vencimiento_inv"))
    return exp
