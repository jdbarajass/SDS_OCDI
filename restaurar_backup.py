"""
Restaurar backup / Simulacro de restauración — Sistema OCDI
============================================================
Recupera el sistema a partir de un ZIP cifrado de Google Drive (los que crea
backup_diario.py) o, en modo --simulacro, comprueba que el último backup SÍ
restaura todo, sin tocar nada del sistema en uso.

Uso:
    python restaurar_backup.py --simulacro         # prueba el ZIP más reciente (no modifica nada)
    python restaurar_backup.py                     # RESTAURA el ZIP más reciente en data\\ocdi.db
    python restaurar_backup.py ruta\\archivo.zip    # restaura (o --simulacro) un ZIP concreto

Contraseña de cifrado (en este orden):
    1. variable de entorno OCDI_BACKUP_PASSWORD
    2. archivo data\\backup_password.key
    3. se pide por teclado (no se muestra al escribir)

Al restaurar:
    - Si ya existe data\\ocdi.db, NO se borra: se renombra a
      data\\ocdi_antes_de_restaurar_<fecha>.db.
    - Si no existe data\\backup_password.key, se crea con la contraseña que
      funcionó, para que los backups nuevos de este PC usen la MISMA
      contraseña que los anteriores.

Ver RESTAURACION.md para el plan de continuidad completo.
"""

import getpass
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pyzipper

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DIRECTORIO_APP = Path(__file__).resolve().parent
DATA_DIR = DIRECTORIO_APP / "data"
BD_PRODUCCION = DATA_DIR / "ocdi.db"
PASSWORD_FILE = DATA_DIR / "backup_password.key"
ARCHIVOS_EXTRA = ["Tipologias_Json.txt", "EntidadesDependencias_Json.txt"]

# Tablas que se muestran en el resumen (el resto igual se comparan todas).
TABLAS_RESUMEN = [
    ("expedientes", "Base Expedientes"),
    ("seguimiento_mensual", "Seguimiento mensual"),
    ("control_autos_sustanciacion", "Control de Autos"),
    ("correspondencia", "Control Trámites Internos"),
    ("sdqs", "SDQS"),
    ("exp_digitales", "Expedientes Digitales"),
    ("sala_agenda", "Sala de Audiencias"),
    ("prestamos_equipos", "Préstamo de Equipos"),
    ("matriz_seguimiento", "Matriz de Seguimiento"),
    ("comp_registro", "Compensatorios"),
    ("usuarios", "Usuarios"),
    ("permisos_modulo", "Permisos"),
    ("logs_actividad", "Log de actividad"),
]

# Páginas que se abren en el simulacro para confirmar que la app funciona.
PAGINAS_PRUEBA = [
    "/login", "/", "/expedientes", "/dashboard", "/control-autos/",
    "/correspondencia/", "/sdqs/", "/digitales/", "/sala/", "/equipos/",
    "/matriz/", "/compensatorios/", "/backup/", "/admin/usuarios",
]


def _directorio_backup() -> Path:
    # Misma carpeta que usa backup_diario.py (incluida la variable OCDI_BACKUP_DIR).
    sys.path.insert(0, str(DIRECTORIO_APP))
    from backup_diario import DIRECTORIO_BACKUP
    return DIRECTORIO_BACKUP


def _zip_mas_reciente() -> Path | None:
    carpeta = _directorio_backup()
    if not carpeta.exists():
        print(f"❌ No se encontró la carpeta de backups: {carpeta}")
        print("   ¿Google Drive para escritorio está instalado y con sesión iniciada?")
        print("   Si Drive quedó en otra ruta, pasa el ZIP directamente:")
        print("   python restaurar_backup.py \"ruta\\al\\ocdi_backup_AAAAMMDD_HHMMSS.zip\"")
        return None
    zips = sorted(carpeta.glob("ocdi_backup_*.zip"), reverse=True)
    if not zips:
        print(f"❌ No hay archivos ocdi_backup_*.zip en {carpeta}")
        return None
    return zips[0]


def _password_valida(zip_path: Path, password: str) -> bool:
    try:
        with pyzipper.AESZipFile(zip_path) as zf:
            zf.setpassword(password.encode("utf-8"))
            zf.read("ocdi.db")
        return True
    except Exception:
        return False


