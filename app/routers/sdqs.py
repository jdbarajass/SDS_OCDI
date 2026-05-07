from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pathlib import Path
from app.template_utils import make_templates
import io

from app.database import get_db, row_to_dict
from app.auth_utils import tpl, puede_escribir as _pw, registrar_log

_MOD = "sdqs"

router = APIRouter(prefix="/sdqs")
templates = make_templates(str(Path(__file__).parent.parent / "templates"))

MESES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
]

ESTADOS_PROCESO = [
    "INDAGACION PREVIA",
    "INVESTIGACION DISCIPLINARIA",
    "INHIBITORIO",
]

ABOGADOS = [
    "CARLOS ALFONSO PARRA MALAVER",
    "CESAR IVAN RODRIGUEZ DAMIAN",
    "DAVID FELIPE MORALES NOGUERA",
    "JANIK HERNANDO DE LA HOZ RIOS",
    "MABEL GICELLA HURTADO SANCHEZ",
    "MARA LUCIA UCROS MERLANO",
    "RODOLFO CARRILLO QUINTERO",
    "ANDRES EDUARDO SANDOVAL MAYORGA",
    "MAGDA XIMENA PAREDES LIEVANO",
    "LUNA GICELL GUZMAN YATE",
    "MARTHA PATRICIA AÑEZ MAESTRE",
]

RESP_MAP = {
    "CESAR RODRIGUEZ":      "CESAR IVAN RODRIGUEZ DAMIAN",
    "DAVID MORALES":        "DAVID FELIPE MORALES NOGUERA",
    "MARA OCRUS":           "MARA LUCIA UCROS MERLANO",
    "MABEL GICELLA HURTADO": "MABEL GICELLA HURTADO SANCHEZ",
    "CARLOS PARRA":         "CARLOS ALFONSO PARRA MALAVER",
    "ANDRES SANDOVAL":      "ANDRES EDUARDO SANDOVAL MAYORGA",
}

_PAGE_SIZE = 25


def _str(val) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    return s if s.upper() != "NAN" else ""


# ── Lista ─────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def lista(
    request: Request,
    mes: str = "",
    competencia_ocdi: str = "",
    responsable: str = "",
    q: str = "",
    page: int = 1,
    msg: str = "",
):
    conn = get_db()
    where, params = ["1=1"], []
    if mes:
        where.append("UPPER(mes) = ?")
        params.append(mes.upper())
    if competencia_ocdi:
        where.append("UPPER(competencia_ocdi) = ?")
        params.append(competencia_ocdi.upper())
    if responsable:
        where.append("UPPER(responsable) = ?")
        params.append(responsable.upper())
    if q:
        where.append("(UPPER(sdqs) LIKE ? OR UPPER(quejoso) LIKE ? OR UPPER(tema) LIKE ?)")
        like = f"%{q.upper()}%"
        params += [like, like, like]

    sql_base = f"FROM sdqs WHERE {' AND '.join(where)}"
    total = conn.execute(f"SELECT COUNT(*) {sql_base}", params).fetchone()[0]
    offset = (page - 1) * _PAGE_SIZE
    rows = conn.execute(
        f"SELECT * {sql_base} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [_PAGE_SIZE, offset],
    ).fetchall()

    meses_bd = [r[0] for r in conn.execute("SELECT DISTINCT mes FROM sdqs WHERE mes IS NOT NULL ORDER BY mes").fetchall()]
    responsables_bd = [r[0] for r in conn.execute("SELECT DISTINCT responsable FROM sdqs WHERE responsable IS NOT NULL AND responsable != '' ORDER BY responsable").fetchall()]
    conn.close()

    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
    registros = [row_to_dict(r) for r in rows]

    return templates.TemplateResponse("sdqs_lista.html", tpl(request, _MOD,
        registros=registros,
        total=total,
        page=page,
        total_pages=total_pages,
        meses_bd=meses_bd,
        responsables_bd=responsables_bd,
        fil_mes=mes,
        fil_competencia=competencia_ocdi,
        fil_responsable=responsable,
        fil_q=q,
        msg=msg,
    ))


# ── Nuevo ─────────────────────────────────────────────────────────────────────

