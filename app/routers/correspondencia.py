from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import date
import io

from urllib.parse import quote_plus as _quote_plus

from app.database import get_db

router = APIRouter(prefix="/correspondencia")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
templates.env.filters["quote_plus"] = _quote_plus

MESES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
]

TIPOS_RESPUESTA = [
    "RESPUESTA",
    "TRASLADO",
    "ANEXO EXPEDIENTE",
    "DEVOLUCION",
    "INFORMATIVO",
    "REUNION",
    "APERTURA EXPEDIENTE",
    "AUTO INHIBITORIO",
    "ANTECEDENTES",
    "RESPUESTA CORREO ELECTRONICO",
]

# Mapa de limpieza de nombres para importación histórica
RESPONSABLE_MAP = {
    "CESAR IVAN": "CESAR IVAN RODRIGUEZ",
    "CESAR RODRIGUEZ": "CESAR IVAN RODRIGUEZ",
    "DAVID FELIPE  MORALES": "DAVID FELIPE MORALES",
    "LUZ ALBA": "LUZ ALBA FARFAN",
    "MABEL HURTADO": "MABEL GICELLA HURTADO",
    "GICELLA HURTADO": "MABEL GICELLA HURTADO",
    "MARA UCROS": "MARA LUCIA UCROS",
    "MARA LUCIA UCROS": "MARA LUCIA UCROS",
    "DE LA HOZ": "JANIK DE LA HOZ",
    "PROFESIONALES": "TODOS LOS PROFESIONALES",
    "TODOS LO PROFESIONALES": "TODOS LOS PROFESIONALES",
}


def _v(val):
    if val is None:
        return None
    s = str(val).strip()
    if s in ("", "nan", "None", "#VALUE!", "#N/A", "#REF!", "—"):
        return None
    return s


def _clean_responsable(nombre: str | None) -> str | None:
    if not nombre:
        return None
    n = str(nombre).strip().upper()
    return RESPONSABLE_MAP.get(n, n.title() if n.islower() else n)


def _semaforo(dias) -> str | None:
    if dias is None:
        return None
    try:
        d = int(dias)
    except (TypeError, ValueError):
        return None
    if d <= 5:
        return "verde"
    if d <= 8:
        return "amarilla"
    return "roja"


def _anios_disponibles():
    return list(range(2024, date.today().year + 3))


def _get_catalogos(conn):
    responsables = [r[0] for r in conn.execute(
        "SELECT nombre FROM corr_responsables ORDER BY nombre"
    ).fetchall()]
    tipos_doc = [r[0] for r in conn.execute(
        "SELECT nombre FROM corr_tipos_documento ORDER BY nombre"
    ).fetchall()]
    return responsables, tipos_doc


# ── Semáforo SQL (cols calculadas) ────────────────────────────────────────────

_SEMAFORO_SQL = """
    CASE
        WHEN c.fecha_ingreso IS NULL THEN NULL
        WHEN UPPER(TRIM(c.tipo_respuesta)) = 'ANEXO EXPEDIENTE' THEN 'verde'
        WHEN c.fecha_radicado_salida IS NOT NULL AND c.fecha_radicado_salida != '' THEN 'respondido'
        WHEN CAST(julianday('now','localtime') - julianday(substr(c.fecha_ingreso,1,10)) AS INTEGER) <= 5 THEN 'verde'
        WHEN CAST(julianday('now','localtime') - julianday(substr(c.fecha_ingreso,1,10)) AS INTEGER) <= 8 THEN 'amarilla'
        ELSE 'roja'
    END AS semaforo
"""

