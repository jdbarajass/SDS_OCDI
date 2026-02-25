from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import date

from app.database import get_db, calcular_alerta, row_to_dict

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = get_db()
    hoy = date.today().isoformat()

    # ── Totales generales ────────────────────────────────
    total = conn.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0]

    # ── Por etapa ────────────────────────────────────────
    por_etapa = [
        {"etapa": r[0] or "Sin etapa", "cantidad": r[1]}
        for r in conn.execute(
            "SELECT etapa, COUNT(*) FROM expedientes GROUP BY etapa ORDER BY COUNT(*) DESC"
        ).fetchall()
    ]

    # ── Por estado ───────────────────────────────────────
    por_estado = [
        {"estado": r[0] or "Sin estado", "cantidad": r[1]}
        for r in conn.execute(
            "SELECT estado_proceso, COUNT(*) FROM expedientes GROUP BY estado_proceso ORDER BY COUNT(*) DESC"
        ).fetchall()
    ]

    # ── Por abogado ──────────────────────────────────────
    por_abogado = [
        {"abogado": r[0] or "Sin asignar", "cantidad": r[1]}
        for r in conn.execute(
            """SELECT nombre_abogado, COUNT(*)
               FROM expedientes
               GROUP BY nombre_abogado
               ORDER BY COUNT(*) DESC"""
        ).fetchall()
    ]

    # ── Por año ──────────────────────────────────────────
    por_anio = [
        {"anio": r[0] or "—", "cantidad": r[1]}
        for r in conn.execute(
            "SELECT anio, COUNT(*) FROM expedientes GROUP BY anio ORDER BY anio DESC"
        ).fetchall()
    ]

    # ── Alertas de vencimiento ───────────────────────────
    # Vencidos (cualquier fecha_vencimiento < hoy)
    vencidos = conn.execute("""
        SELECT COUNT(*) FROM expedientes
        WHERE (fecha_vencimiento_ind < ? AND estado_proceso NOT IN ('AUTO DE ARCHIVO','ARCHIVADO')
               AND fecha_vencimiento_ind IS NOT NULL)
           OR (fecha_vencimiento_inv < ? AND estado_proceso NOT IN ('AUTO DE ARCHIVO','ARCHIVADO')
               AND fecha_vencimiento_inv IS NOT NULL)
    """, (hoy, hoy)).fetchone()[0]

    # Próximos 30 días
    prox30 = conn.execute("""
        SELECT COUNT(*) FROM expedientes
        WHERE (fecha_vencimiento_ind BETWEEN ? AND date(?, '+30 days'))
           OR (fecha_vencimiento_inv BETWEEN ? AND date(?, '+30 days'))
    """, (hoy, hoy, hoy, hoy)).fetchone()[0]

    # Próximos 31-60 días
    prox60 = conn.execute("""
        SELECT COUNT(*) FROM expedientes
        WHERE (fecha_vencimiento_ind BETWEEN date(?, '+31 days') AND date(?, '+60 days'))
           OR (fecha_vencimiento_inv BETWEEN date(?, '+31 days') AND date(?, '+60 days'))
    """, (hoy, hoy, hoy, hoy)).fetchone()[0]

    # ── Expedientes próximos a vencer (detalle, top 15) ──
    proximos_lista = [
        _enriquecer_simple(row_to_dict(r))
        for r in conn.execute("""
            SELECT * FROM expedientes
            WHERE (
                (fecha_vencimiento_ind BETWEEN ? AND date(?, '+60 days'))
                OR (fecha_vencimiento_inv BETWEEN ? AND date(?, '+60 days'))
                OR (fecha_vencimiento_ind < ? AND estado_proceso NOT IN ('AUTO DE ARCHIVO','ARCHIVADO'))
                OR (fecha_vencimiento_inv < ? AND estado_proceso NOT IN ('AUTO DE ARCHIVO','ARCHIVADO'))
            )
            ORDER BY
                CASE WHEN fecha_vencimiento_ind < ? THEN fecha_vencimiento_ind
                     WHEN fecha_vencimiento_inv < ? THEN fecha_vencimiento_inv
                     ELSE MIN(COALESCE(fecha_vencimiento_ind,'9999'), COALESCE(fecha_vencimiento_inv,'9999'))
                END ASC
            LIMIT 15
        """, (hoy, hoy, hoy, hoy, hoy, hoy, hoy, hoy)).fetchall()
    ]

    # ── Expedientes recientes (últimos 10 creados) ───────
    recientes = [
        row_to_dict(r) for r in conn.execute(
            "SELECT * FROM expedientes ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
    ]

    conn.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active": "dashboard",
        "total": total,
        "por_etapa": por_etapa,
        "por_estado": por_estado,
        "por_abogado": por_abogado,
        "por_anio": por_anio,
        "vencidos": vencidos,
        "prox30": prox30,
        "prox60": prox60,
        "proximos_lista": proximos_lista,
        "recientes": recientes,
        "hoy": hoy,
    })


def _enriquecer_simple(exp: dict) -> dict:
    from app.database import calcular_alerta
    exp["alerta_ind"] = calcular_alerta(exp.get("fecha_vencimiento_ind"))
    exp["alerta_inv"] = calcular_alerta(exp.get("fecha_vencimiento_inv"))
    return exp
