"""
Fixtures compartidas de pytest.

SDS-TIC-LN-016 §5.4.3.a: prohibido usar datos reales de producción en
ambientes de pruebas. Estas fixtures garantizan que ningún test que use
`client` o `db_temporal` pueda tocar data/ocdi.db — cada test recibe su
propia base de datos temporal y desechable, sembrada con los mismos datos
sintéticos (usuarios + 3 expedientes de ejemplo con nombres ficticios) que
ya genera init_db() en cualquier instalación nueva.

Los tests existentes que no reciben estas fixtures (test_dias_habiles.py,
test_semaforos.py, etc.) prueban funciones puras y no tocan la base de
datos en absoluto — no necesitan esto.
"""
import pytest


@pytest.fixture
def db_temporal(monkeypatch, tmp_path):
    """Redirige app.database.DB_PATH a un archivo temporal antes de que el
    test importe/arranque la app, para que init_db() nunca toque la BD real.
    Retorna la ruta del archivo temporal (aún no existe hasta el primer uso)."""
    import app.database as dbmod
    tmp_db = tmp_path / "ocdi_test.db"
    monkeypatch.setattr(dbmod, "DB_PATH", tmp_db)
    return tmp_db


@pytest.fixture
def client(db_temporal):
    """TestClient con la app completa corriendo contra una base de datos
    temporal (nunca data/ocdi.db), ya sembrada con los 5 usuarios semilla y
    3 expedientes de ejemplo que init_db() genera automáticamente."""
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c
