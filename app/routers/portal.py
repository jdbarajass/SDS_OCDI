from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
from app.template_utils import make_templates
from datetime import date

from app.database import get_db
from app.auth_utils import tpl
from app.routers.backup import backup_necesario
from app.routers.expedientes import _enriquecer as _enriquecer_expediente
from app.routers.sdqs import _calcular_semaforo_sdqs
from app.routers.correspondencia import _calcular_semaforo_row

router = APIRouter()
templates = make_templates(str(Path(__file__).parent.parent / "templates"))

_UMBRAL_DIAS = 3


def _contar_vencimientos_proximos(conn) -> dict:
    """
    Cuenta cuántos casos activos vencen en <= _UMBRAL_DIAS días (o ya vencieron),
    reutilizando los mismos cálculos que usan la Lista/Dashboard/Reporte de cada
    módulo, para que el banner nunca diverja de lo que se ve en pantalla.
    """
    n_exp = 0
    for row in conn.execute("SELECT * FROM expedientes WHERE eliminado_en IS NULL").fetchall():
        exp = _enriquecer_expediente(dict(row))
        alertas = (exp.get("alerta_ind"), exp.get("alerta_inv"),
                   exp.get("alerta_prescripcion"), exp.get("alerta_prorroga"))
        if any(a and a.get("dias") is not None and a["dias"] <= _UMBRAL_DIAS for a in alertas):
            n_exp += 1

    n_sdqs = 0
    hoy = date.today()
    for row in conn.execute(
        "SELECT * FROM sdqs WHERE eliminado_en IS NULL AND (rad_salida IS NULL OR rad_salida = '')"
    ).fetchall():
        reg = _calcular_semaforo_sdqs(dict(row))
        fv = reg.get("fecha_vencimiento")
        if not fv:
            continue
        try:
            dias_restantes = (date.fromisoformat(str(fv)[:10]) - hoy).days
        except ValueError:
            continue
        if dias_restantes <= _UMBRAL_DIAS:
            n_sdqs += 1

    n_corr = 0
    for row in conn.execute("""
        SELECT * FROM correspondencia
        WHERE eliminado_en IS NULL
          AND (fecha_radicado_salida IS NULL OR fecha_radicado_salida = '')
    """).fetchall():
        reg = _calcular_semaforo_row(dict(row))
        if reg.get("termino_dias"):
            if reg.get("dias_restantes") is not None and reg["dias_restantes"] <= _UMBRAL_DIAS:
                n_corr += 1
        elif reg.get("semaforo") == "roja":
            n_corr += 1

    return {
        "expedientes": n_exp, "sdqs": n_sdqs, "correspondencia": n_corr,
        "total": n_exp + n_sdqs + n_corr,
    }


@router.get("/", response_class=HTMLResponse)
async def hub(request: Request, msg: str = "", backup: str = ""):
    conn = get_db()

    total_base      = conn.execute("SELECT COUNT(*) FROM expedientes WHERE eliminado_en IS NULL").fetchone()[0]
    total_digitales = conn.execute("SELECT COUNT(*) FROM exp_digitales WHERE eliminado_en IS NULL").fetchone()[0]

    hoy = date.today()
    prox_sala = conn.execute(
        "SELECT fecha, franja, titulo, estado FROM sala_agenda WHERE fecha >= ? ORDER BY fecha, franja LIMIT 1",
        (hoy.isoformat(),)
    ).fetchone()

    total_control_autos = conn.execute("SELECT COUNT(*) FROM control_autos_sustanciacion WHERE eliminado_en IS NULL").fetchone()[0]
    total_sdqs = conn.execute("SELECT COUNT(*) FROM sdqs WHERE eliminado_en IS NULL").fetchone()[0]

    total_prestamos_activos = conn.execute(
        "SELECT COUNT(*) FROM prestamos_equipos WHERE estado = 'Prestado'"
    ).fetchone()[0]
    total_bienes = conn.execute("SELECT COUNT(*) FROM bienes_muebles").fetchone()[0]

    total_corr = conn.execute("SELECT COUNT(*) FROM correspondencia WHERE eliminado_en IS NULL").fetchone()[0]
    corr_rojos = conn.execute("""
        SELECT COUNT(*) FROM correspondencia
        WHERE eliminado_en IS NULL
        AND (fecha_radicado_salida IS NULL OR fecha_radicado_salida = '')
        AND (tipo_respuesta IS NULL OR UPPER(TRIM(tipo_respuesta)) NOT IN ('ANEXO EXPEDIENTE', 'ANEXO AL EXPEDIENTE'))
        AND fecha_ingreso IS NOT NULL
        AND CAST(julianday('now','localtime') - julianday(substr(fecha_ingreso,1,10)) AS INTEGER) >= 9
    """).fetchone()[0]

    vencimientos_proximos = _contar_vencimientos_proximos(conn)

    conn.close()

    necesita_bk, ultimo_bk = backup_necesario()
    dia_semana = hoy.weekday()  # 1=martes, 3=jueves
    es_dia_reporte = dia_semana in (1, 3)
    nombre_dia = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"][dia_semana]

    return templates.TemplateResponse("portal.html", tpl(request, None,
        total_base=total_base, total_digitales=total_digitales,
        prox_sala=dict(prox_sala) if prox_sala else None,
        total_corr=total_corr, corr_rojos=corr_rojos,
        total_control_autos=total_control_autos,
        total_sdqs=total_sdqs,
        total_prestamos_activos=total_prestamos_activos,
        total_bienes=total_bienes,
        msg=msg,
        backup_estado=backup,
        necesita_backup=necesita_bk,
        ultimo_backup=ultimo_bk,
        es_dia_reporte=es_dia_reporte,
        nombre_dia=nombre_dia,
        vencimientos_proximos=vencimientos_proximos,
    ))
