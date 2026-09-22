import hashlib
import secrets
from fastapi import Request

# ── Módulos del sistema y sus etiquetas ───────────────────────────────────────

MODULOS_SISTEMA = [
    ("expedientes",     "📁 Base Expedientes"),
    ("control_autos",   "⚖️ Control de Autos"),
    ("correspondencia", "📋 Correspondencia"),
    ("digitales",       "💻 Exp. Digitales"),
    ("sala",            "🗓️ Sala de Audiencias"),
    ("backup",          "📦 Backup"),
    ("sdqs",            "📩 SDQS"),
    ("equipos",         "💻 Préstamo de Equipos"),
    ("matriz",          "🗂️ Matriz de Seguimiento (Abogados)"),
    ("compensatorios",  "⏱️ Compensatorios Fin de Año"),
]

# Roles que siempre tienen acceso completo (no configurables por módulo)
ROLES_SUPERUSUARIO = {"admin", "jefe"}

# Roles que tienen acceso de escritura por defecto (pero configurable)
ROLES_ESCRITURA_DEFAULT = {"secretario", "auxiliar"}

# ── Hashing de contraseñas ────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Genera hash seguro usando PBKDF2-HMAC-SHA256 con salt aleatorio."""
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 260_000
    )
    return f"{salt}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Compara contraseña en texto plano contra el hash almacenado."""
    try:
        salt, h = stored.split("$", 1)
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 260_000
        )
        return secrets.compare_digest(candidate.hex(), h)
    except Exception:
        return False


def new_token() -> str:
    """Genera un token de sesión criptográficamente seguro."""
    return secrets.token_urlsafe(32)


# ── Política de contraseñas (SDS-TIC-LN-016 §5.4.2.d) ─────────────────────────
# Mínimo 12 caracteres (el lineamiento acepta 8 como piso absoluto, pero exige
# combinar las 4 clases de carácter; se fija 12 para cumplir de una vez el
# nivel "recomendado" y no dejarlo como deuda pendiente).

import re as _re

LONGITUD_MINIMA_PASSWORD = 12


def validar_politica_password(password: str) -> str | None:
    """Valida la política de contraseñas. Retorna None si cumple, o un mensaje
    de error legible para mostrar al usuario si no cumple."""
    if len(password) < LONGITUD_MINIMA_PASSWORD:
        return f"La contraseña debe tener mínimo {LONGITUD_MINIMA_PASSWORD} caracteres."
    if not _re.search(r"[A-ZÁÉÍÓÚÑ]", password):
        return "La contraseña debe incluir al menos una mayúscula."
    if not _re.search(r"[a-záéíóúñ]", password):
        return "La contraseña debe incluir al menos una minúscula."
    if not _re.search(r"[0-9]", password):
        return "La contraseña debe incluir al menos un número."
    if not _re.search(r"[^A-Za-z0-9]", password):
        return "La contraseña debe incluir al menos un carácter especial."
    return None


# ── Bloqueo por intentos fallidos (SDS-TIC-LN-016 §5.4.2.d, fuerza bruta) ─────

MAX_INTENTOS_FALLIDOS = 5
MINUTOS_BLOQUEO = 15


