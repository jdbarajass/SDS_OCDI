from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from app.template_utils import make_templates
from datetime import date, timedelta
import calendar

from app.database import get_db
from app.auth_utils import tpl, puede_escribir as _pw, registrar_log

_MOD = "sala"

router = APIRouter(prefix="/sala")
templates = make_templates(str(Path(__file__).parent.parent / "templates"))

FRANJAS = ["08:00-10:00", "10:00-12:00", "14:00-16:00", "16:00-18:00"]
ESTADOS = ["Ocupado"]


def _build_calendar(year: int, month: int, eventos: list[dict]) -> list[list[dict | None]]:
    """Devuelve semanas (lista de listas de 7 celdas).
    Cada celda es None (fuera del mes) o dict con day, fecha, franjas_estado."""

    # Mapear eventos por fecha → franja → evento
    por_fecha: dict[str, dict[str, dict]] = {}
    for ev in eventos:
        f = ev["fecha"]
        por_fecha.setdefault(f, {})[ev["franja"]] = ev

    cal = calendar.Calendar(firstweekday=0)  # Lunes primero
    semanas: list[list[dict | None]] = []
    for semana in cal.monthdatescalendar(year, month):
        fila = []
        for d in semana:
            if d.month != month:
                fila.append(None)
            else:
                fecha_str = d.isoformat()
                franjas_info = []
                for franja in FRANJAS:
                    ev = por_fecha.get(fecha_str, {}).get(franja)
                    franjas_info.append({
                        "franja": franja,
                        "evento": ev,
                        "estado": ev["estado"] if ev else None,
                    })
                fila.append({
                    "day": d.day,
                    "fecha": fecha_str,
                    "es_hoy": d == date.today(),
                    "franjas": franjas_info,
                })
        semanas.append(fila)
    return semanas


# ── Calendario ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def calendario(
    request: Request,
    year: int = 0,
    month: int = 0,
    msg: str = "",
):
    hoy = date.today()
    if not year:
        year = hoy.year
    if not month:
        month = hoy.month

    # Primer y último día del mes para consulta
    primer_dia = date(year, month, 1).isoformat()
    ultimo_dia = date(year, month, calendar.monthrange(year, month)[1]).isoformat()

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM sala_agenda WHERE fecha BETWEEN ? AND ? ORDER BY fecha, franja",
        (primer_dia, ultimo_dia),
    ).fetchall()
    conn.close()

    eventos = [dict(r) for r in rows]
    semanas = _build_calendar(year, month, eventos)

    # Mes anterior / siguiente
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    nombre_mes = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ][month]

    return templates.TemplateResponse("sala.html", tpl(request, _MOD,
        active="sala", year=year, month=month, nombre_mes=nombre_mes,
        semanas=semanas, franjas=FRANJAS, estados=ESTADOS,
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month, msg=msg,
    ))


# ── Nuevo evento ───────────────────────────────────────────────────────────────

@router.get("/evento/nuevo", response_class=HTMLResponse)
async def evento_nuevo_form(
    request: Request,
    fecha: str = "",
    franja: str = "",
):
    user = getattr(request.state, "user", None)
    if not _pw(user, _MOD):
        return RedirectResponse("/sala/?msg=sin_permiso", status_code=303)
    if not fecha:
        fecha = date.today().isoformat()
    return templates.TemplateResponse("sala_form.html", tpl(request, _MOD,
        active="sala", ev={"fecha": fecha, "franja": franja},
        franjas=FRANJAS, estados=ESTADOS, modo="nuevo",
    ))


@router.post("/evento/nuevo")
async def evento_nuevo_post(
    request: Request,
    fecha: str = Form(...),
    franja: str = Form(...),
    titulo: str = Form(""),
    descripcion: str = Form(""),
    estado: str = Form("Ocupado"),
    responsable: str = Form(""),
):
    user = getattr(request.state, "user", None)
    if not _pw(user, _MOD):
        return RedirectResponse("/sala/?msg=sin_permiso", status_code=303)
    conn = get_db()
    conn.execute("""
        INSERT INTO sala_agenda (fecha, franja, titulo, descripcion, estado, responsable)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (fecha, franja, titulo or None, descripcion or None, estado, responsable or None))
    conn.commit()
    conn.close()

    y, m, _ = fecha.split("-")
    return RedirectResponse(f"/sala/?year={y}&month={m}&msg=creado", status_code=303)


# ── Editar evento ──────────────────────────────────────────────────────────────

@router.get("/evento/{ev_id}/editar", response_class=HTMLResponse)
async def evento_editar_form(request: Request, ev_id: int):
    user = getattr(request.state, "user", None)
    if not _pw(user, _MOD):
        return RedirectResponse("/sala/?msg=sin_permiso", status_code=303)
    conn = get_db()
    ev = conn.execute("SELECT * FROM sala_agenda WHERE id = ?", (ev_id,)).fetchone()
    conn.close()
    if not ev:
        return RedirectResponse("/sala/?msg=no_encontrado")
    return templates.TemplateResponse("sala_form.html", tpl(request, _MOD,
        active="sala", ev=dict(ev), franjas=FRANJAS, estados=ESTADOS, modo="editar",
    ))


@router.post("/evento/{ev_id}/editar")
async def evento_editar_post(
    request: Request,
    ev_id: int,
    fecha: str = Form(...),
    franja: str = Form(...),
    titulo: str = Form(""),
    descripcion: str = Form(""),
    estado: str = Form("Ocupado"),
    responsable: str = Form(""),
):
    user = getattr(request.state, "user", None)
    if not _pw(user, _MOD):
        return RedirectResponse("/sala/?msg=sin_permiso", status_code=303)
    conn = get_db()
    conn.execute("""
        UPDATE sala_agenda SET fecha=?, franja=?, titulo=?, descripcion=?, estado=?, responsable=?
        WHERE id=?
    """, (fecha, franja, titulo or None, descripcion or None, estado, responsable or None, ev_id))
    conn.commit()
    conn.close()

    y, m, _ = fecha.split("-")
    return RedirectResponse(f"/sala/?year={y}&month={m}&msg=actualizado", status_code=303)


# ── Eliminar evento ────────────────────────────────────────────────────────────

@router.post("/evento/{ev_id}/eliminar")
async def evento_eliminar(request: Request, ev_id: int):
    user = getattr(request.state, "user", None)
    if not _pw(user, _MOD):
        return RedirectResponse("/sala/?msg=sin_permiso", status_code=303)
    conn = get_db()
    ev = conn.execute("SELECT fecha FROM sala_agenda WHERE id = ?", (ev_id,)).fetchone()
    if ev:
        fecha = ev[0]
        conn.execute("DELETE FROM sala_agenda WHERE id = ?", (ev_id,))
        conn.commit()
        conn.close()
        y, m, _ = fecha.split("-")
        return RedirectResponse(f"/sala/?year={y}&month={m}&msg=eliminado", status_code=303)
    conn.close()
    return RedirectResponse("/sala/?msg=no_encontrado", status_code=303)
