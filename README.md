# OCDI — Sistema de Gestión Disciplinaria
### Secretaría Distrital de Salud (SDS) · Oficina de Control Disciplinario Interno

> **Versión actual: v2.4** — Última actualización: 2026-04-15

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
- **Backup:** botón en el portal descarga un ZIP completo, o copiar `data/ocdi.db` manualmente.
- **Costo total:** $0

---

## 5. Estructura de datos

### Tablas de la base de datos

| Tabla | Módulo | Descripción |
|-------|--------|-------------|
| `expedientes` | Base | Tabla principal — todos los campos del proceso disciplinario (48 campos + metadata) |
| `escaneos` | Base | Registros de escáner por expediente — relación 1:N |
| `actuaciones` | Base | Actuaciones mensuales registradas por expediente — para seguimiento |
| `exp_digitales` | Digitales | Expedientes de seguimiento digital 2025-2026 |
| `exp_comunicaciones` | Digitales | Comunicaciones hijo de cada expediente digital (N:1) con ON DELETE CASCADE |
| `exp_revisiones` | Digitales | Historial de revisiones por expediente digital con fecha |
| `sala_agenda` | Sala | Eventos de sala por fecha y franja horaria |
| `correspondencia` | Reparto | Oficios de la lista de reparto de abogados (14 campos + metadata, incluye `correo_remitente`) |
| `correspondencia_radicados_salida` | Reparto | Radicados de salida múltiples por oficio (N:1) con ON DELETE CASCADE |
| `corr_responsables` | Reparto | Catálogo de responsables (abogados) configurable |
| `corr_tipos_documento` | Reparto | Catálogo de tipos de documento configurable |

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

### Módulo 1 — BASE EXPEDIENTES 2023U (`/expedientes`, `/dashboard`)

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Dashboard** — Métricas totales; estadísticas por etapa, estado, año, origen y tipología; tendencia mensual de ingreso; alertas vencimiento con modal de exportación | ✅ v2.1 |
| 2 | **Lista de expedientes** — Paginación, filtros avanzados, orden por columna, búsqueda numérica inteligente | ✅ v2.1 |
| 3 | **Gestión de expedientes** — Crear, ver, editar (7 bloques con lógica condicional), eliminar | ✅ v1.0 |
| 4 | **Seguimiento mensual** — Tabla de actuaciones por expediente × mes con modal inline | ✅ v1.0 |
| 5 | **Control de autos** — Tabla por tipo × mes y por abogado, con exportación Excel | ✅ v1.0 |
| 6 | **Importar desde Excel** — Cargue masivo `.xlsx` con detección de hoja, duplicados y limpieza de errores | ✅ v2.1 |
| 7 | **Exportar reporte completo** — Excel con formato y colores por alerta | ✅ v1.0 |
| 8 | **Exportar reporte filtrado** — Filtros avanzados + selección de bloques de columnas + opción "todo + indicador EN FILTRO" | ✅ v2.1 |

### Módulo 2 — LISTA DE REPARTO DE ABOGADOS (`/correspondencia/`)

Módulo para el control de oficios y correspondencia recibida, con semáforo de respuesta, catálogos configurables y gestión de múltiples radicados de salida por oficio.

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Dashboard** — Tarjetas 🟢/🟡/🔴/✅, barras por responsable y por mes, tabla de críticos ordenada por días sin respuesta | ✅ v2.3 |
| 2 | **Lista de oficios** — Semáforo por fila, filtros por semáforo/responsable/mes/año/texto, scroll horizontal, paginación | ✅ v2.3 |
| 3 | **Gestión de oficios** — Crear, ver detalle, editar, eliminar. Campo `correo_remitente` visible en formulario y detalle | ✅ v2.4 |
| 4 | **Radicados de salida múltiples** — Por oficio se puede registrar N radicados de salida en tabla separada | ✅ v2.3 |
| 5 | **Semáforo de respuesta** — 🟢 0–5 días · 🟡 6–8 días · 🔴 9+ días · ✅ Respondido. Calculado con `julianday()` SQLite | ✅ v2.3 |
| 6 | **Excepción ANEXO EXPEDIENTE / ANEXO AL EXPEDIENTE** — Ambas variantes siempre aparecen en 🟢 sin conteo de días (muestra `—`). Excluidas de alertas, dashboard rojo/amarillo, portal y backup | ✅ v2.4 |
| 7 | **Catálogos configurables** — CRUD de responsables y tipos de documento desde `/correspondencia/configurar` | ✅ v2.3 |
| 8 | **Tipo de Respuesta — combobox** — 12 opciones predefinidas + texto libre (HTML5 `<datalist>`). Incluye "ANEXO AL EXPEDIENTE" | ✅ v2.4 |
| 9 | **Importar desde Excel histórico** — Acepta formato original (12 cols) y exportado (14 cols); reemplaza todo con confirmación doble | ✅ v2.3 |
| 10 | **Importar desde AgilSalud** (`/correspondencia/importar-agilsalud`) — Carga el archivo `Documentos.xlsx` de AgilSalud; filtra por 2 destinatarias; muestra previsualización; agrega sin borrar datos existentes | ✅ v2.4 |
| 11 | **Exportar a Excel** — Incluye columnas Días Transcurridos y Correo Remitente | ✅ v2.4 |

