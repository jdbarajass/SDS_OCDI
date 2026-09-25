# OCDI — Sistema de Gestión Disciplinaria
### Secretaría Distrital de Salud (SDS) · Oficina de Control Disciplinario Interno

> **Versión actual: v5.6** — Última actualización: 2026-09-22

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
| `control_autos_sustanciacion` | Control Autos | Autos de sustanciación y/o trámites — formato SDS-CDO-FT-001 v4 (6 campos + metadata) |
| `correspondencia` | Reparto | Oficios de la lista de reparto de abogados (17 campos + metadata; incluye `sinproc_personeria`, `tipo_requerimiento`, `termino_dias`) |
| `correspondencia_radicados_salida` | Reparto | Radicados de salida múltiples por oficio (N:1) con ON DELETE CASCADE; incluye campo `url` para hipervínculos |
| `corr_responsables` | Reparto | Catálogo de responsables (abogados) configurable |
| `corr_tipos_documento` | Reparto | Catálogo de tipos de documento configurable |

### Campos de `correspondencia`

`id`, `anio`, `mes`, `fecha_ingreso`, `n_radicado`, `origen` (etiqueta: **Entidad**), `asunto`, `tipo_documento`, `responsable`, `caso_bmp`, `fecha_radicado_salida`, `tipo_respuesta`, `tramite_salida` (etiqueta: **Observaciones**), `correo_remitente`, `sinproc_personeria`, `tipo_requerimiento`, `termino_dias`, `created_at`, `updated_at`

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

### Módulo 1B — CONTROL DE AUTOS DE SUSTANCIACIÓN Y/O TRÁMITES (`/control-autos/`)

Módulo para el registro y seguimiento de autos de sustanciación disciplinaria. Replica el formato oficial **SDS-CDO-FT-001 v4**.

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Lista de autos** — Paginación 25/página, filtros por abogado (select predefinido), texto, exportación Excel | ✅ v2.5 |
| 2 | **CRUD** — Crear, ver detalle, editar, eliminar | ✅ v2.5 |
| 3 | **Encabezado oficial** — Formulario y exportación replican el formato SDS-CDO-FT-001 con membrete institucional, código, versión y firmas | ✅ v2.5 |
| 4 | **ABOGADO RESPONSABLE** — Select con 11 nombres completos en mayúsculas (lista predefinida) | ✅ v2.5 |
| 5 | **ASUNTO AUTO** — Select con 26 tipos oficiales de autos de sustanciación | ✅ v2.5 |
| 6 | **NÚMERO DEL AUTO** — Acepta consecutivo numérico (001, 002…) o texto "DIGITAL" | ✅ v2.5 |
| 7 | **Importar Excel** — Acepta formato original (hoja "NUEVO", datos desde fila 8) y formato exportado (hoja "CONTROL AUTOS", desde fila 7). Filtra filas de pie de página con longitud > 20 caracteres | ✅ v2.5 |
| 8 | **Exportar Excel** — Replica el encabezado oficial con institución, código, versión y firmas. Hoja "CONTROL AUTOS" con 6 columnas | ✅ v2.5 |
| 9 | **Tile en portal** — Muestra conteo de autos registrados | ✅ v2.5 |
| 10 | **Integrado en Backup General** — Hoja 4 "Control Autos" (verde oscuro) en export/import y en ZIP (carpeta `05_Control_Autos_Sustanciacion/`) | ✅ v2.5 |

**Constantes predefinidas:**
- `ABOGADOS_RESPONSABLES` (11): ANDRES EDUARDO SANDOVAL MAYORGA, CARLOS ALFONSO PARRA MALAVER, CESAR IVAN RODRIGUEZ DAMIAN, DAVID FELIPE MORALES NOGUERA, JANIK HERNANDO DE LA HOZ RIOS, JOSE DE JESUS BARAJAS SOTELO, LUNA GICELL GUZMAN YATE, MABEL GICELLA HURTADO SANCHEZ, MAGDA XIMENA PAREDES LIEVANO, MARA LUCIA UCROS MERLANO, MARTHA PATRICIA AÑEZ MAESTRE.
- `ASUNTOS_COMUNES` (26): Apertura Indagación Preliminar, Apertura Investigación Disciplinaria, Auto Inhibitorio, Citar a descargos, Citar a diligencia de versión libre, Comisionar, Decretar pruebas, Dejar sin efecto, Desarchivo, Devolver expediente, Informe de gestión, Nulidad, Ordena traslado, Pliego de Cargos, Prórroga de términos, Recurso de apelación, Recurso de queja, Recurso de reposición, Remisión, Solicitar información, Suspensión provisional, Auto de Archivo, Traslado probatorio, Vista Fiscal, Declarar Prescripción, Envío de Expediente.

### Módulo 2 — CONTROL TRÁMITES INTERNOS OCDI (`/correspondencia/`)

