"""
Copia de seguridad diaria — Sistema OCDI
=========================================
Copia ocdi.db a Google Drive con timestamp.
Conserva los últimos MAX_BACKUPS archivos y elimina los más antiguos.
Registra cada operación en backup_log.txt dentro de la carpeta de backup.

Uso manual : python backup_diario.py
Automático : Tarea programada de Windows (ver configurar_tarea_backup.bat)
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
DIRECTORIO_APP    = Path(__file__).resolve().parent
BASE_DATOS        = DIRECTORIO_APP / "data" / "ocdi.db"
DIRECTORIO_BACKUP = Path(r"G:\Mi unidad\OCDI_Backup")  # Google Drive
MAX_BACKUPS       = 30   # días que se conservan (ajustar si se desea más)
# ──────────────────────────────────────────────────────────────────────────────


def main() -> int:
    ahora = datetime.now()
    ts = ahora.strftime("%Y%m%d_%H%M%S")
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
        return 1

    # 3. Copiar la base de datos con timestamp
    destino = DIRECTORIO_BACKUP / f"ocdi_backup_{ts}.db"
    try:
        shutil.copy2(BASE_DATOS, destino)
    except Exception as e:
        msg = f"{prefijo} ERROR — Fallo al copiar: {e}"
        print(msg)
        _escribir_log(msg)
        return 1

    tamaño_kb = destino.stat().st_size // 1024
    linea_ok = f"{prefijo} OK — {destino.name}  ({tamaño_kb} KB)"
    print(linea_ok)

    # 4. Eliminar backups que superan el límite
    backups = sorted(DIRECTORIO_BACKUP.glob("ocdi_backup_*.db"), reverse=True)
    eliminados = []
    for viejo in backups[MAX_BACKUPS:]:
        try:
            viejo.unlink()
            eliminados.append(viejo.name)
        except Exception:
            pass
    if eliminados:
        print(f"  Eliminados {len(eliminados)} backup(s) antiguo(s).")

    # 5. Escribir log
    _escribir_log(linea_ok)
    if eliminados:
        _escribir_log(f"  Eliminados: {', '.join(eliminados)}")

    print(f"\n✅ Backup guardado en: {destino}")
    print(f"   Se sincronizan automáticamente con Google Drive en la nube.")
    return 0


def _escribir_log(linea: str):
    try:
        log = DIRECTORIO_BACKUP / "backup_log.txt"
        with open(log, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except Exception:
        pass  # Si el log falla, no interrumpir el backup


if __name__ == "__main__":
    sys.exit(main())
