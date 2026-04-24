from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pathlib import Path
from app.template_utils import make_templates
from datetime import date
import io
import zipfile

from app.database import get_db
from app.routers.correspondencia import _calcular_semaforo_row
from app.auth_utils import puede_escribir as _pw, registrar_log

_MOD = "backup"

router = APIRouter(prefix="/backup")
templates = make_templates(str(Path(__file__).parent.parent / "templates"))


def _v(val):
    """Sanitiza valor de celda: devuelve None si está vacío."""
    if val is None:
        return None
    s = str(val).strip()
    if s in ("", "nan", "None", "#VALUE!", "#N/A", "#REF!", "—"):
        return None
    return s


# ── Página principal ───────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def backup_home(request: Request, msg: str = ""):
    conn = get_db()
    total_base          = conn.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0]
    total_digitales     = conn.execute("SELECT COUNT(*) FROM exp_digitales").fetchone()[0]
    total_sala          = conn.execute("SELECT COUNT(*) FROM sala_agenda").fetchone()[0]
    total_control_autos = conn.execute("SELECT COUNT(*) FROM control_autos_sustanciacion").fetchone()[0]
    conn.close()
    return templates.TemplateResponse("backup.html", {
        "request": request,
        "msg": msg,
        "total_base": total_base,
        "total_digitales": total_digitales,
        "total_sala": total_sala,
        "total_control_autos": total_control_autos,
    })


# ── Exportar Excel completo (3 hojas) ─────────────────────────────────────────

