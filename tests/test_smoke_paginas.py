"""
Prueba de humo: cada página principal de cada módulo debe responder 200 tras
la actualización de fastapi/starlette/jinja2 de la Fase 7 (SDS-TIC-LN-016).
No valida contenido específico, solo que el render no explote (regresión
directa del bug de TemplateResponse encontrado al actualizar Starlette).
"""
import pytest


def _login_admin(client):
    import app.database as dbmod
    conn = dbmod.get_db()
    admin = conn.execute("SELECT id FROM usuarios WHERE username='Admin'").fetchone()
    from app.auth_utils import new_token
    token = new_token()
    conn.execute("INSERT INTO sesiones (token, user_id) VALUES (?,?)", (token, admin["id"]))
    conn.commit()
    conn.close()
    client.cookies.set("ocdi_session", token)


PAGINAS = [
    "/",
    "/dashboard",
    "/expedientes",
    "/seguimiento",
    "/importar",
    "/correspondencia",
    "/correspondencia/dashboard",
    "/control-autos",
    "/sdqs",
    "/digitales",
    "/digitales/comunicaciones",
    "/sala",
    "/backup",
    "/backup/restauracion",
    "/pdf-tools",
    "/equipos",
    "/equipos/bienes/lista",
    "/matriz",
    "/compensatorios",
    "/buscar",
    "/admin/usuarios",
    "/admin/logs",
]


@pytest.mark.parametrize("path", PAGINAS)
def test_pagina_responde_200(client, path):
    _login_admin(client)
    r = client.get(path, follow_redirects=True)
    assert r.status_code == 200, f"{path} -> {r.status_code}"
    assert len(r.text) > 0
