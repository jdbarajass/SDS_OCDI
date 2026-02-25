from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import date, timedelta
from typing import List, Optional
import io

from app.database import get_db, calcular_alerta, row_to_dict

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

MESES = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO",
         "JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]

ETAPAS = [
    "INDAGACIÓN PREVIA",
    "INVESTIGACIÓN DISCIPLINARIA",
    "ARCHIVADO",
    "SANCIONADO",
    "OTRO",
]

ESTADOS = [
    "EN TRÁMITE",
    "AUTO DE ARCHIVO",
    "ARCHIVADO",
    "INVESTIGACIÓN DISCIPLINARIA",
    "PLIEGO DE CARGOS",
    "FALLO SANCIONATORIO",
    "FALLO ABSOLUTORIO",
]


def _limpiar(valor):
    """Convierte cadena vacía en None."""
    if valor is None or str(valor).strip() == "":
        return None
    return str(valor).strip()


def _enriquecer(exp: dict) -> dict:
    """Agrega campos calculados de alerta al expediente."""
    exp["alerta_ind"] = calcular_alerta(exp.get("fecha_vencimiento_ind"))
    exp["alerta_inv"] = calcular_alerta(exp.get("fecha_vencimiento_inv"))
    return exp


# ── Listado ────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def lista_expedientes(
    request: Request,
    q: str = "",
    anio: str = "",
    etapa: str = "",
    abogado: str = "",
    msg: str = "",
):
    conn = get_db()

    # Construcción dinámica de filtros
    filtros = []
    params = []
    if q:
        filtros.append("(n_expediente LIKE ? OR investigado LIKE ? OR asunto LIKE ?)")
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if anio:
        filtros.append("anio = ?")
        params.append(int(anio))
    if etapa:
        filtros.append("etapa LIKE ?")
        params.append(f"%{etapa}%")
    if abogado:
        filtros.append("nombre_abogado LIKE ?")
        params.append(f"%{abogado}%")

    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    rows = conn.execute(
        f"SELECT * FROM expedientes {where} ORDER BY anio DESC, n_expediente DESC",
        params,
    ).fetchall()

    abogados = [r[0] for r in conn.execute(
        "SELECT DISTINCT nombre_abogado FROM expedientes WHERE nombre_abogado IS NOT NULL ORDER BY nombre_abogado"
    ).fetchall()]
    anios = [r[0] for r in conn.execute(
        "SELECT DISTINCT anio FROM expedientes WHERE anio IS NOT NULL ORDER BY anio DESC"
    ).fetchall()]

    conn.close()

    expedientes = [_enriquecer(row_to_dict(r)) for r in rows]

    return templates.TemplateResponse("lista.html", {
        "request": request,
        "expedientes": expedientes,
        "total": len(expedientes),
        "q": q, "anio_filtro": anio, "etapa_filtro": etapa, "abogado_filtro": abogado,
        "abogados": abogados,
        "anios": anios,
        "etapas": ETAPAS,
        "msg": msg,
        "active": "lista",
    })


# ── Nuevo expediente ───────────────────────────────────────────────────────────

@router.get("/expediente/nuevo", response_class=HTMLResponse)
async def nuevo_form(request: Request):
    return templates.TemplateResponse("form.html", {
        "request": request,
        "exp": {},
        "escaneos": [],
        "modos": "nuevo",
        "meses": MESES,
        "etapas": ETAPAS,
        "estados": ESTADOS,
        "active": "nuevo",
        "titulo": "Nuevo Expediente",
        "errores": [],
    })


