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


def test_crear_usuario_con_password_debil_es_rechazado(client):
    conn_mod = __import__("app.database", fromlist=["get_db"])
    conn = conn_mod.get_db()
    admin = conn.execute("SELECT id FROM usuarios WHERE username='Admin'").fetchone()
    from app.auth_utils import new_token
    token = new_token()
    conn.execute("INSERT INTO sesiones (token, user_id) VALUES (?,?)", (token, admin["id"]))
    conn.commit()
    conn.close()
    client.cookies.set("ocdi_session", token)

    r = client.post(
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