**Regla de negocio — semáforo:** El semáforo es activo (cuenta días desde hoy) mientras no haya `fecha_radicado_salida`. Una vez registrada la fecha de salida, el registro pasa a ✅ Respondido y muestra los días que tardó la respuesta. Los oficios con `tipo_respuesta` = `ANEXO EXPEDIENTE` o `ANEXO AL EXPEDIENTE` son siempre 🟢 sin conteo de días; se excluyen de toda alerta.

### Módulo 3 — SEGUIMIENTO EXPEDIENTES DIGITALES 2025-2026 (`/digitales/`)

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Dashboard digitales** — Total exps., total comunicaciones, sin respuesta, con queja inicial; 3 tarjetas de alerta por días (🔵/🟡/🔴) con links a vistas filtradas | ✅ v2.2 |
| 2 | **Lista de expedientes digitales** — Paginación, filtros por abogado/etapa/año/alerta/queja/sin respuesta; badge de peor alerta por fila; orden numérico por N° expediente; filtros tipo Excel por columna | ✅ v2.3 |
| 3 | **Detalle + comunicaciones** — Vista completa del expediente con tabla de comunicaciones y formulario para agregar nuevas | ✅ v2.2 |
| 4 | **CRUD expedientes** — Crear, editar y eliminar expedientes digitales | ✅ v2.2 |
| 5 | **Vista global comunicaciones** (`/digitales/comunicaciones`) — Todas las comunicaciones con columna "Días" (🔵/🟡/🔴) y filtros por alerta | ✅ v2.2 |
| 6 | **Sistema de alertas por días** — Azul: 8–12 días sin respuesta / Amarilla: 13 días / Roja: 14+ días. Calculado con `julianday()` SQLite | ✅ v2.2 |
| 7 | **Campo Observaciones Generales** — Campo de notas libres por expediente digital, visible en lista y exportable | ✅ v2.3 |
| 8 | **Columna Últ. Revisión** — Registra y muestra la última fecha en que el abogado marcó revisado el expediente | ✅ v2.3 |
| 9 | **Importar desde Excel** — Estructura padre-hijo; col[0] = expediente, col[8] = comunicación; detección de duplicados | ✅ v2.2 |
| 10 | **Exportar a Excel** — Descarga todos los expedientes con sus comunicaciones + popup de confirmación | ✅ v2.3 |

### Módulo 4 — SALA DE AUDIENCIAS (`/sala/`)

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Calendario mensual** — Vista mes con franjas horarias (08-10, 10-12, 14-16, 16-18) lun–dom | ✅ v2.2 |
| 2 | **Estados de franjas** — 🟢 Disponible por defecto (sin registro) / 🔴 Ocupado (registro en BD) | ✅ v2.2 |
| 3 | **Modal detalle** — Click en franja muestra detalle del evento con opciones Editar/Eliminar | ✅ v2.2 |
| 4 | **CRUD eventos** — Crear desde "+" en día o franja libre, editar, eliminar con confirmación | ✅ v2.2 |
| 5 | **Navegación mensual** — Botones Anterior / Siguiente / Hoy | ✅ v2.2 |