@router.post("/expediente/nuevo")
async def crear_expediente(request: Request):
    form = await request.form()
    data = {k: _limpiar(v) for k, v in form.items()}
    errores = []

    if not data.get("n_expediente"):
        errores.append("El número de expediente es obligatorio.")
    if not data.get("anio"):
        errores.append("El año es obligatorio.")

    if errores:
        return templates.TemplateResponse("form.html", {
            "request": request,
            "exp": data,
            "escaneos": [],
            "modos": "nuevo",
            "meses": MESES,
            "etapas": ETAPAS,
            "estados": ESTADOS,
            "active": "nuevo",
            "titulo": "Nuevo Expediente",
            "errores": errores,
        })

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO expedientes (
            n_expediente, anio, mes, origen_proceso, n_radicado,
            fecha_radicado, fecha_siias, ingreso_siias, ingreso_siad,
            fecha_ingreso_siad, ingreso_sid4,
            nombre_abogado, impedimento, investigado, perfil_indagado,
            entidad_origen, quejoso,
            asunto, tipologia, descripcion_tipologia,
            relacionado_siniestro, responsable_siniestro,
            relacionado_acoso, responsable_acoso,
            relacionado_corrupcion, valores_institucionales, fecha_hechos,
            fecha_apertura_indagacion, numero_auto_apertura_ind,
            fecha_auto_apertura_ind, plazo_ind, fecha_vencimiento_ind,
            numero_auto_traslado_ind, fecha_auto_traslado_ind,
            numero_auto_archivo_ind, fecha_auto_archivo_ind,
            fecha_apertura_investigacion, numero_auto_apertura_inv,
            fecha_auto_apertura_inv, plazo_inv, fecha_vencimiento_inv,
            numero_auto_traslado_inv, fecha_auto_traslado_inv,
            numero_auto_archivo_inv, fecha_auto_archivo_inv,
            etapa, estado_proceso, observaciones_finales,
            created_by
        ) VALUES (
            :n_expediente, :anio, :mes, :origen_proceso, :n_radicado,
            :fecha_radicado, :fecha_siias, :ingreso_siias, :ingreso_siad,
            :fecha_ingreso_siad, :ingreso_sid4,
            :nombre_abogado, :impedimento, :investigado, :perfil_indagado,
            :entidad_origen, :quejoso,
            :asunto, :tipologia, :descripcion_tipologia,
            :relacionado_siniestro, :responsable_siniestro,
            :relacionado_acoso, :responsable_acoso,
            :relacionado_corrupcion, :valores_institucionales, :fecha_hechos,
            :fecha_apertura_indagacion, :numero_auto_apertura_ind,
            :fecha_auto_apertura_ind, :plazo_ind, :fecha_vencimiento_ind,
            :numero_auto_traslado_ind, :fecha_auto_traslado_ind,
            :numero_auto_archivo_ind, :fecha_auto_archivo_ind,
            :fecha_apertura_investigacion, :numero_auto_apertura_inv,
            :fecha_auto_apertura_inv, :plazo_inv, :fecha_vencimiento_inv,
            :numero_auto_traslado_inv, :fecha_auto_traslado_inv,
            :numero_auto_archivo_inv, :fecha_auto_archivo_inv,
            :etapa, :estado_proceso, :observaciones_finales,
            :created_by
        )
    """, {
        "n_expediente": data.get("n_expediente"),
        "anio": data.get("anio"),
        "mes": data.get("mes"),
        "origen_proceso": data.get("origen_proceso"),
        "n_radicado": data.get("n_radicado"),
        "fecha_radicado": data.get("fecha_radicado"),
        "fecha_siias": data.get("fecha_siias"),
        "ingreso_siias": data.get("ingreso_siias", "NO"),
        "ingreso_siad": data.get("ingreso_siad", "NO"),
        "fecha_ingreso_siad": data.get("fecha_ingreso_siad"),
        "ingreso_sid4": data.get("ingreso_sid4", "NO"),
        "nombre_abogado": data.get("nombre_abogado"),
        "impedimento": data.get("impedimento", "NO"),
        "investigado": data.get("investigado"),
        "perfil_indagado": data.get("perfil_indagado"),
        "entidad_origen": data.get("entidad_origen"),
        "quejoso": data.get("quejoso"),
        "asunto": data.get("asunto"),
        "tipologia": data.get("tipologia"),
        "descripcion_tipologia": data.get("descripcion_tipologia"),
        "relacionado_siniestro": data.get("relacionado_siniestro", "NO"),
        "responsable_siniestro": data.get("responsable_siniestro"),
        "relacionado_acoso": data.get("relacionado_acoso", "NO"),
        "responsable_acoso": data.get("responsable_acoso"),
        "relacionado_corrupcion": data.get("relacionado_corrupcion", "NO"),
        "valores_institucionales": data.get("valores_institucionales"),
        "fecha_hechos": data.get("fecha_hechos"),
        "fecha_apertura_indagacion": data.get("fecha_apertura_indagacion"),
        "numero_auto_apertura_ind": data.get("numero_auto_apertura_ind"),
        "fecha_auto_apertura_ind": data.get("fecha_auto_apertura_ind"),
        "plazo_ind": data.get("plazo_ind") or 180,
        "fecha_vencimiento_ind": data.get("fecha_vencimiento_ind"),
        "numero_auto_traslado_ind": data.get("numero_auto_traslado_ind"),
        "fecha_auto_traslado_ind": data.get("fecha_auto_traslado_ind"),
        "numero_auto_archivo_ind": data.get("numero_auto_archivo_ind"),
        "fecha_auto_archivo_ind": data.get("fecha_auto_archivo_ind"),
        "fecha_apertura_investigacion": data.get("fecha_apertura_investigacion"),
        "numero_auto_apertura_inv": data.get("numero_auto_apertura_inv"),
        "fecha_auto_apertura_inv": data.get("fecha_auto_apertura_inv"),
        "plazo_inv": data.get("plazo_inv") or 180,
        "fecha_vencimiento_inv": data.get("fecha_vencimiento_inv"),
        "numero_auto_traslado_inv": data.get("numero_auto_traslado_inv"),
        "fecha_auto_traslado_inv": data.get("fecha_auto_traslado_inv"),
        "numero_auto_archivo_inv": data.get("numero_auto_archivo_inv"),
        "fecha_auto_archivo_inv": data.get("fecha_auto_archivo_inv"),
        "etapa": data.get("etapa"),
        "estado_proceso": data.get("estado_proceso"),
        "observaciones_finales": data.get("observaciones_finales"),
        "created_by": data.get("created_by"),
    })
    exp_id = cur.lastrowid

    # Escaneos dinámicos (campos escaner_fecha_0, escaner_folio_0, etc.)
    i = 0
    while f"escaner_fecha_{i}" in data or f"escaner_folio_{i}" in data:
        fecha = data.get(f"escaner_fecha_{i}")
        folio = data.get(f"escaner_folio_{i}")
        resp = data.get(f"escaner_responsable_{i}")
        if fecha or folio:
            conn.execute(
                "INSERT INTO escaneos (expediente_id, fecha_escaner, folio, responsable) VALUES (?,?,?,?)",
                (exp_id, fecha, folio, resp),
            )
        i += 1

    conn.commit()
    conn.close()
    return RedirectResponse(f"/expediente/{exp_id}?msg=creado", status_code=303)


# ── Ver expediente ─────────────────────────────────────────────────────────────

@router.get("/expediente/{exp_id}", response_class=HTMLResponse)
async def ver_expediente(request: Request, exp_id: int, msg: str = ""):
    conn = get_db()
    row = conn.execute("SELECT * FROM expedientes WHERE id = ?", (exp_id,)).fetchone()
    if not row:
        conn.close()
        return RedirectResponse("/?msg=no_encontrado")

    exp = _enriquecer(row_to_dict(row))
    escaneos = [row_to_dict(r) for r in conn.execute(
        "SELECT * FROM escaneos WHERE expediente_id = ? ORDER BY id", (exp_id,)
    ).fetchall()]
    actuaciones = [row_to_dict(r) for r in conn.execute(
        "SELECT * FROM actuaciones WHERE expediente_id = ? ORDER BY anio DESC, id DESC", (exp_id,)
    ).fetchall()]
    conn.close()

    return templates.TemplateResponse("detalle.html", {
        "request": request,
        "exp": exp,
        "escaneos": escaneos,
        "actuaciones": actuaciones,
        "msg": msg,
        "active": "lista",
    })


# ── Editar expediente ──────────────────────────────────────────────────────────

@router.get("/expediente/{exp_id}/editar", response_class=HTMLResponse)
async def editar_form(request: Request, exp_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM expedientes WHERE id = ?", (exp_id,)).fetchone()
    if not row:
        conn.close()
        return RedirectResponse("/")
    exp = row_to_dict(row)
    escaneos = [row_to_dict(r) for r in conn.execute(
        "SELECT * FROM escaneos WHERE expediente_id = ? ORDER BY id", (exp_id,)
    ).fetchall()]
    conn.close()

    return templates.TemplateResponse("form.html", {
        "request": request,
        "exp": exp,
        "escaneos": escaneos,
        "modos": "editar",
        "meses": MESES,
        "etapas": ETAPAS,
        "estados": ESTADOS,
        "active": "lista",
        "titulo": f"Editar Expediente #{exp['n_expediente']}",
        "errores": [],
    })


@router.post("/expediente/{exp_id}/editar")
async def actualizar_expediente(request: Request, exp_id: int):
    form = await request.form()
    data = {k: _limpiar(v) for k, v in form.items()}
    errores = []

    if not data.get("n_expediente"):
        errores.append("El número de expediente es obligatorio.")
    if not data.get("anio"):
        errores.append("El año es obligatorio.")

    if errores:
        conn = get_db()
        escaneos = [row_to_dict(r) for r in conn.execute(
            "SELECT * FROM escaneos WHERE expediente_id = ? ORDER BY id", (exp_id,)
        ).fetchall()]
        conn.close()
        return templates.TemplateResponse("form.html", {
            "request": request,
            "exp": {**data, "id": exp_id},
            "escaneos": escaneos,
            "modos": "editar",
            "meses": MESES,
            "etapas": ETAPAS,
            "estados": ESTADOS,
            "active": "lista",
            "titulo": f"Editar Expediente #{data.get('n_expediente', '')}",
            "errores": errores,
        })

    conn = get_db()
    conn.execute("""
        UPDATE expedientes SET
            n_expediente=:n_expediente, anio=:anio, mes=:mes,
            origen_proceso=:origen_proceso, n_radicado=:n_radicado,
            fecha_radicado=:fecha_radicado, fecha_siias=:fecha_siias,
            ingreso_siias=:ingreso_siias, ingreso_siad=:ingreso_siad,
            fecha_ingreso_siad=:fecha_ingreso_siad, ingreso_sid4=:ingreso_sid4,
            nombre_abogado=:nombre_abogado, impedimento=:impedimento,
            investigado=:investigado, perfil_indagado=:perfil_indagado,
            entidad_origen=:entidad_origen, quejoso=:quejoso,
            asunto=:asunto, tipologia=:tipologia,
            descripcion_tipologia=:descripcion_tipologia,
            relacionado_siniestro=:relacionado_siniestro,
            responsable_siniestro=:responsable_siniestro,
            relacionado_acoso=:relacionado_acoso,
            responsable_acoso=:responsable_acoso,
            relacionado_corrupcion=:relacionado_corrupcion,
            valores_institucionales=:valores_institucionales,
            fecha_hechos=:fecha_hechos,
            fecha_apertura_indagacion=:fecha_apertura_indagacion,
            numero_auto_apertura_ind=:numero_auto_apertura_ind,
            fecha_auto_apertura_ind=:fecha_auto_apertura_ind,
            plazo_ind=:plazo_ind, fecha_vencimiento_ind=:fecha_vencimiento_ind,
            numero_auto_traslado_ind=:numero_auto_traslado_ind,
            fecha_auto_traslado_ind=:fecha_auto_traslado_ind,
            numero_auto_archivo_ind=:numero_auto_archivo_ind,
            fecha_auto_archivo_ind=:fecha_auto_archivo_ind,
            fecha_apertura_investigacion=:fecha_apertura_investigacion,
            numero_auto_apertura_inv=:numero_auto_apertura_inv,
            fecha_auto_apertura_inv=:fecha_auto_apertura_inv,
            plazo_inv=:plazo_inv, fecha_vencimiento_inv=:fecha_vencimiento_inv,
            numero_auto_traslado_inv=:numero_auto_traslado_inv,
            fecha_auto_traslado_inv=:fecha_auto_traslado_inv,
            numero_auto_archivo_inv=:numero_auto_archivo_inv,
            fecha_auto_archivo_inv=:fecha_auto_archivo_inv,
            etapa=:etapa, estado_proceso=:estado_proceso,
            observaciones_finales=:observaciones_finales,
            updated_at=datetime('now','localtime')
        WHERE id=:id
    """, {**{
        "n_expediente": data.get("n_expediente"),
        "anio": data.get("anio"),
        "mes": data.get("mes"),
        "origen_proceso": data.get("origen_proceso"),
        "n_radicado": data.get("n_radicado"),
        "fecha_radicado": data.get("fecha_radicado"),
        "fecha_siias": data.get("fecha_siias"),
        "ingreso_siias": data.get("ingreso_siias", "NO"),
        "ingreso_siad": data.get("ingreso_siad", "NO"),
        "fecha_ingreso_siad": data.get("fecha_ingreso_siad"),
        "ingreso_sid4": data.get("ingreso_sid4", "NO"),
        "nombre_abogado": data.get("nombre_abogado"),
        "impedimento": data.get("impedimento", "NO"),
        "investigado": data.get("investigado"),
        "perfil_indagado": data.get("perfil_indagado"),
        "entidad_origen": data.get("entidad_origen"),
        "quejoso": data.get("quejoso"),
        "asunto": data.get("asunto"),
        "tipologia": data.get("tipologia"),
        "descripcion_tipologia": data.get("descripcion_tipologia"),
        "relacionado_siniestro": data.get("relacionado_siniestro", "NO"),
        "responsable_siniestro": data.get("responsable_siniestro"),
        "relacionado_acoso": data.get("relacionado_acoso", "NO"),
        "responsable_acoso": data.get("responsable_acoso"),
        "relacionado_corrupcion": data.get("relacionado_corrupcion", "NO"),
        "valores_institucionales": data.get("valores_institucionales"),
        "fecha_hechos": data.get("fecha_hechos"),
        "fecha_apertura_indagacion": data.get("fecha_apertura_indagacion"),
        "numero_auto_apertura_ind": data.get("numero_auto_apertura_ind"),
        "fecha_auto_apertura_ind": data.get("fecha_auto_apertura_ind"),
        "plazo_ind": data.get("plazo_ind") or 180,
        "fecha_vencimiento_ind": data.get("fecha_vencimiento_ind"),
        "numero_auto_traslado_ind": data.get("numero_auto_traslado_ind"),
        "fecha_auto_traslado_ind": data.get("fecha_auto_traslado_ind"),
        "numero_auto_archivo_ind": data.get("numero_auto_archivo_ind"),
        "fecha_auto_archivo_ind": data.get("fecha_auto_archivo_ind"),
        "fecha_apertura_investigacion": data.get("fecha_apertura_investigacion"),
        "numero_auto_apertura_inv": data.get("numero_auto_apertura_inv"),
        "fecha_auto_apertura_inv": data.get("fecha_auto_apertura_inv"),
        "plazo_inv": data.get("plazo_inv") or 180,
        "fecha_vencimiento_inv": data.get("fecha_vencimiento_inv"),
        "numero_auto_traslado_inv": data.get("numero_auto_traslado_inv"),
        "fecha_auto_traslado_inv": data.get("fecha_auto_traslado_inv"),
        "numero_auto_archivo_inv": data.get("numero_auto_archivo_inv"),
        "fecha_auto_archivo_inv": data.get("fecha_auto_archivo_inv"),
        "etapa": data.get("etapa"),
        "estado_proceso": data.get("estado_proceso"),
        "observaciones_finales": data.get("observaciones_finales"),
    }, "id": exp_id})

    # Reemplazar escaneos: borrar los existentes y reinsertar
    conn.execute("DELETE FROM escaneos WHERE expediente_id = ?", (exp_id,))
    i = 0
    while f"escaner_fecha_{i}" in data or f"escaner_folio_{i}" in data:
        fecha = data.get(f"escaner_fecha_{i}")
        folio = data.get(f"escaner_folio_{i}")
        resp = data.get(f"escaner_responsable_{i}")
        if fecha or folio:
            conn.execute(
                "INSERT INTO escaneos (expediente_id, fecha_escaner, folio, responsable) VALUES (?,?,?,?)",
                (exp_id, fecha, folio, resp),
            )
        i += 1

    conn.commit()
    conn.close()
    return RedirectResponse(f"/expediente/{exp_id}?msg=actualizado", status_code=303)


# ── Eliminar expediente ────────────────────────────────────────────────────────

@router.post("/expediente/{exp_id}/eliminar")
async def eliminar_expediente(exp_id: int):
    conn = get_db()
    row = conn.execute("SELECT n_expediente FROM expedientes WHERE id = ?", (exp_id,)).fetchone()
    n = row["n_expediente"] if row else exp_id
    conn.execute("DELETE FROM expedientes WHERE id = ?", (exp_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/?msg=eliminado_{n}", status_code=303)


# ── Exportar filtrado (formulario) ────────────────────────────────────────────

@router.get("/exportar-filtrado", response_class=HTMLResponse)
async def exportar_filtrado_form(request: Request):
    conn = get_db()
    anios = [r[0] for r in conn.execute(
        "SELECT DISTINCT anio FROM expedientes WHERE anio IS NOT NULL ORDER BY anio DESC"
    ).fetchall()]
    abogados = [r[0] for r in conn.execute(
        "SELECT DISTINCT nombre_abogado FROM expedientes WHERE nombre_abogado IS NOT NULL ORDER BY nombre_abogado"
    ).fetchall()]
    # Cargar valores reales desde BD para que los filtros coincidan exactamente
    etapas_bd = [r[0] for r in conn.execute(
        "SELECT DISTINCT etapa FROM expedientes WHERE etapa IS NOT NULL ORDER BY etapa"
    ).fetchall()]
    estados_bd = [r[0] for r in conn.execute(
        "SELECT DISTINCT estado_proceso FROM expedientes WHERE estado_proceso IS NOT NULL ORDER BY estado_proceso"
    ).fetchall()]
    total = conn.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0]
    conn.close()

    return templates.TemplateResponse("exportar_filtrado.html", {
        "request": request,
        "active": "exportar",
        "anios": anios,
        "abogados": abogados,
        "etapas": etapas_bd,
        "estados": estados_bd,
        "total_preview": total,
        "filtros": {
            "anios": [], "abogados": [], "etapas": [], "estados": [],
            "fecha_desde": "", "fecha_hasta": "",
            "solo_vencidos": False, "proximos_30": False, "proximos_60": False,
            "bloques_off": [],
        },
    })


@router.get("/exportar-filtrado/descargar")
async def exportar_filtrado_descargar(request: Request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    params = request.query_params

    # Recoger filtros (los parámetros multi-valor vienen como listas)
    anios_f    = params.getlist("anios")    if hasattr(params, "getlist") else params._list.get("anios", [])
    abogados_f = params.getlist("abogados") if hasattr(params, "getlist") else params._list.get("abogados", [])
    etapas_f   = params.getlist("etapas")   if hasattr(params, "getlist") else params._list.get("etapas", [])
    estados_f  = params.getlist("estados")  if hasattr(params, "getlist") else params._list.get("estados", [])
    bloques_sel = params.getlist("bloques") if hasattr(params, "getlist") else params._list.get("bloques", [])

    # Starlette query params: usar getlist
    anios_f    = list(params.getlist("anios"))
    abogados_f = list(params.getlist("abogados"))
    etapas_f   = list(params.getlist("etapas"))
    estados_f  = list(params.getlist("estados"))
    bloques_sel = list(params.getlist("bloques"))

    fecha_desde   = params.get("fecha_desde", "")
    fecha_hasta   = params.get("fecha_hasta", "")
    solo_vencidos = params.get("solo_vencidos") == "1"
    proximos_30   = params.get("proximos_30") == "1"
    proximos_60   = params.get("proximos_60") == "1"

    # Bloques por defecto: todos si no se seleccionó ninguno
    todos_bloques = ["identificacion", "partes", "asunto", "indagacion", "investigacion", "cierre", "escaneos"]
    if not bloques_sel:
        bloques_sel = todos_bloques

    # Construcción de la consulta
    filtros_sql = []
    params_sql  = []

    if anios_f:
        placeholders = ",".join("?" * len(anios_f))
        filtros_sql.append(f"anio IN ({placeholders})")
        params_sql.extend([int(a) for a in anios_f])
    if abogados_f:
        placeholders = ",".join("?" * len(abogados_f))
        filtros_sql.append(f"nombre_abogado IN ({placeholders})")
        params_sql.extend(abogados_f)
    if etapas_f:
        placeholders = ",".join("?" * len(etapas_f))
        filtros_sql.append(f"etapa IN ({placeholders})")
        params_sql.extend(etapas_f)
    if estados_f:
        placeholders = ",".join("?" * len(estados_f))
        filtros_sql.append(f"estado_proceso IN ({placeholders})")
        params_sql.extend(estados_f)
    if fecha_desde:
        filtros_sql.append("fecha_radicado >= ?")
        params_sql.append(fecha_desde)
    if fecha_hasta:
        filtros_sql.append("fecha_radicado <= ?")
        params_sql.append(fecha_hasta)
    if solo_vencidos:
        filtros_sql.append("(fecha_vencimiento_ind < date('now') OR fecha_vencimiento_inv < date('now'))")
    elif proximos_30:
        filtros_sql.append("""(
            (fecha_vencimiento_ind BETWEEN date('now') AND date('now','+30 days'))
            OR (fecha_vencimiento_inv BETWEEN date('now') AND date('now','+30 days'))
        )""")
    elif proximos_60:
        filtros_sql.append("""(
            (fecha_vencimiento_ind BETWEEN date('now') AND date('now','+60 days'))
            OR (fecha_vencimiento_inv BETWEEN date('now') AND date('now','+60 days'))
        )""")

    where = ("WHERE " + " AND ".join(filtros_sql)) if filtros_sql else ""

    conn = get_db()
    rows = conn.execute(
        f"SELECT * FROM expedientes {where} ORDER BY anio DESC, n_expediente DESC",
        params_sql,
    ).fetchall()

    # Definición de bloques y sus columnas
    col_defs = []
    if "identificacion" in bloques_sel:
        col_defs += [
            ("N° EXPEDIENTE",    "n_expediente"),
            ("AÑO",              "anio"),
            ("MES",              "mes"),
            ("ORIGEN",           "origen_proceso"),
            ("N° RADICADO",      "n_radicado"),
            ("FECHA RADICADO",   "fecha_radicado"),
            ("FECHA SIIAS",      "fecha_siias"),
            ("INGRESO SIIAS",    "ingreso_siias"),
            ("INGRESO SIAD",     "ingreso_siad"),
            ("FECHA SIAD",       "fecha_ingreso_siad"),
            ("INGRESO SID4",     "ingreso_sid4"),
        ]
    if "partes" in bloques_sel:
        col_defs += [
            ("ABOGADO",          "nombre_abogado"),
            ("IMPEDIMENTO",      "impedimento"),
            ("INVESTIGADO",      "investigado"),
            ("PERFIL",           "perfil_indagado"),
            ("ENTIDAD ORIGEN",   "entidad_origen"),
            ("QUEJOSO",          "quejoso"),
        ]
    if "asunto" in bloques_sel:
        col_defs += [
            ("ASUNTO",           "asunto"),
            ("TIPOLOGÍA",        "tipologia"),
            ("DESC. TIPOLOGÍA",  "descripcion_tipologia"),
            ("SINIESTRO",        "relacionado_siniestro"),
            ("RESP. SINIESTRO",  "responsable_siniestro"),
            ("ACOSO/MALTRATO",   "relacionado_acoso"),
            ("RESP. ACOSO",      "responsable_acoso"),
            ("CORRUPCIÓN",       "relacionado_corrupcion"),
            ("VALORES INST.",    "valores_institucionales"),
            ("FECHA HECHOS",     "fecha_hechos"),
        ]
    if "indagacion" in bloques_sel:
        col_defs += [
            ("F. APERTURA IND.", "fecha_apertura_indagacion"),
            ("AUTO APERTURA IND.", "numero_auto_apertura_ind"),
            ("F. AUTO AP. IND.", "fecha_auto_apertura_ind"),
            ("PLAZO IND.",       "plazo_ind"),
            ("F. VENC. IND.",    "fecha_vencimiento_ind"),
            ("AUTO TRASLADO IND.", "numero_auto_traslado_ind"),
            ("F. TRASLADO IND.", "fecha_auto_traslado_ind"),
            ("AUTO ARCHIVO IND.", "numero_auto_archivo_ind"),
            ("F. ARCHIVO IND.",  "fecha_auto_archivo_ind"),
        ]
    if "investigacion" in bloques_sel:
        col_defs += [
            ("F. APERTURA INV.", "fecha_apertura_investigacion"),
            ("AUTO APERTURA INV.", "numero_auto_apertura_inv"),
            ("F. AUTO AP. INV.", "fecha_auto_apertura_inv"),
            ("PLAZO INV.",       "plazo_inv"),
            ("F. VENC. INV.",    "fecha_vencimiento_inv"),
            ("AUTO TRASLADO INV.", "numero_auto_traslado_inv"),
            ("F. TRASLADO INV.", "fecha_auto_traslado_inv"),
            ("AUTO ARCHIVO INV.", "numero_auto_archivo_inv"),
            ("F. ARCHIVO INV.",  "fecha_auto_archivo_inv"),
        ]
    if "cierre" in bloques_sel:
        col_defs += [
            ("ETAPA",            "etapa"),
            ("ESTADO",           "estado_proceso"),
            ("OBSERVACIONES",    "observaciones_finales"),
            ("CREADO POR",       "created_by"),
            ("FECHA CREACIÓN",   "created_at"),
        ]

    # Columna de alerta calculada
    col_defs.append(("ALERTA VENC. IND.", "__alerta_ind__"))
    col_defs.append(("ALERTA VENC. INV.", "__alerta_inv__"))

    # Generar Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "EXPEDIENTES"

    header_fill = PatternFill("solid", fgColor="1B4F8A")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    alt_fill = PatternFill("solid", fgColor="EBF3FD")

    # Encabezados
    for ci, (header, _) in enumerate(col_defs, 1):
        cell = ws.cell(row=1, column=ci, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
    ws.row_dimensions[1].height = 36

    # Datos
    vencido_fill  = PatternFill("solid", fgColor="FADADD")
    proximo_fill  = PatternFill("solid", fgColor="FFF9C4")

    for ri, row in enumerate(rows, 2):
        d = row_to_dict(row)
        alerta_ind = calcular_alerta(d.get("fecha_vencimiento_ind"))
        alerta_inv = calcular_alerta(d.get("fecha_vencimiento_inv"))
        fila_fill  = alt_fill if ri % 2 == 0 else None

        for ci, (_, campo) in enumerate(col_defs, 1):
            if campo == "__alerta_ind__":
                valor = alerta_ind["texto"]
            elif campo == "__alerta_inv__":
                valor = alerta_inv["texto"]
            else:
                valor = d.get(campo)

            cell = ws.cell(row=ri, column=ci, value=valor)
            cell.alignment = Alignment(vertical="center", wrap_text=False)
            if fila_fill:
                cell.fill = fila_fill

        # Colorear fila si hay vencimiento urgente
        if alerta_ind["clase"] == "vencido" or alerta_inv["clase"] == "vencido":
            for ci in range(1, len(col_defs) + 1):
                ws.cell(row=ri, column=ci).fill = vencido_fill
        elif alerta_ind["clase"] == "proximo" or alerta_inv["clase"] == "proximo":
            for ci in range(1, len(col_defs) + 1):
                ws.cell(row=ri, column=ci).fill = proximo_fill

    # Anchos automáticos
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=8)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 45)

    ws.freeze_panes = "A2"

    # Hoja de escaneos (si aplica)
    if "escaneos" in bloques_sel:
        ws_esc = wb.create_sheet("ESCANEOS")
        ids = [row_to_dict(r)["id"] for r in rows]
        esc_headers = ["N° EXPEDIENTE", "AÑO", "FECHA ESCÁNER", "FOLIO", "RESPONSABLE"]
        for ci, h in enumerate(esc_headers, 1):
            cell = ws_esc.cell(row=1, column=ci, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center

        ri_esc = 2
        for exp_row in rows:
            d = row_to_dict(exp_row)
            escs = conn.execute(
                "SELECT * FROM escaneos WHERE expediente_id = ? ORDER BY id", (d["id"],)
            ).fetchall()
            for esc in escs:
                e = row_to_dict(esc)
                ws_esc.cell(row=ri_esc, column=1, value=d["n_expediente"])
                ws_esc.cell(row=ri_esc, column=2, value=d["anio"])
                ws_esc.cell(row=ri_esc, column=3, value=e.get("fecha_escaner"))
                ws_esc.cell(row=ri_esc, column=4, value=e.get("folio"))
                ws_esc.cell(row=ri_esc, column=5, value=e.get("responsable"))
                ri_esc += 1

    # Hoja de resumen
    ws_res = wb.create_sheet("RESUMEN")
    ws_res.cell(row=1, column=1, value="REPORTE OCDI — RESUMEN").font = Font(bold=True, size=13)
    ws_res.cell(row=2, column=1, value=f"Generado el: {date.today().strftime('%d/%m/%Y')}")
    ws_res.cell(row=3, column=1, value=f"Total de expedientes en reporte: {len(rows)}")
    filtros_texto = []
    if anios_f:    filtros_texto.append(f"Años: {', '.join(anios_f)}")
    if abogados_f: filtros_texto.append(f"Abogados: {', '.join(abogados_f)}")
    if etapas_f:   filtros_texto.append(f"Etapas: {', '.join(etapas_f)}")
    if estados_f:  filtros_texto.append(f"Estados: {', '.join(estados_f)}")
    if fecha_desde: filtros_texto.append(f"Fecha desde: {fecha_desde}")
    if fecha_hasta: filtros_texto.append(f"Fecha hasta: {fecha_hasta}")
    if solo_vencidos: filtros_texto.append("Solo vencidos")
    if proximos_30:   filtros_texto.append("Próximos 30 días")
    if proximos_60:   filtros_texto.append("Próximos 60 días")
    ws_res.cell(row=4, column=1, value="Filtros aplicados: " + (", ".join(filtros_texto) if filtros_texto else "Ninguno"))

    conn.close()

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    filtro_str = "_filtrado" if filtros_texto else "_completo"
    filename = f"OCDI_Reporte{filtro_str}_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Exportar Excel ─────────────────────────────────────────────────────────────

@router.get("/exportar")
async def exportar_excel():
    from fastapi.responses import StreamingResponse
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    conn = get_db()
    rows = conn.execute("SELECT * FROM expedientes ORDER BY anio, n_expediente").fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "EXPEDIENTES"

    # Encabezados
    headers = [
        "N. EXPEDIENTE", "AÑO", "MES", "ORIGEN DEL PROCESO",
        "N. RADICADO", "FECHA RADICADO", "FECHA SIIAS",
        "INGRESO SIIAS", "INGRESO SIAD", "FECHA INGRESO SIAD", "INGRESO SID4",
        "NOMBRE ABOGADO", "IMPEDIMENTO", "INVESTIGADO", "PERFIL INDAGADO",
        "ENTIDAD ORIGEN", "QUEJOSO",
        "ASUNTO", "TIPOLOGÍA", "DESCRIPCIÓN TIPOLOGÍA",
        "SINIESTRO", "RESP. SINIESTRO", "ACOSO/MALTRATO", "RESP. ACOSO",
        "CORRUPCIÓN", "VALORES INSTITUCIONALES", "FECHA HECHOS",
        # Indagación
        "F. APERTURA INDAGACIÓN", "AUTO APERTURA IND.", "F. AUTO APERTURA IND.",
        "PLAZO IND. (días)", "F. VENCIMIENTO IND.",
        "AUTO TRASLADO IND.", "F. AUTO TRASLADO IND.",
        "AUTO ARCHIVO IND.", "F. AUTO ARCHIVO IND.",
        # Investigación
        "F. APERTURA INVESTIGACIÓN", "AUTO APERTURA INV.", "F. AUTO APERTURA INV.",
        "PLAZO INV. (días)", "F. VENCIMIENTO INV.",
        "AUTO TRASLADO INV.", "F. AUTO TRASLADO INV.",
        "AUTO ARCHIVO INV.", "F. AUTO ARCHIVO INV.",
        # Cierre
        "ETAPA", "ESTADO DEL PROCESO", "OBSERVACIONES FINALES",
        "CREADO POR", "FECHA CREACIÓN", "ÚLTIMA ACTUALIZACIÓN",
    ]

    # Estilos de encabezado
    header_fill = PatternFill("solid", fgColor="1B4F8A")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center

    ws.row_dimensions[1].height = 40

    # Datos
    campos = [
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

    alt_fill = PatternFill("solid", fgColor="EBF1F8")
    for row_idx, row in enumerate(rows, 2):
        d = row_to_dict(row)
        fill = alt_fill if row_idx % 2 == 0 else None
        for col_idx, campo in enumerate(campos, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=d.get(campo))
            cell.alignment = Alignment(vertical="center", wrap_text=False)
            if fill:
                cell.fill = fill

    # Anchos de columna
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    ws.freeze_panes = "A2"

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"OCDI_Expedientes_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