_DIAS_SQL = """
    CASE
        WHEN c.fecha_ingreso IS NULL THEN NULL
        WHEN UPPER(TRIM(c.tipo_respuesta)) = 'ANEXO EXPEDIENTE' THEN 0
        WHEN c.fecha_radicado_salida IS NOT NULL AND c.fecha_radicado_salida != ''
            THEN CAST(julianday(substr(c.fecha_radicado_salida,1,10)) - julianday(substr(c.fecha_ingreso,1,10)) AS INTEGER)
        ELSE CAST(julianday('now','localtime') - julianday(substr(c.fecha_ingreso,1,10)) AS INTEGER)
    END AS dias_transcurridos
"""


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = get_db()

    total = conn.execute("SELECT COUNT(*) FROM correspondencia").fetchone()[0]

    stats = conn.execute(f"""
        SELECT
            SUM(CASE WHEN fecha_radicado_salida IS NOT NULL AND fecha_radicado_salida != '' THEN 1 ELSE 0 END) AS respondidos,
            SUM(CASE WHEN UPPER(TRIM(tipo_respuesta)) = 'ANEXO EXPEDIENTE' THEN 1
                     WHEN (fecha_radicado_salida IS NULL OR fecha_radicado_salida = '') AND fecha_ingreso IS NOT NULL
                     AND CAST(julianday('now','localtime') - julianday(substr(fecha_ingreso,1,10)) AS INTEGER) <= 5 THEN 1 ELSE 0 END) AS verde,
            SUM(CASE WHEN UPPER(TRIM(tipo_respuesta)) != 'ANEXO EXPEDIENTE'
                     AND (fecha_radicado_salida IS NULL OR fecha_radicado_salida = '') AND fecha_ingreso IS NOT NULL
                     AND CAST(julianday('now','localtime') - julianday(substr(fecha_ingreso,1,10)) AS INTEGER) BETWEEN 6 AND 8 THEN 1 ELSE 0 END) AS amarilla,
            SUM(CASE WHEN UPPER(TRIM(tipo_respuesta)) != 'ANEXO EXPEDIENTE'
                     AND (fecha_radicado_salida IS NULL OR fecha_radicado_salida = '') AND fecha_ingreso IS NOT NULL
                     AND CAST(julianday('now','localtime') - julianday(substr(fecha_ingreso,1,10)) AS INTEGER) >= 9 THEN 1 ELSE 0 END) AS roja
        FROM correspondencia
    """).fetchone()

    por_responsable = conn.execute("""
        SELECT responsable, COUNT(*) cant,
               SUM(CASE WHEN fecha_radicado_salida IS NOT NULL AND fecha_radicado_salida != '' THEN 1 ELSE 0 END) respondidos
        FROM correspondencia WHERE responsable IS NOT NULL
        GROUP BY responsable ORDER BY cant DESC LIMIT 15
    """).fetchall()

    por_mes = conn.execute("""
        SELECT mes, COUNT(*) cant FROM correspondencia
        WHERE mes IS NOT NULL GROUP BY mes
        ORDER BY CASE mes
            WHEN 'ENERO' THEN 1 WHEN 'FEBRERO' THEN 2 WHEN 'MARZO' THEN 3
            WHEN 'ABRIL' THEN 4 WHEN 'MAYO' THEN 5 WHEN 'JUNIO' THEN 6
            WHEN 'JULIO' THEN 7 WHEN 'AGOSTO' THEN 8 WHEN 'SEPTIEMBRE' THEN 9
            WHEN 'OCTUBRE' THEN 10 WHEN 'NOVIEMBRE' THEN 11 WHEN 'DICIEMBRE' THEN 12
            ELSE 99 END
    """).fetchall()

    # Pendientes críticos (rojos) para tabla de alerta — excluye ANEXO EXPEDIENTE
    criticos = conn.execute(f"""
        SELECT c.id, c.n_radicado, c.responsable, c.asunto, c.mes, c.fecha_ingreso,
               {_DIAS_SQL}
        FROM correspondencia c
        WHERE (c.fecha_radicado_salida IS NULL OR c.fecha_radicado_salida = '')
        AND UPPER(TRIM(c.tipo_respuesta)) != 'ANEXO EXPEDIENTE'
        AND c.fecha_ingreso IS NOT NULL
        ORDER BY dias_transcurridos DESC LIMIT 20
    """).fetchall()

    conn.close()

    return templates.TemplateResponse("corr_dashboard.html", {
        "request": request,
        "active": "corr_dashboard",
        "total": total,
        "stats": dict(stats) if stats else {},
        "por_responsable": [dict(r) for r in por_responsable],
        "por_mes": [dict(r) for r in por_mes],
        "criticos": [dict(r) for r in criticos],
    })