@router.get("/exportar")
async def backup_exportar():
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return RedirectResponse("/backup/?msg=error_openpyxl")

    conn = get_db()
    exps        = conn.execute("SELECT * FROM expedientes ORDER BY anio, n_expediente").fetchall()
    dig_exps    = conn.execute("SELECT * FROM exp_digitales ORDER BY anio DESC, n_expediente ASC").fetchall()
    dig_coms    = conn.execute(
        "SELECT * FROM exp_comunicaciones ORDER BY exp_digital_id ASC, fecha_envio ASC, id ASC"
    ).fetchall()
    dig_revs    = conn.execute(
        "SELECT exp_digital_id, MAX(fecha_revision) AS ultima_revision FROM exp_revisiones GROUP BY exp_digital_id"
    ).fetchall()
    sala        = conn.execute("SELECT * FROM sala_agenda ORDER BY fecha, franja").fetchall()
    ctrl_autos  = conn.execute(
        "SELECT * FROM control_autos_sustanciacion ORDER BY fecha_auto ASC, id ASC"
    ).fetchall()
    conn.close()

    ultima_rev = {r["exp_digital_id"]: r["ultima_revision"] for r in dig_revs}
    coms_por_exp: dict[int, list] = {}
    for c in dig_coms:
        coms_por_exp.setdefault(c["exp_digital_id"], []).append(dict(c))

    wb = openpyxl.Workbook()

    h_font    = Font(bold=True, color="FFFFFF", size=10)
    center    = Alignment(horizontal="center", vertical="center", wrap_text=True)
    alt_fill  = PatternFill("solid", fgColor="EBF1F8")
    sub_fill  = PatternFill("solid", fgColor="dbeafe")
    fill_base = PatternFill("solid", fgColor="1B4F8A")
    fill_dig  = PatternFill("solid", fgColor="1e3a5f")
    fill_sala = PatternFill("solid", fgColor="065F46")

    # ── Hoja 1: Base Expedientes ───────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Base Expedientes"

    headers1 = [
        "N. EXPEDIENTE", "AÑO", "MES", "ORIGEN DEL PROCESO",
        "N. RADICADO", "FECHA RADICADO", "FECHA SIIAS",
        "INGRESO SIIAS", "INGRESO SIAD", "FECHA INGRESO SIAD", "INGRESO SID4",
        "NOMBRE ABOGADO", "IMPEDIMENTO", "INVESTIGADO", "PERFIL INDAGADO",
        "ENTIDAD ORIGEN", "QUEJOSO",
        "ASUNTO", "TIPOLOGÍA", "DESCRIPCIÓN TIPOLOGÍA",
        "SINIESTRO", "RESP. SINIESTRO", "ACOSO/MALTRATO", "RESP. ACOSO",
        "CORRUPCIÓN", "VALORES INSTITUCIONALES", "FECHA HECHOS",
        "F. APERTURA INDAGACIÓN", "AUTO APERTURA IND.", "F. AUTO APERTURA IND.",
        "PLAZO IND. (días)", "F. VENCIMIENTO IND.",
        "AUTO TRASLADO IND.", "F. AUTO TRASLADO IND.",
        "AUTO ARCHIVO IND.", "F. AUTO ARCHIVO IND.",
        "F. APERTURA INVESTIGACIÓN", "AUTO APERTURA INV.", "F. AUTO APERTURA INV.",
        "PLAZO INV. (días)", "F. VENCIMIENTO INV.",
        "AUTO TRASLADO INV.", "F. AUTO TRASLADO INV.",
        "AUTO ARCHIVO INV.", "F. AUTO ARCHIVO INV.",
        "ETAPA", "ESTADO DEL PROCESO", "OBSERVACIONES FINALES",
        "CREADO POR", "FECHA CREACIÓN", "ÚLTIMA ACTUALIZACIÓN",
    ]
    campos1 = [
        "n_expediente","anio","mes","origen_proceso","n_radicado",
        "fecha_radicado","fecha_siias","ingreso_siias","ingreso_siad",
        "fecha_ingreso_siad","ingreso_sid4","nombre_abogado","impedimento",
        "investigado","perfil_indagado","entidad_origen","quejoso",
        "asunto","tipologia","descripcion_tipologia",
        "relacionado_siniestro","responsable_siniestro",
        "relacionado_acoso","responsable_acoso","relacionado_corrupcion",
        "valores_institucionales","fecha_hechos",
        "fecha_apertura_indagacion","numero_auto_apertura_ind",
        "fecha_auto_apertura_ind","plazo_ind","fecha_vencimiento_ind",
        "numero_auto_traslado_ind","fecha_auto_traslado_ind",
        "numero_auto_archivo_ind","fecha_auto_archivo_ind",
        "fecha_apertura_investigacion","numero_auto_apertura_inv",
        "fecha_auto_apertura_inv","plazo_inv","fecha_vencimiento_inv",
        "numero_auto_traslado_inv","fecha_auto_traslado_inv",
        "numero_auto_archivo_inv","fecha_auto_archivo_inv",
        "etapa","estado_proceso","observaciones_finales",
        "created_by","created_at","updated_at",
    ]
    for col_idx, h in enumerate(headers1, 1):
        cell = ws1.cell(row=1, column=col_idx, value=h)
        cell.fill = fill_base
        cell.font = h_font
        cell.alignment = center
    ws1.row_dimensions[1].height = 40

    for row_idx, row in enumerate(exps, 2):
        d = dict(row)
        fill = alt_fill if row_idx % 2 == 0 else None
        for col_idx, campo in enumerate(campos1, 1):
            cell = ws1.cell(row=row_idx, column=col_idx, value=d.get(campo))
            cell.alignment = Alignment(vertical="center")
            if fill:
                cell.fill = fill

    for col in ws1.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws1.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)
    ws1.freeze_panes = "A2"

    # ── Hoja 2: Exp. Digitales ─────────────────────────────────────────────────
    ws2 = wb.create_sheet("Exp. Digitales")

    headers2 = [
        "N° Expediente", "Año", "Abogado", "Etapa", "Queja Inicial",
        "Radicado Auto", "Nombre Auto", "Fecha Auto",
        "Obs. Generales", "Última Revisión",
        "Radicado Comunicación", "Dependencia", "Fecha Envío",
        "Fecha Seguimiento", "Radicado Respuesta", "Fecha Respuesta",
        "Responsable", "Observaciones Com.",
    ]
    for col_idx, h in enumerate(headers2, 1):
        cell = ws2.cell(row=1, column=col_idx, value=h)
        cell.fill = fill_dig
        cell.font = h_font
        cell.alignment = center
    ws2.row_dimensions[1].height = 30

    for exp in dig_exps:
        ed = dict(exp)
        exp_coms = coms_por_exp.get(ed["id"], [])
        primera = exp_coms[0] if exp_coms else {}
        row = [
            ed.get("n_expediente"), ed.get("anio"), ed.get("abogado"), ed.get("etapa"),
            ed.get("queja_inicial"), ed.get("radicado_auto"), ed.get("nombre_auto"), ed.get("fecha_auto"),
            ed.get("observaciones"), ultima_rev.get(ed["id"]),
            primera.get("radicado_comunicacion"), primera.get("dependencia"),
            primera.get("fecha_envio"), primera.get("fecha_seguimiento"),
            primera.get("radicado_respuesta"), primera.get("fecha_respuesta"),
            primera.get("responsable"), primera.get("observaciones"),
        ]
        ws2.append(row)
        for com in exp_coms[1:]:
            sub_row = [None] * 10 + [
                com.get("radicado_comunicacion"), com.get("dependencia"),
                com.get("fecha_envio"), com.get("fecha_seguimiento"),
                com.get("radicado_respuesta"), com.get("fecha_respuesta"),
                com.get("responsable"), com.get("observaciones"),
            ]
            ws2.append(sub_row)
            for cell in ws2[ws2.max_row]:
                cell.fill = sub_fill

    col_widths2 = [15, 6, 22, 20, 14, 20, 30, 14, 40, 22, 22, 25, 14, 16, 22, 14, 20, 40]
    for i, w in enumerate(col_widths2, 1):
        ws2.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws2.freeze_panes = "A2"

    # ── Hoja 3: Sala de Audiencias ─────────────────────────────────────────────
    ws3 = wb.create_sheet("Sala de Audiencias")

    headers3 = ["Fecha", "Franja", "Título", "Descripción", "Estado", "Responsable", "Fecha Creación"]
    campos3   = ["fecha", "franja", "titulo", "descripcion", "estado", "responsable", "created_at"]

    for col_idx, h in enumerate(headers3, 1):
        cell = ws3.cell(row=1, column=col_idx, value=h)
        cell.fill = fill_sala
        cell.font = h_font
        cell.alignment = center
    ws3.row_dimensions[1].height = 30

    for row_idx, row in enumerate(sala, 2):
        d = dict(row)
        fill = alt_fill if row_idx % 2 == 0 else None
        for col_idx, campo in enumerate(campos3, 1):
            cell = ws3.cell(row=row_idx, column=col_idx, value=d.get(campo))
            cell.alignment = Alignment(vertical="center")
            if fill:
                cell.fill = fill

    col_widths3 = [14, 16, 30, 40, 12, 25, 20]
    for i, w in enumerate(col_widths3, 1):
        ws3.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws3.freeze_panes = "A2"

    # ── Hoja 4: Control de Autos de Sustanciación ─────────────────────────────
    ws4 = wb.create_sheet("Control Autos")
    fill_autos = PatternFill("solid", fgColor="2E7D32")

    headers4 = ["EXPEDIENTE", "NÚMERO DEL AUTO", "FECHA DEL AUTO", "ASUNTO AUTO", "ABOGADO RESPONSABLE", "OBSERVACIONES"]
    campos4   = ["expediente", "numero_auto", "fecha_auto", "asunto_auto", "abogado_responsable", "observaciones"]

    for col_idx, h in enumerate(headers4, 1):
        cell = ws4.cell(row=1, column=col_idx, value=h)
        cell.fill = fill_autos
        cell.font = h_font
        cell.alignment = center
    ws4.row_dimensions[1].height = 30

    for row_idx, row in enumerate(ctrl_autos, 2):
        d = dict(row)
        fill = alt_fill if row_idx % 2 == 0 else None
        for col_idx, campo in enumerate(campos4, 1):
            cell = ws4.cell(row=row_idx, column=col_idx, value=d.get(campo))
            cell.alignment = Alignment(vertical="center")
            if fill:
                cell.fill = fill

    col_widths4 = [18, 16, 16, 48, 22, 30]
    for i, w in enumerate(col_widths4, 1):
        ws4.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws4.freeze_panes = "A2"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    hoy = date.today().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=OCDI_Respaldo_Completo_{hoy}.xlsx"},
    )


