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


def get_permisos_usuario(user_id: int) -> dict:
    """Retorna dict {modulo: puede_escribir} para el usuario dado."""
    from app.database import get_db
    conn = get_db()
    rows = conn.execute(
        "SELECT modulo, puede_escribir FROM permisos_modulo WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    conn.close()
    return {r["modulo"]: bool(r["puede_escribir"]) for r in rows}


# ── Contexto de template ─────────────────────────────────────────────────────

def tpl(request: Request, modulo: str | None = None, **kwargs) -> dict:
    """
    Construye el contexto de template inyectando current_user y puede_escribir.
    Usar en todos los endpoints que renderizan templates.
    """
    user = getattr(request.state, "user", None)
    pw = puede_escribir(user, modulo) if modulo else False
    return {
        "request": request,
        "current_user": user,
        "puede_escribir": pw,
        **kwargs,
    }


# ── Logging de actividad ─────────────────────────────────────────────────────

def registrar_log(
    user: dict | None,
    accion: str,
    modulo: str | None = None,
    detalle: str | None = None,
    ip: str | None = None,
):
    """Inserta un registro en logs_actividad."""
    from app.database import get_db
    conn = get_db()
    nombre = user["nombre_completo"] if user else "Sistema"
    rol = user.get("rol") if user else None
    uid = user.get("id") if user else None
    conn.execute(
        """INSERT INTO logs_actividad
           (user_id, nombre_usuario, rol, accion, modulo, detalle, ip)
           VALUES (?,?,?,?,?,?,?)""",
        (uid, nombre, rol, accion, modulo, detalle, ip),
    )
    conn.commit()
    conn.close()
