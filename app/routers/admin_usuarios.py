from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from app.template_utils import make_templates

from app.database import get_db
from app.auth_utils import (
    hash_password, MODULOS_SISTEMA, ROLES_SUPERUSUARIO, ROLES_ESCRITURA_DEFAULT, registrar_log
)

router = APIRouter(prefix="/admin")
templates = make_templates(str(Path(__file__).parent.parent / "templates"))


def _require_superuser(request: Request):
    user = getattr(request.state, "user", None)
    if not user or user["rol"] not in ROLES_SUPERUSUARIO:
        return None
    return user


ROLES_VALIDOS = {"admin", "jefe", "secretario", "auxiliar", "abogado"}


# ── Gestión de usuarios ───────────────────────────────────────────────────────

@router.get("/usuarios", response_class=HTMLResponse)
async def admin_usuarios(request: Request, msg: str = ""):
    user = _require_superuser(request)
    if not user:
        return RedirectResponse("/?msg=sin_permiso", status_code=303)

    conn = get_db()
    usuarios = conn.execute(
        "SELECT id, username, nombre_completo, rol, activo, tipo_contrato FROM usuarios ORDER BY rol, nombre_completo"
    ).fetchall()
    permisos_rows = conn.execute(
        "SELECT user_id, modulo, puede_ver, puede_escribir, puede_importar FROM permisos_modulo"
    ).fetchall()
    personal = conn.execute(
        "SELECT id, nombre, activo FROM personal_oficina ORDER BY nombre"
    ).fetchall()
    conn.close()

    permisos: dict = {}
    for row in permisos_rows:
        uid = row["user_id"]
        if uid not in permisos:
            permisos[uid] = {}
        permisos[uid][row["modulo"]] = {
            "puede_ver": row["puede_ver"] != 0,
            "puede_escribir": bool(row["puede_escribir"]),
            "puede_importar": bool(row["puede_importar"]),
        }

    return templates.TemplateResponse("admin_usuarios.html", {
        "request": request,
        "current_user": user,
        "usuarios": [dict(u) for u in usuarios],
        "permisos": permisos,
        "modulos": MODULOS_SISTEMA,
        "personal": [dict(p) for p in personal],
        "msg": msg,
        "active": "admin_usuarios",
    })


@router.post("/usuarios/nuevo")
async def crear_usuario(
    request: Request,
    nombre_completo: str = Form(""),
    rol: str = Form(""),
    username: str = Form(""),
    password: str = Form(""),
    tipo_contrato: str = Form(""),
):
    user = _require_superuser(request)
    if not user or user["rol"] != "admin":
        return RedirectResponse("/admin/usuarios?msg=sin_permiso", status_code=303)

    nombre_completo = nombre_completo.strip().upper()
    rol = rol.strip()
    username = username.strip()
    password = password.strip()
    tipo_contrato = tipo_contrato.strip() or None

    if not nombre_completo or rol not in ROLES_VALIDOS:
        return RedirectResponse("/admin/usuarios?msg=error_usuario_obligatorios", status_code=303)
    if tipo_contrato and tipo_contrato not in ("planta", "contratista"):
        return RedirectResponse("/admin/usuarios?msg=error_usuario_obligatorios", status_code=303)

    # Los abogados ingresan solo seleccionando su nombre (sin contraseña, ver
    # /login/abogado); el resto de roles necesita usuario+contraseña propios.
    if rol == "abogado":
        username, password_hash = None, None
    else:
        if not username or len(password) < 8:
            return RedirectResponse("/admin/usuarios?msg=error_usuario_obligatorios", status_code=303)
        password_hash = hash_password(password)

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO usuarios (username, password_hash, nombre_completo, rol, tipo_contrato) VALUES (?,?,?,?,?)",
            (username, password_hash, nombre_completo, rol, tipo_contrato),
        )
    except Exception:
        conn.close()
        return RedirectResponse("/admin/usuarios?msg=error_usuario_duplicado", status_code=303)

    uid = cur.lastrowid
    # admin y jefe bypasean permisos por módulo — no necesitan filas en permisos_modulo.
    if rol not in ROLES_SUPERUSUARIO:
        puede_escribir_default = 1 if rol in ROLES_ESCRITURA_DEFAULT else 0
        for modulo, _ in MODULOS_SISTEMA:
            conn.execute(
                "INSERT INTO permisos_modulo (user_id, modulo, puede_escribir, puede_ver) VALUES (?,?,?,1)",
                (uid, modulo, puede_escribir_default),
            )
    conn.commit()
    registrar_log(user, "crear_usuario", "usuarios", f"Usuario creado: '{nombre_completo}' (rol={rol})",
                  request.client.host if request.client else None)
    conn.close()
    return RedirectResponse("/admin/usuarios?msg=usuario_creado", status_code=303)


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
        puede_e = 1 if form.get(f"pw_{user_id}_{modulo}") else 0
        puede_v = 1 if form.get(f"pv_{user_id}_{modulo}") else 0
        puede_i = 1 if form.get(f"pi_{user_id}_{modulo}") else 0
        conn.execute("""
            INSERT INTO permisos_modulo (user_id, modulo, puede_escribir, puede_ver, puede_importar)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, modulo) DO UPDATE SET
                puede_escribir = excluded.puede_escribir,
                puede_ver = excluded.puede_ver,
                puede_importar = excluded.puede_importar
        """, (user_id, modulo, puede_e, puede_v, puede_i))

    conn.commit()
    registrar_log(user, "actualizar_permisos", "usuarios",
                  f"Permisos de '{target['nombre_completo']}' actualizados",
                  request.client.host if request.client else None)
    conn.close()
    return RedirectResponse("/admin/usuarios?msg=permisos_actualizados", status_code=303)