### Módulo 5 — EXPORTAR / IMPORTAR GENERAL (`/backup/`)

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Exportar Excel consolidado** — Un único `.xlsx` con 3 hojas: Base Expedientes, Exp. Digitales, Sala de Audiencias | ✅ v2.3 |
| 2 | **Importar Excel consolidado** — Carga el mismo archivo de vuelta reemplazando todo; modal de confirmación doble | ✅ v2.3 |

### Portal Hub (`/`)

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Página de inicio** — 5 tiles clickables con stats en tiempo real para cada módulo, agrupados visualmente | ✅ v2.3 |
| 2 | **Botón Backup ZIP completo** — Descarga un `.zip` con 4 carpetas (una por módulo), cada una con su Excel actualizado | ✅ v2.3 |

---

## 8. Estado del proyecto y changelog

### Fases

| Fase | Descripción | Estado | Fecha |
|------|-------------|--------|-------|
| 0 | Levantamiento de requerimientos y análisis del Excel | ✅ | 2026-02-24 |
| 1 | Diseño de arquitectura y BD | ✅ | 2026-02-24 |
| 2 | v1.0 — Gestión expedientes + Importar/Exportar + Dashboard + Seguimiento + Autos | ✅ | 2026-02-25 |
| 3 | v2.0 — Corrección importación Excel (hoja errónea → 243 registros correctos) | ✅ | 2026-02-27 |
| 4 | v2.1 — Mejoras UX: paginación, filtros avanzados, modal exportar, métricas nuevas, búsqueda inteligente | ✅ | 2026-02-27 |
| 5 | v2.2 — Hub portal + Módulo Expedientes Digitales + Sala de Audiencias + sistema de alertas por días | ✅ | 2026-03-03 |
| 6 | v2.3 — Módulo Correspondencia + mejoras Digitales + Backup ZIP + Exportar/Importar General | ✅ | 2026-04-14 |
| 7 | v2.4 — ANEXO AL EXPEDIENTE + Importador AgilSalud + campo correo_remitente + fix orden rutas | ✅ | 2026-04-15 |
| 8 | Fase 3 — Pruebas con usuarios reales + ajustes | ⏳ Pendiente | — |
| 9 | Fase 4 — Gestión de usuarios/login + despliegue en red local SDS | ⏳ Pendiente | — |

---

### Changelog detallado

#### v2.4 — 2026-04-15 · commits `070095a` → `daa9f11`

**Módulo Correspondencia — mejoras:**

- **Excepción ANEXO AL EXPEDIENTE:** Se extiende la regla de negocio de "ANEXO EXPEDIENTE" a la variante "ANEXO AL EXPEDIENTE". Ambas siempre aparecen en 🟢 verde con días `—` (NULL en SQL, guion en pantalla). Excluidas de: semáforo activo, dashboard rojo/amarillo, portal badge de alertas, tabla de críticos y backup ZIP. Lógica aplicada en `_SEMAFORO_SQL`, `_DIAS_SQL`, bloque Python de detalle, `portal.py` y `backup.py`. Ambas variantes agregadas al datalist del formulario.

- **Importador AgilSalud** (`GET/POST /correspondencia/importar-agilsalud`): Nueva ruta de dos pasos para cargar el archivo `Documentos.xlsx` exportado de AgilSalud.
  - **Filtrado automático:** solo conserva registros cuyo destinatario sea "MARTHA PATRICIA AÑEZ MAESTRE" o "MABEL GICELA HURTADO SANCHEZ". Del Excel de 108 filas se extraen 32 registros.
  - **Columnas mapeadas:** Número de radicado → `n_radicado`, Dependencia Remitente → `origen`, Correo Electrónico Remitente → `correo_remitente`, Fecha de radicación → `fecha_ingreso` + `mes` + `anio` (inferidos), Asunto → `asunto`.
  - **Previsualización obligatoria:** el sistema muestra una tabla con todos los registros a importar antes de confirmar. Solo al confirmar se ejecuta el INSERT.
  - **Modo ADD:** no borra ni sobreescribe datos existentes; solo agrega nuevos registros.
  - Botón de acceso desde sidebar y desde la lista de oficios.

- **Campo `correo_remitente`:** Nueva columna TEXT en la tabla `correspondencia`. Migración automática en `init_db()` para BDs existentes. Visible en formulario de edición, página de detalle, exportar Excel y backup ZIP.

