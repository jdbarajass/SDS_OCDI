"""
Regresión sobre app/auth_utils.py — controles de la Fase 2 de cumplimiento
SDS-TIC-LN-016 (política de contraseñas y bloqueo por intentos fallidos).

No toca la base de datos real: prueba las funciones puras (validación de
política, cálculo de minutos restantes de bloqueo, rate limiting en memoria).
"""
from datetime import datetime, timedelta

from app.auth_utils import (
    validar_politica_password,
    LONGITUD_MINIMA_PASSWORD,
    cuenta_bloqueada,
    rate_limit_login,
    MAX_INTENTOS_POR_IP,
    _intentos_por_ip,
)


# ── validar_politica_password ─────────────────────────────────────────────────

def test_password_valida_no_retorna_error():
    assert validar_politica_password("Correcta#Pass123") is None


def test_password_corta_falla():
    assert validar_politica_password("Ab1#") is not None


def test_password_sin_mayuscula_falla():
    assert validar_politica_password("minuscula123#") is not None


def test_password_sin_minuscula_falla():
    assert validar_politica_password("MAYUSCULA123#") is not None


def test_password_sin_numero_falla():
    assert validar_politica_password("SinNumeroAlguno#") is not None


def test_password_sin_simbolo_falla():
    assert validar_politica_password("SinSimboloAlguno123") is not None


def test_longitud_minima_es_12():
    # Documenta la decisión: se exige el nivel "recomendado" del lineamiento
    # (12 caracteres), no solo el piso absoluto (8).
    assert LONGITUD_MINIMA_PASSWORD == 12
    pwd_11 = "Aa1#aaaaaaa"[:11]
    assert validar_politica_password(pwd_11) is not None


# ── cuenta_bloqueada ─────────────────────────────────────────────────────────

def test_sin_bloqueado_hasta_no_esta_bloqueada():
    assert cuenta_bloqueada({"bloqueado_hasta": None}) == 0


def test_bloqueo_futuro_retorna_minutos_positivos():
    hasta = (datetime.now() + timedelta(minutes=10)).isoformat(timespec="seconds")
    minutos = cuenta_bloqueada({"bloqueado_hasta": hasta})
    assert 1 <= minutos <= 10


def test_bloqueo_pasado_ya_no_bloquea():
    hasta = (datetime.now() - timedelta(minutes=1)).isoformat(timespec="seconds")
    assert cuenta_bloqueada({"bloqueado_hasta": hasta}) == 0


# ── rate_limit_login ───────────────────────────────────────────────────────────

def test_rate_limit_permite_hasta_el_maximo():
    ip = "10.0.0.99"
    _intentos_por_ip.pop(ip, None)
    try:
        for _ in range(MAX_INTENTOS_POR_IP):
            assert rate_limit_login(ip) is False
        assert rate_limit_login(ip) is True
    finally:
        _intentos_por_ip.pop(ip, None)


def test_rate_limit_ip_none_nunca_bloquea():
    assert rate_limit_login(None) is False