def cuenta_bloqueada(user: dict) -> int:
    """Si la cuenta está bloqueada por intentos fallidos, retorna los minutos
    restantes de bloqueo (>=1). Si no está bloqueada, retorna 0."""
    from datetime import datetime
    hasta = user.get("bloqueado_hasta") if isinstance(user, dict) else user["bloqueado_hasta"]
    if not hasta:
        return 0
    try:
        restante = datetime.fromisoformat(hasta) - datetime.now()
    except (ValueError, TypeError):
        return 0
    segundos = restante.total_seconds()
    if segundos <= 0:
        return 0
    return max(1, int(segundos // 60) + 1)


def registrar_intento_fallido(conn, user_id: int) -> int:
    """Incrementa el contador de intentos fallidos de un usuario; si alcanza el
    máximo, bloquea la cuenta por MINUTOS_BLOQUEO minutos.

    Si el bloqueo anterior ya expiró, el contador arranca de cero antes de
    incrementar — si no, un solo intento fallido (p.ej. un error de tipeo)
    justo después de expirar el bloqueo anterior volvería a bloquear la
    cuenta de inmediato, dejando al usuario legítimo con una sola oportunidad
    por ventana de 15 minutos para siempre.

    Retorna MINUTOS_BLOQUEO si este intento fue el que disparó el bloqueo
    (para poder avisarle al usuario de inmediato en vez de esperar a su
    siguiente intento), o 0 si el intento solo quedó registrado."""
    from datetime import datetime, timedelta
    row = conn.execute(
        "SELECT intentos_fallidos, bloqueado_hasta FROM usuarios WHERE id=?", (user_id,)
    ).fetchone()
    if not row:
        return 0

    intentos_previos = row["intentos_fallidos"] or 0
    if row["bloqueado_hasta"] and cuenta_bloqueada(dict(row)) == 0:
        intentos_previos = 0  # el bloqueo anterior ya expiró: arranca de cero

    intentos = intentos_previos + 1
    if intentos >= MAX_INTENTOS_FALLIDOS:
        hasta = (datetime.now() + timedelta(minutes=MINUTOS_BLOQUEO)).isoformat(timespec="seconds")
        conn.execute(
            "UPDATE usuarios SET intentos_fallidos=?, bloqueado_hasta=? WHERE id=?",
            (intentos, hasta, user_id),
        )
        conn.commit()
        return MINUTOS_BLOQUEO
    conn.execute(
        "UPDATE usuarios SET intentos_fallidos=?, bloqueado_hasta=NULL WHERE id=?",
        (intentos, user_id),
    )
    conn.commit()
    return 0


def resetear_intentos_fallidos(conn, user_id: int) -> None:
    """Limpia el contador de intentos fallidos y cualquier bloqueo tras un login exitoso."""
    conn.execute(
        "UPDATE usuarios SET intentos_fallidos=0, bloqueado_hasta=NULL WHERE id=?",
        (user_id,),
    )
    conn.commit()


# ── Rate limiting por IP en endpoints de login ────────────────────────────────
# Protección adicional contra fuerza bruta/fuzzing distribuido entre varios
# usuarios desde el mismo origen. Estado en memoria del proceso: la app corre
# en un único proceso uvicorn (ver iniciar.bat), por lo que no hace falta un
# almacén externo (Redis/etc.) para que el conteo sea consistente.

MAX_INTENTOS_POR_IP = 20
VENTANA_RATE_LIMIT_SEGUNDOS = 300

_intentos_por_ip: dict[str, list[float]] = {}


def rate_limit_login(ip: str | None) -> bool:
    """Registra un intento de login desde `ip` y retorna True si debe bloquearse
    (se superó el máximo de intentos en la ventana de tiempo)."""
    import time
    if not ip:
        return False
    ahora = time.monotonic()

    # Limpieza oportunista: sin esto, cada IP que alguna vez llamó a esta
    # función se queda como llave del diccionario para siempre (cada IP solo
    # poda su propia lista, nunca se borra a sí misma), creciendo sin límite
    # a lo largo de meses de actividad con múltiples IPs de origen.
    vencidas = [
        k for k, v in _intentos_por_ip.items()
        if not v or ahora - v[-1] >= VENTANA_RATE_LIMIT_SEGUNDOS
    ]
    for k in vencidas:
        del _intentos_por_ip[k]

    intentos = _intentos_por_ip.setdefault(ip, [])
    intentos[:] = [t for t in intentos if ahora - t < VENTANA_RATE_LIMIT_SEGUNDOS]
    intentos.append(ahora)
    return len(intentos) > MAX_INTENTOS_POR_IP


# ── Sesión ───────────────────────────────────────────────────────────────────

def get_session_user(request: Request) -> dict | None:
    """Retorna el dict del usuario autenticado según la cookie ocdi_session, o None."""
    from app.database import get_db
    token = request.cookies.get("ocdi_session")
    if not token:
        return None
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
    conn.close()
    return dict(row) if row else None


# ── Permisos ─────────────────────────────────────────────────────────────────

def puede_escribir(user: dict | None, modulo: str) -> bool:
    """True si el usuario tiene permiso de escritura en el módulo dado."""
    if not user:
        return False
    if user["rol"] in ROLES_SUPERUSUARIO:
        return True
    from app.database import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT puede_escribir FROM permisos_modulo WHERE user_id = ? AND modulo = ?",
        (user["id"], modulo)
    ).fetchone()
    conn.close()
    return bool(row and row["puede_escribir"])


def puede_importar(user: dict | None, modulo: str) -> bool:
    """True si el usuario tiene permiso de importación masiva en el módulo dado."""
    if not user:
        return False
    if user["rol"] in ROLES_SUPERUSUARIO:
        return True
    from app.database import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT puede_importar FROM permisos_modulo WHERE user_id = ? AND modulo = ?",
        (user["id"], modulo)
    ).fetchone()
    conn.close()
    return bool(row and row["puede_importar"])