- **Fix crítico de orden de rutas:** Las rutas `/importar-agilsalud` se registraban después de `/{reg_id}`. El path pattern `[^/]+` de Starlette captura cualquier string antes de llegar a las rutas específicas. Se reordenaron todas las rutas estáticas (`/importar-agilsalud`, `/importar-agilsalud/preview`, `/importar-agilsalud/confirmar`) para que queden **antes** de `/{reg_id}` en el router.

---

#### v2.3 — 2026-04-14 · commits `536d120` → `aa1899a`

**Nuevo módulo: Lista de Reparto de Abogados (`/correspondencia/`)**

- Control completo de oficios y correspondencia recibida con 8 rutas: dashboard, lista, nuevo, detalle, editar, eliminar, importar, exportar, configurar catálogos.
- **Semáforo de respuesta** por `julianday()` SQLite: 🟢 0–5 días / 🟡 6–8 días / 🔴 9+ días / ✅ Respondido.
- **Excepción ANEXO EXPEDIENTE:** oficios con ese tipo de respuesta siempre se muestran en 🟢 con 0 días; excluidos de conteos de vencidos en portal, dashboard y tabla de críticos.
- **Radicados de salida múltiples:** tabla `correspondencia_radicados_salida` con CASCADE; se pueden agregar/eliminar desde el formulario de edición.
- **Catálogos configurables** desde `/correspondencia/configurar`: CRUD de responsables y tipos de documento. 12 nombres de abogados prellenados; normalización de 21 variantes del Excel histórico vía `RESPONSABLE_MAP`.
- **Combobox Tipo de Respuesta:** 11 opciones predefinidas + texto libre usando HTML5 `<datalist>`.
- **Importación inteligente del Excel histórico** (295 registros): detección automática de formato — 12 cols (original) o 14 cols (exportado, con AÑO en col[0]); normalización de nombres sucios; reemplaza todo con modal doble de confirmación.
- **Portal actualizado:** nuevo tile "Lista de Reparto de Abogados" con contador de oficios y badge de alerta roja; tiles de Base Expedientes y Reparto agrupados con subtítulo visual.

**Nuevo módulo: Exportar/Importar General (`/backup/`)**

- Exporta un único `.xlsx` con 3 hojas: Base Expedientes, Exp. Digitales, Sala de Audiencias.
- Importa el mismo archivo reemplazando todo el contenido de las 3 tablas con confirmación doble.

**Nuevo feature: Backup ZIP completo (`/backup/zip`)**

- Botón en el portal principal (visible sin entrar a ningún módulo) que descarga `OCDI_Backup_Completo_YYYYMMDD.zip`.
- Estructura ZIP:
  ```
  OCDI/
  ├── 01_Base_Expedientes/Base_Expedientes_YYYYMMDD.xlsx
  ├── 02_Lista_Reparto_Abogados/Correspondencia_YYYYMMDD.xlsx
  ├── 03_Expedientes_Digitales/Exp_Digitales_YYYYMMDD.xlsx
  └── 04_Sala_Audiencias/Sala_Audiencias_YYYYMMDD.xlsx
  ```
- Cada Excel usa el mismo formato que el exportador individual del módulo.

**Mejoras en Expedientes Digitales:**

- **Campo Observaciones Generales** (`observaciones`): campo de notas libres por expediente; visible en lista, exportable en Excel y en Backup ZIP.
- **Columna Últ. Revisión**: registra la última fecha en que el abogado marcó el expediente como revisado (`exp_revisiones`); visible en lista y en exportación.
- **Filtros tipo Excel por columna**: menú desplegable en cada encabezado de la lista con valores únicos de esa columna; permite filtrar por Abogado, Etapa, Año, etc. de forma independiente.
- **Popup de confirmación de descarga Excel**: antes de generar el archivo, muestra cuántos registros se exportarán.

---

#### v2.2 — 2026-03-03 · commits `4d204ee` → `7b8f24e`

**Nuevos módulos:**

- **Hub Portal (`/`):** página de inicio con 3 tiles clickables que muestran stats en tiempo real de cada módulo. Reemplaza a `/` como landing page; el módulo Base pasa a `/expedientes`.
- **Módulo Expedientes Digitales 2025-2026 (`/digitales/`):** gestión completa de seguimiento digital con CRUD, importación desde Excel padre-hijo (39 expedientes / 88 comunicaciones), exportación, dashboard con métricas y vista global de comunicaciones.
- **Sala de Audiencias (`/sala/`):** calendario mensual con franjas horarias (08-10, 10-12, 14-16, 16-18), estados Disponible/Ocupado/Reservado, modal de detalle, CRUD de eventos y navegación mes a mes.

