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

ESTADOS = ["Ocupado"]

PERSONAL_OFICINA = [
    "ANDRES EDUARDO SANDOVAL MAYORGA",
    "CARLOS ALFONSO PARRA MALAVER",
    "CESAR IVAN RODRIGUEZ DAMIAN",
    "DAVID FELIPE MORALES NOGUERA",
    "JANIK HERNANDO DE LA HOZ RIOS",
    "JOSE DE JESUS BARAJAS SOTELO",
    "LUNA GICELL GUZMAN YATE",
    "MABEL GICELLA HURTADO SANCHEZ",
    "MAGDA XIMENA PAREDES LIEVANO",
    "MARA LUCIA UCROS MERLANO",
    "MARTHA PATRICIA AÑEZ MAESTRE",
    "RODOLFO CARRILLO QUINTERO",
]

TODO_EL_DIA = "TODO EL DÍA"


def _parse_franja(franja: str) -> tuple[str, str]:
    """Extrae hora_inicio y hora_fin de una cadena 'HH:MM-HH:MM'. Devuelve vacío para TODO EL DÍA."""
    if franja == TODO_EL_DIA:
        return "", ""
    if franja and len(franja) >= 11 and franja[5] == "-":
        return franja[:5], franja[6:]
    return "", ""


def _build_calendar(year: int, month: int, eventos: list[dict]) -> list[list[dict | None]]:
    """Devuelve semanas (lista de listas de 7 celdas).
    Cada celda es None (fuera del mes) o dict con day, fecha, eventos (lista)."""

    por_fecha: dict[str, list[dict]] = {}
    for ev in eventos:
        por_fecha.setdefault(ev["fecha"], []).append(ev)

    cal = calendar.Calendar(firstweekday=0)  # Lunes primero
    semanas: list[list[dict | None]] = []
    for semana in cal.monthdatescalendar(year, month):
        fila = []
        for d in semana:
            if d.month != month:
                fila.append(None)
            else:
                fecha_str = d.isoformat()
                fila.append({
                    "day": d.day,
                    "fecha": fecha_str,
                    "es_hoy": d == date.today(),
                    "eventos": por_fecha.get(fecha_str, []),
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
        semanas=semanas, estados=ESTADOS,
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
    hora_inicio, hora_fin = _parse_franja(franja)
    return templates.TemplateResponse("sala_form.html", tpl(request, _MOD,
        active="sala",
        ev={"fecha": fecha, "franja": franja, "hora_inicio": hora_inicio, "hora_fin": hora_fin},
        estados=ESTADOS, modo="nuevo",
        personal=PERSONAL_OFICINA,
        TODO_EL_DIA=TODO_EL_DIA,
    ))


@router.post("/evento/nuevo")
async def evento_nuevo_post(
    request: Request,
    fecha: str = Form(...),
    hora_inicio: str = Form(""),
    hora_fin: str = Form(""),
    todo_el_dia: str = Form(""),
    titulo: str = Form(""),
    descripcion: str = Form(""),
    estado: str = Form("Ocupado"),
    responsable: str = Form(""),
):
    user = getattr(request.state, "user", None)
    if not _pw(user, _MOD):
        return RedirectResponse("/sala/?msg=sin_permiso", status_code=303)
    franja = TODO_EL_DIA if todo_el_dia else f"{hora_inicio}-{hora_fin}"
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
    ev_dict = dict(ev)
    ev_dict["hora_inicio"], ev_dict["hora_fin"] = _parse_franja(ev_dict.get("franja", ""))
    return templates.TemplateResponse("sala_form.html", tpl(request, _MOD,
        active="sala", ev=ev_dict, estados=ESTADOS, modo="editar",
        personal=PERSONAL_OFICINA,
        TODO_EL_DIA=TODO_EL_DIA,
    ))


@router.post("/evento/{ev_id}/editar")
async def evento_editar_post(
    request: Request,
    ev_id: int,
    fecha: str = Form(...),
    hora_inicio: str = Form(""),
    hora_fin: str = Form(""),
    todo_el_dia: str = Form(""),
    titulo: str = Form(""),
    descripcion: str = Form(""),
    estado: str = Form("Ocupado"),
    responsable: str = Form(""),
):
    user = getattr(request.state, "user", None)
    if not _pw(user, _MOD):
        return RedirectResponse("/sala/?msg=sin_permiso", status_code=303)
    franja = TODO_EL_DIA if todo_el_dia else f"{hora_inicio}-{hora_fin}"
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
