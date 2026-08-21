"""
Copia de seguridad diaria — Sistema OCDI
=========================================
Crea un ZIP con la base de datos (snapshot consistente via sqlite3.backup) y
los archivos de referencia JSON. Conserva los últimos MAX_BACKUPS archivos.
Registra cada operación en backup_log.txt dentro de la carpeta de backup.

Uso manual : python backup_diario.py
Automático : Tarea programada de Windows (ver configurar_tarea_backup.bat)
             Lunes a Viernes, 4:00 PM  —  o desde la plataforma web
"""

import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# La consola de Windows suele usar cp1252 (no UTF-8), que no puede imprimir
# emojis como ✅ — sin esto, el script termina en error DESPUÉS de que el
# backup ya se hizo con éxito (el ZIP queda bien, pero se ve como "falló").
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
DIRECTORIO_APP    = Path(__file__).resolve().parent
BASE_DATOS        = DIRECTORIO_APP / "data" / "ocdi.db"
DIRECTORIO_BACKUP = Path(
    r"G:\Mi unidad\5) DOCUMENTOS PARA CONSEGUIR TRABAJO"
    r"\Simo\Soportes_SDS\BACKUP_APP_OCDI\Backup_Automatico_OCDI"
)
MAX_BACKUPS = 30

# Archivos de referencia adicionales (no versionados en git)
ARCHIVOS_EXTRA = [
    DIRECTORIO_APP / "Tipologias_Json.txt",
    DIRECTORIO_APP / "EntidadesDependencias_Json.txt",
]

# Archivo de control: fecha del último backup exitoso
_ULTIMO_BACKUP_FILE = DIRECTORIO_APP / "data" / "ultimo_backup.txt"
# ──────────────────────────────────────────────────────────────────────────────


def hacer_backup() -> tuple[bool, str]:
    """
    Ejecuta el backup completo. Devuelve (ok, mensaje).
    Puede ser llamado desde la línea de comandos o desde la plataforma web.
    """
    ahora   = datetime.now()
    ts      = ahora.strftime("%Y%m%d_%H%M%S")
    prefijo = f"[{ahora.strftime('%Y-%m-%d %H:%M:%S')}]"

    if not BASE_DATOS.exists():
        msg = f"{prefijo} ERROR — No se encontró la base de datos: {BASE_DATOS}"
        _escribir_log(msg)
        return False, msg

    try:
        DIRECTORIO_BACKUP.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        msg = f"{prefijo} ERROR — No se pudo crear la carpeta de backup: {e}"
        _escribir_log(msg)
        return False, msg

    # Snapshot consistente (seguro en WAL mode)
    tmp_db = DIRECTORIO_BACKUP / f"_tmp_ocdi_{ts}.db"
    try:
        src = sqlite3.connect(str(BASE_DATOS))
        dst = sqlite3.connect(str(tmp_db))
        src.backup(dst)
        dst.close()
        src.close()
    except Exception as e:
        msg = f"{prefijo} ERROR — Fallo al crear snapshot de la BD: {e}"
        _escribir_log(msg)
        tmp_db.unlink(missing_ok=True)
        return False, msg

    # Empaquetar en ZIP
    zip_path = DIRECTORIO_BACKUP / f"ocdi_backup_{ts}.zip"
    extras_incluidos = []
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmp_db, "ocdi.db")
            for extra in ARCHIVOS_EXTRA:
                if extra.exists():
                    zf.write(extra, extra.name)
                    extras_incluidos.append(extra.name)
    except Exception as e:
        msg = f"{prefijo} ERROR — Fallo al crear ZIP: {e}"
        _escribir_log(msg)
        zip_path.unlink(missing_ok=True)
        return False, msg
    finally:
        tmp_db.unlink(missing_ok=True)

    tamaño_kb = zip_path.stat().st_size // 1024

    # Verificación
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            data = zf.read("ocdi.db")
        tmp_verify = DIRECTORIO_BACKUP / f"_verify_{ts}.db"
        tmp_verify.write_bytes(data)
        conn = sqlite3.connect(str(tmp_verify))
        n_tablas = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        conn.close()
        tmp_verify.unlink(missing_ok=True)
        if n_tablas < 5:
            msg = f"{prefijo} ERROR — Verificación fallida: solo {n_tablas} tablas"
            _escribir_log(msg)
            return False, msg
    except Exception as e:
        msg = f"{prefijo} ERROR — Verificación del backup fallida: {e}"
        _escribir_log(msg)
        return False, msg

    linea_ok = (
        f"{prefijo} OK — {zip_path.name}  ({tamaño_kb} KB, {n_tablas} tablas)"
    )

    # Rotar backups antiguos
    backups = sorted(DIRECTORIO_BACKUP.glob("ocdi_backup_*.zip"), reverse=True)
    eliminados = []
    for viejo in backups[MAX_BACKUPS:]:
        try:
            viejo.unlink()
            eliminados.append(viejo.name)
        except Exception:
            pass

    _escribir_log(linea_ok)
    if eliminados:
        _escribir_log(f"  Eliminados: {', '.join(eliminados)}")

    # Registrar fecha del último backup exitoso
    try:
        _ULTIMO_BACKUP_FILE.write_text(ahora.strftime("%Y-%m-%d"), encoding="utf-8")
    except Exception:
        pass

    resumen = f"Backup OK — {zip_path.name} ({tamaño_kb} KB)"
    if extras_incluidos:
        resumen += f" · Incluye: {', '.join(extras_incluidos)}"
    return True, resumen


def _escribir_log(linea: str):
    try:
        log = DIRECTORIO_BACKUP / "backup_log.txt"
        with open(log, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except Exception:
        pass


def main() -> int:
    ok, msg = hacer_backup()
    print(msg)
    if ok:
        print(f"\n✅ Backup guardado en:\n   {DIRECTORIO_BACKUP}")
        print("   Se sincroniza automáticamente con Google Drive en la nube.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