@router.post("/usuarios/{user_id}/tipo-contrato")
async def cambiar_tipo_contrato(
    request: Request,
    user_id: int,
    tipo_contrato: str = Form(""),
):
    user = _require_superuser(request)
    if not user or user["rol"] != "admin":
        return RedirectResponse("/admin/usuarios?msg=sin_permiso", status_code=303)

    valor = tipo_contrato.strip() or None
    if valor and valor not in ("planta", "contratista"):
        return RedirectResponse("/admin/usuarios?msg=error", status_code=303)

    conn = get_db()
    row = conn.execute("SELECT nombre_completo FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    conn.execute("UPDATE usuarios SET tipo_contrato = ? WHERE id = ?", (valor, user_id))
    conn.commit()
    if row:
        registrar_log(user, "cambiar_tipo_contrato", "usuarios",
                      f"'{row['nombre_completo']}' tipo_contrato → {valor or 'ninguno'}",
                      request.client.host if request.client else None)
    conn.close()
    return RedirectResponse("/admin/usuarios?msg=actualizado", status_code=303)


# ── Personal de la Oficina ────────────────────────────────────────────────────

@router.post("/personal/nuevo")
async def personal_nuevo(request: Request, nombre: str = Form(...)):
    user = _require_superuser(request)
    if not user:
        return RedirectResponse("/admin/usuarios?msg=sin_permiso", status_code=303)
    nombre = nombre.strip().upper()
    if not nombre:
        return RedirectResponse("/admin/usuarios?msg=vacio", status_code=303)
    conn = get_db()
    try:
        conn.execute("INSERT INTO personal_oficina (nombre, activo) VALUES (?, 1)", (nombre,))
        conn.commit()
        registrar_log(user, "personal_nuevo", "admin", f"Persona agregada: '{nombre}'",
                      request.client.host if request.client else None)
    except Exception:
        conn.close()
        return RedirectResponse("/admin/usuarios?msg=duplicado", status_code=303)
    conn.close()
    return RedirectResponse("/admin/usuarios?msg=personal_ok#personal-oficina", status_code=303)


@router.post("/personal/{pid}/editar")
async def personal_editar(request: Request, pid: int, nombre: str = Form(...)):
    user = _require_superuser(request)
    if not user:
        return RedirectResponse("/admin/usuarios?msg=sin_permiso", status_code=303)
    nombre = nombre.strip().upper()
    if not nombre:
        return RedirectResponse("/admin/usuarios?msg=vacio", status_code=303)
    conn = get_db()
    conn.execute("UPDATE personal_oficina SET nombre=? WHERE id=?", (nombre, pid))
    conn.commit()
    registrar_log(user, "personal_editar", "admin", f"Persona actualizada id={pid}: '{nombre}'",
                  request.client.host if request.client else None)
    conn.close()
    return RedirectResponse("/admin/usuarios?msg=personal_ok#personal-oficina", status_code=303)


@router.post("/personal/{pid}/eliminar")
async def personal_eliminar(request: Request, pid: int):
    user = _require_superuser(request)
    if not user:
        return RedirectResponse("/admin/usuarios?msg=sin_permiso", status_code=303)
    conn = get_db()
    conn.execute("DELETE FROM personal_oficina WHERE id=?", (pid,))
    conn.commit()
    registrar_log(user, "personal_eliminar", "admin", f"Persona eliminada id={pid}",
                  request.client.host if request.client else None)
    conn.close()
    return RedirectResponse("/admin/usuarios?msg=personal_ok#personal-oficina", status_code=303)


@router.post("/personal/{pid}/toggle-activo")
async def personal_toggle_activo(request: Request, pid: int):
    user = _require_superuser(request)
    if not user:
        return RedirectResponse("/admin/usuarios?msg=sin_permiso", status_code=303)
    conn = get_db()
    row = conn.execute("SELECT nombre, activo FROM personal_oficina WHERE id=?", (pid,)).fetchone()
    if row:
        new_val = 0 if row["activo"] else 1
        conn.execute("UPDATE personal_oficina SET activo=? WHERE id=?", (new_val, pid))
        conn.commit()
        registrar_log(user, "personal_toggle", "admin",
                      f"'{row['nombre']}' activo → {new_val}",
                      request.client.host if request.client else None)
    conn.close()
    return RedirectResponse("/admin/usuarios?msg=personal_ok#personal-oficina", status_code=303)


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
