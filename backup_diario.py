"""
Copia de seguridad diaria — Sistema OCDI
=========================================
Crea un ZIP con la base de datos (snapshot consistente via sqlite3.backup) y
los archivos de referencia JSON. Conserva los últimos MAX_BACKUPS archivos.
Registra cada operación en backup_log.txt dentro de la carpeta de backup.

Uso manual : python backup_diario.py
Automático : Tarea programada de Windows (ver configurar_tarea_backup.bat)
             Lunes a Viernes, 4:00 PM
"""

import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
DIRECTORIO_APP    = Path(__file__).resolve().parent
BASE_DATOS        = DIRECTORIO_APP / "data" / "ocdi.db"
DIRECTORIO_BACKUP = Path(
    r"G:\Mi unidad\5) DOCUMENTOS PARA CONSEGUIR TRABAJO"
    r"\Simo\Soportes_SDS\BACKUP_APP_OCDI\Backup_Automatico_OCDI"
)
MAX_BACKUPS       = 30   # cantidad de ZIPs que se conservan

# Archivos de referencia adicionales (no versionados en git)
ARCHIVOS_EXTRA = [
    DIRECTORIO_APP / "Tipologias_Json.txt",
    DIRECTORIO_APP / "EntidadesDependencias_Json.txt",
]
# ──────────────────────────────────────────────────────────────────────────────


def main() -> int:
    ahora = datetime.now()
    ts     = ahora.strftime("%Y%m%d_%H%M%S")
    prefijo = f"[{ahora.strftime('%Y-%m-%d %H:%M:%S')}]"

    # 1. Verificar que la base de datos existe
    if not BASE_DATOS.exists():
        msg = f"{prefijo} ERROR — No se encontró la base de datos: {BASE_DATOS}"
        print(msg)
        _escribir_log(msg)
        return 1

    # 2. Crear carpeta de destino si no existe
    try:
        DIRECTORIO_BACKUP.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        msg = f"{prefijo} ERROR — No se pudo crear la carpeta de backup: {e}"
        print(msg)
        _escribir_log(msg)
        return 1

    # 3. Crear snapshot consistente de la BD con sqlite3.backup()
    #    (seguro en WAL mode — shutil.copy2 puede generar archivos corruptos)
    tmp_db = DIRECTORIO_BACKUP / f"_tmp_ocdi_{ts}.db"
    try:
        src = sqlite3.connect(str(BASE_DATOS))
        dst = sqlite3.connect(str(tmp_db))
        src.backup(dst)
        dst.close()
        src.close()
    except Exception as e:
        msg = f"{prefijo} ERROR — Fallo al crear snapshot de la BD: {e}"
        print(msg)
        _escribir_log(msg)
        tmp_db.unlink(missing_ok=True)
        return 1

    # 4. Empaquetar en ZIP (BD + archivos extra)
    zip_path = DIRECTORIO_BACKUP / f"ocdi_backup_{ts}.zip"
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmp_db, "ocdi.db")
            for extra in ARCHIVOS_EXTRA:
                if extra.exists():
                    zf.write(extra, extra.name)
                    print(f"  Incluido: {extra.name}")
                else:
                    print(f"  AVISO: archivo no encontrado (omitido): {extra.name}")
    except Exception as e:
        msg = f"{prefijo} ERROR — Fallo al crear ZIP: {e}"
        print(msg)
        _escribir_log(msg)
        zip_path.unlink(missing_ok=True)
        return 1
    finally:
        tmp_db.unlink(missing_ok=True)

    tamaño_kb = zip_path.stat().st_size // 1024

    # 5. Verificación: abrir el ZIP y confirmar que ocdi.db tiene tablas
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            with zf.open("ocdi.db") as f:
                data = f.read()
        tmp_verify = DIRECTORIO_BACKUP / f"_verify_{ts}.db"
        tmp_verify.write_bytes(data)
        conn = sqlite3.connect(str(tmp_verify))
        n_tablas = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        conn.close()
        tmp_verify.unlink(missing_ok=True)
        if n_tablas < 5:
            msg = f"{prefijo} ERROR — Verificación fallida: solo {n_tablas} tablas en el backup"
            print(msg)
            _escribir_log(msg)
            return 1
    except Exception as e:
        msg = f"{prefijo} ERROR — Verificación del backup fallida: {e}"
        print(msg)
        _escribir_log(msg)
        return 1

    linea_ok = (
        f"{prefijo} OK — {zip_path.name}  ({tamaño_kb} KB, {n_tablas} tablas)"
    )
    print(linea_ok)

    # 6. Eliminar backups que superan el límite
    backups = sorted(DIRECTORIO_BACKUP.glob("ocdi_backup_*.zip"), reverse=True)
    eliminados = []
    for viejo in backups[MAX_BACKUPS:]:
        try:
            viejo.unlink()
            eliminados.append(viejo.name)
        except Exception:
            pass
    if eliminados:
        print(f"  Eliminados {len(eliminados)} backup(s) antiguo(s).")

    # 7. Escribir log
    _escribir_log(linea_ok)
    if eliminados:
        _escribir_log(f"  Eliminados: {', '.join(eliminados)}")

    print(f"\n✅ Backup guardado en:\n   {zip_path}")
    print("   Se sincroniza automáticamente con Google Drive en la nube.")
    return 0


def _escribir_log(linea: str):
    try:
        log = DIRECTORIO_BACKUP / "backup_log.txt"
        with open(log, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
