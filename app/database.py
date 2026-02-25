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
    conn.commit()
    conn.close()


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