**Sistema de alertas por días (Módulo Digitales):**
- Calcula días transcurridos desde `fecha_envio` hasta hoy con `julianday()` de SQLite solo para comunicaciones sin `fecha_respuesta`
- 🔵 Azul: 8–12 días · 🟡 Amarilla: 13 días · 🔴 Roja: 14+ días
- Las alertas aparecen en: columna "Días" de la vista comunicaciones, badge emoji por fila en lista de expedientes, y 3 tarjetas clickables en el dashboard
- Filtros por nivel de alerta en lista de expedientes y en vista comunicaciones

**Sidebars independientes por módulo:**
- Cada módulo tiene su propio base template (`base.html`, `base_digitales.html`, `base_sala.html`) con nav contextual. No se mezclan ítems de navegación entre módulos.

**Correcciones:**
- Orden numérico de N° expediente: `CAST(n_expediente AS INTEGER) ASC` en lugar de orden texto
- Orden de rutas en `digitales.py`: rutas estáticas (`/importar`, `/exportar`, `/comunicaciones`) registradas antes de `/{exp_id}` para evitar que FastAPI intente parsear strings como int
- Variable Jinja2 en loops: uso de `{% set ns = namespace() %}` + `{% set ns.id = valor %}` en lugar de `__setattr__`

---

#### v2.1 — 2026-02-27 · commit `8e33f33`

- **Lista de expedientes — paginación:** selector 25 / 50 / 100 / Todos por página con controles de navegación
- **Lista de expedientes — filtros adicionales:** Origen del proceso, Alerta de vencimiento, Fecha radicado desde/hasta
- **Lista de expedientes — ordenamiento:** click en cualquier encabezado ordena ASC/DESC
- **Lista de expedientes — búsqueda inteligente:** busca número con y sin cero a la izquierda; busca en `n_radicado` y `quejoso`
- **Dashboard — modal de exportación:** tarjetas de alerta abren popup con opciones: solo filtrados / todos con indicador EN FILTRO / ver en lista
- **Dashboard — nuevas métricas:** panel "Por Origen del Proceso", "Top Tipologías", gráfica "Tendencia Mensual de Ingreso" (últimos 24 meses)
- **Bug crítico — alertas con `#VALUE!`:** valores de error de Excel causaban falsos positivos. Filtros ahora usan `date()` SQLite que devuelve NULL para no-fechas.

---

#### v2.0 — 2026-02-27 · commit `fbf2906`

- Corrección crítica de importación Excel: el archivo fuente no tiene hoja "ENCABEZADO"; el sistema ahora busca la primera hoja donde A1 contiene "EXPEDIENTE". Resultado: 243 expedientes importados correctamente.

---

#### v1.0 — 2026-02-25 · commit `635a1d6`

