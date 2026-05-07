import sqlite3
from pathlib import Path
from datetime import date, timedelta

DB_PATH = Path(__file__).parent.parent / "data" / "ocdi.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS expedientes (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    n_expediente                    TEXT NOT NULL,
    anio                            INTEGER,
    mes                             TEXT,
    medio_ingreso                   TEXT,
    n_radicado                      TEXT,
    fecha_radicado                  TEXT,
    abogado_asignado                TEXT,
    entidad_origen                  TEXT,
    quejoso                         TEXT,
    asunto                          TEXT,
    impedimento                     TEXT DEFAULT 'NO',
    fecha_apertura_expediente       TEXT,
    numero_auto_apertura_ind        TEXT,
    fecha_auto_apertura_ind         TEXT,
    tipo_expediente                 TEXT,
    tipologia                       TEXT,
    relacionado_siniestro           TEXT DEFAULT 'NO',
    responsable_siniestro           TEXT,
    relacionado_maltrato            TEXT DEFAULT 'NO',
    relacionado_corrupcion          TEXT DEFAULT 'NO',
    valores_institucionales         TEXT,
    fecha_hechos_obs                TEXT,
    fecha_hechos                    TEXT,
    fecha_ultima_act_indagacion     TEXT,
    numero_auto_ultima_act_ind      TEXT,
    fecha_apertura_investigacion    TEXT,
    numero_auto_apertura_inv        TEXT,
    nombre_investigado              TEXT,
    cedula                          TEXT,
    perfil_investigado              TEXT,
    area_origen_investigado         TEXT,
    fecha_prorroga                  TEXT,
    numero_auto_prorroga            TEXT,
    tiempo_prorroga                 TEXT,
    fecha_ultima_act_investigacion  TEXT,
    numero_auto_ultima_act_inv      TEXT,
    numero_auto_traslado            TEXT,
    fecha_auto_traslado             TEXT,
    numero_auto_acumulacion         TEXT,
    fecha_auto_acumulacion          TEXT,
    expediente_acumula              TEXT,
    fecha_auto_archivo              TEXT,
    numero_auto_archivo             TEXT,
    fecha_auto_pliego_cargos        TEXT,
    numero_auto_pliego_cargos       TEXT,
    etapa_actual                    TEXT,
    estado_proceso                  TEXT,
    observaciones                   TEXT,
    created_at                      TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at                      TEXT DEFAULT (datetime('now', 'localtime')),
    created_by                      TEXT
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

-- ── SEGUIMIENTO MENSUAL DE EXPEDIENTES ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS seguimiento_mensual (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    expediente_id   INTEGER NOT NULL REFERENCES expedientes(id) ON DELETE CASCADE,
    anio            INTEGER NOT NULL,
    mes             TEXT NOT NULL,
    descripcion     TEXT,
    created_by      TEXT,
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(expediente_id, anio, mes)
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

    # Migración v4: reemplazar tabla expedientes si tiene el schema antiguo
    old_cols = [r[1] for r in conn.execute("PRAGMA table_info(expedientes)").fetchall()]
    if old_cols and "ingreso_siias" in old_cols:
        conn.execute("DROP TABLE IF EXISTS escaneos")
        conn.execute("DROP TABLE IF EXISTS actuaciones")
        conn.execute("DROP TABLE IF EXISTS expedientes")
        conn.commit()

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

    # Migración: tipo de contrato por abogado
    try:
        conn.execute("ALTER TABLE usuarios ADD COLUMN tipo_contrato TEXT")
    except Exception:
        pass
    _abogados_planta = [
        "DAVID FELIPE MORALES NOGUERA",
        "JANIK HERNANDO DE LA HOZ RIOS",
        "MABEL GICELLA HURTADO SANCHEZ",
        "RODOLFO CARRILLO QUINTERO",
    ]
    _abogados_contratista = [
        "CARLOS ALFONSO PARRA MALAVER",
        "CESAR IVAN RODRIGUEZ DAMIAN",
        "MARA LUCIA UCROS MERLANO",
    ]
    for nombre in _abogados_planta:
        conn.execute(
            "UPDATE usuarios SET tipo_contrato='planta' WHERE nombre_completo=? AND tipo_contrato IS NULL",
            (nombre,),
        )
    for nombre in _abogados_contratista:
        conn.execute(
            "UPDATE usuarios SET tipo_contrato='contratista' WHERE nombre_completo=? AND tipo_contrato IS NULL",
            (nombre,),
        )

    for nombre in ["RADICADO", "CORREO ELECTRONICO", "SDQS"]:
        try:
            conn.execute("INSERT INTO corr_tipos_documento (nombre) VALUES (?)", (nombre,))
        except Exception:
            pass

    # Seed inicial de usuarios (solo si la tabla está vacía)
    if conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
        _seed_usuarios(conn)

    # Datos demo (solo si la tabla de expedientes está vacía)
    if conn.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0] == 0:
        _seed_expedientes_demo(conn)

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


