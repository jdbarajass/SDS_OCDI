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
    "ANEXO AL EXPEDIENTE",
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

# Condición reutilizable para ambas variantes de ANEXO (sin conteo de días)
_ANEXO_COND = "UPPER(TRIM(c.tipo_respuesta)) IN ('ANEXO EXPEDIENTE', 'ANEXO AL EXPEDIENTE')"

_SEMAFORO_SQL = """
    CASE
        WHEN c.fecha_ingreso IS NULL THEN NULL
        WHEN UPPER(TRIM(c.tipo_respuesta)) IN ('ANEXO EXPEDIENTE', 'ANEXO AL EXPEDIENTE') THEN 'verde'
        WHEN c.fecha_radicado_salida IS NOT NULL AND c.fecha_radicado_salida != '' THEN 'respondido'
        WHEN CAST(julianday('now','localtime') - julianday(substr(c.fecha_ingreso,1,10)) AS INTEGER) <= 5 THEN 'verde'
        WHEN CAST(julianday('now','localtime') - julianday(substr(c.fecha_ingreso,1,10)) AS INTEGER) <= 8 THEN 'amarilla'
        ELSE 'roja'
    END AS semaforo
"""

_DIAS_SQL = """
    CASE
        WHEN c.fecha_ingreso IS NULL THEN NULL
        WHEN UPPER(TRIM(c.tipo_respuesta)) IN ('ANEXO EXPEDIENTE', 'ANEXO AL EXPEDIENTE') THEN NULL
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
            SUM(CASE WHEN UPPER(TRIM(tipo_respuesta)) IN ('ANEXO EXPEDIENTE','ANEXO AL EXPEDIENTE') THEN 1
                     WHEN (fecha_radicado_salida IS NULL OR fecha_radicado_salida = '') AND fecha_ingreso IS NOT NULL
                     AND UPPER(TRIM(tipo_respuesta)) NOT IN ('ANEXO EXPEDIENTE','ANEXO AL EXPEDIENTE')
                     AND CAST(julianday('now','localtime') - julianday(substr(fecha_ingreso,1,10)) AS INTEGER) <= 5 THEN 1 ELSE 0 END) AS verde,
            SUM(CASE WHEN UPPER(TRIM(tipo_respuesta)) NOT IN ('ANEXO EXPEDIENTE','ANEXO AL EXPEDIENTE')
                     AND (fecha_radicado_salida IS NULL OR fecha_radicado_salida = '') AND fecha_ingreso IS NOT NULL
                     AND CAST(julianday('now','localtime') - julianday(substr(fecha_ingreso,1,10)) AS INTEGER) BETWEEN 6 AND 8 THEN 1 ELSE 0 END) AS amarilla,
            SUM(CASE WHEN UPPER(TRIM(tipo_respuesta)) NOT IN ('ANEXO EXPEDIENTE','ANEXO AL EXPEDIENTE')
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
        AND UPPER(TRIM(c.tipo_respuesta)) NOT IN ('ANEXO EXPEDIENTE','ANEXO AL EXPEDIENTE')
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
        filtros.append("""(
            UPPER(TRIM(c.tipo_respuesta)) IN ('ANEXO EXPEDIENTE','ANEXO AL EXPEDIENTE')
            OR (
                (c.fecha_radicado_salida IS NULL OR c.fecha_radicado_salida='')
                AND c.fecha_ingreso IS NOT NULL
                AND UPPER(TRIM(c.tipo_respuesta)) NOT IN ('ANEXO EXPEDIENTE','ANEXO AL EXPEDIENTE')
                AND CAST(julianday('now','localtime') - julianday(substr(c.fecha_ingreso,1,10)) AS INTEGER) <= 5
            )
        )""")
    elif semaforo == "amarilla":
        filtros.append("""(c.fecha_radicado_salida IS NULL OR c.fecha_radicado_salida='') AND c.fecha_ingreso IS NOT NULL
            AND UPPER(TRIM(c.tipo_respuesta)) NOT IN ('ANEXO EXPEDIENTE','ANEXO AL EXPEDIENTE')
            AND CAST(julianday('now','localtime') - julianday(substr(c.fecha_ingreso,1,10)) AS INTEGER) BETWEEN 6 AND 8""")
    elif semaforo == "roja":
        filtros.append("""(c.fecha_radicado_salida IS NULL OR c.fecha_radicado_salida='') AND c.fecha_ingreso IS NOT NULL
            AND UPPER(TRIM(c.tipo_respuesta)) NOT IN ('ANEXO EXPEDIENTE','ANEXO AL EXPEDIENTE')
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
        ORDER BY c.fecha_ingreso DESC
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
    correo_remitente: str = Form(""),
):
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO correspondencia
        (anio, mes, fecha_ingreso, n_radicado, origen, asunto, tipo_documento,
         responsable, caso_bmp, fecha_radicado_salida, tipo_respuesta, tramite_salida,
         correo_remitente)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, [
        anio, _v(mes), _v(fecha_ingreso), _v(n_radicado), _v(origen), _v(asunto),
        _v(tipo_documento), _v(responsable), _v(caso_bmp),
        _v(fecha_radicado_salida), _v(tipo_respuesta), _v(tramite_salida),
        _v(correo_remitente),
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
        ORDER BY c.fecha_ingreso DESC
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
        "ORIGEN AGILSALUD", "CORREO REMITENTE", "ASUNTO AGILSALUD", "TIPO DE DOCUMENTO",
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
            d.get("n_radicado"), d.get("origen"), d.get("correo_remitente"), d.get("asunto"),
            d.get("tipo_documento"), d.get("responsable"), d.get("caso_bmp"),
            d.get("radicados_salida"), d.get("fecha_radicado_salida")[:10] if d.get("fecha_radicado_salida") else None,
            d.get("tipo_respuesta"), d.get("tramite_salida"), d.get("dias_transcurridos"),
        ]
        for ci, v in enumerate(vals, 1):
            cell = ws.cell(row=ri, column=ci, value=v)
            cell.alignment = Alignment(vertical="center", wrap_text=ci in (5, 7))
            if fill:
                cell.fill = fill

    col_widths = [6, 12, 20, 18, 30, 30, 40, 18, 22, 10, 20, 20, 25, 25, 8]
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

    # ── Detectar formato ──────────────────────────────────────────────────────
    # Formato ORIGINAL: hojas con nombres de meses ("ENERO 2026", "FEBRERO2026",...)
    #   - Filas 1-5 son título/encabezado, datos empiezan en fila 6
    #   - 14 cols: MES|FECHA|N.RAD|ORIGEN|ASUNTO|TIPO_DOC|RESPONSABLE|CASO_BMP|
    #              RADICADO_BMP(vacío)|TRAMITE_SAL(vacío)|N_RAD_SAL|FECHA_RADIC|TIPO_RESP|TRAMITE
    # Formato EXPORTADO: hoja "CORRESPONDENCIA" con encabezado en fila 1
    #   - 14 cols: AÑO|MES|FECHA|N.RAD|ORIGEN|ASUNTO|TIPO_DOC|RESPONSABLE|CASO_BMP|
    #              N_RAD_SAL|FECHA_SAL|TIPO_RESP|TRAMITE|DÍAS

    MESES_HOJAS = ("ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO",
                   "JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE")

    hojas_originales = [
        sn for sn in wb.sheetnames
        if any(sn.upper().startswith(m) for m in MESES_HOJAS)
    ]
    es_formato_original = len(hojas_originales) > 0

    def _norm_fecha(f):
        if not f:
            return None
        s = str(f).strip()
        if len(s) >= 10:
            return s[:10]
        return s

    conn = get_db()
    insertados = 0
    try:
        conn.execute("DELETE FROM correspondencia_radicados_salida")
        conn.execute("DELETE FROM correspondencia")

        if es_formato_original:
            # ── Formato original: iterar todas las hojas de meses ─────────────
            for nombre_hoja in hojas_originales:
                ws = wb[nombre_hoja]
                # Columnas del Excel original (0-indexed):
                # 0:MES 1:FECHA 2:N.RADICADOS 3:ORIGEN 4:ASUNTO 5:TIPO_DOC
                # 6:RESPONSABLE 7:CASO_BMP 8:RADICADO_BMP(vacío) 9:TRAMITE_SAL(vacío)
                # 10:N_RADICADO_SALIDA 11:FECHA_RADIC_DOC 12:TIPO_RESPUESTA 13:TRAMITE(sin header)
                for row in ws.iter_rows(min_row=6, values_only=True):
                    if not any(v for v in row if v is not None):
                        continue
                    # Saltar fila de encabezado si por alguna razón quedó en datos
                    if _v(row[0]) and str(row[0]).strip().upper() in ("MES", "MES "):
                        continue

                    mes_val    = _v(row[0])
                    fi_val     = _norm_fecha(_v(row[1]))
                    rad_val    = _v(row[2])
                    orig_val   = _v(row[3])
                    asunto_val = _v(row[4])
                    tipo_d_val = _v(row[5])
                    resp_val   = _v(row[6])
                    bmp_val    = _v(row[7])
                    # row[8] = RADICADO BMP  → siempre vacío, se omite
                    # row[9] = TRAMITE DE SALIDA (header) → siempre vacío, se omite
                    rad_sal    = _v(row[10]) if len(row) > 10 else None
                    fsal_val   = _norm_fecha(_v(row[11]) if len(row) > 11 else None)
                    tipor_val  = _v(row[12]) if len(row) > 12 else None
                    tram_val   = _v(row[13]) if len(row) > 13 else None

                    # Inferir año de la fecha de ingreso
                    anio_val = None
                    if fi_val:
                        try:
                            anio_val = int(fi_val[:4])
                        except Exception:
                            pass

                    if mes_val:
                        mes_val = mes_val.strip().upper()
                    resp_val = _clean_responsable(resp_val)

                    # Necesita al menos fecha o radicado para ser un registro válido
                    if not fi_val and not rad_val:
                        continue

                    cur = conn.execute("""
                        INSERT INTO correspondencia
                        (anio, mes, fecha_ingreso, n_radicado, origen, asunto, tipo_documento,
                         responsable, caso_bmp, fecha_radicado_salida, tipo_respuesta, tramite_salida)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """, [anio_val, mes_val, fi_val, rad_val, orig_val, asunto_val,
                          tipo_d_val, resp_val, bmp_val, fsal_val, tipor_val, tram_val])
                    cid = cur.lastrowid
                    insertados += 1

                    if rad_sal:
                        for r in str(rad_sal).split("|"):
                            r = r.strip()
                            if r:
                                conn.execute(
                                    "INSERT INTO correspondencia_radicados_salida (correspondencia_id, radicado) VALUES (?,?)",
                                    (cid, r),
                                )

        else:
            # ── Formato exportado: hoja "CORRESPONDENCIA" con headers en fila 1 ──
            ws = None
            for nombre in ["CORRESPONDENCIA", "CORR", "2026"]:
                if nombre in wb.sheetnames:
                    ws = wb[nombre]
                    break
            if ws is None:
                ws = wb.active

            # Columnas exportadas (0-indexed):
            # 0:AÑO 1:MES 2:FECHA 3:N.RAD 4:ORIGEN 5:ASUNTO 6:TIPO_DOC
            # 7:RESPONSABLE 8:CASO_BMP 9:N_RAD_SAL 10:FECHA_SAL 11:TIPO_RESP 12:TRAMITE 13:DÍAS
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not any(v for v in row if v is not None):
                    continue
                # Detectar que col[0] sea un año (número entero)
                try:
                    int(row[0])
                except (ValueError, TypeError):
                    continue  # Saltar filas que no sean datos

                anio_val   = _v(row[0])
                mes_val    = _v(row[1])
                fi_val     = _norm_fecha(_v(row[2]))
                rad_val    = _v(row[3])
                orig_val   = _v(row[4])
                asunto_val = _v(row[5])
                tipo_d_val = _v(row[6])
                resp_val   = _v(row[7])
                bmp_val    = _v(row[8])
                rad_sal    = _v(row[9])
                fsal_val   = _norm_fecha(_v(row[10]) if len(row) > 10 else None)
                tipor_val  = _v(row[11]) if len(row) > 11 else None
                tram_val   = _v(row[12]) if len(row) > 12 else None
                # row[13] = DÍAS TRANSCURRIDOS → se omite (valor calculado)

                if mes_val:
                    mes_val = mes_val.strip().upper()
                resp_val = _clean_responsable(resp_val)

                cur = conn.execute("""
                    INSERT INTO correspondencia
                    (anio, mes, fecha_ingreso, n_radicado, origen, asunto, tipo_documento,
                     responsable, caso_bmp, fecha_radicado_salida, tipo_respuesta, tramite_salida)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, [anio_val, mes_val, fi_val, rad_val, orig_val, asunto_val,
                      tipo_d_val, resp_val, bmp_val, fsal_val, tipor_val, tram_val])
                cid = cur.lastrowid
                insertados += 1

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


# ── IMPORTAR DESDE AGIL SALUD (Documentos.xlsx) ───────────────────────────────

_AGILSALUD_DESTINATARIOS = {
    "MARTHA PATRICIA AÑEZ MAESTRE",
    "MABEL GICELA HURTADO SANCHEZ",
}

_MES_NOMBRES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}


@router.get("/importar-agilsalud", response_class=HTMLResponse)
async def importar_agilsalud_form(request: Request, msg: str = ""):
    return templates.TemplateResponse("corr_importar_agilsalud.html", {
        "request": request,
        "active": "corr_importar_agilsalud",
        "msg": msg,
        "preview": None,
    })


@router.post("/importar-agilsalud/preview", response_class=HTMLResponse)
async def importar_agilsalud_preview(request: Request, archivo: UploadFile = File(...)):
    try:
        import openpyxl
    except ImportError:
        return templates.TemplateResponse("corr_importar_agilsalud.html", {
            "request": request, "active": "corr_importar_agilsalud",
            "msg": "error_openpyxl", "preview": None,
        })

    contenido = await archivo.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)
        ws = wb.active
    except Exception:
        return templates.TemplateResponse("corr_importar_agilsalud.html", {
            "request": request, "active": "corr_importar_agilsalud",
            "msg": "error_archivo", "preview": None,
        })

    filas = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        # Columnas (1-indexed → 0-indexed):
        # Col 1 (idx 0): Número de radicado → n_radicado
        # Col 5 (idx 4): Destinatario → responsable (filtrar)
        # Col 7 (idx 6): Dependencia Remitente → origen
        # Col 9 (idx 8): Correo Electrónico Remitente → correo_remitente
        # Col 11 (idx 10): Fecha de radicación → fecha_ingreso
        # Col 13 (idx 12): Asunto → asunto
        destinatario = str(row[4] or "").strip().upper() if len(row) > 4 else ""
        if destinatario not in _AGILSALUD_DESTINATARIOS:
            continue

        n_radicado = str(row[0] or "").strip() if len(row) > 0 else ""
        origen = str(row[6] or "").strip() if len(row) > 6 else ""
        correo_remitente = str(row[8] or "").strip() if len(row) > 8 else ""
        fecha_raw = row[10] if len(row) > 10 else None
        asunto = str(row[12] or "").strip() if len(row) > 12 else ""

        # Parsear fecha
        fecha_ingreso = ""
        mes = ""
        anio = ""
        if fecha_raw:
            try:
                if hasattr(fecha_raw, "strftime"):
                    fecha_ingreso = fecha_raw.strftime("%Y-%m-%d")
                    mes = _MES_NOMBRES.get(fecha_raw.month, "")
                    anio = fecha_raw.year
                else:
                    s = str(fecha_raw).strip()
                    # formato '2026-04-01 07:26:27.280000'
                    fecha_ingreso = s[:10]
                    from datetime import datetime as _dt
                    dt = _dt.fromisoformat(fecha_ingreso)
                    mes = _MES_NOMBRES.get(dt.month, "")
                    anio = dt.year
            except Exception:
                pass

        # Normalizar responsable al nombre canónico del catálogo
        resp_map = {
            "MARTHA PATRICIA AÑEZ MAESTRE": "MARTHA PATRICIA AÑEZ MAESTRE",
            "MABEL GICELA HURTADO SANCHEZ": "MABEL GICELLA HURTADO",
        }
        responsable = resp_map.get(destinatario, destinatario.title())

        filas.append({
            "n_radicado": n_radicado,
            "responsable": responsable,
            "origen": origen,
            "correo_remitente": correo_remitente,
            "fecha_ingreso": fecha_ingreso,
            "mes": mes,
            "anio": anio,
            "asunto": asunto,
        })

    if not filas:
        return templates.TemplateResponse("corr_importar_agilsalud.html", {
            "request": request, "active": "corr_importar_agilsalud",
            "msg": "error_vacio", "preview": None,
        })

    import json
    preview_json = json.dumps(filas, ensure_ascii=False)
    return templates.TemplateResponse("corr_importar_agilsalud.html", {
        "request": request,
        "active": "corr_importar_agilsalud",
        "msg": "",
        "preview": filas,
        "preview_json": preview_json,
    })


@router.post("/importar-agilsalud/confirmar")
async def importar_agilsalud_confirmar(request: Request, datos_json: str = Form(...)):
    import json
    try:
        filas = json.loads(datos_json)
    except Exception:
        return RedirectResponse("/correspondencia/importar-agilsalud?msg=error_import", status_code=303)

    conn = get_db()
    try:
        insertados = 0
        for f in filas:
            conn.execute(
                """INSERT INTO correspondencia
                   (anio, mes, fecha_ingreso, n_radicado, origen, asunto,
                    responsable, correo_remitente)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (f.get("anio") or None, f.get("mes") or None,
                 f.get("fecha_ingreso") or None, f.get("n_radicado") or None,
                 f.get("origen") or None, f.get("asunto") or None,
                 f.get("responsable") or None, f.get("correo_remitente") or None),
            )
            insertados += 1
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        return RedirectResponse("/correspondencia/importar-agilsalud?msg=error_import", status_code=303)
    conn.close()
    return RedirectResponse(f"/correspondencia/importar-agilsalud?msg=ok_{insertados}", status_code=303)


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
    _ANEXO_VALS = {"ANEXO EXPEDIENTE", "ANEXO AL EXPEDIENTE"}
    if reg.get("tipo_respuesta") and reg["tipo_respuesta"].strip().upper() in _ANEXO_VALS:
        dias = None
    reg["dias_transcurridos"] = dias
    if reg.get("tipo_respuesta") and reg["tipo_respuesta"].strip().upper() in _ANEXO_VALS:
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
    correo_remitente: str = Form(""),
):
    conn = get_db()
    conn.execute("""
        UPDATE correspondencia SET
        anio=?, mes=?, fecha_ingreso=?, n_radicado=?, origen=?, asunto=?,
        tipo_documento=?, responsable=?, caso_bmp=?, fecha_radicado_salida=?,
        tipo_respuesta=?, tramite_salida=?, correo_remitente=?,
        updated_at=datetime('now','localtime')
        WHERE id=?
    """, [
        anio, _v(mes), _v(fecha_ingreso), _v(n_radicado), _v(origen), _v(asunto),
        _v(tipo_documento), _v(responsable), _v(caso_bmp),
        _v(fecha_radicado_salida), _v(tipo_respuesta), _v(tramite_salida),
        _v(correo_remitente), reg_id,
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