Módulo para el control de oficios y correspondencia recibida. Incluye semáforo de respuesta dual (días transcurridos o fecha límite según configuración), catálogos configurables y gestión de múltiples radicados de salida con URL.

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Dashboard** — Tarjetas 🟢/🟡/🔴/✅, barras por responsable y por mes, tabla de críticos ordenada por días sin respuesta | ✅ v2.3 |
| 2 | **Lista de oficios** — Semáforo por fila, filtros por semáforo/responsable/mes/año/texto, scroll horizontal, paginación. Columnas: Tipo Req., Término, Observaciones, Entidad | ✅ v2.5 |
| 3 | **Gestión de oficios** — Crear, ver detalle, editar, eliminar. Campos: SINPROC Personería, Tipo de Requerimiento, Término (Días), Entidad (antes "Origen"), Observaciones (antes "Trámite de Salida") | ✅ v2.5 |
| 4 | **Radicados de salida múltiples con URL** — Por oficio se registran N radicados con campo `url` opcional. En formulario y detalle el radicado es un hipervínculo clickable que abre en nueva pestaña | ✅ v2.5 |
| 5 | **Semáforo dual de respuesta** | ✅ v2.5 |
|   | *Modo A — días transcurridos* (cuando `termino_dias` no está definido): 🟢 0–5 días / 🟡 6–8 días / 🔴 9+ días | |
|   | *Modo B — fecha límite* (cuando `termino_dias` está definido): calcula `fecha_termino = fecha_ingreso + N días hábiles Colombia − 2 días`. 🟢 ≥2 días restantes / 🟡 0–1 días restantes / 🔴 pasó la fecha | |
| 6 | **Días hábiles Colombia** — Centralizado en `app/dias_habiles.py` (cálculo de Pascua por algoritmo de Gauss, festivos fijos, Ley Emiliani), usado también por Base Expedientes, SDQS y Expedientes Digitales | ✅ v2.5 · centralizado 2026-08-25 |
| 7 | **Excepción ANEXO EXPEDIENTE / ANEXO AL EXPEDIENTE** — Ambas variantes siempre aparecen en 🟢 sin conteo de días. Excluidas de alertas, dashboard y portal | ✅ v2.4 |
| 8 | **TIPO DE REQUERIMIENTO** — Select con 9 valores predefinidos: DERECHO DE PETICION, TUTELA, PROPOSICION DEL CONSEJO, REQUERIMIENTO ENTES DE CONTROL, PROCURADURIA, CONTRALORIA, PERSONERIA, ANONIMO, DIRECCION DE ASUNTOS DISCIPLINARIOS DE LA SECRETARIA JURIDICA GENERAL | ✅ v2.5 |
| 9 | **TÉRMINO (DIAS)** — Select: 3 / 5 / 10 / 15 / 30 días | ✅ v2.5 |
| 10 | **SINPROC PERSONERÍA** — Campo alfanumérico de texto libre (Ej: 2026-SP-001) | ✅ v2.5 |
| 11 | **Catálogos configurables** — CRUD de responsables y tipos de documento desde `/correspondencia/configurar` | ✅ v2.3 |
| 12 | **Tipo de Respuesta — combobox** — 11 opciones predefinidas + texto libre (HTML5 `<datalist>`) | ✅ v2.4 |
| 13 | **Importar desde Excel** — Detecta automáticamente formato antiguo (15 cols) vs. nuevo (19 cols, con SINPROC/TIPO_REQ/TERMINO/URL). Reemplaza todo | ✅ v2.5 |
| 14 | **Importar desde AgilSalud** — Carga `Documentos.xlsx`; filtra por 2 destinatarias; previsualización obligatoria; modo ADD | ✅ v2.4 |
| 15 | **Exportar a Excel** — Replica el formato oficial **SDS-CDO-FT-007** "CONTROL TRAMITES INTERNOS OCDI" (encabezado azul #333399): AÑO, MES, FECHA INGRESO DE OFICIO, NUMERO RADICADOS, ENTIDAD REMITENTE, ASUNTO, NUMERO SINPROC PERSONERIA, TIPO DE REQUERIMIENTO, TERMINO RESPUESTA (DIAS), TIPO DE DOCUMENTO, RESPONSABLE, CASO BMP, NUMERO RADICADO SALIDA, FECHA RADICADO DE SALIDA, TIPO DE RESPUESTA, TRÁMITE DE SALIDA, FECHA DE VENCIMIENTO TRAMITE | ✅ v5.6 |
| 16 | **Sin campo Correo Remitente** — Eliminado de formulario, lista, detalle, importadores y exportaciones (la columna `correo_remitente` permanece en la BD por compatibilidad histórica, pero no se usa) | ✅ v5.6 |

**Regla de negocio — semáforo:**
- Sin `termino_dias`: semáforo activo cuenta días desde `fecha_ingreso` hasta hoy. Al registrar `fecha_radicado_salida` pasa a ✅ Respondido.
- Con `termino_dias`: se calcula `fecha_termino_respuesta = fecha_ingreso + N días hábiles − 2 días`. Semáforo 🟢/🟡/🔴 según días restantes hasta esa fecha.
- Ambas variantes de ANEXO siempre son 🟢 sin conteo de días.

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
| 1 | **Exportar Excel consolidado** — Un único `.xlsx` con **4 hojas**: Base Expedientes, Exp. Digitales, Sala de Audiencias, **Control Autos** (verde oscuro). La hoja Correspondencia se exporta desde su propio módulo | ✅ v2.5 |
| 2 | **Importar Excel consolidado** — Carga el mismo archivo de vuelta reemplazando todo; modal de confirmación doble | ✅ v2.5 |

### Módulo 6 — AUTENTICACIÓN Y AUTORIZACIÓN

Sistema completo de control de acceso implementado en v3.1.

**Dos flujos de login** (`/login`):
- **Abogados:** eligen nombre en dropdown (sin contraseña) → acceso de solo lectura.
- **Secretarios / Jefe / Admin:** usuario + contraseña (PBKDF2-HMAC-SHA256, 260.000 iteraciones).

**Sesiones:** cookie `ocdi_session` (httponly, samesite=lax). Persisten hasta logout explícito (`POST /logout`). El middleware verifica la sesión en cada request; redirige a `/login` si no hay sesión activa.

**Credenciales iniciales:**

| Usuario | Rol | Persona |
|---------|-----|---------|
| `Secretario1` | secretario | ANDRES EDUARDO SANDOVAL MAYORGA |
| `Secretario2` | secretario | MAGDA XIMENA PAREDES LIEVANO |
| `AuxSecretario` | auxiliar | LUNA GICELL GUZMAN YATE |
| `JefeOficinaOcdi` | jefe | MARTHA PATRICIA AÑEZ MAESTRE |
| `Admin` | admin | JOSE DE JESUS BARAJAS SOTELO |

Los abogados (rol `abogado`, 10 a 2026-09-24) inician sesión por dropdown (sin contraseña). Se dan de alta desde `/admin/usuarios` o directamente en la tabla `usuarios`; todos los desplegables de abogados/responsables del sistema leen de esa tabla, no de listas fijas en el código.

**Modelo de permisos:**
- `admin` y `jefe`: acceso total a todos los módulos (bypass directo, no configurable).
- `secretario` y `auxiliar`: escritura habilitada por defecto (configurable por módulo).
- `abogado`: solo lectura por defecto (configurable por módulo).
- Guards `_pw(user, módulo)` en todos los `POST` endpoints de todos los routers.

**Panel de administración** (`/admin/usuarios` — solo admin/jefe):
- Ver todos los usuarios con rol y estado.
- Admin: activar/desactivar usuarios, cambiar contraseñas.
- Admin/Jefe: toggle de permisos de escritura por módulo y usuario.

**Logs de actividad** (`/admin/logs`):
- Registra: login, logout, crear, editar, eliminar, importar, cambiar_password, toggle_activo, actualizar_permisos.
- Filtros por módulo, acción y usuario. Paginación.

**Archivos clave:**
- `app/auth_utils.py` — hashing, verificación, `puede_escribir()`, `tpl()`, `registrar_log()`.
- `app/routers/auth.py` — endpoints de login/logout.
- `app/routers/admin_usuarios.py` — panel admin y logs.
- `app/templates/login.html` — pantalla dual.
- `app/templates/base_admin.html`, `admin_usuarios.html`, `admin_logs.html`.

### Módulo 7 — SDQS: QUEJAS Y SOLICITUDES (`/sdqs/`)

Módulo para el control de quejas, denuncias y solicitudes ciudadanas (SDQS) recibidas por la oficina, con semáforo de vencimiento basado en `fecha_asignacion` y `fecha_vencimiento`.

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Lista de SDQS** — Semáforo 🟢/🟡/🔴 por fila (según proporción de plazo transcurrido y días restantes), filtros por semáforo/responsable/mes/año/texto | ✅ v3 |
| 2 | **Gestión de SDQS** — Crear, ver, editar, eliminar. Campos: quejoso, correo (opcional), tema, competencia OCDI, BPM, responsable, radicado de salida, observaciones, tipología, valor institucional | ✅ v3 |
| 3 | **Hipervínculos** — `url_sdqs` y `url_rad_salida` opcionales, se muestran como enlaces clicables | ✅ v3 |
| 4 | **Importar/Exportar Excel** — 19+ columnas, detección de encabezado tolerante al reordenamiento, upsert por número de SDQS, round-trip completo (exporta e importa sin pérdida de datos) | ✅ v3 |
| 5 | **Reporte de vencimientos críticos** — Ver Módulo 10 | ✅ |
| 6 | **Integrado en Backup General** — Hoja SDQS en export/import y en el ZIP | ✅ |

**Regla de negocio — semáforo:** sin `fecha_vencimiento` no hay semáforo (se muestra "Sin plazo definido"). Verde = primera mitad del plazo. Amarillo = segunda mitad, con más de 2 días restantes. Rojo = 2 días o menos, o vencido.

---

### Módulo 8 — HERRAMIENTAS PDF (`/pdf-tools/`)

Utilidades de procesamiento de PDF/Word que corren **100% en local**, sin guardar ningún archivo subido en el servidor ni en la base de datos — se procesan en memoria y se devuelven directamente al navegador.

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | Unir varios PDF en uno solo | ✅ |
| 2 | Extraer páginas específicas | ✅ |
| 3 | Eliminar páginas específicas | ✅ |
| 4 | Rotar páginas | ✅ |
| 5 | Comprimir (niveles: leve/fuerte) | ✅ |
| 6 | Convertir PDF → Word y Word → PDF | ✅ |
| 7 | Agregar sello/marca de agua | ✅ |

**Dependencias:** `pypdf`, `PyMuPDF`, `pdf2docx`, `docx2pdf`.

---

### Módulo 9 — PRÉSTAMO DE EQUIPOS Y BIENES MUEBLES (`/equipos/`)

Control de préstamos de equipos de cómputo de la oficina y catálogo de bienes muebles asignados.

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Lista de préstamos** — Estado (Prestado/Devuelto), filtros | ✅ |
| 2 | **CRUD de préstamos** — Crear, ver, editar, marcar devolución, eliminar. Puede vincularse a un bien del catálogo | ✅ |
| 3 | **Catálogo de bienes muebles** (`/equipos/bienes/lista`) — Placa, serial, marca, modelo, responsable, importar/exportar Excel | ✅ |
| 4 | **Tile en portal** — Conteo de préstamos activos y total de bienes | ✅ |

---

### Módulo 10 — REPORTES DE VENCIMIENTOS (`/reportes/`)

Reporte Excel de revisión periódica (pensado para martes y jueves — ver banner en el portal) con los casos críticos de Correspondencia y SDQS.

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Reporte de vencimientos críticos** (`GET /reportes/vencimientos`) — Excel de 2 hojas: Correspondencia y SDQS, cada una con los registros 🔴 vencidos, 🟡 por vencer y ⚠️ sin plazo/fecha definida, coloreados por fila | ✅ |
| 2 | **Banner Mar/Jue en el portal** — Recordatorio visual con botón de descarga directa | ✅ |

Reutiliza las mismas funciones de cálculo de semáforo que los módulos de origen (`_calcular_semaforo_row` de Correspondencia y `_calcular_semaforo_sdqs` de SDQS) para que el reporte nunca diverja de lo que se ve en pantalla.

---

### Módulo 11 — MATRIZ DE SEGUIMIENTO — ABOGADOS (`/matriz/`)

Bitácora manual y exclusiva por abogado sobre en qué va cada trámite dentro del BPM (plataforma AgilSalud, donde OCDI radica y sube expedientes). No es un espejo automático de otros módulos: cada abogado la llena a mano como recordatorio de etapa y pendientes.

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Lista de trámites** — Filtros por expediente/BPM/asunto, tipo de trámite, etapa BPM y estado; paginación | ✅ v5.3 |
| 2 | **CRUD** — Crear, ver detalle, editar, eliminar (papelera de reciclaje) | ✅ v5.3 |
| 3 | **Aislamiento por dueño forzado server-side** — cada abogado solo ve/edita sus propias filas, sin importar lo que venga en el formulario o en la URL; admin/jefe supervisan todo | ✅ v5.3 |
| 4 | **Semáforo de fecha límite** — reutiliza `calcular_alerta()` (mismo cálculo de días hábiles Colombia que el resto del sistema) | ✅ v5.3 |
| 5 | **Historial de cambios y papelera** — mismo patrón que los 5 módulos de casos | ✅ v5.3 |
| 6 | **Exportar Excel** | ✅ v5.3 |
| 7 | **Permisos invertidos** — a diferencia del resto del sistema, aquí abogados tienen escritura por defecto y secretario/auxiliar solo supervisión de lectura | ✅ v5.3 |

Sin importador Excel (es manual por diseño). No integrado al Backup General/ZIP (decisión consciente por alcance).

---

### Módulo 12 — COMPENSATORIOS FIN DE AÑO (`/compensatorios/`)

Control de asistencia y horas compensadas de fin de año, a partir de la **Resolución 2307 de 2026** (modifica temporalmente la Resolución 2316 de 2023) de la Secretaría Distrital de Salud. Aplica a todos los roles del sistema (no solo abogados), ya que la resolución rige para todos los servidores públicos de la oficina.

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Autogestión de horas** — cada funcionario registra sus propias horas compensadas (hora extra AM/PM, sábado, jornada corta 24/31 dic); admin/jefe pueden ver y editar la de cualquiera | ✅ v5.4 |
| 2 | **Elección de turno de descanso** — 3 turnos configurables (21-24 dic / 28-31 dic / 4-7 ene), 34h a compensar cada uno | ✅ v5.4 |
| 3 | **Resumen de toda la oficina** — quién descansa hoy, quién elige qué turno, % de avance de cada uno con semáforo (verde=completo, amarillo=en progreso, rojo=vencido o en riesgo) | ✅ v5.4 |
| 4 | **Jornada corta 24 y 31 de diciembre** — 1.5h fijas de compensación por cada fecha, meta aparte de las 34h del turno | ✅ v5.4 |
| 5 | **Ajustes por justa causa** (admin/jefe) — incapacidades, licencias o permisos que reducen la meta de una persona, con motivo registrado | ✅ v5.4 |
| 6 | **Ciclo configurable, no hardcoded** — turnos, sábados habilitados, fechas y metas se editan desde `/compensatorios/ciclo`; se puede crear un ciclo nuevo cada fin de año sin tocar código | ✅ v5.4 |
| 7 | **Roster por permiso** — el listado de funcionarios del módulo respeta el permiso "puede ver" de cada persona (`/admin/usuarios`), no una lista fija en código; así se puede excluir a alguien (p.ej. contratistas, a quienes no aplica la resolución, o gente que ya no está) sin tocar su acceso al resto del sistema | ✅ v5.4 |
| 8 | **Papelera de reciclaje e historial** — mismo patrón que los demás módulos de casos | ✅ v5.4 |
| 9 | **Exportar Excel** — resumen de apoyo interno (no reemplaza el formato oficial SDS-THO-FT-106 V.1 que exige la resolución) | ✅ v5.4 |

No integrado al Backup General/ZIP ni a la Búsqueda Global (decisión consciente, mismo criterio que Matriz de Seguimiento).

---

### Portal Hub (`/`)

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Sidebar fijo** con los 11 módulos siempre visibles (respeta permisos por usuario), agrupados por uso real: Módulos Disciplinarios / Operación de Oficina / Herramientas y Respaldo / Administración | ✅ v5.2 |
| 2 | **Panel de bienvenida** — avatar de la oficina + 3 alertas compactas (vencimientos ≤3 días, reporte del día, estado del backup) en vez de banners apilados | ✅ v5.2 |
| 3 | **Grilla de tarjetas con stats en tiempo real**, hasta 5 columnas en monitores anchos, responsive | ✅ v5.2 |
| 4 | **Búsqueda global** integrada arriba del panel de bienvenida | ✅ v5.2 |
| 5 | **Botón Backup ZIP completo** — Descarga un `.zip` con 6 carpetas (una por módulo), cada una con su Excel actualizado | ✅ v2.5 |

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
| 8 | v2.5 — Módulo Control de Autos SDS-CDO-FT-001 + mejoras Correspondencia (3 campos, semáforo dual, URLs) | ✅ | 2026-04-21 |
| 9 | v3.1 — Sistema completo de autenticación y autorización (login dual, sesiones, permisos por módulo, panel admin, logs) | ✅ | 2026-04-23 |
| 10 | v3.2 — Formato de fechas DD/MM/YYYY en toda la interfaz | ✅ | 2026-04-23 |
| 11 | Fase 3 — Pruebas con usuarios reales + ajustes | ✅ En curso desde mayo 2026 | — |
| 12 | v3.3–v4.15 — Módulo SDQS, Herramientas PDF, formato de fechas, consecutivos y filtros en Control de Autos | ✅ | 2026-04 a 2026-05 |
| 13 | Auditoría integral del sistema (32 hallazgos, 24 corregidos) — ver `AUDITORIA.md` | ✅ | 2026-06-10 a 2026-06-17 |
| 14 | v5.0–v5.1 — Módulo Préstamo de Equipos y Bienes Muebles, eliminación de Mundial FIFA (código muerto), N/A en exportadores, mejoras UX (toasts, exportar en tiempo real), backup automático v2 (sqlite3.backup + ZIP + página de restauración), reporte de vencimientos críticos | ✅ | 2026-07 a 2026-08-19 |
| 15 | v5.2 — Índices de BD, tests de regresión, historial de cambios, papelera de reciclaje, búsqueda global, banner de vencimientos próximos | ✅ | 2026-08-19 a 2026-08-20 |
| 16 | v5.3 — Migración de todos los semáforos a días hábiles Colombia, enlaces de interés en el portal, módulo Matriz de Seguimiento (Abogados) | ✅ | 2026-08-25 a 2026-09-16 |
| 17 | v5.4 — Módulo Compensatorios Fin de Año (Resolución 2307 de 2026) | ✅ | 2026-09-18 |
| 18 | v5.5 — Cumplimiento del lineamiento SDS-TIC-LN-016 (Desarrollo Seguro de Software), implementado por fases | 🔄 En curso | desde 2026-09-22 |
| 19 | v5.6 — Renombrado "Control Trámites Internos OCDI" (antes Lista de Reparto de Abogados), eliminación del campo Correo Remitente, exportación replicando el formato oficial SDS-CDO-FT-007 | ✅ | 2026-09-22 |

---

### Changelog detallado

#### 2026-09-24 — Plan de continuidad y simulacro de restauración

- **Primer simulacro real de desastre**: clon limpio del repositorio + último backup de Google Drive descifrado + aplicación arrancada desde la copia. Resultado: 31/31 tablas con los mismos registros que producción y 14/14 páginas funcionando. Conclusión: el ZIP del backup sí restaura el sistema completo.
- **Riesgo detectado**: la contraseña de cifrado de los backups (Fase 5 LN-016) solo existía en `data/backup_password.key` del servidor. Si ese disco falla sin una copia de la contraseña, ningún backup se puede abrir. Se entregó al responsable para guardarla fuera del servidor.
- `RESTAURACION.md` reescrito como **plan de continuidad**: qué guardar fuera del servidor, qué se respalda, pérdida máxima de información y tiempo de recuperación, pasos desde `git clone`, firewall/IP, reactivación del backup, simulacro mensual y registro de pruebas. Se corrigieron la falta del paso de la contraseña y la credencial `admin/admin123`, que ya no existe. La página `/backup/restauracion` se actualizó igual.
- Nuevo `restaurar_backup.py`: `python restaurar_backup.py` restaura el último ZIP (pide la contraseña, aparta la BD existente en vez de borrarla, guarda la contraseña para los backups siguientes, verifica integridad y arranque). `--simulacro` prueba el último backup sin tocar el sistema en uso y deja evidencia en `simulacros_log.txt` en Drive.
- `configurar_tarea_backup.bat` ya no tiene fija la ruta de este PC (`c:\Users\JJBarajas\...`, que no existiría en otro PC); ahora usa la carpeta donde está el `.bat`. `backup_diario.py` acepta la variable `OCDI_BACKUP_DIR` para apuntar a otra carpeta de Drive sin tocar código.

#### 2026-09-24 — Alta de 2 abogadas

- **LUZ ALBA FARFAN CASALLAS** (planta, carrera administrativa) y **CARMEN ROSA AVILA ROBLES** (contratista) creadas con rol `abogado` y su `tipo_contrato`. Aparecen en el login y en todos los desplegables de abogado/responsable (Base Expedientes, Control de Autos, Control Trámites Internos, SDQS, Digitales, Sala, Equipos, Matriz) y en los filtros Planta/Contratista.
- Permisos: Luz con el mismo perfil de Nelcy (ve todos los módulos sin editarlos, escribe en su Matriz y en Compensatorios). Carmen con el perfil de los demás contratistas (ve Sala y Equipos, escribe en su Matriz, sin Compensatorios porque la Resolución 2307 aplica solo a planta).
- Los 7 autos históricos de Control de Autos a nombre de "LUZ ALBA FARFAN" se unificaron al nombre completo (ya usado en sus 4 expedientes de Base Expedientes). Se agregaron sus variantes cortas a los mapas de normalización de los importadores de Correspondencia y SDQS.

#### v5.5 — Cumplimiento SDS-TIC-LN-016 (en curso desde 2026-09-22)

La Secretaría Distrital de Salud emitió el lineamiento **SDS-TIC-LN-016 v2 "Desarrollo Seguro de Software"** (2026/09/11), de cumplimiento obligatorio para todo sistema de información de la entidad. Se está implementando por fases, sin interrumpir el uso diario de los 11 usuarios.

**Fase 1 — Eliminación de secretos hardcodeados (2026-09-22)**

- Las 5 contraseñas de los usuarios semilla (Admin, Jefe, 2 Secretarios, Auxiliar) vivían en texto plano en `app/database.py` desde el primer commit del proyecto (2026-02-24), expuestas en el historial público del repositorio de GitHub.
- Se rotaron esas 5 contraseñas directamente en la base de datos de producción (con backup previo).
- `_seed_usuarios()` ya no contiene contraseñas reales: lee variables de entorno opcionales (`OCDI_SEED_PWD_*`, ver `.env.example`) y, si no están definidas, genera una contraseña aleatoria fuerte que se imprime una sola vez en consola al primer arranque.
- Se reescribió el historial de Git (`git filter-repo`) para eliminar las 5 contraseñas de todos los commits pasados, verificado con búsqueda exhaustiva sobre todos los blobs del historial.
- Pendiente: `git push --force` a GitHub — el firewall de la red actual del equipo bloquea github.com; queda pendiente para cuando el usuario se conecte a la red donde sí hay salida (avisa antes de reintentarlo). El historial ya quedó limpio en local.

**Fase 2 — Bloqueo por intentos fallidos y política de contraseñas (2026-09-22)**

- Nuevas columnas `usuarios.intentos_fallidos` y `usuarios.bloqueado_hasta`. Tras 5 intentos fallidos consecutivos de login con usuario/contraseña, la cuenta queda bloqueada 15 minutos (se avisa de inmediato en el intento que dispara el bloqueo, no en el siguiente).
- Rate limiting en memoria por IP en `/login/credencial` y `/login/abogado` (máx. 20 intentos / 5 min) — protección adicional contra fuerza bruta/fuzzing distribuido entre varios usuarios desde el mismo origen. No requiere Redis ni almacén externo porque la app corre en un único proceso uvicorn.
- Política de contraseñas reforzada: mínimo 12 caracteres con mayúscula, minúscula, número y símbolo (antes solo exigía 8 caracteres sin más regla), aplicada tanto al crear un usuario como al cambiarle la contraseña desde `/admin/usuarios`.
- Cambiar la contraseña de un usuario desde el panel admin también limpia cualquier bloqueo activo que tuviera.
- Verificado con un script ad-hoc contra una base de datos temporal (nunca contra `data/ocdi.db`): 5 intentos fallidos bloquean la cuenta, el 6° intento con contraseña correcta sigue rechazado mientras dure el bloqueo. Tests nuevos en `tests/test_auth_seguridad.py` (12 casos, sin tocar la BD real).

**Fase 3 — Cabeceras HTTP de seguridad y manejo de errores fail-closed (2026-09-22)**

- Nuevo middleware `security_headers_middleware` en `app/main.py`: agrega `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` y `Permissions-Policy` a toda respuesta. La CSP permite `'unsafe-inline'` en script/style porque las plantillas actuales usan atributos `style=""` y `onclick=""` inline extensivamente — quitarlo requeriría refactorizar decenas de plantillas, así que queda documentado como deuda técnica futura. Aun así ya bloquea carga de recursos de dominios externos no autorizados, iframes ajenos y envío de formularios a otro origen.
- `Strict-Transport-Security` queda pendiente para la Fase 4 (TLS) — no tiene efecto sobre HTTP plano.
- Nuevo manejador global `@app.exception_handler(Exception)`: cualquier error no controlado se registra en el log del servidor con detalle técnico completo, pero al usuario solo se le muestra una página genérica ("Ocurrió un error inesperado"), nunca trazas de pila ni detalles de la excepción. Verificado forzando un error real de base de datos: el cliente nunca vio `sqlite3` ni ningún traceback en la respuesta.
- Cookie `ocdi_session` ahora fija `secure=True` automáticamente cuando la request llega por HTTPS (`request.url.scheme == "https"`) — no requiere tocar este código de nuevo cuando llegue la Fase 4.

**Fase 5 — Backups cifrados (2026-09-22)**

- `backup_diario.py` ahora cifra el ZIP con AES-256 (librería `pyzipper`, nueva dependencia en `requirements.txt`) antes de escribirlo en la carpeta sincronizada con Google Drive. Antes viajaba sin cifrar a la nube.
- La contraseña de cifrado vive en `data/backup_password.key` — carpeta que nunca se sube a git ni se sincroniza a Drive (solo el `.zip` cifrado viaja ahí), así que la llave y el dato cifrado quedan en dominios de seguridad separados. Se genera sola la primera vez que corre el backup y se imprime una sola vez en consola para guardarla en un gestor de contraseñas.
- El botón "Hacer backup ahora" del portal y la tarea programada de Windows siguen funcionando igual (llaman a la misma función `hacer_backup()`), ahora produciendo ZIPs cifrados.
- `/backup/restauracion` actualizada: explica que el ZIP requiere la contraseña y recomienda 7-Zip/WinRAR para extraerlo (el explorador de Windows integrado no siempre soporta AES-256).
- Verificado con un backup real de producción: el ZIP resultante está genuinamente cifrado (flag AES confirmado, `zipfile` estándar de Python rechaza leerlo sin contraseña), la contraseña correcta lo abre, una incorrecta lo rechaza.

**Fase 6 — Separar pruebas de la base de datos real (2026-09-22)**

- `app/database.py` ahora lee `DB_PATH` de la variable de entorno opcional `OCDI_DB_PATH`; sin ella, el comportamiento es exactamente el de siempre (`data/ocdi.db`).
- Nuevo `crear_bd_prueba.py`: genera una base de datos sandbox con los datos sintéticos que ya produce `init_db()` (5 usuarios semilla + 3 expedientes de ejemplo con nombres ficticios), para navegar la app real en el navegador sin tocar nunca la BD de producción.
- Nuevo `tests/conftest.py` con fixtures `db_temporal`/`client`: cualquier test que use `client` corre contra una base de datos temporal aislada, nunca `data/ocdi.db`. Formaliza como convención permanente lo que antes eran scripts ad-hoc de un solo uso al verificar las Fases 2 y 3.
- Nuevos tests en `tests/test_login_flujo.py` (4 casos) que reproducen como regresión automatizada las verificaciones manuales hechas en las Fases 2 y 3: bloqueo por intentos fallidos end-to-end, redirección sin sesión, rechazo de contraseña débil, presencia de cabeceras de seguridad.
- Verificado end-to-end: se levantó la app real (`uvicorn`) apuntando al sandbox vía `OCDI_DB_PATH`, respondió correctamente, y se confirmó que `data/ocdi.db` (262 expedientes reales) permaneció intacta durante todo el proceso.

**Fase 7 — Dependencias fijadas y escaneo de vulnerabilidades (2026-09-22)**

- Escaneo con `pip-audit` (base de datos OSV) encontró **34 vulnerabilidades conocidas reales** en `jinja2` (3, incluyendo RCE en el sandbox), `python-multipart` (8, DoS y path traversal) y `starlette` (14, incluyendo un SSRF vía UNC path específico de Windows en `StaticFiles` — relevante porque OCDI corre en Windows). También se encontró un CVE en `pypdf`, que `requirements.txt` dejaba sin fijar (`>=4.0.0`).
- Actualizado: `fastapi` 0.115.0→0.141.1, `jinja2` 3.1.4→3.1.6, `python-multipart` 0.0.9→0.0.31, `pypdf` →6.19.0. `starlette` se fija ahora explícitamente en 1.3.1 (antes solo dependencia transitiva de fastapi). Todas las dependencias que usaban `>=` ahora tienen versión exacta con `==`.
- La actualización de Starlette eliminó por completo el shim de compatibilidad de la firma antigua `TemplateResponse(name, context)` (antes solo generaba un warning, ahora rompía con un `TypeError` críptico de Jinja2). Se corrigió en un solo lugar (`app/template_utils.py`, clase `_CompatJinja2Templates`) en vez de tocar los 73 call sites del proyecto en 19 routers.
- Se encontró y corrigió de paso un bug preexistente: `app/routers/seguimiento.py` instanciaba `Jinja2Templates` directamente en vez de usar `make_templates()` (quedó fuera de la migración a `make_templates()` documentada en v3.2) — no tenía el filtro `fmt_fecha` ni, ahora, el fix de compatibilidad. Corregido para seguir el mismo patrón que los demás 18 routers.
- Nuevo `tests/test_smoke_paginas.py` (22 páginas, una por módulo): detectó el problema de `/seguimiento` automáticamente al correr la suite tras la actualización — exactamente el tipo de regresión que este test está pensado para atrapar en futuras actualizaciones de dependencias.
- Nuevo `SBOM.md`: inventario estructurado de las 12 dependencias directas con versión, propósito, licencia y estado de vulnerabilidades, más instrucciones para re-escanear.
- Verificado: `pip-audit` sobre el `requirements.txt` final reporta **0 vulnerabilidades conocidas**; 73/73 tests pasando; módulo de PDF probado funcionalmente tras el salto de 7 versiones de `pypdf` (unir, rotar, extraer páginas); servidor real (`uvicorn`) levantado con las nuevas dependencias contra el sandbox.
- **Pendiente operativo:** esta actualización queda instalada en el entorno Python del PC servidor pero solo toma efecto en el próximo reinicio de `iniciar.bat` (el proceso que ya está corriendo sigue con las versiones viejas en memoria) — reiniciar cuando sea un buen momento para la oficina, no es urgente-urgente porque el servidor activo no cambia de versión solo. Confirmado: el usuario reinició `iniciar.bat` el 2026-09-22 y el servidor respondió correctamente con las nuevas dependencias.

**Fase 8 — Cifrado en reposo de la base de datos: análisis y decisión (2026-09-22, documentado — sin ejecutar)**

El numeral 5.4.1.c.2 del lineamiento exige que los datos sensibles en reposo (bases de datos, archivos, respaldos) estén cifrados con AES-256. Hoy `data/ocdi.db` es un archivo SQLite plano sin ningún cifrado — quien tenga acceso físico o al sistema de archivos del PC servidor puede leerlo directamente.

Se evaluaron dos caminos:

1. **SQLCipher (cifrado a nivel de motor de base de datos)** — descartado por ahora. Requeriría reemplazar el módulo `sqlite3` estándar de Python por una variante cifrada en absolutamente todas las conexiones del proyecto (`app/database.py` y cada router que abre su propia conexión), en un sistema que está en producción activa sirviendo a 11 usuarios. Es la migración de mayor riesgo de todo el plan de cumplimiento — mucho más invasiva que cualquiera de las Fases 1-7 — y la instalación de la librería en Windows suele requerir compilar una extensión C o encontrar un paquete precompilado compatible. Se reserva como opción solo si Dirección TIC exige explícitamente cifrado a nivel de motor de BD y no acepta un control equivalente a nivel de sistema operativo.
2. **BitLocker (cifrado de disco a nivel de Windows) — recomendado.** Cifra todo el disco (o la carpeta `data/`) sin tocar ninguna línea de código de la aplicación; el riesgo de romper el sistema en producción es prácticamente nulo porque la app nunca se entera de que el disco está cifrado. Satisface la exigencia de "datos sensibles en reposo cifrados con AES-256" sin necesitar una migración de motor de base de datos. Requiere permisos de administrador de Windows para activarlo, que esta sesión de trabajo no tiene — debe activarlo un humano con esos permisos.

**Guía rápida para activar BitLocker** (ejecutar como Administrador en el PC servidor):
1. Panel de control → Sistema y seguridad → Cifrado de unidad BitLocker (o buscar "BitLocker" en el menú Inicio).
2. Sobre la unidad donde vive el proyecto (normalmente `C:`) → "Activar BitLocker".
3. Elegir cómo desbloquear el equipo al iniciar (contraseña, o TPM si el equipo lo tiene — la mayoría de PCs de oficina modernos sí).
4. **Guardar la clave de recuperación** que Windows genera — sin ella, si algo falla, se pierde el acceso al disco completo. Guardarla impresa en un lugar físico seguro de la oficina y/o en el gestor de contraseñas institucional, nunca en el mismo PC.
5. Elegir "Cifrar solo el espacio en disco usado" (más rápido) y "Nuevo modo de cifrado" si Windows lo ofrece.
6. Iniciar el cifrado — puede tardar desde minutos hasta unas horas según el tamaño del disco; el PC se puede seguir usando mientras cifra en segundo plano.

Sin ejecutar nada de código en esta fase — queda documentada para que el usuario la active cuando tenga acceso de administrador. **Fase 4 (TLS) y Fase 8 (BitLocker) quedan como las dos únicas fases pendientes del plan**, ambas esperando una acción del usuario fuera del código (hablar con Dirección TIC, y activar BitLocker con permisos de administrador, respectivamente).

**Auditoría del trabajo de las Fases 1-8 (2026-09-22)**

A pedido del usuario, se auditó todo el trabajo de cumplimiento LN-016 (commits `5d64ae7..4ba0e23`) con una revisión de código formal (3 agentes en paralelo sobre el diff completo) más verificación funcional directa. Se encontraron y corrigieron 4 bugs reales:

1. **Cabeceras de seguridad ausentes en la página de error 500** — `@app.exception_handler(Exception)` lo maneja Starlette en `ServerErrorMiddleware`, una capa por FUERA del stack de `@app.middleware("http")`; la respuesta de un error no controlado nunca pasaba por `security_headers_middleware`. Verificado con un 500 forzado: 0 de las 5 cabeceras llegaban al cliente. Corregido aplicando las cabeceras directamente dentro del manejador de excepciones.
2. **El bloqueo de login se auto-perpetuaba** — el contador de intentos fallidos nunca se reseteaba al expirar un bloqueo de 15 minutos (solo se reseteaba en un login exitoso). Efecto real: después del primer bloqueo, un solo error de tipeo volvía a bloquear la cuenta de inmediato por otros 15 minutos, indefinidamente — un usuario legítimo quedaba con una sola oportunidad por ventana para siempre. Corregido: el contador arranca de cero si el bloqueo anterior ya expiró.
3. **Reactivar un usuario no limpiaba un bloqueo previo** — si una cuenta estaba desactivada Y bloqueada por intentos fallidos a la vez, reactivarla desde `/admin/usuarios` no limpiaba el bloqueo, dejando al usuario sin poder entrar hasta 15 min más sin ninguna indicación de por qué. Corregido para que coincida con el comportamiento de "cambiar contraseña", que sí limpiaba el bloqueo.
4. **Contraseñas semilla generadas automáticamente solo se imprimían en consola** — a diferencia de la contraseña de cifrado de backups (que sí se persiste en `data/backup_password.key`), las contraseñas generadas para los 5 usuarios semilla en una instalación nueva solo aparecían en la consola; si se perdía el scrollback antes de copiarlas, quedaban irrecuperables (no habría ningún admin con sesión para resetearlas desde el panel). Corregido: ahora también se guardan en `data/seed_passwords_iniciales.txt` (fuera de git), igual que el patrón ya usado para el backup.

Se corrigieron además dos mejoras menores de robustez encontradas en la misma revisión: `cuenta_bloqueada()` ahora también tolera un valor inválido de tipo en `bloqueado_hasta` (antes solo capturaba `ValueError`, no `TypeError`), y el diccionario en memoria del rate limiter por IP (`_intentos_por_ip`) ahora purga las IPs sin actividad reciente en vez de crecer sin límite a lo largo de meses de actividad.

Se agregaron 6 tests de regresión permanentes para estos 4 bugs (`tests/test_login_flujo.py`, `tests/test_auth_seguridad.py`) y se centralizó en `tests/conftest.py` un fixture `admin_client` (y `admin_client_sin_raise`, necesario específicamente para probar el manejador de errores) que ya usan varios archivos de test, eliminando la duplicación del helper de login que había en `test_smoke_paginas.py`.

**Hallazgo aparte, no relacionado con LN-016:** al probar funcionalmente el módulo de Herramientas PDF tras el upgrade de `pypdf` (Fase 7), se encontró que el endpoint `/pdf-tools/sello` (marca de agua) está roto — `page.insert_text(..., rotate=45)` en `app/routers/pdf_tools.py` lanza `ValueError: bad rotate value` porque PyMuPDF solo acepta múltiplos de 90 en ese parámetro. Confirmado con `git log` que este bug es preexistente (commit `8178d87`, ajeno por completo a este trabajo) y no se corrigió por estar fuera del alcance de la auditoría de cumplimiento — queda pendiente como un hallazgo separado para cuando el usuario decida abordarlo.

Verificado tras los 4 arreglos: 78/78 tests pasando, servidor real respondiendo correctamente, base de datos de producción intacta (13 usuarios, 262 expedientes).

#### v5.6 — 2026-09-22

**Módulo Correspondencia renombrado a "Control Trámites Internos OCDI" + exportación con formato oficial SDS-CDO-FT-007**

- El título visible del módulo (antes "Lista de Reparto de Abogados") pasó a **"CONTROL TRAMITES INTERNOS OCDI"** en la página de lista (`corr_lista.html`), la tarjeta del portal, el texto de ayuda en `/admin/usuarios` y el manual generado (`generar_manual.py`). La URL (`/correspondencia/`), el nombre de la tabla en BD (`correspondencia`) y el encabezado del sidebar ("CORRESPONDENCIA · Reparto Abogados · OCDI") no cambiaron — el usuario solo pidió el título de la página, no la ruta ni la identificación del módulo en el sidebar.
- Se eliminó el campo **Correo Remitente** de todo lo visible: formulario de creación/edición, tabla de lista, vista de detalle, previsualización del importador de AgilSalud, exportación del módulo y las dos exportaciones que lo incluían dentro del Backup General (hoja "Correspondencia" y el Excel individual embebido en el ZIP `OCDI_Backup_Completo`). La columna `correo_remitente` **permanece en la base de datos** sin tocarse — los correos ya guardados de oficios existentes no se borraron, solo dejaron de mostrarse y exportarse, para no perder información histórica que el usuario no pidió eliminar.
- El botón "Exportar Excel" del módulo ahora replica el formato del formulario físico oficial **SDS-CDO-FT-007 "CONTROL TRAMITES INTERNOS OCDI"** (Excel de referencia suministrado por el usuario): mismas 17 columnas en el mismo orden (AÑO, MES, FECHA INGRESO DE OFICIO, NUMERO RADICADOS, ENTIDAD REMITENTE, ASUNTO, NUMERO SINPROC PERSONERIA, TIPO DE REQUERIMIENTO, TERMINO RESPUESTA (DIAS), TIPO DE DOCUMENTO, RESPONSABLE, CASO BMP, NUMERO RADICADO SALIDA, FECHA RADICADO DE SALIDA, TIPO DE RESPUESTA, TRÁMITE DE SALIDA, FECHA DE VENCIMIENTO TRAMITE) y el mismo azul de encabezado del formato físico (`#333399`, extraído directamente de la plantilla `.xls` adjunta con `xlrd`), con texto blanco en negrita. Se retiraron del export las dos columnas calculadas que no existen en el formato oficial (Fecha Revisión Sugerida y Días Transcurridos) — siguen calculándose y usándose para el semáforo dentro de la plataforma, solo no se exportan.
- El mismo rediseño (columnas + color) se aplicó también a la hoja de Correspondencia embebida en el Backup General en ZIP (`make_wb_correspondencia()` en `app/routers/backup.py`), para que ambas exportaciones del módulo queden consistentes entre sí.
- **Verificación de integralidad:** al quitar la columna Correo Remitente de la hoja 6 "Correspondencia" del Backup General (`app/routers/backup.py`), la lógica de restauración de esa misma hoja leía las columnas por posición fija (`row[5]`, `row[9]`, etc.) — se recalcularon a mano los 13 índices posicionales que se recorrían después de la columna eliminada para que la restauración de un backup no quedara desfasada una columna y mezclara datos de columnas distintas.
- El importador general (`/correspondencia/importar`, formato "exportado") mapea encabezados por nombre, no por posición, así que sigue aceptando tanto los archivos ya exportados con el formato anterior como los nuevos: se agregaron los nombres de columna nuevos como alias junto a los antiguos (`TERMINO RESPUESTA (DIAS)` / `TERMINO (DIAS)`, `NUMERO RADICADO SALIDA` / `N RADICADO SALIDA`). De paso se corrigió un bug preexistente ajeno a este cambio: la columna de Trámite de Salida se buscaba con el nombre `OBSERVACIONES`, que ningún export del sistema usó nunca (siempre fue `TRÁMITE DE SALIDA`), por lo que ese campo nunca se recuperaba al reimportar un Excel exportado por la propia plataforma; ahora busca primero `TRÁMITE DE SALIDA`.
- El importador de AgilSalud (`/correspondencia/importar-agilsalud`) dejó de leer y guardar el correo remitente del archivo `Documentos.xlsx` de origen, consistente con que el campo ya no se usa en ningún lugar del sistema.
- La carpeta dentro del ZIP de Backup General pasó de `02_Lista_Reparto_Abogados/` a `02_Control_Tramites_Internos_OCDI/`, solo el nombre de la carpeta — el archivo `.xlsx` y su contenido no cambiaron de estructura por este renombrado.

**Membrete institucional completo en el export (mismo día, segunda vuelta)**

- El usuario pidió además que el export replicara también la cabecera del formulario físico (escudo de la Alcaldía Mayor de Bogotá D.C. + Secretaría de Salud, título y fila Código/Fecha/Versión), no solo los encabezados de columna. El archivo `.xls` original venía protegido en "Vista protegida" por venir de Descargas; se desbloqueó con `Unblock-File` y se convirtió a `.xlsx` vía automatización COM de Excel (`win32com`, Excel sí está instalado en este equipo) únicamente para poder extraer la imagen del escudo incrustada — LibreOffice no está instalado en esta máquina. La imagen quedó guardada como asset permanente del proyecto en `app/static/img/escudo_bogota_sds.png`.
- Nueva función compartida `_agregar_membrete_control_tramites()` en `correspondencia.py` (reutilizada desde `backup.py`, mismo patrón ya usado para `_calcular_semaforo_row`): dibuja el escudo en A1:B2, el título "CONTROL TRAMITES INTERNOS OCDI" fusionado en C1:Q1 y la fila Código/Fecha (fecha del día de la exportación)/Versión en la fila 2, con bordes replicando la caja del formato físico. Los encabezados de columna, antes en la fila 1, pasaron a la fila 3, y los datos a partir de la fila 4 — en `/correspondencia/exportar` y en el Excel embebido en el ZIP de Backup General.
- **Verificación de integralidad:** mover los encabezados de columna de la fila 1 a la fila 3 habría roto silenciosamente la reimportación de cualquier Excel ya exportado por la plataforma, porque el importador general leía la fila de encabezados de forma fija (`min_row=1`). Se cambió esa lógica para que busque la fila cuya primera celda sea "AÑO" (hasta 10 filas), en vez de asumir una posición — así sigue aceptando tanto los exports antiguos (encabezado en fila 1) como los nuevos con membrete (fila 3).
- Verificado extremo a extremo contra `data/ocdi_sandbox.db`: exportar → reimportar el mismo archivo con membrete (los datos quedaron en las columnas correctas), el ZIP de Backup General con el mismo membrete embebido, y una vista previa renderizada del Excel (Excel COM → PDF → imagen con PyMuPDF) comparada visualmente contra la plantilla oficial.
- `.gitignore` ignora `*.png` por defecto (son "documentos de referencia", no código) con excepciones explícitas para los PNG que sí son assets de la app — se agregó `escudo_bogota_sds.png` a esa lista de excepciones; sin este ajuste el logo no se habría subido al repositorio y el export habría quedado sin escudo en cualquier otra instalación.

#### v5.4 — 2026-09-18

**Nuevo módulo: Compensatorios Fin de Año (`/compensatorios/`)**

A partir de la Resolución 2307 de 2026 (modifica temporalmente la Resolución 2316 de 2023) de la Secretaría Distrital de Salud, se creó un módulo para llevar el control de asistencia y horas compensadas de fin de año de todos los funcionarios de la oficina.

- **Autogestión de horas** — cada funcionario (no solo abogados: secretarios, auxiliar, abogados, admin, jefe) registra sus propias horas compensadas; admin/jefe ven y editan la de cualquiera. Mismo patrón de aislamiento por dueño que Matriz de Seguimiento, aplicado ahora a todos los roles.
- **Elección de turno de descanso** — 3 turnos (21-24 dic 2026 / 28-31 dic 2026 / 4-7 ene 2027), 34h a compensar cada uno, ventana de compensación fija (17-sep a 5-nov-2026) independiente del turno elegido.
- **Jornada corta 24 y 31 de diciembre** — 1.5h fijas de compensación por cada fecha trabajada, meta aparte (3h) en ventana posterior (6-10 nov 2026).
- **Semáforo de meta** — reutiliza las mismas clases visuales que ya existían para vencimientos de casos (vigente/próximo/vencido/sin-plazo), calculado sobre horas registradas vs. meta y días hábiles restantes.
- **Ciclo configurable, no hardcoded** — turnos, sábados habilitados, fechas y metas se administran desde `/compensatorios/ciclo` (solo admin/jefe), para reutilizar el módulo en años siguientes sin pedir cambios de código.
- **Ajustes por justa causa** — admin/jefe pueden reducir la meta de una persona (incapacidades, licencias) con motivo registrado, ya que el sistema no tiene una tabla de incapacidades propia.
- **Roster por permiso, no por lista fija** — el resumen de la oficina solo lista a quienes tienen "puede ver" habilitado para el módulo en `/admin/usuarios`; así se excluye a alguien (contratistas, a quienes no aplica la resolución, o personal que ya no está) sin afectar su acceso al resto del sistema. El día de publicación de este módulo se excluyó así a 7 personas señaladas por el usuario.
- **Papelera de reciclaje e historial de cambios**, mismo patrón que los demás módulos de casos. No integrado a Backup General/ZIP ni a Búsqueda Global (decisión consciente, mismo criterio que Matriz de Seguimiento).
- Probado con `TestClient` contra la base de datos real de producción (con backups previos): autogestión de abogado/secretario/admin, spoofing de nombre bloqueado, ajustes de justa causa, duplicados de Dic 24/31, papelera/restaurar/purgar, y exclusión de personal — todo verificado antes de dejar limpios los datos de prueba.

---

#### v5.3 — 2026-08-25 a 2026-09-16

**Semáforos migrados a días hábiles Colombia, enlaces de interés y Matriz de Seguimiento**

- Ver el detalle de la migración a días hábiles Colombia y los enlaces de interés del portal en la sección v5.2 más abajo (ambos cambios se hicieron sobre esa base, entre el 25 de agosto y el 4 de septiembre).

**Nuevo módulo: Matriz de Seguimiento — Abogados (`/matriz/`)**

Bitácora manual y exclusiva por abogado sobre en qué va cada trámite dentro del BPM (plataforma AgilSalud). No es un espejo automático de otros módulos — cada abogado la llena a mano como recordatorio de etapa y pendientes.

- **Aislamiento por dueño forzado server-side** — el filtro por abogado se fuerza siempre a su propio nombre (probado con un POST spoofeado, confirmado bloqueado); admin/jefe supervisan todas las filas.
- **Permisos invertidos respecto al resto del sistema** — abogados tienen escritura por defecto en su propia matriz; secretario/auxiliar quedan con visibilidad de solo supervisión, ajustable en `/admin/usuarios`.
- **Semáforo de fecha límite** reutilizando `calcular_alerta()` (mismo cálculo de días hábiles que el resto del sistema, sin lógica nueva).
- **Papelera de reciclaje e historial de cambios**, mismo patrón que los 5 módulos de casos existentes.
- Integrado al Portal (tile con contador propio para abogados, total para el resto) y a la Búsqueda Global (`/buscar`), respetando el mismo aislamiento por dueño.
- Sin importador Excel (es manual por diseño). No integrado al Backup General ni al ZIP (decisión consciente por alcance, no olvido).
- Verificado corriendo `init_db()` contra la base de datos real de producción (con backup previo) y probando end-to-end: aislamiento cruzado entre abogados, exportación a Excel, bloqueo de escritura para secretario, panel admin mostrando el módulo nuevo.

---

#### v5.2 — 2026-08-19 a 2026-08-20

**Mejoras de robustez y funcionalidad (revisión integral del sistema)**

- **Índices en las 26 tablas de la BD** — evita table scans en los filtros de Expedientes/SDQS/Correspondencia/Digitales y en la verificación de sesión de cada request (la consulta más frecuente de todo el sistema).
- **Tests automatizados** (`tests/`) — cobertura de regresión sobre los cálculos de semáforo y fechas de vencimiento que ya causaron bugs reales documentados en `AUDITORIA.md`, más un smoke test de orden de rutas.
- **Historial de cambios por registro** — en Expedientes, SDQS, Correspondencia, Digitales y Control de Autos, la vista de detalle muestra quién creó/editó/eliminó el registro y cuándo (reutiliza `logs_actividad`).
- **Papelera de reciclaje** — en los mismos 5 módulos, "Eliminar" ahora mueve el registro a una papelera restaurable en vez de borrarlo definitivamente. Solo admin/jefe pueden purgar en definitiva.
- **Búsqueda global** (`/buscar`) — un solo cuadro de búsqueda por número o nombre a través de Expedientes, SDQS, Correspondencia y Digitales.
- **Banner de vencimientos próximos en el portal** — aviso al entrar si hay indagaciones, investigaciones, SDQS o correspondencia venciendo en los próximos 3 días.
- Versión de la app en `main.py` y este README alineadas con la realidad del sistema (venían desactualizadas desde v3.2).

**Correcciones tras revisión de código (8 agentes en paralelo sobre el diff completo, 2026-08-20)**

- Los reimportadores de Excel (Expedientes, Correspondencia, Control de Autos) hacían `DELETE` de la tabla completa, incluyendo los registros en papelera — anulaba la función recién creada. Ahora excluyen los registros en papelera.
- El banner de vencimientos del portal enlazaba a filtros que no coincidían con lo que el banner realmente contaba (mostraba un número pero al hacer clic aparecía una lista distinta). Los botones "Ver" ahora van a la lista sin ese filtro desalineado.
- Expedientes no tenía la misma protección que SDQS contra crear un número que ya está en la papelera (ambos tienen un índice único). Se igualó el comportamiento: aviso claro en vez de error genérico.
- SDQS: reimportar un Excel que contenga un número que está en la papelera ahora lo restaura automáticamente, en vez de actualizarlo de forma invisible.
- Se reemplazaron 5 verificaciones de rol admin/jefe hardcodeadas por la constante compartida ya existente, para que no queden desincronizadas si el modelo de roles cambia.

**Rediseño del portal (`/`, 2026-08-20)**

El portal original apilaba 4 banners grandes antes de mostrar cualquier módulo y usaba tarjetas enormes en una sola columna — la mayoría de usuarios nunca bajaba a ver Sala, Equipos, Herramientas PDF o el juego, y no había ningún aviso de las funciones nuevas (papelera, historial).

- **Sidebar fijo** con todos los módulos siempre visibles (respeta permisos por usuario), agrupados por cómo se usan de verdad: Módulos Disciplinarios / Operación de Oficina / Herramientas y Respaldo / Administración.
- Los 3 banners de estado se consolidaron en un **panel de bienvenida** con 3 alertas compactas (vencimientos próximos, reporte del día, estado del backup) en vez de bloques apilados.
- **Grilla de tarjetas de hasta 5 columnas** para aprovechar monitores de 27″, responsive (sidebar deslizable + 1-2 columnas en pantallas angostas).
- **Escudo original de OCDI** (balanza de la justicia, sin usar marcas registradas) y el **avatar oficial de la oficina** en el header y el panel de bienvenida (`app/static/img/avatar_ocdi.png` y `avatar_ocdi_head.png`).
- Aviso "Novedades v5.2" señalando la papelera de reciclaje y el historial de cambios, que antes no aparecían en ningún lado del portal.
- Dirección visual acordada con el usuario mediante dos maquetas de revisión (Artifacts) antes de portar a la plantilla real (`app/templates/portal.html`).

**Fix: backup automático no funcionaba desde el 19 de agosto (2026-08-21)**

- El botón "Hacer backup ahora" del portal cambiaba a "Haciendo backup…" pero nunca enviaba el formulario — deshabilitar un botón `type="submit"` dentro de su propio `onclick` puede cancelar el envío nativo. Se movió esa lógica al `onsubmit` del formulario.
- `backup_diario.py` terminaba en error (encoding `cp1252` de la consola de Windows no soporta el emoji ✅) **después** de haber creado el backup con éxito — el ZIP quedaba bien pero el script reportaba fallo. Se forzó UTF-8 en la salida.
- Se descubrió que la tarea programada de Windows "OCDI_Backup_Diario" (Lun-Vie 4PM) **nunca había existido** en la máquina de producción, a pesar de estar documentada como activa desde el 19 de agosto — cero backups automáticos habían corrido nunca. Se recreó y se verificó con `schtasks /run` que sí tiene acceso real a la unidad de Google Drive.

**Semáforos migrados a días hábiles Colombia (2026-08-25)**

Los semáforos de SDQS, Base Expedientes y Expedientes Digitales contaban días calendario (`julianday` en SQL o `timedelta` en Python); solo Correspondencia ya usaba días hábiles, con su propia copia de las funciones de festivos. Esto hacía que el mismo caso pudiera verse "al día" en un módulo y "vencido" en otro para el mismo número de días, y que las alertas no coincidieran con el plazo legal real (que se cuenta en días hábiles).

- Nuevo módulo `app/dias_habiles.py` como fuente única de verdad: festivos fijos, Ley Emiliani (traslado al lunes siguiente) y festivos móviles de Semana Santa (algoritmo de Gauss para la Pascua). Reemplaza la copia que vivía solo en `correspondencia.py`.
- `calcular_alerta()` (Base Expedientes), `_calcular_semaforo_sdqs()` (SDQS), `_calcular_semaforo_row()` (Correspondencia) y las alertas azul/amarilla/roja de Expedientes Digitales ahora cuentan sobre esta misma función. En Digitales, como SQLite no puede contar días hábiles, el filtro de alerta se sacó del `WHERE` (antes usaba `julianday`) y se calcula en Python antes de armar la consulta.
- El preview de semáforo en el formulario de Expedientes (JavaScript, antes de guardar) replica el mismo algoritmo en el navegador para no mostrarle al usuario un número que luego el servidor corrija.
- Regla de conteo (confirmada con el usuario): el día de partida no se cuenta — del 12 al 25 de agosto de 2026 son 8 días hábiles, no 13 (calendario) ni 14. Cubierto en `tests/test_dias_habiles.py`.
- Efecto visible: los contadores de "días" en las listas y dashboards de los 4 módulos ahora pueden diferir de lo que mostraban antes (menos días que en calendario, porque fines de semana y festivos ya no cuentan) — es el comportamiento correcto, no una regresión.

**Enlaces de interés en el portal (2026-09-04)**

- Nueva sección "Enlaces de interés" en el Portal Central con accesos directos a las plataformas externas que el equipo usa a diario: AgilSalud, Mesa de Ayuda (Aranda / Línea 55), Intranet SDS, Isolución, SharePoint OCDI y el aplicativo OCDI local (marcado como disponible solo dentro de la red de la oficina).

---

#### v5.0–v5.1 — 2026-07 a 2026-08-19

- **Nuevo módulo: Préstamo de Equipos y Bienes Muebles** (`/equipos/`) — control de préstamos + catálogo de bienes, importar/exportar Excel.
- **Eliminación de la Polla Mundial FIFA 2026** — módulo experimental retirado como código muerto (decisión confirmada del usuario, no se revive).
- **N/A en celdas vacías** en todos los exportadores Excel del sistema (Expedientes, SDQS, Correspondencia, Digitales, Control de Autos, Equipos, Seguimiento, Backup).
- **Exportar con filtros en tiempo real** — los botones "Exportar Excel" de Control de Autos, SDQS, Expedientes y Seguimiento leen los filtros actuales del formulario en el momento del clic (antes requerían presionar "Filtrar" primero).
- **Badge PENDIENTE + filtro por Tipo de Respuesta** en Correspondencia.
- **Sistema de backup automático v2** — `backup_diario.py` reescrito con `sqlite3.backup()` (seguro en modo WAL), ZIP con la BD + catálogos JSON, tarea programada Lunes–Viernes 4PM, página de restauración dentro de la plataforma (`/backup/restauracion`) y banner en el portal cuando el backup del día está pendiente.
- **Reporte de vencimientos críticos** (`/reportes/vencimientos`) — Excel de Correspondencia + SDQS para revisión Mar/Jue, con banner en el portal.

---

#### Auditoría integral — 2026-06-10 a 2026-06-17

Revisión exhaustiva de los 11 módulos de negocio + arquitectura + barrido de rutas, actuando como auditor senior. **32 hallazgos (H1–H32), 24 corregidos** con cambios de código verificados contra datos reales. Documento completo: [`AUDITORIA.md`](AUDITORIA.md).

Patrones sistémicos corregidos en todo el código: colisión de rutas por orden de registro en FastAPI, Dashboard con cálculo divergente de su propia Lista, rutas de detalle sin propagar mensajes de confirmación. Pendientes de acción manual del usuario (no son bugs de código): corregir un número de auto duplicado en Control de Autos, y revisar ~136 SDQS históricos sin fecha de vencimiento.

---

#### v3.3–v4.15 — 2026-04 a 2026-05

- **Nuevo módulo: SDQS — Quejas y Solicitudes** (`/sdqs/`) con semáforo de vencimiento propio, importar/exportar Excel de 19+ columnas y hipervínculos opcionales.
- **Nuevo módulo: Herramientas PDF** (`/pdf-tools/`) — unir, extraer, eliminar páginas, rotar, comprimir, convertir PDF↔Word, agregar sello. Procesamiento 100% local, sin almacenamiento de archivos subidos.
- **Control de Autos** — número de auto consecutivo sugerido automáticamente, lista ordenada por más reciente, exportación con filtros.
- **Correcciones de datos** — normalización de nombres de auto (ej. "VINCULACIÓN A INVESTIGACIÓN DISCIPLINARIA"), fix de fechas en importador de Expedientes, fix de crash por UNIQUE en SDQS.

---

#### v3.2 — 2026-04-23

**Formato de fechas DD/MM/YYYY en toda la interfaz**

- Todas las fechas visibles en pantalla ahora se muestran en formato **DD/MM/YYYY** (o **DD/MM/YYYY HH:MM:SS** para timestamps).
- Nuevo archivo `app/template_utils.py` con función `_fmt_fecha()` y factory `make_templates()`.
- `_fmt_fecha` convierte cualquier string `YYYY-MM-DD` o `YYYY-MM-DD HH:MM:SS` al formato local; retorna vacío para valores nulos (compatible con `{{ valor or '—' }}`).
- `make_templates(directory)` reemplaza `Jinja2Templates(directory)` en todos los routers; registra `fmt_fecha` como filtro Jinja2 automáticamente.
- **Todos los 13 routers** actualizados para usar `make_templates()` (admin_usuarios, auth, autos, backup, control_autos, correspondencia, dashboard, digitales, expedientes, importar, portal, sala, seguimiento).
- **Plantillas actualizadas** con filtro `| fmt_fecha`: detalle.html, lista.html, corr_lista.html, corr_detalle.html, corr_dashboard.html, digitales_lista.html, digitales_detalle.html, ca_lista.html, ca_detalle.html, admin_logs.html.
- **No se modificaron** los atributos `value=` de inputs `type="date"` (siguen en ISO, que es lo que el navegador y SQLite requieren internamente).
- **No se modificaron** la lógica Python, consultas SQL ni almacenamiento en BD (todo sigue en ISO internamente).

---

#### v3.1 — 2026-04-23

**Sistema completo de autenticación y autorización**

- **Dos flujos de login** en una sola pantalla (`/login`): dropdown de abogados (sin contraseña) y formulario usuario/contraseña para secretarios/jefe/admin.
- **Contraseñas PBKDF2-HMAC-SHA256** (260.000 iteraciones) almacenadas como `salt$hash` en la BD. Sin texto plano en ningún punto.
- **Sesiones por cookie** `ocdi_session` (httponly, samesite=lax). Middleware HTTP verifica cada request; no expiran hasta logout explícito.
- **Modelo de permisos por módulo:** 6 módulos del sistema registrados en `MODULOS_SISTEMA`. Roles `admin`/`jefe` tienen acceso total (bypass). Roles `secretario`/`auxiliar` escritura por defecto. Rol `abogado` solo lectura por defecto. Todo configurable en `/admin/usuarios`.
- **Guards** `_pw(user, módulo)` aplicados en **todos los POST endpoints** de todos los routers. Respuesta: `RedirectResponse(...?msg=sin_permiso, 303)`.
- **4 tablas nuevas en BD:** `usuarios`, `sesiones`, `permisos_modulo`, `logs_actividad`. Seed automático de 12 usuarios al primer arranque.
- **Panel admin** (`/admin/usuarios`): toggle activo/inactivo, cambio de contraseñas, matriz de permisos por módulo.
- **Log de actividad** (`/admin/logs`): cada escritura queda registrada con usuario, rol, módulo, detalle e IP. Filtros y paginación.
- **Flash message `sin_permiso`** agregado a todos los base templates.
- Commit: `8273187`

---

#### v2.5 — 2026-04-21

**Nuevo módulo: Control de Autos de Sustanciación y/o Trámites (`/control-autos/`)**

- Implementación completa del formato oficial **SDS-CDO-FT-001 v4** en web.
- **6 campos de datos:** EXPEDIENTE, NÚMERO DEL AUTO, FECHA DEL AUTO, ASUNTO AUTO, ABOGADO RESPONSABLE, OBSERVACIONES.
- **ABOGADO RESPONSABLE:** `<select>` con 11 abogados en mayúsculas. El mismo select se usa en el filtro de la lista.
- **ASUNTO AUTO:** `<select>` con 26 tipos oficiales de autos de sustanciación. Admite valor fuera de lista en registros existentes.
- **NÚMERO DEL AUTO:** acepta consecutivos numéricos (001, 002…) o la palabra "DIGITAL". Badge azul para numéricos, morado para DIGITAL en la lista.
- **Importar Excel:** acepta el formato original del OCDI (hoja "NUEVO", datos desde fila 8, encabezados en fila 7) y el formato exportado (hoja "CONTROL AUTOS", desde fila 7). Filtra filas de glosario del pie de página comprobando `len(numero_auto) > 20`.
- **Exportar Excel:** replica el encabezado oficial con institución, código SDS-CDO-FT-001, versión 4 y firmantes.
- **Tile en portal:** muestra conteo de autos con pluralización correcta.
- **Backup General integrado:** Hoja 4 "Control Autos" (cabecera verde `#2E7D32`) en export/import del backup. ZIP incluye carpeta `05_Control_Autos_Sustanciacion/`.
- **Base de datos:** nueva tabla `control_autos_sustanciacion` (10 campos). Migración automática si BD existente.
- **Fix corrección de datos:** 96 registros importados tenían nombres abreviados en ABOGADO_RESPONSABLE (ej. "ANDRES SANDOVAL" → "ANDRES EDUARDO SANDOVAL MAYORGA"). Se normalizaron los 7 patrones abreviados mediante SQL UPDATE con LIKE. LUZ ALBA FARFAN (7 registros, no en lista predefinida) se dejó tal cual.
- **Fix ca_form.html:** Faltaba `{% endif %}` antes de `{% endblock %}` en `{% block heading %}`, causando `TemplateSyntaxError` (Internal Server Error 500) en todos los endpoints del módulo.

---

**Mejoras módulo Correspondencia (`/correspondencia/`)**

- **3 nuevos campos en BD** (migración automática para BDs existentes):
  - `sinproc_personeria TEXT` — número alfanumérico de la Personería (Ej: 2026-SP-001)
  - `tipo_requerimiento TEXT` — tipo de requerimiento con 9 valores predefinidos
  - `termino_dias INTEGER` — plazo legal de respuesta en días (select: 3/5/10/15/30)
  - `correspondencia_radicados_salida.url TEXT` — URL del radicado de salida para hipervínculo

- **Semáforo dual de respuesta:** el cálculo de semáforo se movió completamente a Python (`_calcular_semaforo_row()`):
  - *Sin `termino_dias`:* misma lógica anterior de días transcurridos (verde ≤5 / amarilla 6-8 / roja ≥9).
  - *Con `termino_dias`:* calcula `fecha_termino_respuesta = fecha_ingreso + N días hábiles Colombia − 2 días`. Semáforo según días restantes hasta esa fecha (verde ≥2 / amarilla 0-1 / roja <0).
  - Los tooltips del semáforo en la lista muestran la fecha límite y días restantes cuando aplica.

- **Días hábiles Colombia** — función `_add_dias_habiles(inicio, dias)`:
  - Festivos fijos: 1-ene, 1-may, 20-jul, 7-ago, 8-dic, 25-dic.
  - Festivos Ley Emiliani (siguiente lunes si no cae en lunes): 6-ene, 19-mar, 29-jun, 15-ago, 12-oct, 1-nov, 11-nov.
  - Festivos basados en Pascua (algoritmo Gauss): Jueves Santo (−3), Viernes Santo (−2), Ascensión (Ley Emiliani, +39), Corpus Christi (Ley Emiliani, +60), Sagrado Corazón (Ley Emiliani, +68).

- **Hipervínculos radicado de salida:** en el formulario de edición se muestra una tabla con radicado + URL; en el detalle el radicado es un `<a target="_blank">`. En la lista el texto queda plano (la URL se ve en detalle/editar).

- **Formulario `corr_form.html`** reorganizado en 4 secciones:
  1. Identificación del Oficio
  2. Contenido del Oficio
  3. **Datos del Requerimiento** (nueva): SINPROC Personería, Tipo de Requerimiento, Término (Días)
  4. Respuesta / Salida

- **Renombrado de etiquetas UI** (sin cambio en columna BD):
  - "Origen AGILSALUD" → **Entidad**
  - "Trámite de Salida" → **Observaciones**

- **Lista `corr_lista.html`:** nuevas columnas "Tipo Req." y "Término"; columna "Días / Límite" muestra fecha ISO cuando hay `termino_dias`, o conteo de días si no lo hay.

- **Exportar (19 columnas):** ENTIDAD, SINPROC PERSONERIA, TIPO DE REQUERIMIENTO, TERMINO (DIAS), N RADICADO SALIDA, URL RADICADO SALIDA, OBSERVACIONES (renombradas desde ORIGEN y TRAMITE DE SALIDA).

- **Importar — detección de formato:**
  - Formato original (hojas con nombres de meses): sin cambios.
  - Formato exportado — detecta si es **nuevo (≥19 cols)** o **antiguo (15 cols)** leyendo el encabezado; en el nuevo lee SINPROC, TIPO_REQ, TERMINO, URL.

- **Backup ZIP:** la hoja Correspondencia del ZIP también pasa a 19 columnas con el nuevo formato.

- **Filtrado semáforo en Python:** el endpoint `/correspondencia/` ya no usa SQL para filtrar por semáforo; recupera todas las filas que cumplen los otros filtros, calcula el semáforo en Python para cada fila y aplica el filtro en memoria. Esto permite que los dos modos de semáforo funcionen correctamente en el filtro lateral.

---

#### v2.4 — 2026-04-15 · commits `070095a` → `daa9f11`

**Módulo Correspondencia — mejoras:**

- **Excepción ANEXO AL EXPEDIENTE:** Se extiende la regla de negocio de "ANEXO EXPEDIENTE" a la variante "ANEXO AL EXPEDIENTE". Ambas siempre aparecen en 🟢 verde con días `—` (NULL en SQL, guion en pantalla). Excluidas de: semáforo activo, dashboard rojo/amarillo, portal badge de alertas, tabla de críticos y backup ZIP.

- **Importador AgilSalud** (`GET/POST /correspondencia/importar-agilsalud`): Nueva ruta de dos pasos para cargar el archivo `Documentos.xlsx` exportado de AgilSalud.
  - **Filtrado automático:** solo conserva registros cuyo destinatario sea "MARTHA PATRICIA AÑEZ MAESTRE" o "MABEL GICELA HURTADO SANCHEZ".
  - **Columnas mapeadas:** Número de radicado → `n_radicado`, Dependencia Remitente → `origen`, Correo Electrónico Remitente → `correo_remitente`, Fecha de radicación → `fecha_ingreso` + `mes` + `anio`, Asunto → `asunto`.
  - **Previsualización obligatoria:** muestra tabla antes de confirmar; usa JSON oculto en form para pasar datos del preview al confirm.
  - **Modo ADD:** no borra datos existentes; solo agrega nuevos registros.

- **Campo `correo_remitente`:** Nueva columna TEXT en `correspondencia`. Migración automática en `init_db()`.

- **Fix crítico de orden de rutas:** Rutas `/importar-agilsalud` reubicadas **antes** de `/{reg_id}` en el router para evitar captura por el path pattern `[^/]+`.

---

#### v2.3 — 2026-04-14 · commits `536d120` → `aa1899a`

**Nuevo módulo: Lista de Reparto de Abogados (`/correspondencia/`)**

- Control completo de oficios con 8 rutas: dashboard, lista, nuevo, detalle, editar, eliminar, importar, exportar, configurar catálogos.
- **Semáforo de respuesta** por `julianday()` SQLite: 🟢 0–5 días / 🟡 6–8 días / 🔴 9+ días / ✅ Respondido.
- **Radicados de salida múltiples:** tabla `correspondencia_radicados_salida` con CASCADE.
- **Catálogos configurables** desde `/correspondencia/configurar`.
- **Portal actualizado:** nuevo tile con contador y badge de alerta roja.

**Nuevo módulo: Exportar/Importar General (`/backup/`)**

- Excel único con 3 hojas (luego ampliado a 4 en v2.5) + Backup ZIP completo por módulo.

---

#### v2.2 — 2026-03-03 · commits `4d204ee` → `7b8f24e`

- Hub Portal (`/`), Módulo Expedientes Digitales, Sala de Audiencias, sidebars independientes por módulo, sistema de alertas por días (julianday SQLite).

---

#### v2.1 — 2026-02-27 · commit `8e33f33`

- Paginación, filtros adicionales, ordenamiento de columnas, búsqueda inteligente, modal exportar, nuevas métricas en dashboard. Fix alertas con `#VALUE!`.

---

#### v2.0 — 2026-02-27 · commit `fbf2906`

- Corrección crítica de importación: 243 expedientes importados correctamente desde la hoja correcta.

---

#### v1.0 — 2026-02-25 · commit `635a1d6`

- Sistema completo inicial: dashboard, gestión de expedientes (CRUD), seguimiento mensual, control de autos, importar/exportar Excel.

---

## 9. Decisiones técnicas tomadas

| Fecha | Decisión | Justificación |
|-------|----------|---------------|
| 2026-02-24 | **SQLite** como base de datos | Gratuito, sin instalación, archivo único fácil de respaldar. 11 usuarios concurrentes es manejable con WAL mode activado. |
| 2026-02-24 | **Interfaz web** (no app de escritorio) | Los clientes solo necesitan un navegador. Sin instalación en los 10 PCs usuario. |
| 2026-02-24 | **Python + FastAPI** como backend | Ecosistema maduro, fácil de instalar en Windows, openpyxl para Excel. |
| 2026-02-24 | **PC de la oficina como servidor** en la LAN | No requiere servidores externos ni pagos. Usa la red de cable existente de la SDS. |
| 2026-02-25 | **Construcción por fases** empezando con módulos críticos | El prototipo construye los cimientos compartidos. Los módulos restantes se añaden sin reescribir lo existente. |
| 2026-02-27 | **`date()` de SQLite** en todos los filtros de fecha | Previene falsos positivos cuando hay valores no-fecha en columnas de fecha (errores `#VALUE!` de Excel). |
| 2026-02-27 | **`CAST(n_expediente AS INTEGER)`** en búsqueda numérica | Permite buscar "046" y encontrar expedientes guardados como "46" (sin cero a la izquierda, como los lee Excel). |
| 2026-03-03 | **`julianday()` de SQLite** para alertas de días | Calcula días transcurridos directamente en SQL sin lógica Python post-proceso. |
| 2026-03-03 | **Rutas estáticas antes de `/{id}`** en cada router | FastAPI evalúa rutas en orden de registro. Rutas como `/importar` deben ir antes de `/{id}` para no ser capturadas como parámetro. |
| 2026-04-14 | **Tabla separada `correspondencia_radicados_salida`** para radicados de salida | Un oficio puede tener N radicados de salida. Tabla hija con CASCADE permite agregar/eliminar individualmente. |
| 2026-04-14 | **HTML5 `<datalist>`** para Tipo de Respuesta | Ofrece sugerencias predefinidas sin restringir el texto libre. |
| 2026-04-14 | **`RESPONSABLE_MAP`** en importación de Correspondencia | El Excel histórico tiene 21 variantes sucias del mismo nombre. El mapa normaliza al vuelo durante la importación. |
| 2026-04-14 | **Backup ZIP estructurado** desde el portal | Un solo clic genera un respaldo completo organizado por módulo, sin conocimiento técnico. |
| 2026-04-15 | **`IN (...)` para variantes de ANEXO** en semáforo | Cubre ambas variantes del texto en un solo chequeo, tanto en SQL como en Python. |
| 2026-04-15 | **Importador AgilSalud con previsualización de 2 pasos** | JSON oculto en form pasa datos del preview al confirm sin re-leer el archivo. |
| 2026-04-21 | **Listas predefinidas para Control de Autos** (`ABOGADOS_RESPONSABLES`, `ASUNTOS_COMUNES`) | El formato SDS-CDO-FT-001 tiene valores estandarizados que no deben variar libre. Selects garantizan consistencia; admiten valores fuera de lista en edición para compatibilidad histórica. |
| 2026-04-21 | **Filtro de pie de página en importación de Control Autos** (`len(numero_auto) > 20`) | El Excel oficial tiene filas de glosario al final (ej. "NUMERO DEL EXPEDIENTE — Corresponde al..."). Los números de auto válidos son ≤7 caracteres ("DIGITAL" o "001"). La longitud descarta las filas de descripción sin necesitar leer el contenido. |
| 2026-04-21 | **Semáforo Correspondencia movido a Python** | La nueva lógica de fecha límite requiere calcular días hábiles (Pascua, Ley Emiliani), imposible en SQLite. Se recuperan todas las filas que cumplen los filtros no-semáforo y se filtra el semáforo en Python. Con ~300 filas el overhead es nulo. |
| 2026-04-21 | **`fecha_termino = fecha_ingreso + N días hábiles − 2`** | Los 2 días de "colchón" sirven como alerta temprana (amarillo) antes del vencimiento real, permitiendo actuar a tiempo. |
| 2026-04-21 | **`url TEXT` en `correspondencia_radicados_salida`** | Los radicados de salida tienen un hipervínculo en el sistema AgilSalud. Almacenar la URL en la BD permite mostrar el enlace directo sin salir de la aplicación. |
| 2026-04-23 | **PBKDF2-HMAC-SHA256 para contraseñas** | Estándar recomendado para entornos sin dependencias externas. 260.000 iteraciones con salt aleatorio. No requiere `bcrypt` ni librerías adicionales — está en la stdlib de Python. |
| 2026-04-23 | **Login dual en una sola pantalla** | Abogados: dropdown rápido (sin contraseña — solo lectura). Resto del personal: formulario usuario/contraseña. Un solo HTML con dos paneles simplifica la experiencia y la navegación. |
| 2026-04-23 | **`ROLES_SUPERUSUARIO` bypass permisos** | Admin y jefe tienen acceso total sin verificar la tabla `permisos_modulo`. Si un admin accidentalmente desactiva todos sus permisos, no queda bloqueado del sistema. |
| 2026-04-23 | **Filtro Jinja2 `fmt_fecha` + `make_templates()`** | Las fechas se almacenan en ISO (`YYYY-MM-DD`) en SQLite para que las comparaciones SQL funcionen correctamente. La conversión a `DD/MM/YYYY` ocurre únicamente en la capa de presentación, centralizada en un filtro Jinja2 registrado en todos los templates automáticamente. Cero cambios en lógica Python o SQL. |

---

## 10. Estructura de archivos

```
SDS_OCDI/
├── app/
│   ├── __init__.py
│   ├── main.py                             # FastAPI app — middleware de sesión + registra routers
│   ├── database.py                         # Esquema SQLite (16 tablas), get_db(), init_db(), seed_usuarios()
│   ├── auth_utils.py                       # hash_password, verify_password, puede_escribir, tpl, registrar_log
│   ├── template_utils.py                   # make_templates() + filtro fmt_fecha (DD/MM/YYYY)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                         # /login, /login/abogado, /login/credencial, /logout
│   │   ├── admin_usuarios.py               # /admin/usuarios — gestión usuarios y permisos
│   │   ├── portal.py                       # GET /  → hub portal con tiles y stats
│   │   ├── expedientes.py                  # /expedientes — Lista, CRUD, exportar Excel
│   │   ├── dashboard.py                    # /dashboard — métricas BASE 2023U
│   │   ├── importar.py                     # /importar — cargue masivo Excel BASE
│   │   ├── seguimiento.py                  # /seguimiento — actuaciones mensuales
│   │   ├── digitales.py                    # /digitales/* — módulo completo digitales 2025-2026
│   │   ├── sala.py                         # /sala/* — sala de audiencias
│   │   ├── backup.py                       # /backup/* — exportar/importar general (7 hojas) + ZIP (6 carpetas)
│   │   ├── correspondencia.py              # /correspondencia/* — lista de reparto abogados
│   │   ├── control_autos.py               # /control-autos/* — autos de sustanciación SDS-CDO-FT-001
│   │   ├── sdqs.py                         # /sdqs/* — quejas y solicitudes ciudadanas
│   │   ├── pdf_tools.py                    # /pdf-tools/* — utilidades PDF/Word locales, sin almacenamiento
│   │   ├── equipos.py                      # /equipos/* — préstamo de equipos + catálogo de bienes muebles
│   │   └── reportes.py                     # /reportes/vencimientos — reporte Excel de críticos
│   ├── static/
│   │   ├── css/style.css                   # Estilos completos (sin dependencias externas)
│   │   └── js/app.js                       # Lógica de formulario, tabs, escaneos dinámicos
│   └── templates/
│       ├── login.html                      # Pantalla de login dual (dropdown abogados + form credenciales)
│       ├── base.html                       # Sidebar BASE EXPEDIENTES (con widget usuario/logout)
│       ├── base_digitales.html             # Sidebar EXP. DIGITALES
│       ├── base_sala.html                  # Sidebar SALA AUDIENCIAS
│       ├── base_correspondencia.html       # Sidebar LISTA DE REPARTO
│       ├── base_control_autos.html         # Sidebar CONTROL DE AUTOS
│       ├── base_admin.html                 # Sidebar ADMINISTRACIÓN (con atajos a todos los módulos)
│       ├── admin_usuarios.html             # /admin/usuarios — tabla usuarios + matriz permisos
│       ├── admin_logs.html                 # /admin/logs — historial de actividad paginado
│       ├── portal.html                     # Hub sin sidebar — 6 tiles + botón backup ZIP
│       ├── lista.html                      # /expedientes lista
│       ├── form.html                       # Crear/editar expediente BASE (7 bloques)
│       ├── detalle.html                    # Detalle expediente BASE
│       ├── dashboard.html                  # Dashboard BASE 2023U
│       ├── importar.html                   # Importar Excel BASE
│       ├── exportar_filtrado.html          # Exportar reporte personalizado
│       ├── seguimiento.html                # Seguimiento mensual
│       ├── autos.html                      # Control de autos BASE
│       ├── backup.html                     # Exportar/Importar general (4 módulos)
│       ├── digitales_lista.html            # /digitales/ lista con filtros tipo Excel
│       ├── digitales_dashboard.html        # /digitales/dashboard con tarjetas de alerta
│       ├── digitales_detalle.html          # /digitales/{id} detalle + comunicaciones
│       ├── digitales_form.html             # Crear/editar expediente digital
│       ├── digitales_comunicaciones.html   # /digitales/comunicaciones vista global
│       ├── digitales_importar.html         # Importar Excel digitales
│       ├── sala.html                       # /sala/ calendario mensual
│       ├── sala_form.html                  # Crear/editar evento de sala
│       ├── corr_lista.html                 # /correspondencia/ lista con semáforo dual
│       ├── corr_dashboard.html             # /correspondencia/dashboard
│       ├── corr_detalle.html               # /correspondencia/{id} detalle + hipervínculos
│       ├── corr_form.html                  # Crear/editar oficio (4 secciones + URL radicado)
│       ├── corr_importar.html              # Importar Excel correspondencia (auto-detecta formato)
│       ├── corr_importar_agilsalud.html    # Importar desde AgilSalud (Documentos.xlsx) — 2 pasos
│       ├── corr_configurar.html            # Configurar catálogos (responsables, tipos doc)
│       ├── ca_lista.html                   # /control-autos/ lista con filtros
│       ├── ca_form.html                    # Crear/editar auto (encabezado oficial SDS)
│       ├── ca_detalle.html                 # /control-autos/{id} detalle
│       ├── ca_importar.html                # Importar Excel formato original y exportado
│       ├── base_sdqs.html, sdqs_lista.html, sdqs_form.html, sdqs_importar.html      # Módulo SDQS
│       ├── base_pdf_tools.html, pdf_tools.html                                     # Módulo Herramientas PDF
│       ├── base_equipos.html, equipos_lista.html, equipos_form.html,
│       │   equipos_detalle.html, bienes_lista.html, bienes_importar.html           # Préstamo de Equipos / Bienes
│       ├── restauracion.html               # /backup/restauracion — guía de recuperación
│       └── digitales_abogados.html         # Catálogo de abogados de Digitales (editable)
├── data/
│   └── ocdi.db                             # Base de datos SQLite (se crea al iniciar)
├── iniciar.bat                             # Script Windows — libera puerto 8000 e inicia
├── backup_diario.py                        # Backup cifrado (AES-256) de la BD a Google Drive
├── ejecutar_backup.bat                     # Backup manual con doble clic
├── configurar_tarea_backup.bat             # Crea la tarea programada Lun–Vie 4PM
├── restaurar_backup.py                     # Restaura el último backup / --simulacro para probarlo
├── crear_bd_prueba.py                      # BD sandbox con datos ficticios (pruebas)
├── requirements.txt                        # Dependencias Python
├── INSTALACION.md                          # Guía paso a paso para instalar en Windows
├── RESTAURACION.md                         # Plan de continuidad: recuperar el sistema en otro PC
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

### Ambiente de pruebas (sandbox)

OCDI corre en un solo PC con una sola base de datos por diseño — no hay servidores separados de desarrollo/QA. Para verificar cambios o navegar la interfaz sin tocar nunca `data/ocdi.db` real (SDS-TIC-LN-016 §5.4.3.a: prohibido usar datos reales en ambientes no productivos):

```bash
# 1. Crear una BD de prueba con datos sintéticos (5 usuarios semilla + 3
#    expedientes de ejemplo con nombres ficticios, nunca datos reales)
python crear_bd_prueba.py

# 2. Levantar la app apuntando a esa BD en vez de la real
set OCDI_DB_PATH=data\ocdi_sandbox.db
python -m uvicorn app.main:app --reload
```

`data/ocdi_sandbox.db` (como todo `data/`) está fuera de git. Los tests automatizados que necesitan una base de datos (`tests/conftest.py`, fixtures `client`/`db_temporal`) ya usan este mismo mecanismo automáticamente — ningún test toca la BD real.

### Importar datos históricos

**Base Expedientes:**
1. Módulo Base → Importar Excel → seleccionar el `.xlsx` del archivo padre del OCDI
2. El sistema detecta automáticamente la hoja correcta (busca "EXPEDIENTE" en celda A1)
3. Los expedientes duplicados (mismo N° + mismo año) se omiten

**Correspondencia:**
1. Módulo Lista de Reparto → Importar → seleccionar el Excel de correspondencia
2. Acepta formato original (hojas de meses) o exportado (auto-detecta 15 o 19 columnas)
3. **Reemplaza todos los registros actuales** — confirmar en el modal de alerta

**Control de Autos:**
1. Módulo Control de Autos → Importar → seleccionar el `.xlsx`
2. Acepta formato original OCDI (hoja "NUEVO", fila 8+) o exportado (hoja "CONTROL AUTOS")
3. Filtra automáticamente las filas de glosario del pie de página

**Expedientes Digitales:**
1. Módulo Digitales → Importar → seleccionar el Excel padre-hijo de seguimiento digital

### Backup y respaldo

**Backup automático cifrado (el que permite recuperar TODO el sistema):**
- `backup_diario.py`, ejecutado por la tarea programada `OCDI_Backup_Diario` de lunes a viernes a las 4:00 PM, o con el botón **"Hacer backup ahora"** del portal.
- Crea en Google Drive un ZIP cifrado (AES-256) con un snapshot completo de `data/ocdi.db` + catálogos JSON. Conserva los últimos 30.
- La contraseña de cifrado está en `data/backup_password.key` y **debe estar guardada también fuera del servidor**: sin ella los backups no se pueden abrir.
- **Recuperar el sistema en otro PC:** ver **[RESTAURACION.md](RESTAURACION.md)** (plan de continuidad). Resumen: `git clone` → `pip install -r requirements.txt` → `python restaurar_backup.py` → `iniciar.bat` → `configurar_tarea_backup.bat`.
- **Probar que el último backup restaura todo** (sin tocar el sistema en uso): `python restaurar_backup.py --simulacro`. Recomendado una vez al mes.
- No copies `data/ocdi.db` a mano con el servidor encendido: la base usa modo WAL y la copia puede quedar incompleta. Usa siempre el backup.

**Backup ZIP de Excel por módulo (para consulta, no para restaurar el sistema):**
- En el portal principal, clic en **"📦 Descargar Backup Completo (.zip)"**
- Descarga un ZIP con una carpeta por módulo, con el Excel actualizado de cada uno

### Exportar reportes

**Reporte completo (Base Expedientes):**
- Lista de Expedientes → botón "Exportar Excel"

**Correspondencia:**
- Lista de Reparto → Exportar (19 columnas con nuevos campos)

**Control de Autos:**
- Lista de Autos → Exportar (formato oficial SDS-CDO-FT-001)

**Exportar/Importar General:**
- Módulo Backup → descarga un único Excel con 4 hojas: Base + Digitales + Sala + Control Autos

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
| `pypdf` | 4.0+ | Unir, extraer, eliminar páginas y rotar PDF (Módulo Herramientas PDF) |
| `PyMuPDF` | 1.23+ | Comprimir PDF y agregar sello/marca de agua |
| `pdf2docx` | 0.5.6+ | Convertir PDF → Word |
| `docx2pdf` | 0.1.8+ | Convertir Word → PDF |

---

## 12. Archivos de referencia

| Archivo | Descripción |
|---------|-------------|
| `BASE EXPEDIENTES 2023U ORIGINAL 22-10-2025.xlsx` | Archivo de datos históricos importado. 243 expedientes en hoja `2023 - 2024`. Columnas 1–51 mapean a los 48 campos de la BD. |
| `CORRESPONDENCIA 2026.xlsx` / `Correspondencia_20260421.xlsx` | Archivo histórico de correspondencia. 302 registros. Desde v2.5 soporta formato de 19 columnas con SINPROC, TIPO_REQ, TERMINO y URL. |
| `SDS-CDO-FT-001_v4control_AUTOS1.xlsx` | Formato oficial de Control de Autos. Hoja "NUEVO", encabezados fila 7, datos desde fila 8, 6 columnas (B:G). Pie de página con glosario (filas 122+). |
| `INSTALACION.md` | Guía paso a paso para instalar Python y ejecutar el sistema en Windows. |