def _seed_expedientes_demo(conn):
    """Inserta 3 expedientes de ejemplo para mostrar el formato de datos."""
    registros = [
        {
            "n_expediente": "001",
            "anio": 2024,
            "mes": "ENERO",
            "medio_ingreso": "RADICADO",
            "n_radicado": "2024-001-SDS",
            "fecha_radicado": "2024-01-15",
            "abogado_asignado": "MABEL GICELLA HURTADO SANCHEZ",
            "impedimento": "NO",
            "tipo_expediente": "DISCIPLINARIO",
            "nombre_investigado": "JUAN CARLOS PÉREZ LÓPEZ",
            "cedula": "12345678",
            "perfil_investigado": "SERVIDOR PÚBLICO",
            "area_origen_investigado": "SECRETARÍA DE SALUD",
            "entidad_origen": "SECRETARÍA DE SALUD DISTRITAL",
            "quejoso": "ANÓNIMO",
            "asunto": "INCUMPLIMIENTO DE FUNCIONES Y RESPONSABILIDADES EN EL CARGO DE ENFERMERO JEFE",
            "tipologia": "INCUMPLIMIENTO DE DEBERES",
            "relacionado_siniestro": "NO",
            "relacionado_maltrato": "NO",
            "relacionado_corrupcion": "NO",
            "valores_institucionales": "RESPONSABILIDAD",
            "fecha_hechos_obs": "2023-11-20",
            "fecha_hechos": "2023-11-20",
            "fecha_apertura_expediente": "2024-01-15",
            "numero_auto_apertura_ind": "AUTO-001-2024",
            "fecha_auto_apertura_ind": "2024-01-15",
            "etapa_actual": "INDAGACIÓN PREVIA",
            "estado_proceso": "ABIERTO",
            "observaciones": "Expediente de ejemplo — indagación en curso.",
            "created_by": "SISTEMA",
        },
        {
            "n_expediente": "002",
            "anio": 2024,
            "mes": "MARZO",
            "medio_ingreso": "CORREO ELECTRÓNICO",
            "n_radicado": "2024-025-SDS",
            "fecha_radicado": "2024-03-10",
            "abogado_asignado": "CARLOS ALFONSO PARRA MALAVER",
            "impedimento": "NO",
            "tipo_expediente": "DISCIPLINARIO",
            "nombre_investigado": "MARÍA ELENA GARCÍA RODRÍGUEZ",
            "cedula": "87654321",
            "perfil_investigado": "SERVIDOR PÚBLICO",
            "area_origen_investigado": "HOSPITAL SANTA CLARA",
            "entidad_origen": "HOSPITAL SANTA CLARA E.S.E.",
            "quejoso": "PEDRO RUIZ MARTÍNEZ",
            "asunto": "TRATO INDEBIDO Y MALTRATO A USUARIOS DEL SERVICIO DE URGENCIAS",
            "tipologia": "MALTRATO",
            "relacionado_siniestro": "NO",
            "relacionado_maltrato": "SI",
            "relacionado_corrupcion": "NO",
            "valores_institucionales": "RESPETO",
            "fecha_hechos_obs": "2024-02-15",
            "fecha_hechos": "2024-02-15",
            "fecha_apertura_expediente": "2024-03-10",
            "numero_auto_apertura_ind": "AUTO-025-2024",
            "fecha_auto_apertura_ind": "2024-03-10",
            "fecha_ultima_act_indagacion": "2024-05-20",
            "numero_auto_ultima_act_ind": "AUTO-025-A-2024",
            "fecha_apertura_investigacion": "2024-06-01",
            "numero_auto_apertura_inv": "AUTO-025-INV-2024",
            "etapa_actual": "INVESTIGACIÓN DISCIPLINARIA",
            "estado_proceso": "ABIERTO",
            "observaciones": "Expediente de ejemplo — investigación abierta por maltrato.",
            "created_by": "SISTEMA",
        },
        {
            "n_expediente": "003",
            "anio": 2023,
            "mes": "JULIO",
            "medio_ingreso": "SDQS",
            "n_radicado": "2023-089-SDS",
            "fecha_radicado": "2023-07-05",
            "abogado_asignado": "DAVID FELIPE MORALES NOGUERA",
            "impedimento": "NO",
            "tipo_expediente": "DISCIPLINARIO",
            "nombre_investigado": "CARLOS AUGUSTO MÉNDEZ TORRES",
            "cedula": "11223344",
            "perfil_investigado": "CONTRATISTA",
            "area_origen_investigado": "SUBSECRETARÍA ADMINISTRATIVA",
            "entidad_origen": "SECRETARÍA DE SALUD DISTRITAL",
            "quejoso": "AUDITORÍA INTERNA",
            "asunto": "IRREGULARIDADES EN CONTRATACIÓN Y POSIBLE CORRUPCIÓN EN PROCESO DE SELECCIÓN DE PROVEEDORES",
            "tipologia": "CORRUPCIÓN",
            "relacionado_siniestro": "NO",
            "relacionado_maltrato": "NO",
            "relacionado_corrupcion": "SI",
            "valores_institucionales": "TRANSPARENCIA, INTEGRIDAD",
            "fecha_hechos_obs": "2023-05-10",
            "fecha_hechos": "2023-05-10",
            "fecha_apertura_expediente": "2023-07-05",
            "numero_auto_apertura_ind": "AUTO-089-2023",
            "fecha_auto_apertura_ind": "2023-07-05",
            "fecha_ultima_act_indagacion": "2023-09-15",
            "numero_auto_ultima_act_ind": "AUTO-089-A-2023",
            "fecha_apertura_investigacion": "2023-10-01",
            "numero_auto_apertura_inv": "AUTO-089-INV-2023",
            "fecha_ultima_act_investigacion": "2024-01-20",
            "numero_auto_ultima_act_inv": "AUTO-089-INV-A-2023",
            "fecha_auto_archivo": "2024-02-01",
            "numero_auto_archivo": "AUTO-089-ARCH-2024",
            "etapa_actual": "ARCHIVO",
            "estado_proceso": "AUTO DE ARCHIVO",
            "observaciones": "Expediente de ejemplo — archivado por prescripción de la acción disciplinaria.",
            "created_by": "SISTEMA",
        },
    ]

    campos = [
        "n_expediente", "anio", "mes", "medio_ingreso", "n_radicado", "fecha_radicado",
        "abogado_asignado", "impedimento", "tipo_expediente", "nombre_investigado", "cedula",
        "perfil_investigado", "area_origen_investigado", "entidad_origen", "quejoso", "asunto",
        "tipologia", "relacionado_siniestro", "relacionado_maltrato", "relacionado_corrupcion",
        "valores_institucionales", "fecha_hechos_obs", "fecha_hechos", "fecha_apertura_expediente",
        "numero_auto_apertura_ind", "fecha_auto_apertura_ind", "fecha_ultima_act_indagacion",
        "numero_auto_ultima_act_ind", "fecha_apertura_investigacion", "numero_auto_apertura_inv",
        "fecha_ultima_act_investigacion", "numero_auto_ultima_act_inv",
        "fecha_auto_archivo", "numero_auto_archivo",
        "etapa_actual", "estado_proceso", "observaciones", "created_by",
    ]
    placeholders = ", ".join("?" * len(campos))
    cols = ", ".join(campos)
    sql = f"INSERT INTO expedientes ({cols}) VALUES ({placeholders})"
    for r in registros:
        vals = [r.get(c) for c in campos]
        conn.execute(sql, vals)


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
