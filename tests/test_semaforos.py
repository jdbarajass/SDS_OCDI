"""
Regresión sobre los cálculos de semáforo de SDQS y Correspondencia.

Estos dos cálculos ya causaron bugs reales documentados en AUDITORIA.md:
- H17: el Dashboard de Correspondencia reimplementaba su propio cálculo de
  semáforo y divergía de la Lista (6 de 9 casos verdes en Lista salían
  rojos en Dashboard). Se corrigió centralizando todo en
  _calcular_semaforo_row().
- H19: 136 de 159 SDQS pendientes nunca mostraban semáforo porque
  fecha_vencimiento no era obligatoria.

No tocan la base de datos — ambas funciones reciben un dict plano y
devuelven un dict plano, así que se prueban de forma aislada.
"""
from datetime import date, timedelta

from app.routers.sdqs import _calcular_semaforo_sdqs
from app.routers.correspondencia import (
    _calcular_semaforo_row,
    _add_dias_habiles,
    _subtract_dias_habiles,
)


def _iso(d: date) -> str:
    return d.isoformat()


# ── SDQS ─────────────────────────────────────────────────────────────────────

def test_sdqs_respondido_si_hay_radicado_salida():
    reg = {"rad_salida": "RAD-001", "fecha_asignacion": "2026-01-01", "fecha_vencimiento": "2026-01-10"}
    out = _calcular_semaforo_sdqs(reg)
    assert out["semaforo_sdqs"] == "respondido"
    assert out["estado_dias"] is None


def test_sdqs_sin_fecha_vencimiento_no_tiene_semaforo():
    """H19: sin fecha_vencimiento, el semáforo debe quedar en None, no crashear ni asumir un color."""
    reg = {"rad_salida": "", "fecha_asignacion": "2026-01-01", "fecha_vencimiento": None}
    out = _calcular_semaforo_sdqs(reg)
    assert out["semaforo_sdqs"] is None
    assert out["estado_dias"] is None


def test_sdqs_verde_primera_mitad_del_plazo():
    hoy = date.today()
    reg = {
        "rad_salida": "",
        "fecha_asignacion": _iso(hoy - timedelta(days=2)),
        "fecha_vencimiento": _iso(hoy + timedelta(days=28)),  # plazo total 30 días
    }
    out = _calcular_semaforo_sdqs(reg)
    assert out["semaforo_sdqs"] == "verde"


def test_sdqs_amarillo_segunda_mitad_del_plazo():
    hoy = date.today()
    reg = {
        "rad_salida": "",
        "fecha_asignacion": _iso(hoy - timedelta(days=20)),
        "fecha_vencimiento": _iso(hoy + timedelta(days=10)),  # plazo total 30 días, van 20
    }
    out = _calcular_semaforo_sdqs(reg)
    assert out["semaforo_sdqs"] == "amarillo"


def test_sdqs_rojo_dos_dias_o_menos():
    hoy = date.today()
    reg = {
        "rad_salida": "",
        "fecha_asignacion": _iso(hoy - timedelta(days=29)),
        "fecha_vencimiento": _iso(hoy + timedelta(days=1)),
    }
    out = _calcular_semaforo_sdqs(reg)
    assert out["semaforo_sdqs"] == "rojo"


# ── Correspondencia ──────────────────────────────────────────────────────────

def test_corr_anexo_expediente_siempre_verde():
    reg = {"tipo_respuesta": "ANEXO EXPEDIENTE", "fecha_ingreso": "2020-01-01"}
    out = _calcular_semaforo_row(reg)
    assert out["semaforo"] == "verde"
    assert out["dias_transcurridos"] is None


def test_corr_anexo_al_expediente_tambien_verde():
    """La variante 'ANEXO AL EXPEDIENTE' debe cubrirse igual que 'ANEXO EXPEDIENTE' (H1/v2.4)."""
    reg = {"tipo_respuesta": "ANEXO AL EXPEDIENTE", "fecha_ingreso": "2020-01-01"}
    out = _calcular_semaforo_row(reg)
    assert out["semaforo"] == "verde"


def test_corr_respondido_si_hay_radicado_salida():
    reg = {
        "tipo_respuesta": None,
        "fecha_ingreso": "2026-01-01",
        "fecha_radicado_salida": "2026-01-06",
    }
    out = _calcular_semaforo_row(reg)
    assert out["semaforo"] == "respondido"
    assert out["dias_transcurridos"] == 5


def test_corr_sin_fecha_ingreso_no_tiene_semaforo():
    reg = {"tipo_respuesta": None, "fecha_ingreso": None, "fecha_radicado_salida": None}
    out = _calcular_semaforo_row(reg)
    assert out["semaforo"] is None


def test_corr_modo_a_sin_termino_dias_verde_amarilla_roja():
    """Sin termino_dias: verde <=5 días, amarilla 6-8, roja >=9 (calendario, desde fecha_ingreso)."""
    hoy = date.today()

    verde = _calcular_semaforo_row({
        "tipo_respuesta": None, "fecha_radicado_salida": None,
        "fecha_ingreso": _iso(hoy - timedelta(days=3)),
    })
    assert verde["semaforo"] == "verde"

    amarilla = _calcular_semaforo_row({
        "tipo_respuesta": None, "fecha_radicado_salida": None,
        "fecha_ingreso": _iso(hoy - timedelta(days=7)),
    })
    assert amarilla["semaforo"] == "amarilla"

    roja = _calcular_semaforo_row({
        "tipo_respuesta": None, "fecha_radicado_salida": None,
        "fecha_ingreso": _iso(hoy - timedelta(days=10)),
    })
    assert roja["semaforo"] == "roja"


def test_corr_modo_b_con_termino_dias_consistente_con_helpers_de_dias_habiles():
    """
    Modo B (con termino_dias): fecha_vencimiento = fecha_ingreso + N días hábiles;
    fecha_termino_respuesta = fecha_vencimiento - 2 días hábiles. Se valida que el
    resultado de _calcular_semaforo_row sea consistente con llamar directamente a
    los mismos helpers de días hábiles que usa Reportes de Vencimientos, en vez de
    fijar fechas de calendario a mano (evita depender del día de la semana de hoy).
    """
    hoy = date.today()
    termino = 5
    fecha_venc_esperada = _add_dias_habiles(hoy, termino)
    fecha_rev_esperada = _subtract_dias_habiles(fecha_venc_esperada, 2)
    dias_restantes_esperados = (fecha_rev_esperada - hoy).days

    out = _calcular_semaforo_row({
        "tipo_respuesta": None,
        "fecha_radicado_salida": None,
        "fecha_ingreso": _iso(hoy),
        "termino_dias": termino,
    })

    assert out["fecha_vencimiento"] == fecha_venc_esperada.isoformat()
    assert out["dias_restantes"] == dias_restantes_esperados
    if dias_restantes_esperados >= 2:
        assert out["semaforo"] == "verde"
    elif dias_restantes_esperados >= 0:
        assert out["semaforo"] == "amarilla"
    else:
        assert out["semaforo"] == "roja"