@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo_get(request: Request):
    return templates.TemplateResponse("sdqs_form.html", tpl(request, _MOD,
        modo="nuevo",
        registro={},
        meses=MESES,
        abogados=ABOGADOS,
        estados=ESTADOS_PROCESO,
    ))


@router.post("/nuevo")
async def nuevo_post(
    request: Request,
    mes: str = Form(""),
    fecha_radicado: str = Form(""),
    sdqs_num: str = Form("", alias="sdqs"),
    quejoso: str = Form(""),
    correo: str = Form(""),
    tema: str = Form(""),
    competencia_ocdi: str = Form("NO"),
    bpm: str = Form(""),
    responsable: str = Form(""),
    rad_salida: str = Form(""),
    fecha_respuesta: str = Form(""),
    observaciones: str = Form(""),
    estado_proceso: str = Form(""),
    hecho_corrupto: str = Form(""),
    valor_institucional: str = Form(""),
    tipologia: str = Form(""),
):
    user = request.state.user
    if not _pw(user, _MOD):
        return RedirectResponse(f"/sdqs/?msg=sin_permiso", status_code=303)

    obligatorios = [mes, fecha_radicado, sdqs_num, quejoso, correo, tema, competencia_ocdi, observaciones]
    if any(not v.strip() for v in obligatorios):
        return RedirectResponse(f"/sdqs/nuevo?msg=error_obligatorios", status_code=303)

    conn = get_db()
    conn.execute(
        """INSERT INTO sdqs
           (mes, fecha_radicado, sdqs, quejoso, correo, tema, competencia_ocdi,
            bpm, responsable, rad_salida, fecha_respuesta, observaciones,
            estado_proceso, hecho_corrupto, valor_institucional, tipologia, created_by)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (mes.upper(), fecha_radicado, sdqs_num.upper(), quejoso.upper(), correo,
         tema.upper(), competencia_ocdi.upper(),
         bpm or None, responsable or None, rad_salida or None, fecha_respuesta or None,
         observaciones, estado_proceso or None, hecho_corrupto or None,
         valor_institucional or None, tipologia or None,
         user.get("nombre_completo") if user else None),
    )
    conn.commit()
    conn.close()
    registrar_log(user, "crear", _MOD, f"SDQS: {sdqs_num}")
    return RedirectResponse("/sdqs/?msg=creado", status_code=303)


# ── Ver ───────────────────────────────────────────────────────────────────────

@router.get("/{id}", response_class=HTMLResponse)
async def ver(request: Request, id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM sdqs WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not row:
        return RedirectResponse("/sdqs/?msg=no_encontrado", status_code=303)
    return templates.TemplateResponse("sdqs_form.html", tpl(request, _MOD,
        modo="ver",
        registro=row_to_dict(row),
        meses=MESES,
        abogados=ABOGADOS,
        estados=ESTADOS_PROCESO,
    ))


# ── Editar ────────────────────────────────────────────────────────────────────

@router.get("/{id}/editar", response_class=HTMLResponse)
async def editar_get(request: Request, id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM sdqs WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not row:
        return RedirectResponse("/sdqs/?msg=no_encontrado", status_code=303)
    return templates.TemplateResponse("sdqs_form.html", tpl(request, _MOD,
        modo="editar",
        registro=row_to_dict(row),
        meses=MESES,
        abogados=ABOGADOS,
        estados=ESTADOS_PROCESO,
    ))


@router.post("/{id}/editar")
async def editar_post(
    request: Request,
    id: int,
    mes: str = Form(""),
    fecha_radicado: str = Form(""),
    sdqs_num: str = Form("", alias="sdqs"),
    quejoso: str = Form(""),
    correo: str = Form(""),
    tema: str = Form(""),
    competencia_ocdi: str = Form("NO"),
    bpm: str = Form(""),
    responsable: str = Form(""),
    rad_salida: str = Form(""),
    fecha_respuesta: str = Form(""),
    observaciones: str = Form(""),
    estado_proceso: str = Form(""),
    hecho_corrupto: str = Form(""),
    valor_institucional: str = Form(""),
    tipologia: str = Form(""),
):
    user = request.state.user
    if not _pw(user, _MOD):
        return RedirectResponse(f"/sdqs/?msg=sin_permiso", status_code=303)

    conn = get_db()
    conn.execute(
        """UPDATE sdqs SET
           mes=?, fecha_radicado=?, sdqs=?, quejoso=?, correo=?, tema=?,
           competencia_ocdi=?, bpm=?, responsable=?, rad_salida=?,
           fecha_respuesta=?, observaciones=?, estado_proceso=?,
           hecho_corrupto=?, valor_institucional=?, tipologia=?,
           updated_at=datetime('now','localtime')
           WHERE id=?""",
        (mes.upper(), fecha_radicado, sdqs_num.upper(), quejoso.upper(), correo,
         tema.upper(), competencia_ocdi.upper(),
         bpm or None, responsable or None, rad_salida or None, fecha_respuesta or None,
         observaciones, estado_proceso or None, hecho_corrupto or None,
         valor_institucional or None, tipologia or None, id),
    )
    conn.commit()
    conn.close()
    registrar_log(user, "editar", _MOD, f"ID: {id}")
    return RedirectResponse(f"/sdqs/{id}?msg=actualizado", status_code=303)


# ── Eliminar ──────────────────────────────────────────────────────────────────

@router.post("/{id}/eliminar")
async def eliminar(request: Request, id: int):
    user = request.state.user
    if not _pw(user, _MOD):
        return RedirectResponse("/sdqs/?msg=sin_permiso", status_code=303)
    conn = get_db()
    conn.execute("DELETE FROM sdqs WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    registrar_log(user, "eliminar", _MOD, f"ID: {id}")
    return RedirectResponse("/sdqs/?msg=eliminado", status_code=303)


# ── Exportar Excel ────────────────────────────────────────────────────────────

@router.get("/exportar")
async def exportar(
    request: Request,
    mes: str = "",
    competencia_ocdi: str = "",
    responsable: str = "",
    q: str = "",
):
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return RedirectResponse("/sdqs/?msg=error_archivo", status_code=303)

    conn = get_db()
    where, params = ["1=1"], []
    if mes:
        where.append("UPPER(mes) = ?")
        params.append(mes.upper())
    if competencia_ocdi:
        where.append("UPPER(competencia_ocdi) = ?")
        params.append(competencia_ocdi.upper())
    if responsable:
        where.append("UPPER(responsable) = ?")
        params.append(responsable.upper())
    if q:
        where.append("(UPPER(sdqs) LIKE ? OR UPPER(quejoso) LIKE ? OR UPPER(tema) LIKE ?)")
        like = f"%{q.upper()}%"
        params += [like, like, like]

    rows = conn.execute(
        f"SELECT * FROM sdqs WHERE {' AND '.join(where)} ORDER BY id",
        params,
    ).fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SDQS"

    headers = [
        "MES", "FECHA RAD", "SDQS", "QUEJOSO", "CORREO", "TEMA",
        "COMPETENCIA OCDI", "BPM", "RESPONSABLE", "RAD SALIDA",
        "FECHA RESPUESTA", "OBSERVACIONES", "ESTADO PROCESO",
        "HECHO CORRUPTO", "VALOR INSTITUCIONAL", "TIPOLOGIA",
    ]
    header_fill = PatternFill("solid", fgColor="1B4F8A")
    header_font = Font(bold=True, color="FFFFFF")
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for r in rows:
        d = row_to_dict(r)
        ws.append([
            d.get("mes"), d.get("fecha_radicado"), d.get("sdqs"),
            d.get("quejoso"), d.get("correo"), d.get("tema"),
            d.get("competencia_ocdi"), d.get("bpm"), d.get("responsable"),
            d.get("rad_salida"), d.get("fecha_respuesta"), d.get("observaciones"),
            d.get("estado_proceso"), d.get("hecho_corrupto"),
            d.get("valor_institucional"), d.get("tipologia"),
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=SDQS_export.xlsx"},
    )


# ── Importar ──────────────────────────────────────────────────────────────────

@router.get("/importar", response_class=HTMLResponse)
async def importar_get(request: Request, msg: str = ""):
    conn = get_db()
    total_bd = conn.execute("SELECT COUNT(*) FROM sdqs").fetchone()[0]
    conn.close()
    return templates.TemplateResponse("sdqs_importar.html", tpl(request, _MOD,
        total_bd=total_bd,
        msg=msg,
    ))


@router.post("/importar")
async def importar_post(request: Request, archivo: UploadFile = File(...)):
    user = request.state.user
    if not _pw(user, _MOD):
        return RedirectResponse("/sdqs/importar?msg=sin_permiso", status_code=303)

    contenido = await archivo.read()
    count, errors = _importar_excel_sdqs(contenido)
    if errors:
        return RedirectResponse(f"/sdqs/importar?msg=error_archivo", status_code=303)
    registrar_log(user, "importar", _MOD, f"{count} registros importados")
    return RedirectResponse(f"/sdqs/importar?msg=importado_{count}", status_code=303)


@router.post("/limpiar")
async def limpiar(request: Request):
    user = request.state.user
    if not _pw(user, _MOD):
        return RedirectResponse("/sdqs/importar?msg=sin_permiso", status_code=303)
    conn = get_db()
    conn.execute("DELETE FROM sdqs")
    conn.commit()
    conn.close()
    registrar_log(user, "limpiar", _MOD, "Tabla SDQS borrada")
    return RedirectResponse("/sdqs/importar?msg=importado_0", status_code=303)


# ── Helper de importación Excel ───────────────────────────────────────────────

def _importar_excel_sdqs(archivo_bytes: bytes):
    try:
        import openpyxl
    except ImportError:
        return 0, ["openpyxl no instalado"]

    try:
        wb = openpyxl.load_workbook(io.BytesIO(archivo_bytes), data_only=True)
        ws = wb.active
    except Exception as e:
        return 0, [str(e)]

    def _fecha(val):
        if val is None:
            return None
        try:
            from datetime import datetime, date
            if isinstance(val, (datetime, date)):
                return val.isoformat()[:10]
            s = str(val).strip()
            if not s or s.upper() == "NAN":
                return None
            return s[:10]
        except Exception:
            return None

    conn = get_db()
    count = 0
    errors = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        try:
            mes        = _str(row[0]).upper() if len(row) > 0 else ""
            fecha_rad  = _fecha(row[1]) if len(row) > 1 else None
            sdqs_num   = _str(row[2]).upper() if len(row) > 2 else ""
            quejoso    = _str(row[3]).upper() if len(row) > 3 else ""
            correo     = _str(row[4]) if len(row) > 4 else ""
            tema       = _str(row[5]).upper() if len(row) > 5 else ""
            comp_ocdi  = _str(row[6]).upper() if len(row) > 6 else "NO"
            bpm        = _str(row[7]) or None if len(row) > 7 else None
            resp_raw   = _str(row[8]).upper() if len(row) > 8 else ""
            rad_sal    = _str(row[9]) or None if len(row) > 9 else None
            fecha_resp = _fecha(row[10]) if len(row) > 10 else None
            obs        = _str(row[11]) if len(row) > 11 else ""
            estado     = _str(row[12]).upper() or None if len(row) > 12 else None
            hecho      = _str(row[13]) or None if len(row) > 13 else None
            valor_inst = _str(row[14]) or None if len(row) > 14 else None
            tipologia  = _str(row[15]) or None if len(row) > 15 else None

            if not sdqs_num:
                continue

            responsable = RESP_MAP.get(resp_raw, resp_raw) or None

            conn.execute(
                """INSERT OR IGNORE INTO sdqs
                   (mes, fecha_radicado, sdqs, quejoso, correo, tema, competencia_ocdi,
                    bpm, responsable, rad_salida, fecha_respuesta, observaciones,
                    estado_proceso, hecho_corrupto, valor_institucional, tipologia,
                    created_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (mes, fecha_rad, sdqs_num, quejoso, correo or "", tema,
                 comp_ocdi if comp_ocdi in ("SI", "NO") else "NO",
                 bpm, responsable, rad_sal, fecha_resp, obs,
                 estado if estado else None, hecho, valor_inst, tipologia,
                 "IMPORTACION"),
            )
            count += conn.execute("SELECT changes()").fetchone()[0]
        except Exception as e:
            errors.append(str(e))

    conn.commit()
    conn.close()
    return count, errors
