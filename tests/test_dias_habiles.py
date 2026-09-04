"""
Regresión sobre app/dias_habiles.py — fuente única de días hábiles Colombia
usada por todos los semáforos (SDQS, Correspondencia, Base Expedientes,
Expedientes Digitales).

El caso de test_ejemplo_usuario_12_al_25_agosto_2026 reproduce exactamente el
ejemplo que pidió el usuario al solicitar este cambio (2026-08-25): del 12 al
25 de agosto de 2026 deben contarse 8 días hábiles, no 13 ni 14 — el 15 de
agosto (festivo) se traslada al lunes 17 (Ley Emiliani), y el conteo no
incluye el propio 12 de agosto (se empieza a contar el día hábil siguiente).
"""
from datetime import date, timedelta

from app.dias_habiles import (
    dias_habiles_diff,
    festivos_colombia,
    sumar_dias_habiles,
    restar_dias_habiles,
)


def test_ejemplo_usuario_12_al_25_agosto_2026():
    assert dias_habiles_diff(date(2026, 8, 12), date(2026, 8, 25)) == 8


def test_15_agosto_2026_se_traslada_al_lunes_17():
    """15 de agosto de 2026 cae sábado → Ley Emiliani lo traslada al lunes 17."""
    festivos = festivos_colombia(2026)
    assert date(2026, 8, 15) not in festivos
    assert date(2026, 8, 17) in festivos


def test_no_cuenta_el_dia_de_partida():
    """El día `desde` nunca se cuenta, aunque sea hábil."""
    lunes = date(2026, 8, 24)  # lunes hábil
    assert dias_habiles_diff(lunes, lunes) == 0


def test_fin_de_semana_no_suma_dias_habiles():
    viernes = date(2026, 8, 21)
    lunes_siguiente = date(2026, 8, 24)
    # Entre viernes y el lunes siguiente solo cuenta el propio lunes.
    assert dias_habiles_diff(viernes, lunes_siguiente) == 1


def test_diff_negativo_para_fecha_pasada():
    """Si `hasta` es anterior a `desde`, el resultado es negativo (p.ej. un
    vencimiento ya pasado, mostrado como 'vencido hace N días hábiles')."""
    assert dias_habiles_diff(date(2026, 8, 25), date(2026, 8, 12)) == -8


def test_sumar_y_restar_son_inversos_en_dia_habil():
    inicio = date(2026, 8, 12)
    fin = sumar_dias_habiles(inicio, 8)
    assert fin == date(2026, 8, 25)
    assert restar_dias_habiles(fin, 8) == inicio


def test_semana_completa_siempre_5_dias_habiles_sin_festivos():
    """7 días calendario consecutivos sin festivos = siempre 5 días hábiles,
    sin importar en qué día de la semana empiece (weekend wrap exacto)."""
    base = date(2027, 3, 1)  # año sin festivos móviles cercanos a esta fecha
    for offset in range(7):
        inicio = base + timedelta(days=offset)
        fin = inicio + timedelta(days=7)
        festivos = festivos_colombia(inicio.year) | festivos_colombia(fin.year)
        if any(inicio < f <= fin for f in festivos):
            continue  # evitar semanas que sí cruzan un festivo
        assert dias_habiles_diff(inicio, fin) == 5