def _obtener_password(zip_path: Path) -> str | None:
    candidatas = []
    if os.environ.get("OCDI_BACKUP_PASSWORD"):
        candidatas.append(("variable OCDI_BACKUP_PASSWORD", os.environ["OCDI_BACKUP_PASSWORD"]))
    if PASSWORD_FILE.exists():
        candidatas.append((str(PASSWORD_FILE), PASSWORD_FILE.read_text(encoding="utf-8").strip()))
    for origen, pwd in candidatas:
        if _password_valida(zip_path, pwd):
            print(f"🔑 Contraseña tomada de: {origen}")
            return pwd
        print(f"⚠️  La contraseña de {origen} NO abre este backup.")
    for intento in range(3):
        pwd = getpass.getpass("🔑 Escribe la contraseña de cifrado de los backups (no se verá al escribir): ").strip()
        if _password_valida(zip_path, pwd):
            return pwd
        print("   Contraseña incorrecta.")
    print("❌ Sin la contraseña correcta no es posible abrir el backup.")
    return None


def _conteos(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        tablas = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        return {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tablas}
    finally:
        conn.close()


def _integridad(db_path: Path) -> str:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        conn.close()


# Se ejecuta en un proceso aparte con OCDI_DB_PATH apuntando a la copia, para
# que la app arranque contra esa BD y nunca contra data\ocdi.db.
_SCRIPT_ARRANQUE = r"""
import json, secrets, sqlite3, sys, os
paginas = json.loads(sys.argv[1])
res = {"init_db": False, "paginas": {}, "http": False}
from app.database import init_db, DB_PATH
init_db()
res["init_db"] = True
try:
    from fastapi.testclient import TestClient
except Exception:
    print(json.dumps(res)); sys.exit(0)
from app.main import app
conn = sqlite3.connect(str(DB_PATH))
admin = conn.execute("SELECT id FROM usuarios WHERE rol='admin' AND activo=1 LIMIT 1").fetchone()
tok = secrets.token_urlsafe(32)
if admin:
    conn.execute("INSERT INTO sesiones (token, user_id) VALUES (?,?)", (tok, admin[0])); conn.commit()
with TestClient(app) as cl:
    res["http"] = True
    for p in paginas:
        if p != "/login" and admin:
            cl.cookies.set("ocdi_session", tok)
        r = cl.get(p, follow_redirects=False)
        res["paginas"][p] = r.status_code
conn.execute("DELETE FROM sesiones WHERE token=?", (tok,)); conn.commit(); conn.close()
print(json.dumps(res))
"""


def _arrancar_app_contra(db_path: Path) -> dict | None:
    env = dict(os.environ, OCDI_DB_PATH=str(db_path))
    proc = subprocess.run(
        [sys.executable, "-c", _SCRIPT_ARRANQUE, json.dumps(PAGINAS_PRUEBA)],
        cwd=DIRECTORIO_APP, env=env, capture_output=True, text=True, encoding="utf-8",
    )
    ultima = (proc.stdout.strip().splitlines() or [""])[-1]
    try:
        return json.loads(ultima)
    except Exception:
        print("❌ La aplicación NO pudo arrancar con la base de datos restaurada:")
        print((proc.stderr or proc.stdout)[-2000:])
        return None


def _extraer(zip_path: Path, password: str, destino: Path) -> None:
    with pyzipper.AESZipFile(zip_path) as zf:
        zf.setpassword(password.encode("utf-8"))
        for nombre in ["ocdi.db"] + ARCHIVOS_EXTRA:
            if nombre in zf.namelist():
                zf.extract(nombre, destino)


def _resumen_tablas(conteos: dict[str, int], comparar: dict[str, int] | None = None) -> None:
    for tabla, etiqueta in TABLAS_RESUMEN:
        if tabla not in conteos:
            continue
        linea = f"   {etiqueta:28} {conteos[tabla]:>7}"
        if comparar is not None and tabla in comparar:
            linea += f"   (sistema en uso: {comparar[tabla]})"
        print(linea)


def _registrar_simulacro(linea: str) -> None:
    try:
        with open(_directorio_backup() / "simulacros_log.txt", "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except Exception:
        pass


def simulacro(zip_path: Path) -> int:
    print(f"\n🧪 SIMULACRO DE RESTAURACIÓN (no modifica el sistema en uso)\n   Backup: {zip_path.name}\n")
    password = _obtener_password(zip_path)
    if not password:
        return 1
    tmp = Path(tempfile.mkdtemp(prefix="ocdi_simulacro_"))
    fallos = []
    try:
        _extraer(zip_path, password, tmp)
        db = tmp / "ocdi.db"
        integ = _integridad(db)
        print(f"✔ ZIP descifrado. Integridad de la base de datos: {integ}")
        if integ != "ok":
            fallos.append("integridad")

        antes = _conteos(db)
        prod = _conteos(BD_PRODUCCION) if BD_PRODUCCION.exists() else None
        print(f"✔ {len(antes)} tablas en el backup. Registros principales:")
        _resumen_tablas(antes, prod)

        faltan = [t for t in (prod or {}) if t not in antes]
        if faltan:
            print(f"⚠️  Tablas del sistema en uso que NO están en el backup: {faltan}")
            fallos.append("tablas faltantes")

        res = _arrancar_app_contra(db)
        if not res or not res.get("init_db"):
            fallos.append("arranque")
        else:
            print("✔ La aplicación arrancó con el backup restaurado.")
            if res.get("http"):
                malas = {p: c for p, c in res["paginas"].items() if c != 200}
                print(f"✔ Páginas abiertas: {len(res['paginas']) - len(malas)}/{len(res['paginas'])} respondieron bien.")
                if malas:
                    print(f"❌ Páginas con error: {malas}")
                    fallos.append("páginas")
            else:
                print("ℹ️  Prueba de páginas omitida (falta el paquete httpx; opcional).")
    finally:
        # La copia descifrada contiene datos reales: se borra siempre.
        shutil.rmtree(tmp, ignore_errors=True)

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if fallos:
        print(f"\n❌ SIMULACRO FALLIDO: {', '.join(fallos)}")
        _registrar_simulacro(f"[{fecha}] FALLÓ — {zip_path.name} — {', '.join(fallos)}")
        return 1
    print("\n✅ SIMULACRO EXITOSO — este backup restaura el sistema completo.")
    print("   (Diferencias pequeñas en los conteos = lo registrado después de la hora del backup.)")
    _registrar_simulacro(f"[{fecha}] OK — {zip_path.name} — {len(antes)} tablas")
    return 0


def restaurar(zip_path: Path) -> int:
    print(f"\n♻️  RESTAURACIÓN DEL SISTEMA\n   Backup: {zip_path.name}\n")
    password = _obtener_password(zip_path)
    if not password:
        return 1

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if BD_PRODUCCION.exists():
        resp = input(f"⚠️  Ya existe {BD_PRODUCCION}. Se guardará aparte y se reemplazará por el backup. ¿Continuar? (s/n): ")
        if resp.strip().lower() not in ("s", "si", "sí"):
            print("Cancelado. No se modificó nada.")
            return 1
        apartado = DATA_DIR / f"ocdi_antes_de_restaurar_{ts}.db"
        BD_PRODUCCION.rename(apartado)
        for sufijo in ("-wal", "-shm"):
            resto = BD_PRODUCCION.with_name(BD_PRODUCCION.name + sufijo)
            if resto.exists():
                resto.rename(apartado.with_name(apartado.name + sufijo))
        print(f"   Base de datos anterior guardada como: {apartado.name}")

    tmp = Path(tempfile.mkdtemp(prefix="ocdi_restaurar_"))
    try:
        _extraer(zip_path, password, tmp)
        shutil.move(str(tmp / "ocdi.db"), BD_PRODUCCION)
        for nombre in ARCHIVOS_EXTRA:
            if (tmp / nombre).exists():
                shutil.copy2(tmp / nombre, DIRECTORIO_APP / nombre)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"✔ Base de datos restaurada en {BD_PRODUCCION}")

    if not PASSWORD_FILE.exists():
        PASSWORD_FILE.write_text(password, encoding="utf-8")
        print(f"✔ Contraseña guardada en {PASSWORD_FILE} (los backups nuevos usarán la misma).")
    elif PASSWORD_FILE.read_text(encoding="utf-8").strip() != password:
        print(f"⚠️  {PASSWORD_FILE} tiene OTRA contraseña. Los backups nuevos usarían esa, distinta")
        print("   de la de los backups anteriores. Si no es intencional, reemplaza su contenido")
        print("   por la contraseña con la que acabas de restaurar.")

    integ = _integridad(BD_PRODUCCION)
    print(f"✔ Integridad: {integ}")
    res = _arrancar_app_contra(BD_PRODUCCION)
    if not res or not res.get("init_db") or integ != "ok":
        print("\n❌ La restauración NO quedó bien. La BD anterior (si había) está en data\\ocdi_antes_de_restaurar_*.db")
        return 1
    print("✔ La aplicación arranca correctamente con los datos restaurados. Registros:")
    _resumen_tablas(_conteos(BD_PRODUCCION))
    print("\n✅ RESTAURACIÓN COMPLETA. Siguiente paso: iniciar.bat (ver RESTAURACION.md, Paso 5).")
    return 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    es_simulacro = "--simulacro" in sys.argv
    zip_path = Path(args[0]) if args else _zip_mas_reciente()
    if not zip_path:
        return 1
    if not zip_path.exists():
        print(f"❌ No existe el archivo: {zip_path}")
        return 1
    return simulacro(zip_path) if es_simulacro else restaurar(zip_path)


if __name__ == "__main__":
    sys.exit(main())
