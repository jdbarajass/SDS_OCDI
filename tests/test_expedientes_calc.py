"""
Regresión sobre las fechas de vencimiento calculadas de Base Expedientes
(_enriquecer) y la clasificación de alerta (calcular_alerta), que alimentan
tanto la Lista como el Dashboard — el patrón "Dashboard con cálculo propio
divergente de su Lista" se repitió 2 veces en AUDITORIA.md (H9/H10, H17).
"""
from datetime import date

from app.database import calcular_alerta
from app.routers.expedientes import _enriquecer, _add_months, _add_years


def test_enriquecer_fecha_vencimiento_indagacion_6_meses():
    exp = {"fecha_auto_apertura_ind": "2026-01-15"}
    out = _enriquecer(exp)
    assert out["fecha_vencimiento_ind"] == _add_months(date(2026, 1, 15), 6).isoformat()


def test_enriquecer_fecha_vencimiento_investigacion_6_meses():
    exp = {"fecha_apertura_investigacion": "2026-01-15"}
    out = _enriquecer(exp)
    assert out["fecha_vencimiento_inv"] == _add_months(date(2026, 1, 15), 6).isoformat()


def test_enriquecer_prescripcion_5_anios_desde_hechos():
    exp = {"fecha_hechos": "2026-02-20"}
    out = _enriquecer(exp)
    assert out["fecha_prescripcion"] == _add_years(date(2026, 2, 20), 5).isoformat()


def test_enriquecer_sin_fechas_no_calcula_vencimientos():
    out = _enriquecer({})
    assert out["fecha_vencimiento_ind"] is None
    assert out["fecha_vencimiento_inv"] is None
    assert out["fecha_prescripcion"] is None


def test_add_months_respeta_fin_de_mes():
    """31 de enero + 1 mes no debe desbordar a marzo (febrero no tiene día 31)."""
    assert _add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_calcular_alerta_vencido():
    fecha = date.today().replace(day=1)
    if fecha >= date.today():
        fecha = date(date.today().year - 1, 12, 1)
    out = calcular_alerta(fecha.isoformat())
    assert out["clase"] == "vencido"
    assert out["dias"] < 0


def test_calcular_alerta_proximo_dentro_de_30_dias():
    from datetime import timedelta
    fecha = date.today() + timedelta(days=5)
    out = calcular_alerta(fecha.isoformat())
    assert out["clase"] == "proximo"
    assert out["dias"] == 5


def test_calcular_alerta_vigente_mas_de_30_dias():
    from datetime import timedelta
    fecha = date.today() + timedelta(days=90)
    out = calcular_alerta(fecha.isoformat())
    assert out["clase"] == "vigente"


def test_calcular_alerta_sin_fecha():
    out = calcular_alerta(None)
    assert out["clase"] == "sin-plazo"
    assert out["dias"] is None
