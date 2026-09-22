"""
Regresión end-to-end del flujo de login sobre la app real (vía TestClient),
usando siempre una base de datos temporal — nunca data/ocdi.db (ver
tests/conftest.py y SDS-TIC-LN-016 §5.4.3.a).

Reproduce en forma de test automatizado lo que antes se verificaba a mano
con scripts ad-hoc de un solo uso al implementar la Fase 2 (bloqueo por
intentos fallidos) y la Fase 3 (cabeceras de seguridad) del cumplimiento
SDS-TIC-LN-016.
"""


def test_login_credencial_incorrecta_5_veces_bloquea_la_cuenta(client):
    for _ in range(4):
        r = client.post(
            "/login/credencial",
            data={"username": "Secretario1", "password": "incorrecta", "next": "/"},
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert "error=credenciales_invalidas" in r.headers["location"]

    # 5° intento: se dispara el bloqueo y se avisa de inmediato
    r = client.post(
        "/login/credencial",
        data={"username": "Secretario1", "password": "incorrecta", "next": "/"},
        follow_redirects=False,
    )
    assert "error=cuenta_bloqueada" in r.headers["location"]

    # 6° intento, incluso con password correcta, sigue bloqueado
    r = client.post(
        "/login/credencial",
        data={"username": "Secretario1", "password": "cualquier-cosa", "next": "/"},
        follow_redirects=False,
    )
    assert "error=cuenta_bloqueada" in r.headers["location"]


def test_login_sin_sesion_redirige_a_login(client):
    r = client.get("/expedientes", follow_redirects=False)
    assert r.status_code in (303, 307)
    assert "/login" in r.headers["location"]


def test_crear_usuario_con_password_debil_es_rechazado(admin_client):
    r = admin_client.post(
        "/admin/usuarios/nuevo",
        data={
            "nombre_completo": "PRUEBA TEST",
            "rol": "secretario",
            "username": "pruebatest",
            "password": "debil123",  # sin mayúscula ni símbolo, y corta
        },
        follow_redirects=False,
    )
    assert "msg=password_corta" in r.headers["location"]


def test_paginas_autenticadas_incluyen_cabeceras_de_seguridad(client):
    r = client.get("/login")
    assert "content-security-policy" in {k.lower() for k in r.headers.keys()}
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"


def test_bloqueo_expirado_no_se_reactiva_con_un_solo_error(client):
    """Regresión: antes, si el contador de intentos fallidos no se reseteaba
    al expirar un bloqueo anterior, un solo error (p.ej. un typo) justo
    después de que el bloqueo expiraba volvía a bloquear la cuenta de
    inmediato — dejando al usuario legítimo con una sola oportunidad por
    ventana de 15 min para siempre. Se simula un bloqueo ya expirado y se
    verifica que un solo intento fallido NO vuelve a bloquear."""
    from datetime import datetime, timedelta
    import app.database as dbmod

    conn = dbmod.get_db()
    pasado = (datetime.now() - timedelta(minutes=1)).isoformat(timespec="seconds")
    conn.execute(
        "UPDATE usuarios SET intentos_fallidos=5, bloqueado_hasta=? WHERE username='Secretario1'",
        (pasado,),
    )
    conn.commit()
    conn.close()

    r = client.post(
        "/login/credencial",
        data={"username": "Secretario1", "password": "typo", "next": "/"},
        follow_redirects=False,
    )
    assert "error=credenciales_invalidas" in r.headers["location"]
    assert "error=cuenta_bloqueada" not in r.headers["location"]


def test_pagina_error_500_incluye_cabeceras_de_seguridad(admin_client_sin_raise):
    """Regresión: @app.exception_handler(Exception) lo maneja Starlette en
    ServerErrorMiddleware, una capa por FUERA de @app.middleware("http") — la
    respuesta de un 500 no controlado no pasaba por security_headers_middleware
    y salía sin CSP/X-Frame-Options, justo la página donde más importan.

    Usa raise_server_exceptions=False porque TestClient por defecto relanza
    la excepción cruda (para depurar) en vez de devolver la respuesta HTTP
    real — un navegador real siempre recibe la respuesta del exception
    handler, nunca la excepción cruda."""
    import app.database as dbmod
    conn = dbmod.get_db()
    conn.execute("DROP TABLE expedientes")
    conn.commit()
    conn.close()

    r = admin_client_sin_raise.get("/expedientes", follow_redirects=False)
    assert r.status_code == 500
    headers = {k.lower() for k in r.headers.keys()}
    assert "content-security-policy" in headers
    assert "x-frame-options" in headers


def test_reactivar_usuario_limpia_bloqueo(admin_client):
    """Regresión: reactivar una cuenta desactivada (toggle_activo) no limpiaba
    un bloqueo por intentos fallidos previo, dejando al usuario reactivado
    sin poder entrar hasta 15 min más, sin ninguna indicación de por qué."""
    from datetime import datetime, timedelta
    import app.database as dbmod

    conn = dbmod.get_db()
    futuro = (datetime.now() + timedelta(minutes=10)).isoformat(timespec="seconds")
    conn.execute(
        "UPDATE usuarios SET activo=0, intentos_fallidos=5, bloqueado_hasta=? WHERE username='Secretario1'",
        (futuro,),
    )
    conn.commit()
    user_id = conn.execute("SELECT id FROM usuarios WHERE username='Secretario1'").fetchone()[0]
    conn.close()

    admin_client.post(f"/admin/usuarios/{user_id}/toggle-activo", follow_redirects=False)

    conn = dbmod.get_db()
    row = conn.execute(
        "SELECT activo, intentos_fallidos, bloqueado_hasta FROM usuarios WHERE id=?", (user_id,)
    ).fetchone()
    conn.close()
    assert row["activo"] == 1
    assert row["intentos_fallidos"] == 0
    assert row["bloqueado_hasta"] is None
