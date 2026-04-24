import sqlite3
from pathlib import Path
from datetime import date, timedelta

DB_PATH = Path(__file__).parent.parent / "data" / "ocdi.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS expedientes (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Bloque 1: Identificacion
    n_expediente                TEXT NOT NULL,
    anio                        INTEGER,
    mes                         TEXT,
    origen_proceso              TEXT,
    n_radicado                  TEXT,
    fecha_radicado              TEXT,
    fecha_siias                 TEXT,
    ingreso_siias               TEXT DEFAULT 'NO',
    ingreso_siad                TEXT DEFAULT 'NO',
    fecha_ingreso_siad          TEXT,
    ingreso_sid4                TEXT DEFAULT 'NO',

    -- Bloque 2: Asignacion y partes
    nombre_abogado              TEXT,
    impedimento                 TEXT DEFAULT 'NO',
    investigado                 TEXT,
    perfil_indagado             TEXT,
    entidad_origen              TEXT,
    quejoso                     TEXT,

    -- Bloque 3: Asunto y tipologia
    asunto                      TEXT,
    tipologia                   TEXT,
    descripcion_tipologia       TEXT,
    relacionado_siniestro       TEXT DEFAULT 'NO',
    responsable_siniestro       TEXT,
    relacionado_acoso           TEXT DEFAULT 'NO',
    responsable_acoso           TEXT,
    relacionado_corrupcion      TEXT DEFAULT 'NO',
    valores_institucionales     TEXT,
    fecha_hechos                TEXT,

    -- Bloque 4: Indagacion Previa
    fecha_apertura_indagacion   TEXT,
    numero_auto_apertura_ind    TEXT,
    fecha_auto_apertura_ind     TEXT,
    plazo_ind                   INTEGER DEFAULT 180,
    fecha_vencimiento_ind       TEXT,
    numero_auto_traslado_ind    TEXT,
    fecha_auto_traslado_ind     TEXT,
    numero_auto_archivo_ind     TEXT,
    fecha_auto_archivo_ind      TEXT,

    -- Bloque 5: Investigacion Disciplinaria (condicional)
    fecha_apertura_investigacion TEXT,
    numero_auto_apertura_inv    TEXT,
    fecha_auto_apertura_inv     TEXT,
    plazo_inv                   INTEGER DEFAULT 180,
    fecha_vencimiento_inv       TEXT,
    numero_auto_traslado_inv    TEXT,
    fecha_auto_traslado_inv     TEXT,
    numero_auto_archivo_inv     TEXT,
    fecha_auto_archivo_inv      TEXT,

    -- Bloque 6: Cierre
    etapa                       TEXT,
    estado_proceso              TEXT,
    observaciones_finales       TEXT,

    -- Metadata
    created_at                  TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at                  TEXT DEFAULT (datetime('now', 'localtime')),
    created_by                  TEXT
);

CREATE TABLE IF NOT EXISTS escaneos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    expediente_id   INTEGER NOT NULL,
    fecha_escaner   TEXT,
    folio           TEXT,
    responsable     TEXT,
    FOREIGN KEY (expediente_id) REFERENCES expedientes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS actuaciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    expediente_id   INTEGER NOT NULL,
    mes             TEXT,
    anio            INTEGER,
    descripcion     TEXT,
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    created_by      TEXT,
    FOREIGN KEY (expediente_id) REFERENCES expedientes(id) ON DELETE CASCADE
);

-- ── ABOGADOS DIGITALES ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS abogados_digitales (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE
);

