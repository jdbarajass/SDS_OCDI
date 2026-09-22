# SBOM — Inventario de Software (Software Bill of Materials)

**Sistema:** OCDI — Sistema de Gestión Disciplinaria (SDS)
**Generado:** 2026-09-22 (Fase 7 de cumplimiento SDS-TIC-LN-016 §5.4.2.e / §5.6)
**Herramienta de escaneo:** [pip-audit](https://pypi.org/project/pip-audit/) contra la base de datos [OSV](https://osv.dev/) (Open Source Vulnerabilities)
**Resultado del último escaneo:** 0 vulnerabilidades conocidas en las dependencias declaradas en `requirements.txt`

> Este documento se debe regenerar (o al menos re-escanear) cada vez que se agregue, quite o actualice una dependencia en `requirements.txt`, y periódicamente durante la vigencia del sistema en producción (§5.6.3 — gestión de parches).

## Cómo re-escanear

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

## Componentes de terceros (dependencias directas)

| Paquete | Versión | Propósito en OCDI | Licencia | Estado (2026-09-22) |
|---|---|---|---|---|
| fastapi | **0.141.1** | Framework web / enrutamiento de la API y las vistas | MIT | ✅ Sin CVEs conocidos |
| starlette | **1.3.1** | Motor ASGI subyacente de FastAPI (fijado explícitamente por ser crítico para seguridad — antes solo transitivo) | BSD-3 | ✅ Sin CVEs conocidos |
| uvicorn[standard] | 0.30.6 | Servidor ASGI que ejecuta la aplicación | BSD-3 | ✅ Sin CVEs conocidos |
| jinja2 | **3.1.6** | Motor de plantillas HTML (Jinja2Templates) | BSD-3 | ✅ Sin CVEs conocidos (antes 3.1.4 tenía 3 CVEs de RCE en el sandbox) |
| python-multipart | **0.0.31** | Parseo de formularios `multipart/form-data` (subida de archivos) | Apache-2.0 | ✅ Sin CVEs conocidos (antes 0.0.9 tenía 8 CVEs de DoS/path traversal) |
| aiofiles | 23.2.1 | Operaciones de archivo asíncronas | Apache-2.0 | ✅ Sin CVEs conocidos |
| openpyxl | 3.1.5 | Lectura/escritura de archivos Excel (importadores/exportadores) | MIT | ✅ Sin CVEs conocidos |
| pypdf | **6.19.0** | Unir, extraer, rotar páginas PDF (módulo Herramientas PDF) | BSD-3 | ✅ Sin CVEs conocidos (antes 6.12.2 tenía CVE-2026-57204 y PYSEC-2026-3913) |
| pdf2docx | 0.5.13 | Conversión PDF → Word | GPL-3.0 | ✅ Sin CVEs conocidos |
| PyMuPDF | 1.27.2.3 | Compresión de PDF, sello/marca de agua | AGPL-3.0 / comercial | ✅ Sin CVEs conocidos |
| docx2pdf | 0.1.8 | Conversión Word → PDF | MIT | ✅ Sin CVEs conocidos |
| pyzipper | 0.4.0 | Cifrado AES-256 de los backups (`backup_diario.py`, Fase 5) | Apache-2.0 | ✅ Sin CVEs conocidos |

**Cambios de esta fase (Fase 7, 2026-09-22):**
- `fastapi` 0.115.0 → 0.141.1, `jinja2` 3.1.4 → 3.1.6, `python-multipart` 0.0.9 → 0.0.31, `pypdf` (sin fijar) → 6.19.0: cerraban vulnerabilidades reales conocidas (RCE en el sandbox de Jinja2, DoS y path traversal en python-multipart, DoS y SSRF vía UNC path en Windows en Starlette, CVE en pypdf).
- `starlette` se agrega como dependencia directa fijada (antes solo transitiva vía fastapi) por su relevancia de seguridad.
- Todas las dependencias que antes usaban `>=` (sin techo) ahora tienen versión exacta fijada con `==`, para reproducibilidad y trazabilidad ante nuevas vulnerabilidades (§5.4.2.e.1).
- La actualización de Starlette eliminó el shim de compatibilidad para la firma antigua de `TemplateResponse(name, context)` — se corrigió centralizadamente en `app/template_utils.py` (ver README v5.5, Fase 7) en vez de modificar los 73 call sites del proyecto.

## Dependencias de desarrollo (no van a producción)

| Paquete | Uso |
|---|---|
| pytest | Ejecutar `tests/` |
| pip-audit | Escaneo de vulnerabilidades (SCA) — no se agrega a `requirements.txt`, se instala solo cuando se re-escanea |

## Notas

- No se detectaron licencias copyleft fuertes incompatibles con el uso interno de la entidad; `pdf2docx` (GPL-3.0) y `PyMuPDF` (AGPL-3.0/comercial) se usan como herramientas de procesamiento server-side sin redistribuir el código fuente de OCDI, dentro de una entidad pública — si en el futuro OCDI se libera como software de código abierto, revisar la compatibilidad de licencias con el equipo legal de la SDS.
- El entorno de ejecución de este PC tiene otros paquetes Python instalados globalmente (`requests`, `werkzeug`, `python-dotenv`, etc.) que **no son dependencias de OCDI** — pertenecen a otras herramientas del mismo equipo y no forman parte de este inventario ni del `requirements.txt` del proyecto.