# ── Importar Excel completo (reemplaza todo) ───────────────────────────────────

@router.post("/importar")
async def backup_importar(request: Request, archivo: UploadFile = File(...)):
    user = getattr(request.state, "user", None)
    if not _pw(user, _MOD):
        return RedirectResponse("/backup/?msg=sin_permiso", status_code=303)
    try:
        import openpyxl
    except ImportError:
        return RedirectResponse("/backup/?msg=error_openpyxl", status_code=303)

    contenido = await archivo.read()
    if not contenido:
        return RedirectResponse("/backup/?msg=error_vacio", status_code=303)

    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)
    except Exception:
        return RedirectResponse("/backup/?msg=error_archivo", status_code=303)

    conn = get_db()
    stats = {"base": 0, "digitales": 0, "coms": 0, "sala": 0, "autos": 0}

    try:
        # ── Hoja 1: Base Expedientes ───────────────────────────────────────────
        if "Base Expedientes" in wb.sheetnames:
            ws1 = wb["Base Expedientes"]
            campos1 = [
                "n_expediente","anio","mes","origen_proceso","n_radicado",
                "fecha_radicado","fecha_siias","ingreso_siias","ingreso_siad",
                "fecha_ingreso_siad","ingreso_sid4","nombre_abogado","impedimento",
                "investigado","perfil_indagado","entidad_origen","quejoso",
                "asunto","tipologia","descripcion_tipologia",
                "relacionado_siniestro","responsable_siniestro",
                "relacionado_acoso","responsable_acoso","relacionado_corrupcion",
                "valores_institucionales","fecha_hechos",
                "fecha_apertura_indagacion","numero_auto_apertura_ind",
                "fecha_auto_apertura_ind","plazo_ind","fecha_vencimiento_ind",
                "numero_auto_traslado_ind","fecha_auto_traslado_ind",
                "numero_auto_archivo_ind","fecha_auto_archivo_ind",
                "fecha_apertura_investigacion","numero_auto_apertura_inv",
                "fecha_auto_apertura_inv","plazo_inv","fecha_vencimiento_inv",
                "numero_auto_traslado_inv","fecha_auto_traslado_inv",
                "numero_auto_archivo_inv","fecha_auto_archivo_inv",
                "etapa","estado_proceso","observaciones_finales",
                "created_by","created_at","updated_at",
            ]
            # Borrar todo (CASCADE elimina escaneos y actuaciones)
            conn.execute("DELETE FROM escaneos")
            conn.execute("DELETE FROM actuaciones")
            conn.execute("DELETE FROM expedientes")
            for row in ws1.iter_rows(min_row=2, values_only=True):
                if not any(v for v in row if v is not None):
                    continue
                n_exp = _v(row[0]) if len(row) > 0 else None
                if not n_exp:
                    continue
                vals = [_v(row[i]) if i < len(row) else None for i in range(len(campos1))]
                conn.execute(
                    f"INSERT INTO expedientes ({', '.join(campos1)}) VALUES ({', '.join(['?']*len(campos1))})",
                    vals,
                )
                stats["base"] += 1

        # ── Hoja 2: Exp. Digitales ─────────────────────────────────────────────
        if "Exp. Digitales" in wb.sheetnames:
            ws2 = wb["Exp. Digitales"]
            # Borrar todo (CASCADE elimina comunicaciones y revisiones)
            conn.execute("DELETE FROM exp_revisiones")
            conn.execute("DELETE FROM exp_comunicaciones")
            conn.execute("DELETE FROM exp_digitales")

            current_exp_id = None
            for row in ws2.iter_rows(min_row=2, values_only=True):
                if not any(v for v in row if v is not None):
                    continue
                n_exp = _v(row[0]) if len(row) > 0 else None
                if n_exp:
                    # Fila de expediente
                    cur = conn.execute(
                        """INSERT INTO exp_digitales
                           (n_expediente, anio, abogado, etapa, queja_inicial,
                            radicado_auto, nombre_auto, fecha_auto, observaciones)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        [
                            n_exp,
                            _v(row[1]) if len(row) > 1 else None,
                            _v(row[2]) if len(row) > 2 else None,
                            _v(row[3]) if len(row) > 3 else None,
                            _v(row[4]) if len(row) > 4 else None,
                            _v(row[5]) if len(row) > 5 else None,
                            _v(row[6]) if len(row) > 6 else None,
                            _v(row[7]) if len(row) > 7 else None,
                            _v(row[8]) if len(row) > 8 else None,
                        ],
                    )
                    current_exp_id = cur.lastrowid
                    stats["digitales"] += 1
                    # Restaurar última revisión si existe
                    ultima_rev_val = _v(row[9]) if len(row) > 9 else None
                    if ultima_rev_val:
                        conn.execute(
                            "INSERT INTO exp_revisiones (exp_digital_id, fecha_revision) VALUES (?, ?)",
                            (current_exp_id, ultima_rev_val),
                        )

                # Comunicación (fila principal o sub-fila)
                if current_exp_id:
                    rad_com    = _v(row[10]) if len(row) > 10 else None
                    dependencia = _v(row[11]) if len(row) > 11 else None
                    if rad_com or dependencia:
                        conn.execute(
                            """INSERT INTO exp_comunicaciones
                               (exp_digital_id, radicado_comunicacion, dependencia,
                                fecha_envio, fecha_seguimiento, radicado_respuesta,
                                fecha_respuesta, responsable, observaciones)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            [
                                current_exp_id,
                                rad_com,
                                dependencia,
                                _v(row[12]) if len(row) > 12 else None,
                                _v(row[13]) if len(row) > 13 else None,
                                _v(row[14]) if len(row) > 14 else None,
                                _v(row[15]) if len(row) > 15 else None,
                                _v(row[16]) if len(row) > 16 else None,
                                _v(row[17]) if len(row) > 17 else None,
                            ],
                        )
                        stats["coms"] += 1

        # ── Hoja 3: Sala de Audiencias ─────────────────────────────────────────
        if "Sala de Audiencias" in wb.sheetnames:
            ws3 = wb["Sala de Audiencias"]
            conn.execute("DELETE FROM sala_agenda")
            for row in ws3.iter_rows(min_row=2, values_only=True):
                if not any(v for v in row if v is not None):
                    continue
                fecha  = _v(row[0]) if len(row) > 0 else None
                franja = _v(row[1]) if len(row) > 1 else None
                if not fecha or not franja:
                    continue
                conn.execute(
                    """INSERT INTO sala_agenda (fecha, franja, titulo, descripcion, estado, responsable)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    [
                        fecha, franja,
                        _v(row[2]) if len(row) > 2 else None,
                        _v(row[3]) if len(row) > 3 else None,
                        _v(row[4]) if len(row) > 4 else "Ocupado",
                        _v(row[5]) if len(row) > 5 else None,
                    ],
                )
                stats["sala"] += 1

        # ── Hoja 4: Control de Autos de Sustanciación ─────────────────────────
        if "Control Autos" in wb.sheetnames:
            ws4 = wb["Control Autos"]
            conn.execute("DELETE FROM control_autos_sustanciacion")
            for row in ws4.iter_rows(min_row=2, values_only=True):
                if not any(v for v in row if v is not None):
                    continue
                expediente  = _v(row[0]) if len(row) > 0 else None
                numero_auto = _v(row[1]) if len(row) > 1 else None
                fecha_raw   = row[2] if len(row) > 2 else None
                from datetime import datetime as _dt
                if fecha_raw and hasattr(fecha_raw, 'strftime'):
                    fecha_auto = fecha_raw.strftime("%Y-%m-%d")
                elif fecha_raw:
                    s = str(fecha_raw).strip()
                    fecha_auto = None
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                        try:
                            fecha_auto = _dt.strptime(s, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            pass
                    if not fecha_auto:
                        fecha_auto = s
                else:
                    fecha_auto = None
                asunto_auto = _v(row[3]) if len(row) > 3 else None
                abogado     = _v(row[4]) if len(row) > 4 else None
                obs         = _v(row[5]) if len(row) > 5 else None
                if not any([expediente, numero_auto, fecha_auto, asunto_auto, abogado]):
                    continue
                # Saltar filas de descripción del pie del formato
                if numero_auto and len(numero_auto) > 20:
                    continue
                conn.execute(
                    """INSERT INTO control_autos_sustanciacion
                       (expediente, numero_auto, fecha_auto, asunto_auto, abogado_responsable, observaciones)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    [expediente, numero_auto, fecha_auto, asunto_auto, abogado, obs],
                )
                stats["autos"] += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return RedirectResponse("/backup/?msg=error_import", status_code=303)

    conn.close()
    msg = f"ok_{stats['base']}_{stats['digitales']}_{stats['coms']}_{stats['sala']}_{stats['autos']}"
    return RedirectResponse(f"/backup/?msg={msg}", status_code=303)


