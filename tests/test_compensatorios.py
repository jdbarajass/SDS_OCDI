"""
Regresión sobre el semáforo de metas de horas del módulo Compensatorios Fin
de Año (Resolución 2307 de 2026). _estado_meta() es una función pura (no
toca la base de datos): recibe horas registradas, meta y fecha límite, y
devuelve la clase de semáforo reutilizando las mismas clases CSS que ya
existen para vencimientos de casos (vigente/proximo/vencido/sin-plazo).
"""
from datetime import date, timedelta

from app.routers.compensatorios import _estado_meta
from app.dias_habiles import dias_habiles_diff


def _iso(d: date) -> str:
    return d.isoformat()


def test_meta_completa_es_vigente():
    out = _estado_meta(horas_reg=34, meta=34, fecha_limite_str="2026-11-05")
    assert out["clase"] == "vigente"
    assert out["pct"] == 100
    assert out["faltante"] == 0


def test_meta_superada_sigue_vigente_y_no_pasa_de_100_pct():
    out = _estado_meta(horas_reg=40, meta=34, fecha_limite_str="2026-11-05")
    assert out["clase"] == "vigente"
    assert out["pct"] == 100


def test_meta_cero_es_sin_plazo():
    out = _estado_meta(horas_reg=0, meta=0, fecha_limite_str="2026-11-05")
    assert out["clase"] == "sin-plazo"


def test_sin_fecha_limite_con_horas_pendientes_es_proximo():
    out = _estado_meta(horas_reg=10, meta=34, fecha_limite_str=None)
    assert out["clase"] == "proximo"
    assert out["faltante"] == 24


def test_fecha_limite_vencida_con_horas_pendientes_es_vencido():
    ayer = date.today() - timedelta(days=1)
    out = _estado_meta(horas_reg=10, meta=34, fecha_limite_str=_iso(ayer))
    assert out["clase"] == "vencido"
    assert "Venció" in out["texto"]


def test_en_riesgo_cuando_no_alcanzan_los_dias_habiles_restantes():
    """Si faltan más horas que días hábiles quedan hasta el límite, se marca
    en riesgo (vencido) aunque el plazo no haya pasado todavía."""
    hoy = date.today()
    # Un día hábil hacia adelante, pero faltan 34h — imposible a 1h/día.
    limite = hoy + timedelta(days=1)
    while dias_habiles_diff(hoy, limite) < 1:
        limite += timedelta(days=1)
    out = _estado_meta(horas_reg=0, meta=34, fecha_limite_str=_iso(limite))
    assert out["clase"] == "vencido"
    assert "riesgo" in out["texto"].lower()


def test_con_margen_suficiente_es_proximo():
    hoy = date.today()
    limite = hoy
    while dias_habiles_diff(hoy, limite) < 34:
        limite += timedelta(days=1)
    out = _estado_meta(horas_reg=0, meta=34, fecha_limite_str=_iso(limite))
    assert out["clase"] == "proximo"
