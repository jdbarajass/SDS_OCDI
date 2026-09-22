import logging
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.template_utils import make_templates
from pathlib import Path

logger = logging.getLogger("ocdi")

from app.database import init_db
from app.routers import (
    expedientes, importar, dashboard, seguimiento,
    portal, digitales, sala, backup, correspondencia, control_autos,
    pdf_tools, equipos, reportes, buscar, matriz, compensatorios,
)
from app.routers import sdqs as sdqs_router
from app.routers import auth as auth_router
from app.routers import admin_usuarios

BASE_DIR = Path(__file__).parent

app = FastAPI(
    title="OCDI - Sistema de Gestión Disciplinaria",
    description="Secretaría Distrital de Salud - Oficina de Control Disciplinario Interno",
    version="5.4.0",
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = make_templates(str(BASE_DIR / "templates"))

# ── Middleware de autenticación ───────────────────────────────────────────────

_RUTAS_PUBLICAS = {"/login", "/login/abogado", "/login/credencial", "/logout", "/favicon.ico"}

# Mapa de prefijos de URL a módulo para verificar visibilidad
_URL_MODULO_MAP = [
    ("/dashboard",       "expedientes"),
    ("/expedientes",     "expedientes"),
    ("/seguimiento",     "expedientes"),
    ("/importar",        "expedientes"),
    ("/autos",           "expedientes"),
    ("/correspondencia", "correspondencia"),
    ("/control-autos",   "control_autos"),
    ("/sdqs",            "sdqs"),
    ("/digitales",       "digitales"),
    ("/sala",            "sala"),
    ("/backup",          "backup"),
    ("/equipos",         "equipos"),
    ("/matriz",          "matriz"),
    ("/compensatorios",  "compensatorios"),
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
                permisos = {m: {"puede_ver": True, "puede_escribir": True, "puede_importar": True} for m in modulos}
            else:
                perm_rows = conn.execute(
                    "SELECT modulo, puede_ver, puede_escribir, puede_importar FROM permisos_modulo WHERE user_id = ?",
                    (user["id"],)
                ).fetchall()
                permisos = {m: {"puede_ver": True, "puede_escribir": False, "puede_importar": False} for m in modulos}
                for pr in perm_rows:
                    permisos[pr["modulo"]] = {
                        "puede_ver": pr["puede_ver"] != 0,
                        "puede_escribir": bool(pr["puede_escribir"]),
                        "puede_importar": bool(pr["puede_importar"]),
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


# ── Cabeceras de seguridad HTTP (SDS-TIC-LN-016 §5.4.4.b) ────────────────────
# CSP permite 'unsafe-inline' en script/style porque las plantillas actuales
# usan extensivamente atributos style="" y onclick="" inline — una CSP
# estricta (nonces, sin inline) rompería la UI existente. Aun así esta
# política ya bloquea la carga de recursos/scripts de dominios externos no
# autorizados, iframes ajenos (clickjacking) y el envío de formularios a
# otro origen, que es la parte que más importa contra XSS con exfiltración.
# Strict-Transport-Security queda para la Fase 4 (TLS): HSTS sobre HTTP plano
# no tiene efecto y los navegadores lo ignoran hasta que haya HTTPS real.

_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


def _set_security_headers(response):
    response.headers["Content-Security-Policy"] = _CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    return _set_security_headers(response)


# ── Manejo de errores fail-closed (SDS-TIC-LN-016 §5.4.2.f) ──────────────────
# Cualquier excepción no controlada se registra en el log del servidor con su
# detalle técnico completo, pero al usuario solo se le muestra un mensaje
# genérico — nunca trazas de pila, rutas de servidor ni nombres de librerías.

_ERROR_500_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Error — OCDI</title>
<style>
  body{font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;background:#f1f5f9;
       display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
  .box{background:#fff;border-radius:12px;padding:36px 40px;box-shadow:0 4px 20px rgba(0,0,0,.08);
       max-width:420px;text-align:center}
  h1{font-size:20px;color:#1e293b;margin:0 0 8px}
  p{font-size:14px;color:#64748b;margin:0 0 20px}
  a{display:inline-block;background:#2563eb;color:#fff;text-decoration:none;padding:9px 20px;
    border-radius:7px;font-size:13px;font-weight:600}
</style></head>
<body><div class="box">
  <h1>⚠️ Ocurrió un error inesperado</h1>
  <p>El equipo técnico ya quedó notificado. Intente de nuevo en unos minutos.</p>
  <a href="/">Volver al portal</a>
</div></body></html>"""


@app.exception_handler(Exception)
async def manejador_errores_no_controlados(request: Request, exc: Exception):
    # Starlette maneja @app.exception_handler(Exception) en ServerErrorMiddleware,
    # una capa por FUERA del stack de @app.middleware("http") — la respuesta que
    # arma este handler nunca pasa por security_headers_middleware, así que las
    # cabeceras se aplican aquí directamente (si no, la página de error, que es
    # justo donde más importan por defensa en profundidad, quedaría sin CSP ni
    # X-Frame-Options). Verificado con un 500 forzado: sin esto, 0 de las 5
    # cabeceras llegaban al cliente en esa respuesta.
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return _set_security_headers(HTMLResponse(content=_ERROR_500_HTML, status_code=500))


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router.router)
app.include_router(admin_usuarios.router)
app.include_router(portal.router)
app.include_router(dashboard.router)
app.include_router(expedientes.router)
app.include_router(importar.router)
app.include_router(seguimiento.router)
app.include_router(digitales.router)
app.include_router(sala.router)
app.include_router(backup.router)
app.include_router(correspondencia.router)
app.include_router(control_autos.router)
app.include_router(sdqs_router.router)
app.include_router(pdf_tools.router)
app.include_router(equipos.router)
app.include_router(reportes.router)
app.include_router(buscar.router)
app.include_router(matriz.router)
app.include_router(compensatorios.router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(str(BASE_DIR / "static" / "favicon.png"), media_type="image/png")


@app.on_event("startup")
async def startup():
    init_db()
