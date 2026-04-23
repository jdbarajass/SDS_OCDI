from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import get_db
from app.auth_utils import (
    hash_password, MODULOS_SISTEMA, ROLES_SUPERUSUARIO, registrar_log
)

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _require_superuser(request: Request):
    user = getattr(request.state, "user", None)
    if not user or user["rol"] not in ROLES_SUPERUSUARIO:
        return None
    return user


# ── Gestión de usuarios ───────────────────────────────────────────────────────

@router.get("/usuarios", response_class=HTMLResponse)
async def admin_usuarios(request: Request, msg: str = ""):
    user = _require_superuser(request)
    if not user:
        return RedirectResponse("/?msg=sin_permiso", status_code=303)

    conn = get_db()
    usuarios = conn.execute(
        "SELECT id, username, nombre_completo, rol, activo FROM usuarios ORDER BY rol, nombre_completo"
    ).fetchall()
    permisos_rows = conn.execute(
        "SELECT user_id, modulo, puede_escribir FROM permisos_modulo"
    ).fetchall()
    conn.close()

    permisos: dict = {}
    for row in permisos_rows:
        uid = row["user_id"]
        if uid not in permisos:
            permisos[uid] = {}
        permisos[uid][row["modulo"]] = bool(row["puede_escribir"])

    return templates.TemplateResponse("admin_usuarios.html", {
        "request": request,
        "current_user": user,
        "usuarios": [dict(u) for u in usuarios],
        "permisos": permisos,
        "modulos": MODULOS_SISTEMA,
        "msg": msg,
        "active": "admin_usuarios",
    })


@router.post("/usuarios/{user_id}/toggle-activo")
async def toggle_activo(request: Request, user_id: int):
    user = _require_superuser(request)
    if not user or user["rol"] != "admin":
        return RedirectResponse("/admin/usuarios?msg=sin_permiso", status_code=303)

    conn = get_db()
    row = conn.execute(
        "SELECT activo, nombre_completo FROM usuarios WHERE id = ?", (user_id,)
    ).fetchone()
    if row:
        new_val = 0 if row["activo"] else 1
        conn.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (new_val, user_id))
        conn.commit()
        registrar_log(user, "toggle_activo", "usuarios",
                      f"'{row['nombre_completo']}' activo → {new_val}",
                      request.client.host if request.client else None)
    conn.close()
    return RedirectResponse("/admin/usuarios?msg=actualizado", status_code=303)


@router.post("/usuarios/{user_id}/cambiar-password")
async def cambiar_password(
    request: Request,
    user_id: int,
    nueva_password: str = Form(""),
):
    user = _require_superuser(request)
    if not user or user["rol"] != "admin":
        return RedirectResponse("/admin/usuarios?msg=sin_permiso", status_code=303)

    nueva_password = (nueva_password or "").strip()
    if len(nueva_password) < 8:
        return RedirectResponse("/admin/usuarios?msg=password_corta", status_code=303)

    hashed = hash_password(nueva_password)
    conn = get_db()
    row = conn.execute("SELECT nombre_completo FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    conn.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?", (hashed, user_id))
    conn.commit()
    if row:
        registrar_log(user, "cambiar_password", "usuarios",
                      f"Contraseña actualizada para '{row['nombre_completo']}'",
                      request.client.host if request.client else None)
    conn.close()
    return RedirectResponse("/admin/usuarios?msg=password_actualizada", status_code=303)


@router.post("/usuarios/{user_id}/permisos")
async def actualizar_permisos(request: Request, user_id: int):
    user = _require_superuser(request)
    if not user:
        return RedirectResponse("/admin/usuarios?msg=sin_permiso", status_code=303)

    form = await request.form()
    conn = get_db()

    target = conn.execute(
        "SELECT nombre_completo, rol FROM usuarios WHERE id = ?", (user_id,)
    ).fetchone()
    if not target:
        conn.close()
        return RedirectResponse("/admin/usuarios?msg=no_encontrado", status_code=303)

    if target["rol"] in ROLES_SUPERUSUARIO:
        conn.close()
        return RedirectResponse("/admin/usuarios?msg=sin_permiso", status_code=303)

    for modulo, _ in MODULOS_SISTEMA:
        puede = 1 if form.get(f"perm_{user_id}_{modulo}") else 0
        conn.execute("""
            INSERT INTO permisos_modulo (user_id, modulo, puede_escribir)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, modulo) DO UPDATE SET puede_escribir = excluded.puede_escribir
        """, (user_id, modulo, puede))

    conn.commit()
    registrar_log(user, "actualizar_permisos", "usuarios",
                  f"Permisos de '{target['nombre_completo']}' actualizados",
                  request.client.host if request.client else None)
    conn.close()
    return RedirectResponse("/admin/usuarios?msg=permisos_actualizados", status_code=303)


# ── Registro de actividad ─────────────────────────────────────────────────────

@router.get("/logs", response_class=HTMLResponse)
async def admin_logs(
    request: Request,
    modulo: str = "",
    accion: str = "",
    usuario: str = "",
    page: int = 1,
    por_pagina: int = 50,
):
    user = _require_superuser(request)
    if not user:
        return RedirectResponse("/?msg=sin_permiso", status_code=303)

    conn = get_db()

    filtros = ["1=1"]
    params: list = []
    if modulo:
        filtros.append("modulo = ?")
        params.append(modulo)
    if accion:
        filtros.append("accion LIKE ?")
        params.append(f"%{accion}%")
    if usuario:
        filtros.append("nombre_usuario LIKE ?")
        params.append(f"%{usuario}%")

    where = " AND ".join(filtros)
    total = conn.execute(
        f"SELECT COUNT(*) FROM logs_actividad WHERE {where}", params
    ).fetchone()[0]
    offset = (page - 1) * por_pagina

    logs = conn.execute(
        f"SELECT * FROM logs_actividad WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [por_pagina, offset],
    ).fetchall()

    modulos_list = [r[0] for r in conn.execute(
        "SELECT DISTINCT modulo FROM logs_actividad WHERE modulo IS NOT NULL ORDER BY modulo"
    ).fetchall()]
    acciones_list = [r[0] for r in conn.execute(
        "SELECT DISTINCT accion FROM logs_actividad ORDER BY accion"
    ).fetchall()]
    conn.close()

    total_pages = max(1, (total + por_pagina - 1) // por_pagina)

    return templates.TemplateResponse("admin_logs.html", {
        "request": request,
        "current_user": user,
        "logs": [dict(l) for l in logs],
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "modulo_filtro": modulo,
        "accion_filtro": accion,
        "usuario_filtro": usuario,
        "modulos_list": modulos_list,
        "acciones_list": acciones_list,
        "active": "admin_logs",
    })
