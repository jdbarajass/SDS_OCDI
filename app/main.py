from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.template_utils import make_templates
from pathlib import Path

from app.database import init_db
from app.routers import (
    expedientes, importar, dashboard, seguimiento, autos,
    portal, digitales, sala, backup, correspondencia, control_autos,
)
from app.routers import auth as auth_router
from app.routers import admin_usuarios

BASE_DIR = Path(__file__).parent

app = FastAPI(
    title="OCDI - Sistema de Gestión Disciplinaria",
    description="Secretaría Distrital de Salud - Oficina de Control Disciplinario Interno",
    version="3.0.0",
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = make_templates(str(BASE_DIR / "templates"))

# ── Middleware de autenticación ───────────────────────────────────────────────

_RUTAS_PUBLICAS = {"/login", "/login/abogado", "/login/credencial", "/logout"}

# Mapa de prefijos de URL a módulo para verificar visibilidad
_URL_MODULO_MAP = [
    ("/dashboard",       "expedientes"),
    ("/expedientes",     "expedientes"),
    ("/seguimiento",     "expedientes"),
    ("/importar",        "expedientes"),
    ("/autos",           "expedientes"),
    ("/correspondencia", "correspondencia"),
    ("/control-autos",   "control_autos"),
    ("/digitales",       "digitales"),
    ("/sala",            "sala"),
    ("/backup",          "backup"),
]

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Rutas públicas: estáticos y login/logout
    if path.startswith("/static") or path in _RUTAS_PUBLICAS:
        return await call_next(request)

    # Verificar sesión activa y cargar permisos en el mismo query
    from app.database import get_db
    from app.auth_utils import MODULOS_SISTEMA, ROLES_SUPERUSUARIO
    token = request.cookies.get("ocdi_session")
    user = None
    permisos: dict = {}

    if token:
        conn = get_db()
        row = conn.execute("""
            SELECT u.id, u.username, u.nombre_completo, u.rol, u.activo
            FROM sesiones s
            JOIN usuarios u ON u.id = s.user_id
            WHERE s.token = ? AND u.activo = 1
        """, (token,)).fetchone()
        if row:
            conn.execute(
                "UPDATE sesiones SET last_seen = datetime('now','localtime') WHERE token = ?",
                (token,)
            )
            user = dict(row)
            modulos = [m for m, _ in MODULOS_SISTEMA]
            if user["rol"] in ROLES_SUPERUSUARIO:
                permisos = {m: {"puede_ver": True, "puede_escribir": True} for m in modulos}
            else:
                perm_rows = conn.execute(
                    "SELECT modulo, puede_ver, puede_escribir FROM permisos_modulo WHERE user_id = ?",
                    (user["id"],)
                ).fetchall()
                permisos = {m: {"puede_ver": True, "puede_escribir": False} for m in modulos}
                for pr in perm_rows:
                    permisos[pr["modulo"]] = {
                        "puede_ver": pr["puede_ver"] != 0,
                        "puede_escribir": bool(pr["puede_escribir"]),
                    }
        conn.commit()
        conn.close()

    if user is None:
        from urllib.parse import quote_plus
        next_url = quote_plus(str(request.url.path))
        response = RedirectResponse(f"/login?next={next_url}&error=sin_sesion")
        if token:
            response.delete_cookie("ocdi_session")
        return response

    request.state.user = user
    request.state.permisos = permisos

    # Bloquear acceso a módulos sin visibilidad (no aplica a superusuarios)
    if user["rol"] not in ROLES_SUPERUSUARIO:
        for prefix, modulo in _URL_MODULO_MAP:
            if path.startswith(prefix):
                if not permisos.get(modulo, {}).get("puede_ver", True):
                    return RedirectResponse("/?msg=sin_acceso", status_code=303)
                break

    return await call_next(request)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router.router)
app.include_router(admin_usuarios.router)
app.include_router(portal.router)
app.include_router(dashboard.router)
app.include_router(expedientes.router)
app.include_router(importar.router)
app.include_router(seguimiento.router)
app.include_router(autos.router)
app.include_router(digitales.router)
app.include_router(sala.router)
app.include_router(backup.router)
app.include_router(correspondencia.router)
app.include_router(control_autos.router)


@app.on_event("startup")
async def startup():
    init_db()
