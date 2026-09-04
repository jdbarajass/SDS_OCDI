"""
Cálculo de días hábiles según el calendario colombiano (fines de semana + festivos).

Fuente única de verdad para todos los semáforos del sistema que cuentan días
hábiles: SDQS, Correspondencia, Base Expedientes y Expedientes Digitales.
Antes cada módulo tenía su propia copia de estas funciones (duplicado en
correspondencia.py); se centralizaron aquí para que festivos y reglas de
conteo no puedan divergir entre módulos.

Regla de conteo: al contar días hábiles "desde" una fecha, esa fecha NO se
cuenta — el conteo empieza el día hábil siguiente (así lo pidió el usuario:
del 12 al 25 de agosto de 2026 hay 8 días hábiles, no 13 ni 14).
"""
from datetime import date, timedelta

_FESTIVOS_FIJOS = [(1, 1), (5, 1), (7, 20), (8, 7), (12, 8), (12, 25)]
# Ley Emiliani: estos festivos se trasladan al lunes siguiente si no caen en lunes
_FESTIVOS_LEY_EMILIANI = [(1, 6), (3, 19), (6, 29), (8, 15), (10, 12), (11, 1), (11, 11)]


def _easter(year: int) -> date:
    """Algoritmo de Gauss para el Domingo de Pascua."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _next_monday(d: date) -> date:
    """Retorna d si ya es lunes, o el lunes siguiente."""
    days_ahead = (7 - d.weekday()) % 7
    return d if days_ahead == 0 else d + timedelta(days=days_ahead)


def festivos_colombia(year: int) -> set:
    """Festivos de Colombia para un año: fijos + Ley Emiliani + Semana Santa."""
    festivos = set()
    for m, day in _FESTIVOS_FIJOS:
        festivos.add(date(year, m, day))
    for m, day in _FESTIVOS_LEY_EMILIANI:
        festivos.add(_next_monday(date(year, m, day)))
    easter = _easter(year)
    festivos.add(easter - timedelta(days=3))   # Jueves Santo
    festivos.add(easter - timedelta(days=2))   # Viernes Santo
    festivos.add(_next_monday(easter + timedelta(days=39)))   # Ascensión
    festivos.add(_next_monday(easter + timedelta(days=60)))   # Corpus Christi
    festivos.add(_next_monday(easter + timedelta(days=68)))   # Sagrado Corazón
    return festivos


def _festivos_rango(a: date, b: date) -> set:
    lo, hi = (a, b) if a <= b else (b, a)
    festivos = set()
    for year in range(lo.year, hi.year + 1):
        festivos |= festivos_colombia(year)
    return festivos


def _weekdays_estrictamente_despues(lo: date, hi: date) -> int:
    """Cuenta días lunes-viernes en (lo, hi], asumiendo lo <= hi."""
    total_days = (hi - lo).days
    full_weeks, remainder = divmod(total_days, 7)
    count = full_weeks * 5
    for n in range(1, remainder + 1):
        if (lo + timedelta(days=n)).weekday() < 5:
            count += 1
    return count


def dias_habiles_diff(desde: date, hasta: date) -> int:
    """
    Cuenta los días hábiles entre `desde` y `hasta`, sin contar `desde` (el
    conteo arranca el día hábil siguiente a `desde`).

    - hasta > desde  → cantidad de días hábiles transcurridos (positivo).
    - hasta < desde  → cantidad de días hábiles en el pasado (negativo, p.ej.
      "vencido hace N días hábiles").
    - hasta == desde → 0.
    """
    if hasta == desde:
        return 0
    sign = 1 if hasta > desde else -1
    lo, hi = (desde, hasta) if hasta > desde else (hasta, desde)
    weekdays = _weekdays_estrictamente_despues(lo, hi)
    festivos = _festivos_rango(lo, hi)
    festivos_habiles = sum(1 for f in festivos if lo < f <= hi and f.weekday() < 5)
    return sign * (weekdays - festivos_habiles)


def sumar_dias_habiles(inicio: date, dias: int) -> date:
    """Avanza `dias` días hábiles desde `inicio` (sin contar `inicio`)."""
    festivos = festivos_colombia(inicio.year) | festivos_colombia(inicio.year + 1)
    current = inicio
    count = 0
    while count < dias:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in festivos:
            count += 1
    return current


def restar_dias_habiles(fin: date, dias: int) -> date:
    """Retrocede `dias` días hábiles desde `fin` (sin contar `fin`)."""
    festivos = festivos_colombia(fin.year) | festivos_colombia(fin.year - 1)
    current = fin
    count = 0
    while count < dias:
        current -= timedelta(days=1)
        if current.weekday() < 5 and current not in festivos:
            count += 1
    return current


def festivos_iso_rango(anio_desde: int, anio_hasta: int) -> list:
    """Lista ordenada (ISO strings) de festivos colombianos entre dos años,
    ambos incluidos. Pensada para inyectar en templates y calcular días
    hábiles también en el preview JS del formulario de Expedientes."""
    festivos = set()
    for year in range(anio_desde, anio_hasta + 1):
        festivos |= festivos_colombia(year)
    return sorted(f.isoformat() for f in festivos)
