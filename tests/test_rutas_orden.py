"""
Smoke test de orden de registro de rutas.

AUDITORIA.md documenta el mismo patrón de bug repetido 2 veces (H1, H8):
una ruta dinámica de un solo segmento (ej. `/correspondencia/{reg_id}`)
registrada ANTES que una ruta estática con la misma cantidad de segmentos
(ej. `/correspondencia/importar-agilsalud`) — FastAPI resuelve por orden
de registro, así que la ruta dinámica "roba" todas las requests que
debían llegar a la estática.

Este test no necesita base de datos: solo inspecciona `app.routes` después
de importar `app.main`, sin levantar el servidor.
"""
from app.main import app


def _segmentos(path: str) -> list[str]:
    return [s for s in path.strip("/").split("/") if s != ""]


def _es_dinamico(segmento: str) -> bool:
    return segmento.startswith("{") and segmento.endswith("}")


def test_rutas_estaticas_no_quedan_atrapadas_detras_de_rutas_dinamicas():
    rutas = [
        r for r in app.routes
        if hasattr(r, "path") and hasattr(r, "methods") and r.methods
    ]

    conflictos = []
    for i, dinamica in enumerate(rutas):
        seg_din = _segmentos(dinamica.path)
        if not any(_es_dinamico(s) for s in seg_din):
            continue  # esta ruta es estática, no nos interesa como "capturadora"

        for j, estatica in enumerate(rutas):
            if i == j:
                continue
            seg_est = _segmentos(estatica.path)
            if any(_es_dinamico(s) for s in seg_est):
                continue  # solo comparamos contra rutas 100% estáticas
            if len(seg_din) != len(seg_est):
                continue  # distinta cantidad de segmentos, no compiten por el mismo path

            # ¿Coinciden todos los segmentos literales? (los dinámicos matchean cualquier valor)
            compatibles = all(
                _es_dinamico(sd) or sd == se
                for sd, se in zip(seg_din, seg_est)
            )
            if not compatibles:
                continue

            if not (dinamica.methods & estatica.methods):
                continue  # no comparten método HTTP, no hay colisión real

            if i < j:
                # La dinámica está registrada ANTES que la estática que debería
                # poder alcanzarse: exactamente el patrón de H1/H8.
                conflictos.append((dinamica.path, estatica.path))

    assert not conflictos, (
        "Rutas dinámicas registradas antes que una ruta estática que capturarían "
        f"(patrón H1/H8 de AUDITORIA.md): {conflictos}"
    )
