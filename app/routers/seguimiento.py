from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import date

from app.database import get_db, row_to_dict

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

MESES_ORD = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO",
             "JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]


@router.get("/seguimiento", response_class=HTMLResponse)
async def seguimiento_lista(
    request: Request,
    anio: str = "",
    abogado: str = "",
    mes: str = "",
    q: str = "",
):
    anio_actual = str(date.today().year)
    anio_sel = anio or anio_actual

    conn = get_db()
    # Filtros de expedientes
    filtros, params_q = [], []
    if q:
        filtros.append("(e.n_expediente LIKE ? OR e.investigado LIKE ?)")
        params_q += [f"%{q}%", f"%{q}%"]
    if abogado:
        filtros.append("e.nombre_abogado = ?")
        params_q.append(abogado)

    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""

    expedientes = [row_to_dict(r) for r in conn.execute(
        f"SELECT * FROM expedientes {where} ORDER BY n_expediente ASC", params_q
    ).fetchall()]

    # Cargar todas las actuaciones del año seleccionado
    acts_rows = conn.execute(
        "SELECT * FROM actuaciones WHERE anio = ?", (anio_sel,)
    ).fetchall()
    # Indexar por (expediente_id, mes)
    acts_map = {}
    for r in acts_rows:
        a = row_to_dict(r)
        key = (a["expediente_id"], a["mes"])
        acts_map[key] = a

    abogados = [r[0] for r in conn.execute(
        "SELECT DISTINCT nombre_abogado FROM expedientes WHERE nombre_abogado IS NOT NULL ORDER BY nombre_abogado"
    ).fetchall()]
    anios = [r[0] for r in conn.execute(
        "SELECT DISTINCT anio FROM expedientes WHERE anio IS NOT NULL ORDER BY anio DESC"
    ).fetchall()]
    conn.close()

    return templates.TemplateResponse("seguimiento.html", {
        "request": request,
        "active": "seguimiento",
        "expedientes": expedientes,
        "acts_map": acts_map,
        "meses": MESES_ORD,
        "anio_sel": anio_sel,
        "abogados": abogados,
        "anios": anios,
        "abogado_sel": abogado,
        "q": q,
    })


@router.post("/seguimiento/guardar")
async def guardar_actuacion(request: Request):
    form = await request.form()
    exp_id  = int(form.get("expediente_id"))
    anio    = int(form.get("anio"))
    mes     = form.get("mes", "").strip()
    desc    = form.get("descripcion", "").strip()
    created_by = form.get("created_by", "").strip() or None

    conn = get_db()
    # Verificar si ya existe una actuación para ese mes/año/expediente
    existente = conn.execute(
        "SELECT id FROM actuaciones WHERE expediente_id=? AND anio=? AND mes=?",
        (exp_id, anio, mes)
    ).fetchone()

    if existente:
        if desc:
            conn.execute(
                "UPDATE actuaciones SET descripcion=?, created_by=?, created_at=datetime('now','localtime') WHERE id=?",
                (desc, created_by, existente["id"])
            )
        else:
            conn.execute("DELETE FROM actuaciones WHERE id=?", (existente["id"],))
    elif desc:
        conn.execute(
            "INSERT INTO actuaciones (expediente_id, mes, anio, descripcion, created_by) VALUES (?,?,?,?,?)",
            (exp_id, mes, anio, desc, created_by)
        )
    conn.commit()
    conn.close()

    # Redirigir de vuelta al seguimiento con el mismo año
    return RedirectResponse(f"/seguimiento?anio={anio}&msg=guardado", status_code=303)
