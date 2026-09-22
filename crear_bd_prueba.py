"""
Crear base de datos de prueba (sandbox) — Sistema OCDI
========================================================
SDS-TIC-LN-016 §5.4.3.a / §5.5: ningún ambiente de desarrollo o pruebas debe
usar datos reales de producción sin anonimizar. OCDI corre en un solo PC con
una sola base de datos por diseño (no hay servidores separados de dev/QA),
así que este script crea una base de datos alterna, vacía, que se llena
automáticamente con los datos sintéticos que ya genera init_db() (5 usuarios
semilla + 3 expedientes de ejemplo con nombres ficticios) — nunca con datos
reales de expedientes, quejosos o funcionarios.

Uso:
    python crear_bd_prueba.py                     # crea data/ocdi_sandbox.db
    python crear_bd_prueba.py ruta\\personalizada.db

Para levantar la app completa contra esa BD (navegar en el navegador sin
tocar nunca data/ocdi.db real):

    Windows (cmd):
        set OCDI_DB_PATH=data\\ocdi_sandbox.db
        python -m uvicorn app.main:app --reload

    PowerShell:
        $env:OCDI_DB_PATH = "data\\ocdi_sandbox.db"
        python -m uvicorn app.main:app --reload

data/ocdi_sandbox.db (o la ruta que elijas) NUNCA se sube a git — toda la
carpeta data/ está en .gitignore.
"""
import sys
from pathlib import Path

# La consola de Windows suele usar cp1252, que no puede imprimir emojis.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DIRECTORIO_APP = Path(__file__).resolve().parent
DEFAULT_PATH = DIRECTORIO_APP / "data" / "ocdi_sandbox.db"


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH

    if destino.exists():
        respuesta = input(
            f"⚠️  Ya existe '{destino}'. ¿Borrarla y recrearla desde cero? [s/N]: "
        ).strip().lower()
        if respuesta != "s":
            print("Cancelado. La base de datos existente no se modificó.")
            return 1
        destino.unlink()

    destino.parent.mkdir(parents=True, exist_ok=True)

    import os
    os.environ["OCDI_DB_PATH"] = str(destino)
    import app.database as dbmod
    dbmod.DB_PATH = destino  # por si app.database ya se había importado antes

    dbmod.init_db()

    print(f"✅ Base de datos de prueba creada en: {destino}")
    print("   Incluye 5 usuarios semilla (contraseñas nuevas generadas — ver consola)")
    print("   y 3 expedientes de ejemplo con nombres ficticios (no son datos reales).")
    print()
    print("   Para navegarla en el navegador:")
    print(f'     set OCDI_DB_PATH={destino}')
    print("     python -m uvicorn app.main:app --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