-- ── EXPEDIENTES DIGITALES ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS exp_digitales (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    n_expediente        TEXT,
    anio                INTEGER,
    abogado             TEXT,
    etapa               TEXT,
    queja_inicial       TEXT DEFAULT 'No',
    radicado_auto       TEXT,
    nombre_auto         TEXT,
    fecha_auto          TEXT,
    observaciones       TEXT,
    created_at          TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS exp_comunicaciones (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    exp_digital_id          INTEGER NOT NULL REFERENCES exp_digitales(id) ON DELETE CASCADE,
    radicado_comunicacion   TEXT,
    dependencia             TEXT,
    fecha_envio             TEXT,
    fecha_seguimiento       TEXT,
    radicado_respuesta      TEXT,
    fecha_respuesta         TEXT,
    responsable             TEXT,
    observaciones           TEXT,
    created_at              TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS exp_revisiones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    exp_digital_id  INTEGER NOT NULL REFERENCES exp_digitales(id) ON DELETE CASCADE,
    fecha_revision  TEXT DEFAULT (datetime('now', 'localtime'))
);

-- ── SALA DE AUDIENCIAS ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sala_agenda (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           TEXT NOT NULL,
    franja          TEXT NOT NULL,
    titulo          TEXT,
    descripcion     TEXT,
    estado          TEXT DEFAULT 'Ocupado',
    responsable     TEXT,
    created_at      TEXT DEFAULT (datetime('now', 'localtime'))
);

-- ── CONTROL DE AUTOS DE SUSTANCIACIÓN Y/O TRÁMITES ──────────────────────────
CREATE TABLE IF NOT EXISTS control_autos_sustanciacion (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    expediente          TEXT,
    numero_auto         TEXT,
    fecha_auto          TEXT,
    asunto_auto         TEXT,
    abogado_responsable TEXT,
    observaciones       TEXT,
    created_at          TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT DEFAULT (datetime('now', 'localtime')),
    created_by          TEXT
);

-- ── AUTENTICACIÓN Y AUDITORÍA ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT UNIQUE,
    password_hash   TEXT,
    nombre_completo TEXT NOT NULL,
    rol             TEXT NOT NULL CHECK(rol IN ('admin','jefe','secretario','auxiliar','abogado')),
    activo          INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS sesiones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token       TEXT UNIQUE NOT NULL,
    user_id     INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    created_at  TEXT DEFAULT (datetime('now', 'localtime')),
    last_seen   TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS permisos_modulo (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    modulo          TEXT NOT NULL,
    puede_escribir  INTEGER DEFAULT 0,
    UNIQUE(user_id, modulo)
);

CREATE TABLE IF NOT EXISTS logs_actividad (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER,
    nombre_usuario  TEXT NOT NULL,
    rol             TEXT,
    accion          TEXT NOT NULL,
    modulo          TEXT,
    detalle         TEXT,
    ip              TEXT,
    created_at      TEXT DEFAULT (datetime('now', 'localtime'))
);

-- ── CORRESPONDENCIA / LISTA DE REPARTO DE ABOGADOS ───────────────────────────
CREATE TABLE IF NOT EXISTS correspondencia (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    anio                    INTEGER,
    mes                     TEXT,
    fecha_ingreso           TEXT,
    n_radicado              TEXT,
    origen                  TEXT,
    asunto                  TEXT,
    tipo_documento          TEXT,
    responsable             TEXT,
    caso_bmp                TEXT,
    fecha_radicado_salida   TEXT,
    tipo_respuesta          TEXT,
    tramite_salida          TEXT,
    correo_remitente        TEXT,
    sinproc_personeria      TEXT,
    tipo_requerimiento      TEXT,
    termino_dias            INTEGER,
    created_at              TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at              TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS correspondencia_radicados_salida (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    correspondencia_id  INTEGER NOT NULL REFERENCES correspondencia(id) ON DELETE CASCADE,
    radicado            TEXT NOT NULL,
    url                 TEXT,
    created_at          TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS corr_responsables (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS corr_tipos_documento (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE
);
"""


def get_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    # Migraciones: agregar columnas nuevas a tablas existentes
    try:
        conn.execute("ALTER TABLE exp_digitales ADD COLUMN observaciones TEXT")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE correspondencia ADD COLUMN correo_remitente TEXT")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE correspondencia ADD COLUMN sinproc_personeria TEXT")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE correspondencia ADD COLUMN tipo_requerimiento TEXT")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE correspondencia ADD COLUMN termino_dias INTEGER")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE correspondencia_radicados_salida ADD COLUMN url TEXT")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE permisos_modulo ADD COLUMN puede_ver INTEGER DEFAULT 1")
    except Exception:
        pass
    # Migrar corr_responsables a nombres completos oficiales
    nombres_completos = [
        "ANDRES EDUARDO SANDOVAL MAYORGA",
        "CARLOS ALFONSO PARRA MALAVER",
        "CESAR IVAN RODRIGUEZ DAMIAN",
        "DAVID FELIPE MORALES NOGUERA",
        "JANIK HERNANDO DE LA HOZ RIOS",
        "JOSE DE JESUS BARAJAS SOTELO",
        "LUNA GICELL GUZMAN YATE",
        "MABEL GICELLA HURTADO SANCHEZ",
        "MAGDA XIMENA PAREDES LIEVANO",
        "MARA LUCIA UCROS MERLANO",
        "MARTHA PATRICIA AÑEZ MAESTRE",
        "RODOLFO CARRILLO QUINTERO",
        "TODOS LOS PROFESIONALES",
    ]
    conn.execute("DELETE FROM corr_responsables")
    for nombre in nombres_completos:
        try:
            conn.execute("INSERT INTO corr_responsables (nombre) VALUES (?)", (nombre,))
        except Exception:
            pass
    # Normalizar responsables en registros existentes de correspondencia
    responsables_map = [
        ("ANDRES SANDOVAL",             "ANDRES EDUARDO SANDOVAL MAYORGA"),
        ("ANDRES EDUARDO SANDOVAL",     "ANDRES EDUARDO SANDOVAL MAYORGA"),
        ("CARLOS PARRA",                "CARLOS ALFONSO PARRA MALAVER"),
        ("CARLOS ALFONSO PARRA",        "CARLOS ALFONSO PARRA MALAVER"),
        ("CESAR IVAN",                  "CESAR IVAN RODRIGUEZ DAMIAN"),
        ("CESAR IVAN RODRIGUEZ",        "CESAR IVAN RODRIGUEZ DAMIAN"),
        ("CESAR RODRIGUEZ",             "CESAR IVAN RODRIGUEZ DAMIAN"),
        ("DAVID FELIPE  MORALES",       "DAVID FELIPE MORALES NOGUERA"),
        ("DAVID FELIPE MORALES",        "DAVID FELIPE MORALES NOGUERA"),
        ("DAVID MORALES",               "DAVID FELIPE MORALES NOGUERA"),
        ("DE LA HOZ",                   "JANIK HERNANDO DE LA HOZ RIOS"),
        ("JANIK DE LA HOZ",             "JANIK HERNANDO DE LA HOZ RIOS"),
        ("JANIK HERNANDO DE LA HOZ",    "JANIK HERNANDO DE LA HOZ RIOS"),
        ("JOSE BARAJAS",                "JOSE DE JESUS BARAJAS SOTELO"),
        ("LUNA GUZMAN",                 "LUNA GICELL GUZMAN YATE"),
        ("LUNA GICELL GUZMAN",          "LUNA GICELL GUZMAN YATE"),
        ("MABEL HURTADO",               "MABEL GICELLA HURTADO SANCHEZ"),
        ("MABEL GICELLA HURTADO",       "MABEL GICELLA HURTADO SANCHEZ"),
        ("GICELLA HURTADO",             "MABEL GICELLA HURTADO SANCHEZ"),
        ("MABEL GICELA HURTADO SANCHEZ","MABEL GICELLA HURTADO SANCHEZ"),
        ("MAGDA PAREDES",               "MAGDA XIMENA PAREDES LIEVANO"),
        ("MAGDA XIMENA PAREDES",        "MAGDA XIMENA PAREDES LIEVANO"),
        ("MARA UCROS",                  "MARA LUCIA UCROS MERLANO"),
        ("MARA LUCIA UCROS",            "MARA LUCIA UCROS MERLANO"),
        ("MARTHA AÑEZ",                 "MARTHA PATRICIA AÑEZ MAESTRE"),
        ("MARTHA PATRICIA AÑEZ",        "MARTHA PATRICIA AÑEZ MAESTRE"),
        ("RODOLFO CARRILLO",             "RODOLFO CARRILLO QUINTERO"),
        ("TODOS LO PROFESIONALES",      "TODOS LOS PROFESIONALES"),
    ]
    for old, new in responsables_map:
        conn.execute(
            "UPDATE correspondencia SET responsable=? WHERE UPPER(TRIM(responsable))=?",
            (new, old.upper()),
        )

    # Normalizar origen y asunto a mayúsculas en todos los registros históricos
    conn.execute("UPDATE correspondencia SET origen = UPPER(origen) WHERE origen IS NOT NULL AND origen != UPPER(origen)")
    conn.execute("UPDATE correspondencia SET asunto = UPPER(asunto) WHERE asunto IS NOT NULL AND asunto != UPPER(asunto)")

    for nombre in ["RADICADO", "CORREO ELECTRONICO", "SDQS"]:
        try:
            conn.execute("INSERT INTO corr_tipos_documento (nombre) VALUES (?)", (nombre,))
        except Exception:
            pass

    # Seed inicial de usuarios (solo si la tabla está vacía)
    if conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
        _seed_usuarios(conn)

    conn.commit()
    conn.close()


def _seed_usuarios(conn):
    """Crea los usuarios iniciales del sistema con contraseñas hasheadas."""
    from app.auth_utils import hash_password, MODULOS_SISTEMA

    # (username, password_plaintext, nombre_completo, rol)
    usuarios_credencial = [
        ("Admin",           "Admin@OCDI#Ing",   "JOSE DE JESUS BARAJAS SOTELO",    "admin"),
        ("JefeOficinaOcdi", "OCDI@Jefe#Martha", "MARTHA PATRICIA AÑEZ MAESTRE",    "jefe"),
        ("Secretario1",     "SDS@2026#.And",    "ANDRES EDUARDO SANDOVAL MAYORGA", "secretario"),
        ("Secretario2",     "SDS@2026#*Mag",    "MAGDA XIMENA PAREDES LIEVANO",    "secretario"),
        ("AuxSecretario",   "SDS@2026#_Lun",    "LUNA GICELL GUZMAN YATE",         "auxiliar"),
    ]
    # Abogados (sin contraseña, solo seleccionan su nombre)
    abogados = [
        "CARLOS ALFONSO PARRA MALAVER",
        "CESAR IVAN RODRIGUEZ DAMIAN",
        "DAVID FELIPE MORALES NOGUERA",
        "JANIK HERNANDO DE LA HOZ RIOS",
        "MABEL GICELLA HURTADO SANCHEZ",
        "MARA LUCIA UCROS MERLANO",
        "RODOLFO CARRILLO QUINTERO",
    ]

    modulos = [m for m, _ in MODULOS_SISTEMA]

    for username, pwd, nombre, rol in usuarios_credencial:
        cur = conn.execute(
            "INSERT INTO usuarios (username, password_hash, nombre_completo, rol) VALUES (?,?,?,?)",
            (username, hash_password(pwd), nombre, rol),
        )
        uid = cur.lastrowid
        # admin y jefe no necesitan filas de permisos (bypasean la verificación)
        if rol not in ("admin", "jefe"):
            for modulo in modulos:
                conn.execute(
                    "INSERT INTO permisos_modulo (user_id, modulo, puede_escribir, puede_ver) VALUES (?,?,1,1)",
                    (uid, modulo),
                )

    for nombre in abogados:
        cur = conn.execute(
            "INSERT INTO usuarios (username, password_hash, nombre_completo, rol) VALUES (?,?,?,?)",
            (None, None, nombre, "abogado"),
        )
        uid = cur.lastrowid
        for modulo in modulos:
            conn.execute(
                "INSERT INTO permisos_modulo (user_id, modulo, puede_escribir, puede_ver) VALUES (?,?,0,1)",
                (uid, modulo),
            )


def calcular_alerta(fecha_vencimiento: str | None) -> dict:
    """Retorna dias restantes y clase CSS de alerta para una fecha de vencimiento."""
    if not fecha_vencimiento:
        return {"dias": None, "clase": "sin-plazo", "texto": "Sin plazo"}
    try:
        fv = date.fromisoformat(fecha_vencimiento)
        dias = (fv - date.today()).days
        if dias < 0:
            return {"dias": dias, "clase": "vencido", "texto": f"Vencido hace {abs(dias)} días"}
        elif dias <= 30:
            return {"dias": dias, "clase": "proximo", "texto": f"Vence en {dias} días"}
        else:
            return {"dias": dias, "clase": "vigente", "texto": f"{dias} días restantes"}
    except (ValueError, TypeError):
        return {"dias": None, "clase": "sin-plazo", "texto": "Sin plazo"}


def row_to_dict(row) -> dict:
    if row is None:
        return {}
    return dict(row)
