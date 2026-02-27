# OCDI — Sistema de Gestión Disciplinaria
### Secretaría Distrital de Salud (SDS) · Oficina de Control Disciplinario Interno

> **Versión actual: v2.1** — Última actualización: 2026-02-27

---

## Tabla de contenido
1. [Contexto del proyecto](#1-contexto-del-proyecto)
2. [Problema actual](#2-problema-actual)
3. [Solución propuesta](#3-solución-propuesta)
4. [Arquitectura técnica](#4-arquitectura-técnica)
5. [Estructura de datos](#5-estructura-de-datos)
6. [Flujo del proceso disciplinario](#6-flujo-del-proceso-disciplinario)
7. [Módulos del sistema](#7-módulos-del-sistema)
8. [Estado del proyecto y changelog](#8-estado-del-proyecto-y-changelog)
9. [Decisiones técnicas tomadas](#9-decisiones-técnicas-tomadas)
10. [Estructura de archivos](#10-estructura-de-archivos)
11. [Guía de instalación y uso](#11-guía-de-instalación-y-uso)
12. [Archivos de referencia](#12-archivos-de-referencia)

---

## 1. Contexto del proyecto

| Campo | Detalle |
|-------|---------|
| **Entidad** | Secretaría Distrital de Salud (SDS) de Bogotá |
| **Dependencia** | Oficina de Control Disciplinario Interno (OCDI) |
| **Inicio** | 24 de febrero de 2026 |
| **Usuarios** | 11 personas dentro de la misma oficina |
| **Repositorio** | https://github.com/jdbarajass/SDS_OCDI |

---

## 2. Problema actual

- La oficina maneja su base de datos en **archivos Excel alojados en SharePoint**.
- Existe un archivo **"padre"** (el formato general con todos los campos) y varios archivos **"hijos"** más pequeños, uno por cada abogado asignado.
- El proceso actual consiste en que cada persona llena su archivo hijo y luego **copia y pega** la información al archivo padre, lo cual es manual, propenso a errores e ineficiente.
- El archivo padre tiene **226 columnas**, de las cuales ~66 son campos reales y el resto son columnas vacías/sin usar.
- No existe un sistema centralizado que permita visualizar, filtrar ni hacer seguimiento de los expedientes de forma ágil.

---

## 3. Solución propuesta

Aplicación **web local** (LAN) que:

- Centraliza toda la información en una **base de datos SQLite** en un PC de la oficina.
- Permite a las 11 personas **ingresar y consultar** desde sus equipos vía red local, sin internet.
- Tiene **lógica condicional** en el formulario (si no avanza a Investigación, no se muestran esos campos).
- Permite **importar masivamente** el Excel existente para migrar información histórica.
- Permite **exportar reportes en Excel** con formato, colores de alerta y filtros configurables.
- Es **completamente gratuita** — sin servidores pagos, sin dominios, sin suscripciones.

---

## 4. Arquitectura técnica

### Stack tecnológico

| Componente | Tecnología | Justificación |
|------------|------------|---------------|
| Backend | Python 3.x + FastAPI | Ligero, rápido, gratuito, fácil de mantener |
| Base de datos | SQLite | Archivo único, fácil backup, soporta 11 usuarios concurrentes |
| Frontend | HTML + CSS + JavaScript (vanilla) | Accesible desde cualquier navegador sin instalar nada |
| Motor de plantillas | Jinja2 | Integrado en FastAPI |
| Servidor HTTP | Uvicorn | Incluido en FastAPI |
| Excel | openpyxl | Leer y generar `.xlsx` con estilos y colores |

### Diagrama de red

```
[PC Servidor] ─── corre Python + FastAPI + SQLite
       │
   [Red LAN — SDS]
       │
[PC Usuario 1]  → Chrome → http://192.168.X.X:8000
[PC Usuario 2]  → Chrome → http://192.168.X.X:8000
     ...
[PC Usuario 11] → Chrome → http://192.168.X.X:8000
```

- **Sin instalación en PCs clientes:** solo necesitan un navegador (Chrome/Edge).
- **Sin internet requerido:** todo corre en la red interna de la SDS.
- **Backup:** copiar el archivo `data/ocdi.db` a USB o carpeta compartida.
- **Costo total:** $0

---

## 5. Estructura de datos

### Tablas de la base de datos

| Tabla | Descripción |
|-------|-------------|
| `expedientes` | Tabla principal — todos los campos del proceso disciplinario (48 campos + metadata) |
| `escaneos` | Registros de escáner por expediente — relación 1:N |
| `actuaciones` | Actuaciones mensuales registradas por expediente — para seguimiento |

### Campos del expediente por bloques

#### Bloque 1 — Identificación
`n_expediente`, `anio`, `mes`, `origen_proceso`, `n_radicado`, `fecha_radicado`, `fecha_siias`, `ingreso_siias`, `ingreso_siad`, `fecha_ingreso_siad`, `ingreso_sid4`

#### Bloque 2 — Asignación y partes
`nombre_abogado`, `impedimento`, `investigado`, `perfil_indagado`, `entidad_origen`, `quejoso`

#### Bloque 3 — Asunto y tipología
`asunto`, `tipologia`, `descripcion_tipologia`, `relacionado_siniestro`, `responsable_siniestro`, `relacionado_acoso`, `responsable_acoso`, `relacionado_corrupcion`, `valores_institucionales`, `fecha_hechos`

#### Bloque 4 — Indagación Previa
`fecha_apertura_indagacion`, `numero_auto_apertura_ind`, `fecha_auto_apertura_ind`, `plazo_ind` (días), `fecha_vencimiento_ind`, `numero_auto_traslado_ind`, `fecha_auto_traslado_ind`, `numero_auto_archivo_ind`, `fecha_auto_archivo_ind`

#### Bloque 5 — Investigación Disciplinaria (condicional)
`fecha_apertura_investigacion`, `numero_auto_apertura_inv`, `fecha_auto_apertura_inv`, `plazo_inv` (días), `fecha_vencimiento_inv`, `numero_auto_traslado_inv`, `fecha_auto_traslado_inv`, `numero_auto_archivo_inv`, `fecha_auto_archivo_inv`

#### Bloque 6 — Cierre
`etapa`, `estado_proceso`, `observaciones_finales`

#### Metadata
`created_at`, `updated_at`, `created_by`

---

## 6. Flujo del proceso disciplinario

```
[Entrada del requerimiento]
         ↓
[Registro del expediente]
  - Origen, radicado, fechas, investigado, asunto
         ↓
[Indagación Previa]
  - Auto de apertura
  - Plazo (generalmente 180 días)
  - Actuaciones durante el plazo
         ↓
    ¿Mérito suficiente?
       /       \
     NO         SÍ
     ↓           ↓
[Archivo]   [Investigación Disciplinaria]
             - Nuevo auto de apertura
             - Nuevo plazo
             - Actuaciones
                  ↓
             ¿Falta probada?
               /       \
             NO         SÍ
             ↓           ↓
         [Archivo]   [Sanción / Pliego de cargos]
```

**Regla de negocio clave:** Los campos de Investigación Disciplinaria solo se muestran/llenan si el expediente avanzó a esa etapa.

---

## 7. Módulos del sistema

| # | Módulo | Descripción | Estado |
|---|--------|-------------|--------|
| 1 | **Dashboard** | Métricas totales; estadísticas por etapa, estado, año, origen y tipología; tendencia mensual de ingreso; alertas vencimiento (vencidos / 30 / 60 días) con modal de exportación | ✅ v2.1 |
| 2 | **Lista de expedientes** | Listado con paginación (25/50/100/Todos), filtros por texto, año, etapa, abogado, origen, alerta, rango de fechas; orden por cualquier columna; búsqueda numérica inteligente | ✅ v2.1 |
| 3 | **Gestión de expedientes** | Crear, ver, editar con formulario de 7 bloques y lógica condicional; eliminar | ✅ v1.0 |
| 4 | **Seguimiento mensual** | Tabla interactiva de actuaciones por expediente × mes con modal de edición inline | ✅ v1.0 |
| 5 | **Control de autos** | Tabla de autos por tipo × mes y por abogado, con exportación a Excel | ✅ v1.0 |
| 6 | **Importar desde Excel** | Cargue masivo del archivo padre `.xlsx`; detección automática de la hoja correcta; detección de duplicados; limpieza de valores de error de Excel | ✅ v2.1 |
| 7 | **Exportar reporte completo** | Todos los expedientes en Excel con formato, colores por alerta, fila de metadatos | ✅ v1.0 |
| 8 | **Exportar reporte filtrado** | Filtros avanzados (año, abogado, etapa, estado, fechas, vencimientos) + selección de bloques de columnas + opción "solo filtrados" o "todo con indicador EN FILTRO" | ✅ v2.1 |
| 9 | **Gestión de usuarios/login** | Autenticación por usuario con roles | ⏳ Pendiente (Fase 3) |

---

## 8. Estado del proyecto y changelog

### Fases

| Fase | Descripción | Estado | Fecha |
|------|-------------|--------|-------|
| 0 | Levantamiento de requerimientos y análisis del Excel | ✅ | 2026-02-24 |
| 1 | Diseño de arquitectura y BD | ✅ | 2026-02-24 |
| 2 | v1.0 — Gestión expedientes + Importar/Exportar + Dashboard + Seguimiento + Autos | ✅ | 2026-02-25 |
| 3 | v2.0 — Corrección importación Excel (hoja errónea → 243 registros correctos) | ✅ | 2026-02-27 |
| 4 | v2.1 — Mejoras UX: paginación, filtros avanzados, modal exportar, métricas nuevas, búsqueda inteligente, corrección alertas con `#VALUE!` | ✅ | 2026-02-27 |
| 5 | Fase 3 — Pruebas con usuarios reales + ajustes | ⏳ Pendiente | — |
| 6 | Fase 4 — Gestión de usuarios/login + despliegue en red local SDS | ⏳ Pendiente | — |

---

### Changelog detallado

#### v2.1 — 2026-02-27 · commit `8e33f33`

**Nuevas funcionalidades:**

- **Lista de expedientes — paginación:** selector 25 / 50 / 100 / Todos por página con controles de navegación (primera, anterior, páginas, siguiente, última)
- **Lista de expedientes — filtros adicionales:** Origen del proceso (dropdown), Alerta de vencimiento (Vencidos / 30 días / 60 días), Fecha radicado desde/hasta
- **Lista de expedientes — ordenamiento:** click en cualquier encabezado de columna ordena ascendente/descendente; flecha ↑↓ indica columna y dirección activa
- **Lista de expedientes — búsqueda inteligente:** al buscar un número (ej. "046") también compara `CAST(n_expediente AS INTEGER) = 46` para encontrar expedientes guardados sin cero a la izquierda; además busca en `n_radicado` y `quejoso`
- **Dashboard — modal de exportación:** las tarjetas de alerta (Vencidos, 30 días, 60 días) ahora abren un popup con tres opciones: descargar solo los filtrados, descargar todos con columna `EN FILTRO`, o ver en la lista
- **Dashboard — nuevas métricas:** panel "Por Origen del Proceso", panel "Top Tipologías", gráfica de barras "Tendencia Mensual de Ingreso" (últimos 24 meses)
- **Exportación con `incluir_todos=1`:** descarga todos los expedientes con columna `EN FILTRO` (SI/NO); filas del filtro aparecen primero en colores normales; resto en gris claro con texto gris; AutoFiltro de Excel activado para filtrar desde la columna A

**Correcciones de errores:**

- **Bug crítico — alertas con `#VALUE!`:** valores de error de Excel importados como texto causaban que expedientes vigentes aparecieran como vencidos. Los filtros de alerta ahora usan `date()` de SQLite que devuelve NULL para textos no-fecha, excluyéndolos correctamente. Afectaba: filtros de lista, conteos del dashboard, lista de próximos a vencer
- **Limpieza de BD:** se pusieron en NULL 5 registros con fechas inválidas (`fecha_vencimiento_inv = "#VALUE!"` en expedientes 46 y 53; `fecha_radicado` con errores de tipeo en expedientes 17, 23, 33)
- **Importador:** `_fecha()` ya no almacena formatos no reconocidos; devuelve `None` en lugar de guardar strings de error de Excel

---

#### v2.0 — 2026-02-27 · commit `fbf2906`

- **Corrección crítica de importación Excel:** el archivo `BASE EXPEDIENTES 2023U ORIGINAL 22-10-2025.xlsx` no tiene hoja "ENCABEZADO"; el código caía en el fallback `wb.sheetnames[0]` que era la hoja de controles (`HOJA DE CONTROLES`), importando solo 2 filas incorrectas. La corrección busca la primera hoja donde la celda A1 contiene "EXPEDIENTE". Resultado: 243 expedientes importados correctamente.
- Corrección del bloque de identificación en exportar reporte filtrado
- **Conteos dashboard:** `prox30` y `prox60` ahora excluyen expedientes con `estado_proceso IN ('AUTO DE ARCHIVO', 'ARCHIVADO')` para consistencia con el conteo de vencidos

---

#### v1.0 — 2026-02-25 · commit `635a1d6`

- Sistema completo inicial: dashboard, gestión de expedientes (CRUD), seguimiento mensual, control de autos, importar desde Excel, exportar Excel completo y filtrado
- Borrado total de BD con confirmación en página de importar

---

## 9. Decisiones técnicas tomadas

| Fecha | Decisión | Justificación |
|-------|----------|---------------|
| 2026-02-24 | **SQLite** como base de datos | Gratuito, sin instalación, archivo único fácil de respaldar. 11 usuarios concurrentes es manejable con WAL mode activado. |
| 2026-02-24 | **Interfaz web** (no app de escritorio) | Los clientes solo necesitan un navegador. Sin instalación en los 10 PCs usuario. |
| 2026-02-24 | **Python + FastAPI** como backend | Ecosistema maduro, fácil de instalar en Windows, openpyxl para Excel. |
| 2026-02-24 | **PC de la oficina como servidor** en la LAN | No requiere servidores externos ni pagos. Usa la red de cable existente de la SDS. |
| 2026-02-24 | **Lógica condicional por etapa** en el formulario | Evitar que se llenen campos irrelevantes según el estado del expediente. |
| 2026-02-25 | **Construcción por fases** empezando con módulos críticos | El prototipo construye los cimientos compartidos. Los módulos restantes se añaden sin reescribir lo existente. |
| 2026-02-27 | **`date()` de SQLite** en todos los filtros de fecha | Previene falsos positivos cuando hay valores no-fecha en columnas de fecha (errores `#VALUE!` de Excel). |
| 2026-02-27 | **`CAST(n_expediente AS INTEGER)`** en búsqueda numérica | Permite buscar "046" y encontrar expedientes guardados como "46" (sin cero a la izquierda, como los lee Excel al importar). |
| 2026-02-27 | **AutoFiltro en exportación** con `incluir_todos=1` | El usuario puede quitar el filtro EN FILTRO desde Excel para ver todos los expedientes, o dejarlo para ver solo los del filtro. |

---

## 10. Estructura de archivos

```
SDS_OCDI/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app — monta routers y archivos estáticos
│   ├── database.py                # Esquema SQLite, get_db(), calcular_alerta(), row_to_dict()
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── expedientes.py         # Lista, CRUD, exportar Excel completo y filtrado
│   │   ├── dashboard.py           # Dashboard con métricas, alertas, tendencia mensual
│   │   ├── importar.py            # Importación masiva desde Excel (.xlsx)
│   │   ├── seguimiento.py         # Seguimiento mensual de actuaciones
│   │   └── autos.py               # Control de autos por tipo y mes
│   ├── static/
│   │   ├── css/style.css          # Estilos completos (sin dependencias externas)
│   │   └── js/app.js              # Lógica de formulario, tabs, escaneos dinámicos
│   └── templates/
│       ├── base.html              # Plantilla base — sidebar + layout + nav
│       ├── lista.html             # Lista con filtros avanzados y paginación
│       ├── form.html              # Formulario crear/editar (7 secciones con tabs)
│       ├── detalle.html           # Vista detalle del expediente
│       ├── dashboard.html         # Dashboard con métricas y modal de exportación
│       ├── importar.html          # Importación Excel con zona de drop y resultado
│       ├── exportar_filtrado.html # Exportación personalizada con selección de bloques
│       ├── seguimiento.html       # Tabla de seguimiento mensual
│       └── autos.html             # Tabla de control de autos
├── data/
│   └── ocdi.db                    # Base de datos SQLite (generada automáticamente al iniciar)
├── iniciar.bat                    # Script Windows — libera puerto 8000 e inicia el servidor
├── requirements.txt               # Dependencias Python
└── README.md                      # Este archivo
```

---

## 11. Guía de instalación y uso

### Primera vez (instalación)

```bash
# 1. Tener Python 3.10+ instalado (verificar con: python --version)

# 2. Instalar dependencias (solo una vez)
pip install -r requirements.txt

# 3. Iniciar el servidor
iniciar.bat   # doble clic en Windows
```

### Uso diario

1. Doble clic en `iniciar.bat` en el PC servidor
2. Esperar el mensaje `Uvicorn running on http://0.0.0.0:8000`
3. En cualquier PC de la red abrir Chrome/Edge: `http://<IP-del-servidor>:8000`
   - Para conocer la IP: ejecutar `ipconfig` en el servidor y buscar "Dirección IPv4"
4. Para detener: `Ctrl+C` en la ventana de comandos

### Importar datos desde Excel

1. Ir a **Importar** en el menú lateral
2. Seleccionar el archivo `.xlsx` (acepta el formato padre del OCDI)
3. El sistema detecta automáticamente la hoja correcta buscando la que tenga "EXPEDIENTE" en celda A1
4. Los expedientes duplicados (mismo N° + mismo año) se omiten automáticamente
5. Se muestra el resumen: insertados / omitidos / errores

### Exportar reportes

**Reporte completo:**
- Menú → Lista de Expedientes → botón "Exportar Excel"
- Descarga todos los expedientes con colores de alerta

**Reporte filtrado/personalizado:**
- Menú → Exportar Reporte, o desde el dashboard → tarjeta de alerta → "Exportar →"
- Seleccionar filtros (año, abogado, etapa, estado, fechas, vencimientos)
- Seleccionar bloques de columnas a incluir
- **Opción 1 — "Solo los filtrados":** Excel limpio con solo los expedientes del filtro
- **Opción 2 — "Todo + indicador":** Excel con todos los expedientes + columna `EN FILTRO` (SI/NO); filas filtradas primero. Desde Excel: usar el AutoFiltro en la columna A para ver solo los del filtro, o quitar el filtro para ver todos.

### Backup de la base de datos

Copiar el archivo `data/ocdi.db` a una carpeta segura, USB o nube. Para restaurar, reemplazar ese archivo antes de iniciar el servidor.

---

### Dependencias

| Paquete | Versión | Uso |
|---------|---------|-----|
| `fastapi` | 0.115+ | Framework web backend |
| `uvicorn[standard]` | 0.30+ | Servidor ASGI |
| `jinja2` | 3.1+ | Motor de plantillas HTML |
| `python-multipart` | 0.0.9+ | Subida de archivos (importar Excel) |
| `openpyxl` | 3.1.5 | Leer y generar archivos `.xlsx` con estilos |
| `aiofiles` | 23.2+ | Servicio de archivos estáticos asíncronos |

---

## 12. Archivos de referencia

| Archivo | Descripción |
|---------|-------------|
| `BASE EXPEDIENTES 2023U ORIGINAL 22-10-2025.xlsx` | Archivo de datos históricos importado. 243 expedientes en hoja `2023 - 2024`. Columnas 1–51 mapean a los 48 campos de la BD. |
| `Diagarama de Flujo OCDI.jpg` | Diagrama de flujo del proceso disciplinario interno |
| `CONTROL DISCIPLINARIO_V10.pdf` | Documento normativo / procedimiento de control disciplinario |
| `Decreto_641_de_2025.pdf` | Decreto de referencia legal |
| `procedimientoa ctual.pdf` | Descripción del procedimiento actual |
| `WhatsApp Image 2026-02-23 at 12.25.38.jpeg` | Organigrama de la Secretaría Distrital de Salud |
| `Prompt SDS.txt` | Descripción original del requerimiento |