def puede_ver(user: dict | None, modulo: str) -> bool:
    """True si el usuario tiene visibilidad del módulo dado (puede ver el tile/acceder)."""
    if not user:
        return False
    if user["rol"] in ROLES_SUPERUSUARIO:
        return True
    from app.database import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT puede_ver FROM permisos_modulo WHERE user_id = ? AND modulo = ?",
        (user["id"], modulo)
    ).fetchone()
    conn.close()
    if row is None:
        return True  # sin fila → visible por defecto
    return row["puede_ver"] != 0  # NULL o 1 → True; 0 → False


def get_permisos_usuario(user_id: int) -> dict:
    """Retorna dict {modulo: {puede_ver, puede_escribir, puede_importar}} para el usuario dado."""
    from app.database import get_db
    conn = get_db()
    rows = conn.execute(
        "SELECT modulo, puede_ver, puede_escribir, puede_importar FROM permisos_modulo WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    conn.close()
    return {
        r["modulo"]: {
            "puede_ver": r["puede_ver"] != 0,
            "puede_escribir": bool(r["puede_escribir"]),
            "puede_importar": bool(r["puede_importar"]),
        }
        for r in rows
    }


# ── Contexto de template ─────────────────────────────────────────────────────

def tpl(request: Request, modulo: str | None = None, **kwargs) -> dict:
    """
    Construye el contexto de template inyectando current_user, puede_escribir y permisos.
    Usar en todos los endpoints que renderizan templates.
    """
    user = getattr(request.state, "user", None)
    permisos = getattr(request.state, "permisos", {})
    if modulo:
        if user and user["rol"] in ROLES_SUPERUSUARIO:
            pw = True
            pi = True
        else:
            pw = permisos.get(modulo, {}).get("puede_escribir", False)
            pi = permisos.get(modulo, {}).get("puede_importar", False)
    else:
        pw = False
        pi = False
    return {
        "request": request,
        "current_user": user,
        "puede_escribir": pw,
        "puede_importar": pi,
        "permisos": permisos,
        **kwargs,
    }


# ── Logging de actividad ─────────────────────────────────────────────────────

def registrar_log(
    user: dict | None,
    accion: str,
    modulo: str | None = None,
    detalle: str | None = None,
    ip: str | None = None,
    registro_id: int | None = None,
):
    """Inserta un registro en logs_actividad. registro_id (opcional) referencia
    el id del registro afectado en su tabla de origen — permite construir un
    historial "qué cambió y cuándo" por registro individual (ver historial_registro)."""
    from app.database import get_db
    conn = get_db()
    nombre = user["nombre_completo"] if user else "Sistema"
    rol = user.get("rol") if user else None
    uid = user.get("id") if user else None
    conn.execute(
        """INSERT INTO logs_actividad
           (user_id, nombre_usuario, rol, accion, modulo, detalle, ip, registro_id)
           VALUES (?,?,?,?,?,?,?,?)""",
        (uid, nombre, rol, accion, modulo, detalle, ip, registro_id),
    )
    conn.commit()
    conn.close()


def historial_registro(conn, modulo: str, registro_id: int) -> list[dict]:
    """Devuelve el historial de acciones (crear/editar/eliminar) sobre un registro
    específico, más reciente primero. Reutiliza logs_actividad — no es una tabla
    de auditoría nueva."""
    rows = conn.execute(
        """SELECT nombre_usuario, rol, accion, detalle, created_at
           FROM logs_actividad
           WHERE modulo = ? AND registro_id = ?
           ORDER BY created_at DESC, id DESC""",
        (modulo, registro_id),
    ).fetchall()
    return [dict(r) for r in rows]