# ── LISTA ──────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def lista(
    request: Request,
    q: str = "",
    semaforo: str = "",
    responsable: str = "",
    mes: str = "",
    anio: str = "",
    page: int = 1,
    por_pagina: int = 25,
    msg: str = "",
):
    conn = get_db()
    responsables, tipos_doc = _get_catalogos(conn)

    filtros = ["1=1"]
    params: list = []

    if q.strip():
        filtros.append("(c.n_radicado LIKE ? OR c.origen LIKE ? OR c.asunto LIKE ? OR c.caso_bmp LIKE ?)")
        params += [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"]
    if responsable.strip():
        filtros.append("c.responsable = ?")
        params.append(responsable.strip())
    if mes.strip():
        filtros.append("c.mes = ?")
        params.append(mes.strip())
    if anio.strip():
        filtros.append("c.anio = ?")
        params.append(int(anio.strip()))
    if semaforo == "verde":
        filtros.append("""(c.fecha_radicado_salida IS NULL OR c.fecha_radicado_salida='') AND c.fecha_ingreso IS NOT NULL
            AND CAST(julianday('now','localtime') - julianday(substr(c.fecha_ingreso,1,10)) AS INTEGER) <= 5""")
    elif semaforo == "amarilla":
        filtros.append("""(c.fecha_radicado_salida IS NULL OR c.fecha_radicado_salida='') AND c.fecha_ingreso IS NOT NULL
            AND CAST(julianday('now','localtime') - julianday(substr(c.fecha_ingreso,1,10)) AS INTEGER) BETWEEN 6 AND 8""")
    elif semaforo == "roja":
        filtros.append("""(c.fecha_radicado_salida IS NULL OR c.fecha_radicado_salida='') AND c.fecha_ingreso IS NOT NULL
            AND CAST(julianday('now','localtime') - julianday(substr(c.fecha_ingreso,1,10)) AS INTEGER) >= 9""")
    elif semaforo == "respondido":
        filtros.append("c.fecha_radicado_salida IS NOT NULL AND c.fecha_radicado_salida != ''")

    where = " AND ".join(filtros)

    total = conn.execute(f"SELECT COUNT(*) FROM correspondencia c WHERE {where}", params).fetchone()[0]
    offset = (page - 1) * por_pagina

    rows = conn.execute(f"""
        SELECT c.*,
               GROUP_CONCAT(rs.radicado, ' | ') AS radicados_salida,
               {_SEMAFORO_SQL},
               {_DIAS_SQL}
        FROM correspondencia c
        LEFT JOIN correspondencia_radicados_salida rs ON rs.correspondencia_id = c.id
        WHERE {where}
        GROUP BY c.id
        ORDER BY
            CASE WHEN (c.fecha_radicado_salida IS NULL OR c.fecha_radicado_salida='') THEN 0 ELSE 1 END,
            dias_transcurridos DESC,
            c.fecha_ingreso DESC
        LIMIT ? OFFSET ?
    """, params + [por_pagina, offset]).fetchall()

    anios_bd = [r[0] for r in conn.execute(
        "SELECT DISTINCT anio FROM correspondencia WHERE anio IS NOT NULL ORDER BY anio DESC"
    ).fetchall()]
    conn.close()

    total_pages = max(1, (total + por_pagina - 1) // por_pagina)

    return templates.TemplateResponse("corr_lista.html", {
        "request": request,
        "active": "corr_lista",
        "rows": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "por_pagina": por_pagina,
        "q": q,
        "semaforo": semaforo,
        "responsable": responsable,
        "mes": mes,
        "anio": anio,
        "responsables": responsables,
        "meses": MESES,
        "anios": anios_bd,
        "msg": msg,
        "back_url": request.url.path + ("?" + str(request.url.query) if request.url.query else ""),
    })


# ── NUEVO ──────────────────────────────────────────────────────────────────────

@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo_form(request: Request):
    conn = get_db()
    responsables, tipos_doc = _get_catalogos(conn)
    conn.close()
    return templates.TemplateResponse("corr_form.html", {
        "request": request,
        "active": "corr_nuevo",
        "modo": "nuevo",
        "reg": {},
        "radicados_salida": [],
        "responsables": responsables,
        "tipos_doc": tipos_doc,
        "tipos_respuesta": TIPOS_RESPUESTA,
        "meses": MESES,
        "anios": _anios_disponibles(),
    })


@router.post("/nuevo")
async def nuevo_post(
    request: Request,
    anio: int = Form(None),
    mes: str = Form(""),
    fecha_ingreso: str = Form(""),
    n_radicado: str = Form(""),
    origen: str = Form(""),
    asunto: str = Form(""),
    tipo_documento: str = Form(""),
    responsable: str = Form(""),
    caso_bmp: str = Form(""),
    fecha_radicado_salida: str = Form(""),
    tipo_respuesta: str = Form(""),
    tramite_salida: str = Form(""),
):
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO correspondencia
        (anio, mes, fecha_ingreso, n_radicado, origen, asunto, tipo_documento,
         responsable, caso_bmp, fecha_radicado_salida, tipo_respuesta, tramite_salida)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, [
        anio, _v(mes), _v(fecha_ingreso), _v(n_radicado), _v(origen), _v(asunto),
        _v(tipo_documento), _v(responsable), _v(caso_bmp),
        _v(fecha_radicado_salida), _v(tipo_respuesta), _v(tramite_salida),
    ])
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return RedirectResponse(f"/correspondencia/{new_id}/editar?msg=creado", status_code=303)


# ── EXPORTAR EXCEL ─────────────────────────────────────────────────────────────

@router.get("/exportar")
async def exportar():
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return RedirectResponse("/correspondencia/?msg=error_openpyxl")

    conn = get_db()
    rows = conn.execute(f"""
        SELECT c.*,
               GROUP_CONCAT(rs.radicado, ' | ') AS radicados_salida,
               {_DIAS_SQL}
        FROM correspondencia c
        LEFT JOIN correspondencia_radicados_salida rs ON rs.correspondencia_id = c.id
        GROUP BY c.id
        ORDER BY c.anio DESC, c.fecha_ingreso DESC
    """).fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CORRESPONDENCIA"

    h_fill = PatternFill("solid", fgColor="1B4F8A")
    h_font = Font(bold=True, color="FFFFFF", size=10)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    alt_fill = PatternFill("solid", fgColor="EBF1F8")

    headers = [
        "AÑO", "MES", "FECHA INGRESO DE OFICIO", "N. RADICADOS",
        "ORIGEN AGILSALUD", "ASUNTO AGILSALUD", "TIPO DE DOCUMENTO",
        "RESPONSABLE", "CASO BMP", "N RADICADO SALIDA",
        "FECHA RADICADO DE SALIDA", "TIPO DE RESPUESTA", "TRAMITE DE SALIDA",
        "DÍAS TRANSCURRIDOS",
    ]
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.fill = h_fill
        cell.font = h_font
        cell.alignment = center
    ws.row_dimensions[1].height = 36

    for ri, row in enumerate(rows, 2):
        d = dict(row)
        fill = alt_fill if ri % 2 == 0 else None
        vals = [
            d.get("anio"), d.get("mes"), d.get("fecha_ingreso")[:10] if d.get("fecha_ingreso") else None,
            d.get("n_radicado"), d.get("origen"), d.get("asunto"),
            d.get("tipo_documento"), d.get("responsable"), d.get("caso_bmp"),
            d.get("radicados_salida"), d.get("fecha_radicado_salida")[:10] if d.get("fecha_radicado_salida") else None,
            d.get("tipo_respuesta"), d.get("tramite_salida"), d.get("dias_transcurridos"),
        ]
        for ci, v in enumerate(vals, 1):
            cell = ws.cell(row=ri, column=ci, value=v)
            cell.alignment = Alignment(vertical="center", wrap_text=ci in (5, 6))
            if fill:
                cell.fill = fill

    col_widths = [6, 12, 20, 18, 35, 45, 18, 22, 10, 20, 20, 25, 25, 8]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws.freeze_panes = "A2"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    hoy = date.today().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Correspondencia_{hoy}.xlsx"},
    )


