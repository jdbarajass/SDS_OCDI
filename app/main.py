from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ── Middleware de autenticación ───────────────────────────────────────────────

_RUTAS_PUBLICAS = {"/login", "/login/abogado", "/login/credencial", "/logout"}

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Rutas públicas: estáticos y login/logout
    if path.startswith("/static") or path in _RUTAS_PUBLICAS:
        return await call_next(request)

    # Verificar sesión activa
    from app.database import get_db
    token = request.cookies.get("ocdi_session")
    user = None

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
            conn.commit()
            user = dict(row)
        conn.close()

    if user is None:
        from urllib.parse import quote_plus
        next_url = quote_plus(str(request.url.path))
        response = RedirectResponse(f"/login?next={next_url}&error=sin_sesion")
        if token:
            response.delete_cookie("ocdi_session")
        return response

    request.state.user = user
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
