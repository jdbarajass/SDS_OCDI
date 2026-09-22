from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from app.template_utils import make_templates

from app.database import get_db
from app.auth_utils import (
    verify_password, new_token, registrar_log, get_session_user,
    cuenta_bloqueada, registrar_intento_fallido, resetear_intentos_fallidos,
    rate_limit_login,
)

router = APIRouter()
templates = make_templates(str(Path(__file__).parent.parent / "templates"))


# ── LOGIN ─────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, next: str = "/", error: str = "", minutos: int = 0):
    # Si ya está autenticado, redirigir al portal
    if get_session_user(request):
        return RedirectResponse("/")
    conn = get_db()
    abogados = conn.execute(
        "SELECT id, nombre_completo FROM usuarios WHERE rol = 'abogado' AND activo = 1 ORDER BY nombre_completo"
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("login.html", {
        "request": request,
        "abogados": [dict(r) for r in abogados],
        "next": next,
        "error": error,
        "minutos": minutos,
    })


@router.post("/login/abogado")
async def login_abogado(
    request: Request,
    user_id: int = Form(...),
    next: str = Form("/"),
):
    """Login para abogados: solo eligen su nombre, sin contraseña."""
    ip = request.client.host if request.client else None
    if rate_limit_login(ip):
        return RedirectResponse("/login?error=demasiados_intentos", status_code=303)

    conn = get_db()
    user = conn.execute(
        "SELECT id, nombre_completo, rol FROM usuarios WHERE id = ? AND rol = 'abogado' AND activo = 1",
        (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return RedirectResponse("/login?error=usuario_invalido", status_code=303)

    token = new_token()
    conn.execute(
        "INSERT INTO sesiones (token, user_id) VALUES (?,?)",
        (token, user["id"])
    )
    conn.commit()

    registrar_log(dict(user), "login", None, "Acceso seleccionando nombre",
                  request.client.host if request.client else None)
    conn.close()

    dest = next if next.startswith("/") else "/"
    response = RedirectResponse(dest, status_code=303)
    response.set_cookie("ocdi_session", token, httponly=True, samesite="lax")
    return response


@router.post("/login/credencial")
async def login_credencial(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    """Login con usuario y contraseña para secretarios, jefe y admin."""
    ip = request.client.host if request.client else None
    if rate_limit_login(ip):
        return RedirectResponse("/login?error=demasiados_intentos", status_code=303)

    conn = get_db()
    user = conn.execute(
        "SELECT id, username, nombre_completo, rol, password_hash, bloqueado_hasta FROM usuarios "
        "WHERE username = ? AND activo = 1 AND password_hash IS NOT NULL",
        (username.strip(),)
    ).fetchone()

    if user:
        minutos_restantes = cuenta_bloqueada(dict(user))
        if minutos_restantes:
            conn.close()
            return RedirectResponse(
                f"/login?error=cuenta_bloqueada&minutos={minutos_restantes}", status_code=303
            )

    if not user or not verify_password(password, user["password_hash"]):
        if user:
            minutos_bloqueo = registrar_intento_fallido(conn, user["id"])
            if minutos_bloqueo:
                conn.close()
                return RedirectResponse(
                    f"/login?error=cuenta_bloqueada&minutos={minutos_bloqueo}", status_code=303
                )
        conn.close()
        return RedirectResponse("/login?error=credenciales_invalidas", status_code=303)

    resetear_intentos_fallidos(conn, user["id"])

    token = new_token()
    conn.execute(
        "INSERT INTO sesiones (token, user_id) VALUES (?,?)",
        (token, user["id"])
    )
    conn.commit()

    registrar_log(dict(user), "login", None, f"Acceso con usuario '{user['username']}'",
                  request.client.host if request.client else None)
    conn.close()

    dest = next if next.startswith("/") else "/"
    response = RedirectResponse(dest, status_code=303)
    response.set_cookie("ocdi_session", token, httponly=True, samesite="lax")
    return response


# ── LOGOUT ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get("ocdi_session")
    user = getattr(request.state, "user", None)

    if token:
        conn = get_db()
        conn.execute("DELETE FROM sesiones WHERE token = ?", (token,))
        conn.commit()
        conn.close()

    if user:
        registrar_log(user, "logout", None, None,
                      request.client.host if request.client else None)

    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("ocdi_session")
    return response


@router.get("/logout")
async def logout_get(request: Request):
    """Permite cerrar sesión desde un enlace <a href="/logout">."""
    return await logout(request)