- Sistema completo inicial: dashboard, gestión de expedientes (CRUD), seguimiento mensual, control de autos, importar desde Excel, exportar Excel completo y filtrado.

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
| 2026-02-27 | **AutoFiltro en exportación** con `incluir_todos=1` | El usuario puede quitar el filtro EN FILTRO desde Excel para ver todos los expedientes. |
| 2026-03-03 | **Sidebars independientes por módulo** | Cada ventana tiene su propio menú lateral. Evita confusión entre los módulos. |
| 2026-03-03 | **`julianday()` de SQLite** para alertas de días | Calcula días transcurridos directamente en SQL sin lógica Python post-proceso. |
| 2026-03-03 | **Rutas estáticas antes de `/{id}`** en cada router | FastAPI evalúa rutas en orden de registro. Rutas como `/importar` deben ir antes de `/{id}` para no ser capturadas como parámetro. |
| 2026-04-14 | **Tabla separada `correspondencia_radicados_salida`** para radicados de salida | Un oficio puede tener N radicados de salida. Usar una tabla hija con CASCADE evita concatenar en un solo campo y permite agregar/eliminar individualmente. |
| 2026-04-14 | **HTML5 `<datalist>`** para Tipo de Respuesta | Ofrece sugerencias predefinidas sin restringir el texto libre. Permite importar las ~80 variantes históricas del Excel sin mapeo. |
| 2026-04-14 | **`RESPONSABLE_MAP` en importación** de Correspondencia | El Excel histórico tiene 21 variantes sucias del mismo nombre (ej. "CESAR IVAN", "CESAR RODRIGUEZ", "CESAR IVAN RODRIGUEZ"). El mapa normaliza al vuelo durante la importación. |
| 2026-04-14 | **Excepción `ANEXO EXPEDIENTE`** en semáforo | Regla de negocio: estos oficios no requieren respuesta formal, por lo tanto no acumulan días de vencimiento. Se aplica en SQL (`_SEMAFORO_SQL`, `_DIAS_SQL`) y en código Python para el detalle. |
| 2026-04-14 | **Backup ZIP estructurado** desde el portal | Un solo clic genera un respaldo completo organizado por módulo, sin necesidad de entrar a cada sección. Facilita copias periódicas sin conocimiento técnico. |
| 2026-04-15 | **`IN (...)` para variantes de ANEXO** en semáforo | Se usó `UPPER(TRIM(tipo_respuesta)) IN ('ANEXO EXPEDIENTE', 'ANEXO AL EXPEDIENTE')` en lugar de `=` para cubrir ambas variantes del texto en un solo chequeo, tanto en SQL como en Python. |
| 2026-04-15 | **Importador AgilSalud con previsualización de 2 pasos** | El archivo de AgilSalud varía en contenido pero no en estructura. El paso de previsualización permite verificar los datos antes de insertar, evitando importaciones erróneas. Se usa JSON oculto en el form para pasar los datos del preview al confirm sin re-leer el archivo. |
| 2026-04-15 | **Rutas AgilSalud antes de `/{reg_id}`** | Starlette compila `/{reg_id}` con regex `[^/]+` que captura cualquier segmento, incluyendo strings como "importar-agilsalud". Si se registra después de `/{reg_id}`, la ruta nunca se alcanza. Todas las rutas estáticas van primero. |

---

## 10. Estructura de archivos

```
SDS_OCDI/
├── app/
│   ├── __init__.py
│   ├── main.py                             # FastAPI app — registra todos los routers
│   ├── database.py                         # Esquema SQLite (11 tablas), get_db(), init_db()
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── portal.py                       # GET /  → hub portal con tiles y stats
│   │   ├── expedientes.py                  # /expedientes — Lista, CRUD, exportar Excel
│   │   ├── dashboard.py                    # /dashboard — métricas BASE 2023U
│   │   ├── importar.py                     # /importar — cargue masivo Excel BASE
│   │   ├── seguimiento.py                  # /seguimiento — actuaciones mensuales
│   │   ├── autos.py                        # /autos — control de autos
│   │   ├── digitales.py                    # /digitales/* — módulo completo digitales 2025-2026
│   │   ├── sala.py                         # /sala/* — sala de audiencias
│   │   ├── backup.py                       # /backup/* — exportar/importar general + ZIP
│   │   └── correspondencia.py             # /correspondencia/* — lista de reparto abogados
│   ├── static/
│   │   ├── css/style.css                   # Estilos completos (sin dependencias externas)
│   │   └── js/app.js                       # Lógica de formulario, tabs, escaneos dinámicos
│   └── templates/
│       ├── base.html                       # Sidebar BASE EXPEDIENTES
│       ├── base_digitales.html             # Sidebar EXP. DIGITALES
│       ├── base_sala.html                  # Sidebar SALA AUDIENCIAS
│       ├── base_correspondencia.html       # Sidebar LISTA DE REPARTO
│       ├── portal.html                     # Hub sin sidebar — tiles + botón backup ZIP
│       ├── lista.html                      # /expedientes lista
│       ├── form.html                       # Crear/editar expediente BASE (7 bloques)
│       ├── detalle.html                    # Detalle expediente BASE
│       ├── dashboard.html                  # Dashboard BASE 2023U
│       ├── importar.html                   # Importar Excel BASE
│       ├── exportar_filtrado.html          # Exportar reporte personalizado
│       ├── seguimiento.html                # Seguimiento mensual
│       ├── autos.html                      # Control de autos
│       ├── backup.html                     # Exportar/Importar general (3 módulos)
│       ├── digitales_lista.html            # /digitales/ lista con filtros tipo Excel
│       ├── digitales_dashboard.html        # /digitales/dashboard con tarjetas de alerta
│       ├── digitales_detalle.html          # /digitales/{id} detalle + comunicaciones
│       ├── digitales_form.html             # Crear/editar expediente digital
│       ├── digitales_comunicaciones.html   # /digitales/comunicaciones vista global
│       ├── digitales_importar.html         # Importar Excel digitales
│       ├── sala.html                       # /sala/ calendario mensual
│       ├── sala_form.html                  # Crear/editar evento de sala
│       ├── corr_lista.html                 # /correspondencia/ lista con semáforo
│       ├── corr_dashboard.html             # /correspondencia/dashboard
│       ├── corr_detalle.html               # /correspondencia/{id} detalle
│       ├── corr_form.html                  # Crear/editar oficio de correspondencia
│       ├── corr_importar.html              # Importar Excel correspondencia (formato histórico)
│       ├── corr_importar_agilsalud.html    # Importar desde AgilSalud (Documentos.xlsx) — 2 pasos
│       └── corr_configurar.html            # Configurar catálogos (responsables, tipos doc)
├── data/
│   └── ocdi.db                             # Base de datos SQLite (se crea al iniciar)
├── iniciar.bat                             # Script Windows — libera puerto 8000 e inicia
├── requirements.txt                        # Dependencias Python
├── INSTALACION.md                          # Guía paso a paso para instalar en Windows
└── README.md                               # Este archivo
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

Ver [INSTALACION.md](INSTALACION.md) para la guía completa paso a paso.

### Uso diario

1. Doble clic en `iniciar.bat` en el PC servidor
2. Esperar el mensaje `Application startup complete`
3. En cualquier PC de la red abrir Chrome/Edge: `http://<IP-del-servidor>:8000`
   - Para conocer la IP: ejecutar `ipconfig` en el servidor y buscar "Dirección IPv4"