# ── IMPORTAR ───────────────────────────────────────────────────────────────────

@router.get("/importar", response_class=HTMLResponse)
async def importar_form(request: Request, msg: str = ""):
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM correspondencia").fetchone()[0]
    conn.close()
    return templates.TemplateResponse("corr_importar.html", {
        "request": request,
        "active": "corr_importar",
        "msg": msg,
        "total_actual": total,
    })


@router.post("/importar")
async def importar_post(archivo: UploadFile = File(...)):
    try:
        import openpyxl
    except ImportError:
        return RedirectResponse("/correspondencia/importar?msg=error_openpyxl", status_code=303)

    contenido = await archivo.read()
    if not contenido:
        return RedirectResponse("/correspondencia/importar?msg=error_vacio", status_code=303)

    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)
    except Exception:
        return RedirectResponse("/correspondencia/importar?msg=error_archivo", status_code=303)

    # Aceptar hoja llamada "2026", "CORRESPONDENCIA" o la primera
    ws = None
    for nombre in ["CORRESPONDENCIA", "2026"]:
        if nombre in wb.sheetnames:
            ws = wb[nombre]
            break
    if ws is None:
        ws = wb.active

    conn = get_db()
    insertados = 0
    try:
        conn.execute("DELETE FROM correspondencia_radicados_salida")
        conn.execute("DELETE FROM correspondencia")

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(v for v in row if v is not None):
                continue

            # Detectar si es el formato EXPORTADO (14 cols, col 0 = AÑO int)
            # o el formato ORIGINAL (12 cols, col 0 = MES)
            if len(row) >= 14 and row[0] is not None:
                try:
                    int(row[0])
                    formato_export = True
                except (ValueError, TypeError):
                    formato_export = False
            else:
                formato_export = False

            if formato_export:
                anio_val   = _v(row[0])
                mes_val    = _v(row[1])
                fi_val     = _v(row[2])
                rad_val    = _v(row[3])
                orig_val   = _v(row[4])
                asunto_val = _v(row[5])
                tipo_d_val = _v(row[6])
                resp_val   = _v(row[7])
                bmp_val    = _v(row[8])
                rad_sal    = _v(row[9])
                fsal_val   = _v(row[10])
                tipor_val  = _v(row[11])
                tram_val   = _v(row[12])
            else:
                mes_val    = _v(row[0])
                fi_val     = _v(row[1])
                rad_val    = _v(row[2])
                orig_val   = _v(row[3])
                asunto_val = _v(row[4])
                tipo_d_val = _v(row[5])
                resp_val   = _v(row[6])
                bmp_val    = _v(row[7])
                rad_sal    = _v(row[8])
                fsal_val   = _v(row[9])
                tipor_val  = _v(row[10])
                tram_val   = _v(row[11]) if len(row) > 11 else None
                # Inferir año de la fecha de ingreso
                anio_val = None
                if fi_val:
                    try:
                        anio_val = str(fi_val[:4])
                    except Exception:
                        pass

            # Normalizar mes
            if mes_val:
                mes_val = mes_val.strip().upper()

            # Limpiar responsable
            resp_val = _clean_responsable(resp_val)

            # Normalizar fecha (puede venir como datetime con hora)
            def _norm_fecha(f):
                if not f:
                    return None
                s = str(f).strip()
                if len(s) >= 10:
                    return s[:10]
                return s

            fi_val   = _norm_fecha(fi_val)
            fsal_val = _norm_fecha(fsal_val)

            cur = conn.execute("""
                INSERT INTO correspondencia
                (anio, mes, fecha_ingreso, n_radicado, origen, asunto, tipo_documento,
                 responsable, caso_bmp, fecha_radicado_salida, tipo_respuesta, tramite_salida)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, [anio_val, mes_val, fi_val, rad_val, orig_val, asunto_val,
                  tipo_d_val, resp_val, bmp_val, fsal_val, tipor_val, tram_val])
            cid = cur.lastrowid
            insertados += 1

            # Radicados de salida (puede ser pipe-separated o single value)
            if rad_sal:
                for r in str(rad_sal).split("|"):
                    r = r.strip()
                    if r:
                        conn.execute(
                            "INSERT INTO correspondencia_radicados_salida (correspondencia_id, radicado) VALUES (?,?)",
                            (cid, r),
                        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return RedirectResponse(f"/correspondencia/importar?msg=error_import", status_code=303)

    conn.close()
    return RedirectResponse(f"/correspondencia/importar?msg=ok_{insertados}", status_code=303)


# ── CONFIGURAR CATÁLOGOS ───────────────────────────────────────────────────────

@router.get("/configurar", response_class=HTMLResponse)
async def configurar(request: Request, msg: str = ""):
    conn = get_db()
    responsables = conn.execute(
        "SELECT id, nombre FROM corr_responsables ORDER BY nombre"
    ).fetchall()
    tipos_doc = conn.execute(
        "SELECT id, nombre FROM corr_tipos_documento ORDER BY nombre"
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("corr_configurar.html", {
        "request": request,
        "active": "corr_configurar",
        "responsables": [dict(r) for r in responsables],
        "tipos_doc": [dict(r) for r in tipos_doc],
        "tipos_respuesta": TIPOS_RESPUESTA,
        "msg": msg,
    })


@router.post("/configurar/responsable/nuevo")
async def responsable_nuevo(nombre: str = Form(...)):
    nombre = nombre.strip().upper()
    if not nombre:
        return RedirectResponse("/correspondencia/configurar?msg=vacio", status_code=303)
    conn = get_db()
    try:
        conn.execute("INSERT INTO corr_responsables (nombre) VALUES (?)", (nombre,))
        conn.commit()
    except Exception:
        conn.close()
        return RedirectResponse("/correspondencia/configurar?msg=duplicado", status_code=303)
    conn.close()
    return RedirectResponse("/correspondencia/configurar?msg=ok", status_code=303)


@router.post("/configurar/responsable/{rid}/editar")
async def responsable_editar(rid: int, nombre: str = Form(...)):
    nombre = nombre.strip().upper()
    if not nombre:
        return RedirectResponse("/correspondencia/configurar?msg=vacio", status_code=303)
    conn = get_db()
    conn.execute("UPDATE corr_responsables SET nombre=? WHERE id=?", (nombre, rid))
    conn.commit()
    conn.close()
    return RedirectResponse("/correspondencia/configurar?msg=ok", status_code=303)


@router.post("/configurar/responsable/{rid}/eliminar")
async def responsable_eliminar(rid: int):
    conn = get_db()
    conn.execute("DELETE FROM corr_responsables WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    return RedirectResponse("/correspondencia/configurar?msg=ok", status_code=303)


@router.post("/configurar/tipo_doc/nuevo")
async def tipo_doc_nuevo(nombre: str = Form(...)):
    nombre = nombre.strip().upper()
    if not nombre:
        return RedirectResponse("/correspondencia/configurar?msg=vacio", status_code=303)
    conn = get_db()
    try:
        conn.execute("INSERT INTO corr_tipos_documento (nombre) VALUES (?)", (nombre,))
        conn.commit()
    except Exception:
        conn.close()
        return RedirectResponse("/correspondencia/configurar?msg=duplicado", status_code=303)
    conn.close()
    return RedirectResponse("/correspondencia/configurar?msg=ok", status_code=303)


@router.post("/configurar/tipo_doc/{tid}/editar")
async def tipo_doc_editar(tid: int, nombre: str = Form(...)):
    nombre = nombre.strip().upper()
    conn = get_db()
    conn.execute("UPDATE corr_tipos_documento SET nombre=? WHERE id=?", (nombre, tid))
    conn.commit()
    conn.close()
    return RedirectResponse("/correspondencia/configurar?msg=ok", status_code=303)


@router.post("/configurar/tipo_doc/{tid}/eliminar")
async def tipo_doc_eliminar(tid: int):
    conn = get_db()
    conn.execute("DELETE FROM corr_tipos_documento WHERE id=?", (tid,))
    conn.commit()
    conn.close()
    return RedirectResponse("/correspondencia/configurar?msg=ok", status_code=303)


# ── VER / EDITAR / ELIMINAR ────────────────────────────────────────────────────

@router.get("/{reg_id}", response_class=HTMLResponse)
async def ver(request: Request, reg_id: int, back: str = ""):
    conn = get_db()
    row = conn.execute("SELECT * FROM correspondencia WHERE id=?", (reg_id,)).fetchone()
    if not row:
        conn.close()
        return RedirectResponse("/correspondencia/?msg=no_encontrado")
    radicados = conn.execute(
        "SELECT * FROM correspondencia_radicados_salida WHERE correspondencia_id=? ORDER BY id",
        (reg_id,),
    ).fetchall()
    conn.close()
    reg = dict(row)
    dias = None
    if reg.get("fecha_ingreso"):
        try:
            fi = date.fromisoformat(reg["fecha_ingreso"][:10])
            if reg.get("fecha_radicado_salida"):
                fs = date.fromisoformat(reg["fecha_radicado_salida"][:10])
                dias = (fs - fi).days
            else:
                dias = (date.today() - fi).days
        except Exception:
            pass
    if reg.get("tipo_respuesta") and reg["tipo_respuesta"].strip().upper() == "ANEXO EXPEDIENTE":
        dias = 0
    reg["dias_transcurridos"] = dias
    if reg.get("tipo_respuesta") and reg["tipo_respuesta"].strip().upper() == "ANEXO EXPEDIENTE":
        reg["semaforo"] = "verde"
    elif reg.get("fecha_radicado_salida"):
        reg["semaforo"] = "respondido"
    else:
        reg["semaforo"] = _semaforo(dias)
    return templates.TemplateResponse("corr_detalle.html", {
        "request": request,
        "active": "corr_lista",
        "reg": reg,
        "radicados": [dict(r) for r in radicados],
        "back": back or "/correspondencia/",
    })


@router.get("/{reg_id}/editar", response_class=HTMLResponse)
async def editar_form(request: Request, reg_id: int, msg: str = "", back: str = ""):
    conn = get_db()
    row = conn.execute("SELECT * FROM correspondencia WHERE id=?", (reg_id,)).fetchone()
    if not row:
        conn.close()
        return RedirectResponse("/correspondencia/?msg=no_encontrado")
    radicados = conn.execute(
        "SELECT * FROM correspondencia_radicados_salida WHERE correspondencia_id=? ORDER BY id",
        (reg_id,),
    ).fetchall()
    responsables, tipos_doc = _get_catalogos(conn)
    conn.close()
    return templates.TemplateResponse("corr_form.html", {
        "request": request,
        "active": "corr_lista",
        "modo": "editar",
        "reg": dict(row),
        "radicados_salida": [dict(r) for r in radicados],
        "responsables": responsables,
        "tipos_doc": tipos_doc,
        "tipos_respuesta": TIPOS_RESPUESTA,
        "meses": MESES,
        "anios": _anios_disponibles(),
        "msg": msg,
        "back": back or "/correspondencia/",
    })


@router.post("/{reg_id}/editar")
async def editar_post(
    reg_id: int,
    anio: int = Form(None),
    mes: str = Form(""),
    fecha_ingreso: str = Form(""),
    n_radicado: str = Form(""),
    origen: str = Form(""),
    asunto: str = Form(""),
    tipo_documento: str = Form(""),
    responsable: str = Form(""),
    caso_bmp: str = Form(""),
    fecha_radicado_salida: str = Form(""),
    tipo_respuesta: str = Form(""),
    tramite_salida: str = Form(""),
):
    conn = get_db()
    conn.execute("""
        UPDATE correspondencia SET
        anio=?, mes=?, fecha_ingreso=?, n_radicado=?, origen=?, asunto=?,
        tipo_documento=?, responsable=?, caso_bmp=?, fecha_radicado_salida=?,
        tipo_respuesta=?, tramite_salida=?,
        updated_at=datetime('now','localtime')
        WHERE id=?
    """, [
        anio, _v(mes), _v(fecha_ingreso), _v(n_radicado), _v(origen), _v(asunto),
        _v(tipo_documento), _v(responsable), _v(caso_bmp),
        _v(fecha_radicado_salida), _v(tipo_respuesta), _v(tramite_salida),
        reg_id,
    ])
    conn.commit()
    conn.close()
    return RedirectResponse(f"/correspondencia/{reg_id}/editar?msg=actualizado", status_code=303)


@router.post("/{reg_id}/eliminar")
async def eliminar(reg_id: int):
    conn = get_db()
    conn.execute("DELETE FROM correspondencia WHERE id=?", (reg_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/correspondencia/?msg=eliminado", status_code=303)


# ── RADICADOS DE SALIDA ────────────────────────────────────────────────────────

@router.post("/{reg_id}/radicado_salida/nuevo")
async def radicado_nuevo(reg_id: int, radicado: str = Form(...)):
    r = radicado.strip()
    if r:
        conn = get_db()
        conn.execute(
            "INSERT INTO correspondencia_radicados_salida (correspondencia_id, radicado) VALUES (?,?)",
            (reg_id, r),
        )
        conn.commit()
        conn.close()
    return RedirectResponse(f"/correspondencia/{reg_id}/editar?msg=rad_ok", status_code=303)


@router.post("/radicado_salida/{rad_id}/eliminar")
async def radicado_eliminar(rad_id: int):
    conn = get_db()
    row = conn.execute(
        "SELECT correspondencia_id FROM correspondencia_radicados_salida WHERE id=?", (rad_id,)
    ).fetchone()
    conn.execute("DELETE FROM correspondencia_radicados_salida WHERE id=?", (rad_id,))
    conn.commit()
    reg_id = row["correspondencia_id"] if row else None
    conn.close()
    if reg_id:
        return RedirectResponse(f"/correspondencia/{reg_id}/editar?msg=rad_eliminado", status_code=303)
    return RedirectResponse("/correspondencia/", status_code=303)