# ── Backup ZIP completo (4 carpetas, 4 Excel) ─────────────────────────────────

@router.get("/zip")
async def backup_zip():
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return RedirectResponse("/backup/?msg=error_openpyxl")

    hoy = date.today().strftime("%Y%m%d")
    conn = get_db()

    # ── Cargar todos los datos ────────────────────────────────────────────────
    exps      = conn.execute("SELECT * FROM expedientes ORDER BY anio, n_expediente").fetchall()
    dig_exps  = conn.execute("SELECT * FROM exp_digitales ORDER BY anio DESC, n_expediente ASC").fetchall()
    dig_coms  = conn.execute(
        "SELECT * FROM exp_comunicaciones ORDER BY exp_digital_id ASC, fecha_envio ASC, id ASC"
    ).fetchall()
    dig_revs  = conn.execute(
        "SELECT exp_digital_id, MAX(fecha_revision) AS ultima_revision FROM exp_revisiones GROUP BY exp_digital_id"
    ).fetchall()
    sala         = conn.execute("SELECT * FROM sala_agenda ORDER BY fecha, franja").fetchall()
    ctrl_autos_z = conn.execute(
        "SELECT * FROM control_autos_sustanciacion ORDER BY fecha_auto ASC, id ASC"
    ).fetchall()
    corr_rows_raw = conn.execute("""
        SELECT c.*,
               GROUP_CONCAT(rs.radicado, ' | ') AS radicados_salida,
               GROUP_CONCAT(COALESCE(rs.url, ''), ' | ') AS radicados_urls
        FROM correspondencia c
        LEFT JOIN correspondencia_radicados_salida rs ON rs.correspondencia_id = c.id
        GROUP BY c.id
        ORDER BY c.fecha_ingreso DESC
    """).fetchall()
    corr_rows = [_calcular_semaforo_row(dict(r)) for r in corr_rows_raw]
    conn.close()

    ultima_rev = {r["exp_digital_id"]: r["ultima_revision"] for r in dig_revs}
    coms_por_exp: dict[int, list] = {}
    for c in dig_coms:
        coms_por_exp.setdefault(c["exp_digital_id"], []).append(dict(c))

    h_font   = Font(bold=True, color="FFFFFF", size=10)
    center   = Alignment(horizontal="center", vertical="center", wrap_text=True)
    alt_fill = PatternFill("solid", fgColor="EBF1F8")
    sub_fill = PatternFill("solid", fgColor="dbeafe")

    def make_wb_base() -> io.BytesIO:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Base Expedientes"
        fill = PatternFill("solid", fgColor="1B4F8A")
        headers = [
            "N. EXPEDIENTE","AÑO","MES","ORIGEN DEL PROCESO","N. RADICADO",
            "FECHA RADICADO","FECHA SIIAS","INGRESO SIIAS","INGRESO SIAD",
            "FECHA INGRESO SIAD","INGRESO SID4","NOMBRE ABOGADO","IMPEDIMENTO",
            "INVESTIGADO","PERFIL INDAGADO","ENTIDAD ORIGEN","QUEJOSO",
            "ASUNTO","TIPOLOGÍA","DESCRIPCIÓN TIPOLOGÍA","SINIESTRO","RESP. SINIESTRO",
            "ACOSO/MALTRATO","RESP. ACOSO","CORRUPCIÓN","VALORES INSTITUCIONALES",
            "FECHA HECHOS","F. APERTURA INDAGACIÓN","AUTO APERTURA IND.","F. AUTO APERTURA IND.",
            "PLAZO IND. (días)","F. VENCIMIENTO IND.","AUTO TRASLADO IND.","F. AUTO TRASLADO IND.",
            "AUTO ARCHIVO IND.","F. AUTO ARCHIVO IND.","F. APERTURA INVESTIGACIÓN",
            "AUTO APERTURA INV.","F. AUTO APERTURA INV.","PLAZO INV. (días)","F. VENCIMIENTO INV.",
            "AUTO TRASLADO INV.","F. AUTO TRASLADO INV.","AUTO ARCHIVO INV.","F. AUTO ARCHIVO INV.",
            "ETAPA","ESTADO DEL PROCESO","OBSERVACIONES FINALES","CREADO POR",
            "FECHA CREACIÓN","ÚLTIMA ACTUALIZACIÓN",
        ]
        campos = [
            "n_expediente","anio","mes","origen_proceso","n_radicado","fecha_radicado",
            "fecha_siias","ingreso_siias","ingreso_siad","fecha_ingreso_siad","ingreso_sid4",
            "nombre_abogado","impedimento","investigado","perfil_indagado","entidad_origen",
            "quejoso","asunto","tipologia","descripcion_tipologia","relacionado_siniestro",
            "responsable_siniestro","relacionado_acoso","responsable_acoso","relacionado_corrupcion",
            "valores_institucionales","fecha_hechos","fecha_apertura_indagacion",
            "numero_auto_apertura_ind","fecha_auto_apertura_ind","plazo_ind","fecha_vencimiento_ind",
            "numero_auto_traslado_ind","fecha_auto_traslado_ind","numero_auto_archivo_ind",
            "fecha_auto_archivo_ind","fecha_apertura_investigacion","numero_auto_apertura_inv",
            "fecha_auto_apertura_inv","plazo_inv","fecha_vencimiento_inv","numero_auto_traslado_inv",
            "fecha_auto_traslado_inv","numero_auto_archivo_inv","fecha_auto_archivo_inv",
            "etapa","estado_proceso","observaciones_finales","created_by","created_at","updated_at",
        ]
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=ci, value=h)
            cell.fill = fill; cell.font = h_font; cell.alignment = center
        ws.row_dimensions[1].height = 40
        for ri, row in enumerate(exps, 2):
            d = dict(row)
            rf = alt_fill if ri % 2 == 0 else None
            for ci, campo in enumerate(campos, 1):
                cell = ws.cell(row=ri, column=ci, value=d.get(campo))
                cell.alignment = Alignment(vertical="center")
                if rf: cell.fill = rf
        for col in ws.columns:
            ml = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(ml + 4, 40)
        ws.freeze_panes = "A2"
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        return buf

    def make_wb_correspondencia() -> io.BytesIO:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "CORRESPONDENCIA"
        fill = PatternFill("solid", fgColor="1B4F8A")
        link_font = Font(color="0563C1", underline="single", size=10)
        headers = [
            "AÑO", "MES", "FECHA INGRESO DE OFICIO", "N. RADICADOS",
            "ENTIDAD", "CORREO REMITENTE", "ASUNTO", "NUMERO SINPROC PERSONERIA",
            "TIPO DE REQUERIMIENTO", "TERMINO (DIAS)", "TIPO DE DOCUMENTO",
            "RESPONSABLE", "CASO BMP", "N RADICADO SALIDA",
            "FECHA RADICADO DE SALIDA", "TIPO DE RESPUESTA", "OBSERVACIONES",
            "FECHA DE VENCIMIENTO LEGAL",
            "FECHA REVISIÓN SUGERIDA (−2 días hábiles)",
            "DÍAS TRANSCURRIDOS",
        ]
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=ci, value=h)
            cell.fill = fill; cell.font = h_font; cell.alignment = center
        ws.row_dimensions[1].height = 36
        for ri, d in enumerate(corr_rows, 2):
            rf = alt_fill if ri % 2 == 0 else None
            urls_str = d.get("radicados_urls") or ""
            urls_list = [u.strip() for u in urls_str.split(" | ")] if urls_str.strip() else []
            first_url = next((u for u in urls_list if u), None)
            vals = [
                d.get("anio"), d.get("mes"),
                d.get("fecha_ingreso")[:10] if d.get("fecha_ingreso") else None,
                d.get("n_radicado"), d.get("origen"), d.get("correo_remitente"), d.get("asunto"),
                d.get("sinproc_personeria"), d.get("tipo_requerimiento"), d.get("termino_dias"),
                d.get("tipo_documento"), d.get("responsable"), d.get("caso_bmp"),
                d.get("radicados_salida"),           # col 14 — N RADICADO SALIDA
                d.get("fecha_radicado_salida")[:10] if d.get("fecha_radicado_salida") else None,
                d.get("tipo_respuesta"), d.get("tramite_salida"),
                d.get("fecha_vencimiento"),           # col 18 — plazo legal real
                d.get("fecha_termino_respuesta"),     # col 19 — fecha revisión sugerida
                d.get("dias_transcurridos"),
            ]
            for ci, v in enumerate(vals, 1):
                cell = ws.cell(row=ri, column=ci, value=v)
                cell.alignment = Alignment(vertical="center", wrap_text=ci in (5, 7))
                if rf: cell.fill = rf
            if first_url and d.get("radicados_salida"):
                rad_cell = ws.cell(row=ri, column=14)
                rad_cell.hyperlink = first_url
                rad_cell.font = link_font
        col_widths = [6, 12, 20, 18, 30, 30, 40, 20, 40, 10, 18, 28, 10, 22, 20, 25, 30, 20, 28, 8]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
        ws.freeze_panes = "A2"
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        return buf

    def make_wb_digitales() -> io.BytesIO:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "EXP DIGIT 2025-2026"
        fill = PatternFill("solid", fgColor="1e3a5f")
        headers = [
            "N° Expediente","Año","Abogado","Etapa","Queja Inicial",
            "Radicado Auto","Nombre Auto","Fecha Auto",
            "Obs. Generales","Última Revisión",
            "Radicado Comunicación","Dependencia","Fecha Envío",
            "Fecha Seguimiento","Radicado Respuesta","Fecha Respuesta",
            "Responsable","Observaciones",
        ]
        ws.append(["SEGUIMIENTO EXPEDIENTES DIGITALES"])
        ws.append(headers)
        for cell in ws[2]:
            cell.font = h_font; cell.fill = fill
            cell.alignment = Alignment(horizontal="center")
        for exp in dig_exps:
            ed = dict(exp)
            exp_coms = coms_por_exp.get(ed["id"], [])
            primera = exp_coms[0] if exp_coms else {}
            ws.append([
                ed.get("n_expediente"), ed.get("anio"), ed.get("abogado"), ed.get("etapa"),
                ed.get("queja_inicial"), ed.get("radicado_auto"), ed.get("nombre_auto"), ed.get("fecha_auto"),
                ed.get("observaciones"), ultima_rev.get(ed["id"]),
                primera.get("radicado_comunicacion"), primera.get("dependencia"),
                primera.get("fecha_envio"), primera.get("fecha_seguimiento"),
                primera.get("radicado_respuesta"), primera.get("fecha_respuesta"),
                primera.get("responsable"), primera.get("observaciones"),
            ])
            for com in exp_coms[1:]:
                sr = [None]*10 + [
                    com.get("radicado_comunicacion"), com.get("dependencia"),
                    com.get("fecha_envio"), com.get("fecha_seguimiento"),
                    com.get("radicado_respuesta"), com.get("fecha_respuesta"),
                    com.get("responsable"), com.get("observaciones"),
                ]
                ws.append(sr)
                for cell in ws[ws.max_row]: cell.fill = sub_fill
        col_widths = [15, 6, 22, 20, 14, 20, 30, 14, 40, 22, 22, 25, 14, 16, 22, 14, 20, 40]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        return buf

    def make_wb_sala() -> io.BytesIO:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sala de Audiencias"
        fill = PatternFill("solid", fgColor="065F46")
        headers = ["Fecha","Franja","Título","Descripción","Estado","Responsable","Fecha Creación"]
        campos  = ["fecha","franja","titulo","descripcion","estado","responsable","created_at"]
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=ci, value=h)
            cell.fill = fill; cell.font = h_font; cell.alignment = center
        ws.row_dimensions[1].height = 30
        for ri, row in enumerate(sala, 2):
            d = dict(row)
            rf = alt_fill if ri % 2 == 0 else None
            for ci, campo in enumerate(campos, 1):
                cell = ws.cell(row=ri, column=ci, value=d.get(campo))
                cell.alignment = Alignment(vertical="center")
                if rf: cell.fill = rf
        col_widths = [14, 16, 30, 40, 12, 25, 20]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
        ws.freeze_panes = "A2"
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        return buf

    def make_wb_control_autos() -> io.BytesIO:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Control Autos"
        fill = PatternFill("solid", fgColor="2E7D32")
        headers = ["EXPEDIENTE", "NÚMERO DEL AUTO", "FECHA DEL AUTO", "ASUNTO AUTO", "ABOGADO RESPONSABLE", "OBSERVACIONES"]
        campos  = ["expediente", "numero_auto", "fecha_auto", "asunto_auto", "abogado_responsable", "observaciones"]
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=ci, value=h)
            cell.fill = fill; cell.font = h_font; cell.alignment = center
        ws.row_dimensions[1].height = 30
        alt_autos = PatternFill("solid", fgColor="F1F8E9")
        for ri, row in enumerate(ctrl_autos_z, 2):
            d = dict(row)
            rf = alt_autos if ri % 2 == 0 else None
            for ci, campo in enumerate(campos, 1):
                cell = ws.cell(row=ri, column=ci, value=d.get(campo))
                cell.alignment = Alignment(vertical="center")
                if rf: cell.fill = rf
        col_widths = [18, 16, 16, 48, 22, 30]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
        ws.freeze_panes = "A2"
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        return buf

    # ── Construir ZIP ─────────────────────────────────────────────────────────
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            f"OCDI/01_Base_Expedientes/Base_Expedientes_{hoy}.xlsx",
            make_wb_base().read(),
        )
        zf.writestr(
            f"OCDI/02_Lista_Reparto_Abogados/Correspondencia_{hoy}.xlsx",
            make_wb_correspondencia().read(),
        )
        zf.writestr(
            f"OCDI/03_Expedientes_Digitales/Exp_Digitales_{hoy}.xlsx",
            make_wb_digitales().read(),
        )
        zf.writestr(
            f"OCDI/04_Sala_Audiencias/Sala_Audiencias_{hoy}.xlsx",
            make_wb_sala().read(),
        )
        zf.writestr(
            f"OCDI/05_Control_Autos_Sustanciacion/SDS-CDO-FT-001_Control_Autos_{hoy}.xlsx",
            make_wb_control_autos().read(),
        )
    zip_buf.seek(0)

    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=OCDI_Backup_Completo_{hoy}.zip"},
    )