4. Para detener: `Ctrl+C` en la ventana de comandos

### Importar datos históricos

**Base Expedientes:**
1. Módulo Base → Importar Excel → seleccionar el `.xlsx` del archivo padre del OCDI
2. El sistema detecta automáticamente la hoja correcta (busca "EXPEDIENTE" en celda A1)
3. Los expedientes duplicados (mismo N° + mismo año) se omiten

**Correspondencia:**
1. Módulo Lista de Reparto → Importar → seleccionar `CORRESPONDENCIA 2026.xlsx`
2. Acepta formato original (12 columnas) o exportado (14 columnas con AÑO y Días)
3. **Reemplaza todos los registros actuales** — confirmar en el modal de alerta

**Expedientes Digitales:**
1. Módulo Digitales → Importar → seleccionar el Excel padre-hijo de seguimiento digital

### Backup y respaldo

**Backup ZIP completo (recomendado):**
- En el portal principal, clic en **"📦 Descargar Backup Completo (.zip)"**
- Descarga un ZIP con 4 carpetas, una por módulo, con el Excel actualizado de cada uno

**Backup de base de datos:**
- Copiar el archivo `data/ocdi.db` a una carpeta segura, USB o nube
- Para restaurar: reemplazar ese archivo antes de iniciar el servidor

### Exportar reportes

**Reporte completo (Base Expedientes):**
- Lista de Expedientes → botón "Exportar Excel"

**Reporte filtrado/personalizado:**
- Menú → Exportar Reporte, o desde el dashboard → tarjeta de alerta → "Exportar →"
- Opción 1 — "Solo los filtrados": Excel limpio con solo los expedientes del filtro
- Opción 2 — "Todo + indicador": todos los expedientes con columna `EN FILTRO` (SI/NO)

**Correspondencia:**
- Lista de Reparto → Exportar (desde el sidebar)

**Exportar/Importar General:**
- Módulo Backup → descarga un único Excel con Base + Digitales + Sala en 3 hojas

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
| `CORRESPONDENCIA 2026.xlsx` | Archivo histórico de correspondencia. 295 registros importables desde `/correspondencia/importar`. |
| `INSTALACION.md` | Guía paso a paso para instalar Python y ejecutar el sistema en Windows. |
