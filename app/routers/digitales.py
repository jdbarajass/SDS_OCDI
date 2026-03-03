from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import date
import io

from app.database import get_db

router = APIRouter(prefix="/digitales")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _texto(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "nan", "None", "#VALUE!", "#N/A", "#REF!"):
        return None
    return s


def _fecha(v) -> str | None:
    if v is None:
        return None
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    if s in ("", "nan", "None", "#VALUE!", "#N/A"):
        return None
    # Accept YYYY-MM-DD or DD/MM/YYYY
    if len(s) == 10 and s[4] == "-":
        return s
    if len(s) == 10 and s[2] == "/":
        parts = s.split("/")
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return None


# ── Lista ──────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def lista(
    request: Request,
    q: str = "",
    abogado: str = "",
    etapa: str = "",
    anio: str = "",
    msg: str = "",
    page: int = 1,
    por_pagina: int = 20,
):
    conn = get_db()

    filtros = ["1=1"]
    params: list = []

    if q.strip():
        filtros.append("(n_expediente LIKE ? OR investigado LIKE ? OR radicado_auto LIKE ?)")
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if abogado.strip():
        filtros.append("abogado = ?")
        params.append(abogado.strip())
    if etapa.strip():
        filtros.append("etapa = ?")
        params.append(etapa.strip())
    if anio.strip():
        filtros.append("anio = ?")
        params.append(int(anio.strip()))

    where = " AND ".join(filtros)

    total = conn.execute(f"SELECT COUNT(*) FROM exp_digitales WHERE {where}", params).fetchone()[0]
    offset = (page - 1) * por_pagina
    rows = conn.execute(
        f"SELECT * FROM exp_digitales WHERE {where} ORDER BY anio DESC, n_expediente ASC LIMIT ? OFFSET ?",
        params + [por_pagina, offset],
    ).fetchall()

    abogados = [r[0] for r in conn.execute(
        "SELECT DISTINCT abogado FROM exp_digitales WHERE abogado IS NOT NULL ORDER BY abogado"
    ).fetchall()]
    etapas = [r[0] for r in conn.execute(
        "SELECT DISTINCT etapa FROM exp_digitales WHERE etapa IS NOT NULL ORDER BY etapa"
    ).fetchall()]
    anios = [r[0] for r in conn.execute(
        "SELECT DISTINCT anio FROM exp_digitales WHERE anio IS NOT NULL ORDER BY anio DESC"
    ).fetchall()]

    conn.close()

    total_pages = max(1, (total + por_pagina - 1) // por_pagina)

    return templates.TemplateResponse("digitales_lista.html", {
        "request": request,
        "active": "digitales_lista",
        "rows": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "por_pagina": por_pagina,
        "q": q,
        "abogado": abogado,
        "etapa": etapa,
        "anio": anio,
        "abogados": abogados,
        "etapas": etapas,
        "anios": anios,
        "msg": msg,
    })


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = get_db()

    total = conn.execute("SELECT COUNT(*) FROM exp_digitales").fetchone()[0]

    por_etapa = conn.execute("""
        SELECT etapa, COUNT(*) cant FROM exp_digitales
        WHERE etapa IS NOT NULL GROUP BY etapa ORDER BY cant DESC
    """).fetchall()

    por_abogado = conn.execute("""
        SELECT abogado, COUNT(*) cant FROM exp_digitales
        WHERE abogado IS NOT NULL GROUP BY abogado ORDER BY cant DESC
    """).fetchall()

    sin_respuesta = conn.execute("""
        SELECT COUNT(*) FROM exp_comunicaciones
        WHERE fecha_respuesta IS NULL OR fecha_respuesta = ''
    """).fetchone()[0]

    total_coms = conn.execute("SELECT COUNT(*) FROM exp_comunicaciones").fetchone()[0]

    queja_si = conn.execute(
        "SELECT COUNT(*) FROM exp_digitales WHERE queja_inicial = 'Sí' OR queja_inicial = 'Si' OR queja_inicial = 'SI'"
    ).fetchone()[0]

    por_anio = conn.execute("""
        SELECT anio, COUNT(*) cant FROM exp_digitales
        WHERE anio IS NOT NULL GROUP BY anio ORDER BY anio DESC
    """).fetchall()

    conn.close()

    return templates.TemplateResponse("digitales_dashboard.html", {
        "request": request,
        "active": "digitales_dash",
        "total": total,
        "por_etapa": [dict(r) for r in por_etapa],
        "por_abogado": [dict(r) for r in por_abogado],
        "sin_respuesta": sin_respuesta,
        "total_coms": total_coms,
        "queja_si": queja_si,
        "por_anio": [dict(r) for r in por_anio],
    })


# ── Nuevo ──────────────────────────────────────────────────────────────────────

@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo_form(request: Request):
    return templates.TemplateResponse("digitales_form.html", {
        "request": request,
        "active": "digitales_lista",
        "exp": {},
        "comunicaciones": [],
        "modo": "nuevo",
    })


@router.post("/nuevo")
async def nuevo_post(
    request: Request,
    n_expediente: str = Form(""),
    anio: str = Form(""),
    abogado: str = Form(""),
    etapa: str = Form(""),
    queja_inicial: str = Form("No"),
    radicado_auto: str = Form(""),
    nombre_auto: str = Form(""),
    fecha_auto: str = Form(""),
):
    conn = get_db()
    conn.execute("""
        INSERT INTO exp_digitales (n_expediente, anio, abogado, etapa, queja_inicial,
            radicado_auto, nombre_auto, fecha_auto)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        _texto(n_expediente), int(anio) if anio.strip() else None,
        _texto(abogado), _texto(etapa), queja_inicial or "No",
        _texto(radicado_auto), _texto(nombre_auto), _fecha(fecha_auto),
    ))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return RedirectResponse(f"/digitales/{new_id}?msg=creado", status_code=303)


# ── Detalle ────────────────────────────────────────────────────────────────────

@router.get("/{exp_id}", response_class=HTMLResponse)
async def detalle(request: Request, exp_id: int, msg: str = ""):
    conn = get_db()
    exp = conn.execute("SELECT * FROM exp_digitales WHERE id = ?", (exp_id,)).fetchone()
    if not exp:
        conn.close()
        return RedirectResponse("/digitales/?msg=no_encontrado")
    comunicaciones = conn.execute(
        "SELECT * FROM exp_comunicaciones WHERE exp_digital_id = ? ORDER BY fecha_envio ASC, id ASC",
        (exp_id,)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("digitales_detalle.html", {
        "request": request,
        "active": "digitales_lista",
        "exp": dict(exp),
        "comunicaciones": [dict(c) for c in comunicaciones],
        "msg": msg,
    })


# ── Editar ─────────────────────────────────────────────────────────────────────

@router.get("/{exp_id}/editar", response_class=HTMLResponse)
async def editar_form(request: Request, exp_id: int):
    conn = get_db()
    exp = conn.execute("SELECT * FROM exp_digitales WHERE id = ?", (exp_id,)).fetchone()
    if not exp:
        conn.close()
        return RedirectResponse("/digitales/?msg=no_encontrado")
    comunicaciones = conn.execute(
        "SELECT * FROM exp_comunicaciones WHERE exp_digital_id = ? ORDER BY fecha_envio ASC, id ASC",
        (exp_id,)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("digitales_form.html", {
        "request": request,
        "active": "digitales_lista",
        "exp": dict(exp),
        "comunicaciones": [dict(c) for c in comunicaciones],
        "modo": "editar",
    })


@router.post("/{exp_id}/editar")
async def editar_post(
    request: Request,
    exp_id: int,
    n_expediente: str = Form(""),
    anio: str = Form(""),
    abogado: str = Form(""),
    etapa: str = Form(""),
    queja_inicial: str = Form("No"),
    radicado_auto: str = Form(""),
    nombre_auto: str = Form(""),
    fecha_auto: str = Form(""),
):
    conn = get_db()
    conn.execute("""
        UPDATE exp_digitales SET n_expediente=?, anio=?, abogado=?, etapa=?, queja_inicial=?,
            radicado_auto=?, nombre_auto=?, fecha_auto=?,
            updated_at=datetime('now','localtime')
        WHERE id=?
    """, (
        _texto(n_expediente), int(anio) if anio.strip() else None,
        _texto(abogado), _texto(etapa), queja_inicial or "No",
        _texto(radicado_auto), _texto(nombre_auto), _fecha(fecha_auto),
        exp_id,
    ))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/digitales/{exp_id}?msg=actualizado", status_code=303)


# ── Eliminar expediente ────────────────────────────────────────────────────────

@router.post("/{exp_id}/eliminar")
async def eliminar(exp_id: int):
    conn = get_db()
    row = conn.execute("SELECT n_expediente FROM exp_digitales WHERE id = ?", (exp_id,)).fetchone()
    if row:
        n = row[0] or str(exp_id)
        conn.execute("DELETE FROM exp_digitales WHERE id = ?", (exp_id,))
        conn.commit()
        conn.close()
        return RedirectResponse(f"/digitales/?msg=eliminado_{n}", status_code=303)
    conn.close()
    return RedirectResponse("/digitales/?msg=no_encontrado", status_code=303)


# ── Comunicaciones ─────────────────────────────────────────────────────────────

@router.post("/{exp_id}/comunicacion/nueva")
async def com_nueva(
    exp_id: int,
    radicado_comunicacion: str = Form(""),
    dependencia: str = Form(""),
    fecha_envio: str = Form(""),
    fecha_seguimiento: str = Form(""),
    radicado_respuesta: str = Form(""),
    fecha_respuesta: str = Form(""),
    responsable: str = Form(""),
    observaciones: str = Form(""),
):
    conn = get_db()
    conn.execute("""
        INSERT INTO exp_comunicaciones
            (exp_digital_id, radicado_comunicacion, dependencia, fecha_envio,
             fecha_seguimiento, radicado_respuesta, fecha_respuesta, responsable, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        exp_id,
        _texto(radicado_comunicacion), _texto(dependencia),
        _fecha(fecha_envio), _fecha(fecha_seguimiento),
        _texto(radicado_respuesta), _fecha(fecha_respuesta),
        _texto(responsable), _texto(observaciones),
    ))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/digitales/{exp_id}?msg=com_creada", status_code=303)


@router.post("/comunicacion/{com_id}/editar")
async def com_editar(
    com_id: int,
    radicado_comunicacion: str = Form(""),
    dependencia: str = Form(""),
    fecha_envio: str = Form(""),
    fecha_seguimiento: str = Form(""),
    radicado_respuesta: str = Form(""),
    fecha_respuesta: str = Form(""),
    responsable: str = Form(""),
    observaciones: str = Form(""),
):
    conn = get_db()
    row = conn.execute("SELECT exp_digital_id FROM exp_comunicaciones WHERE id = ?", (com_id,)).fetchone()
    if not row:
        conn.close()
        return RedirectResponse("/digitales/", status_code=303)
    exp_id = row[0]
    conn.execute("""
        UPDATE exp_comunicaciones SET
            radicado_comunicacion=?, dependencia=?, fecha_envio=?,
            fecha_seguimiento=?, radicado_respuesta=?, fecha_respuesta=?,
            responsable=?, observaciones=?
        WHERE id=?
    """, (
        _texto(radicado_comunicacion), _texto(dependencia),
        _fecha(fecha_envio), _fecha(fecha_seguimiento),
        _texto(radicado_respuesta), _fecha(fecha_respuesta),
        _texto(responsable), _texto(observaciones),
        com_id,
    ))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/digitales/{exp_id}?msg=com_actualizada", status_code=303)


@router.post("/comunicacion/{com_id}/eliminar")
async def com_eliminar(com_id: int):
    conn = get_db()
    row = conn.execute("SELECT exp_digital_id FROM exp_comunicaciones WHERE id = ?", (com_id,)).fetchone()
    if not row:
        conn.close()
        return RedirectResponse("/digitales/", status_code=303)
    exp_id = row[0]
    conn.execute("DELETE FROM exp_comunicaciones WHERE id = ?", (com_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/digitales/{exp_id}?msg=com_eliminada", status_code=303)


# ── Importar Excel ─────────────────────────────────────────────────────────────

@router.get("/importar", response_class=HTMLResponse)
async def importar_form(request: Request, msg: str = ""):
    return templates.TemplateResponse("digitales_importar.html", {
        "request": request,
        "active": "digitales_importar",
        "msg": msg,
        "resultado": None,
    })


@router.post("/importar", response_class=HTMLResponse)
async def importar_post(request: Request, archivo: UploadFile = File(...)):
    try:
        import openpyxl
    except ImportError:
        return templates.TemplateResponse("digitales_importar.html", {
            "request": request,
            "active": "digitales_importar",
            "msg": "error_openpyxl",
            "resultado": None,
        })

    contenido = await archivo.read()
    wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)

    # Seleccionar hoja
    hoja = None
    for nombre in wb.sheetnames:
        if "EXP DIGIT" in nombre.upper() or "EXPEDIENTE" in nombre.upper() or "DIGIT" in nombre.upper():
            hoja = wb[nombre]
            break
    if hoja is None:
        hoja = wb.active

    conn = get_db()
    exp_insertados = 0
    exp_omitidos = 0
    coms_insertadas = 0
    ultimo_exp_id: int | None = None

    for idx, row in enumerate(hoja.iter_rows(values_only=True)):
        if idx < 2:  # fila 0 = título, fila 1 = cabeceras
            continue

        col = list(row)
        # Asegurar al menos 16 columnas
        while len(col) < 16:
            col.append(None)

        n_exp = _texto(col[0])
        radicado_com = _texto(col[8])

        if n_exp:
            # Fila padre — expediente
            anio_val = col[1]
            try:
                anio_int = int(anio_val) if anio_val else None
            except (ValueError, TypeError):
                anio_int = None

            # Verificar duplicado
            existing = conn.execute(
                "SELECT id FROM exp_digitales WHERE n_expediente = ? AND anio = ?",
                (n_exp, anio_int)
            ).fetchone()

            if existing:
                ultimo_exp_id = existing[0]
                exp_omitidos += 1
            else:
                conn.execute("""
                    INSERT INTO exp_digitales
                        (n_expediente, anio, abogado, etapa, queja_inicial,
                         radicado_auto, nombre_auto, fecha_auto)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    n_exp, anio_int,
                    _texto(col[2]), _texto(col[3]),
                    _texto(col[4]) or "No",
                    _texto(col[5]), _texto(col[6]), _fecha(col[7]),
                ))
                ultimo_exp_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                exp_insertados += 1

            # Si la fila padre también tiene comunicación (col 9 = radicado_com)
            radicado_com_padre = _texto(col[8])
            if radicado_com_padre and ultimo_exp_id:
                conn.execute("""
                    INSERT INTO exp_comunicaciones
                        (exp_digital_id, radicado_comunicacion, dependencia, fecha_envio,
                         fecha_seguimiento, radicado_respuesta, fecha_respuesta, responsable, observaciones)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ultimo_exp_id,
                    radicado_com_padre,
                    _texto(col[9]), _fecha(col[10]), _fecha(col[11]),
                    _texto(col[12]), _fecha(col[13]), _texto(col[14]), _texto(col[15]),
                ))
                coms_insertadas += 1

        elif radicado_com and ultimo_exp_id:
            # Fila hija — comunicación del último expediente
            conn.execute("""
                INSERT INTO exp_comunicaciones
                    (exp_digital_id, radicado_comunicacion, dependencia, fecha_envio,
                     fecha_seguimiento, radicado_respuesta, fecha_respuesta, responsable, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ultimo_exp_id,
                radicado_com,
                _texto(col[9]), _fecha(col[10]), _fecha(col[11]),
                _texto(col[12]), _fecha(col[13]), _texto(col[14]), _texto(col[15]),
            ))
            coms_insertadas += 1

    conn.commit()
    conn.close()

    resultado = {
        "exp_insertados": exp_insertados,
        "exp_omitidos": exp_omitidos,
        "coms_insertadas": coms_insertadas,
    }

    return templates.TemplateResponse("digitales_importar.html", {
        "request": request,
        "active": "digitales_importar",
        "msg": "ok",
        "resultado": resultado,
    })


# ── Exportar Excel ─────────────────────────────────────────────────────────────

@router.get("/exportar")
async def exportar():
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return RedirectResponse("/digitales/?msg=error_openpyxl")

    conn = get_db()
    exps = conn.execute("SELECT * FROM exp_digitales ORDER BY anio DESC, n_expediente ASC").fetchall()
    coms = conn.execute(
        "SELECT * FROM exp_comunicaciones ORDER BY exp_digital_id ASC, fecha_envio ASC, id ASC"
    ).fetchall()
    conn.close()

    # Agrupar comunicaciones por exp_id
    coms_por_exp: dict[int, list] = {}
    for c in coms:
        eid = c["exp_digital_id"]
        coms_por_exp.setdefault(eid, []).append(dict(c))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "EXP DIGIT 2025-2026"

    header_fill = PatternFill("solid", fgColor="1e3a5f")
    header_font = Font(bold=True, color="FFFFFF")
    sub_fill = PatternFill("solid", fgColor="dbeafe")

    cabeceras = [
        "N° Expediente", "Año", "Abogado", "Etapa", "Queja Inicial",
        "Radicado Auto", "Nombre Auto", "Fecha Auto",
        "Radicado Comunicación", "Dependencia", "Fecha Envío",
        "Fecha Seguimiento", "Radicado Respuesta", "Fecha Respuesta",
        "Responsable", "Observaciones",
    ]
    ws.append(["SEGUIMIENTO EXPEDIENTES DIGITALES"])
    ws.append(cabeceras)
    for cell in ws[2]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for exp in exps:
        ed = dict(exp)
        exp_coms = coms_por_exp.get(ed["id"], [])
        primera_com = exp_coms[0] if exp_coms else {}

        row = [
            ed.get("n_expediente"), ed.get("anio"), ed.get("abogado"), ed.get("etapa"),
            ed.get("queja_inicial"), ed.get("radicado_auto"), ed.get("nombre_auto"), ed.get("fecha_auto"),
            primera_com.get("radicado_comunicacion"), primera_com.get("dependencia"),
            primera_com.get("fecha_envio"), primera_com.get("fecha_seguimiento"),
            primera_com.get("radicado_respuesta"), primera_com.get("fecha_respuesta"),
            primera_com.get("responsable"), primera_com.get("observaciones"),
        ]
        ws.append(row)

        for com in exp_coms[1:]:
            sub_row = [
                None, None, None, None, None, None, None, None,
                com.get("radicado_comunicacion"), com.get("dependencia"),
                com.get("fecha_envio"), com.get("fecha_seguimiento"),
                com.get("radicado_respuesta"), com.get("fecha_respuesta"),
                com.get("responsable"), com.get("observaciones"),
            ]
            ws.append(sub_row)
            for cell in ws[ws.max_row]:
                cell.fill = sub_fill

    # Anchos de columna
    col_widths = [15, 6, 22, 20, 14, 20, 30, 14, 22, 25, 14, 16, 22, 14, 20, 40]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    hoy = date.today().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=exp_digitales_{hoy}.xlsx"},
    )
