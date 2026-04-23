# OCDI — Sistema de Gestión Disciplinaria
### Secretaría Distrital de Salud (SDS) · Oficina de Control Disciplinario Interno

> **Versión actual: v3.2** — Última actualización: 2026-04-23

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

### Módulo 2 — LISTA DE REPARTO DE ABOGADOS (`/correspondencia/`)

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
| 6 | **Días hábiles Colombia** — Función Python `_add_dias_habiles()` con cálculo de Pascua (algoritmo de Gauss), festivos fijos, festivos Ley Emiliani (siguiente lunes) y festivos móviles basados en Pascua | ✅ v2.5 |
| 7 | **Excepción ANEXO EXPEDIENTE / ANEXO AL EXPEDIENTE** — Ambas variantes siempre aparecen en 🟢 sin conteo de días. Excluidas de alertas, dashboard y portal | ✅ v2.4 |
| 8 | **TIPO DE REQUERIMIENTO** — Select con 9 valores predefinidos: DERECHO DE PETICION, TUTELA, PROPOSICION DEL CONSEJO, REQUERIMIENTO ENTES DE CONTROL, PROCURADURIA, CONTRALORIA, PERSONERIA, ANONIMO, DIRECCION DE ASUNTOS DISCIPLINARIOS DE LA SECRETARIA JURIDICA GENERAL | ✅ v2.5 |
| 9 | **TÉRMINO (DIAS)** — Select: 3 / 5 / 10 / 15 / 30 días | ✅ v2.5 |
| 10 | **SINPROC PERSONERÍA** — Campo alfanumérico de texto libre (Ej: 2026-SP-001) | ✅ v2.5 |
| 11 | **Catálogos configurables** — CRUD de responsables y tipos de documento desde `/correspondencia/configurar` | ✅ v2.3 |
| 12 | **Tipo de Respuesta — combobox** — 11 opciones predefinidas + texto libre (HTML5 `<datalist>`) | ✅ v2.4 |
| 13 | **Importar desde Excel** — Detecta automáticamente formato antiguo (15 cols) vs. nuevo (19 cols, con SINPROC/TIPO_REQ/TERMINO/URL). Reemplaza todo | ✅ v2.5 |
| 14 | **Importar desde AgilSalud** — Carga `Documentos.xlsx`; filtra por 2 destinatarias; previsualización obligatoria; modo ADD | ✅ v2.4 |
| 15 | **Exportar a Excel** — 19 columnas: AÑO, MES, FECHA INGRESO, N. RADICADOS, ENTIDAD, CORREO REMITENTE, ASUNTO, TIPO DOC, RESPONSABLE, CASO BMP, SINPROC PERSONERIA, TIPO DE REQUERIMIENTO, TERMINO (DIAS), N RADICADO SALIDA, URL RADICADO SALIDA, FECHA RADICADO DE SALIDA, TIPO DE RESPUESTA, OBSERVACIONES, DÍAS TRANSCURRIDOS | ✅ v2.5 |

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

Los 7 abogados inician sesión por dropdown (sin contraseña).

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

---

### Portal Hub (`/`)

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | **Página de inicio** — 6 tiles clickables con stats en tiempo real para cada módulo, agrupados visualmente | ✅ v2.5 |
| 2 | **Botón Backup ZIP completo** — Descarga un `.zip` con 5 carpetas (una por módulo), cada una con su Excel actualizado | ✅ v2.5 |

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
| 11 | Fase 3 — Pruebas con usuarios reales + ajustes | ⏳ Pendiente | — |

---

### Changelog detallado

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
│   │   ├── autos.py                        # /autos — control de autos BASE
│   │   ├── digitales.py                    # /digitales/* — módulo completo digitales 2025-2026
│   │   ├── sala.py                         # /sala/* — sala de audiencias
│   │   ├── backup.py                       # /backup/* — exportar/importar general (4 hojas) + ZIP
│   │   ├── correspondencia.py              # /correspondencia/* — lista de reparto abogados
│   │   └── control_autos.py               # /control-autos/* — autos de sustanciación SDS-CDO-FT-001
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
│       └── ca_importar.html               # Importar Excel formato original y exportado
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

**Backup ZIP completo (recomendado):**
- En el portal principal, clic en **"📦 Descargar Backup Completo (.zip)"**
- Descarga un ZIP con 5 carpetas, una por módulo, con el Excel actualizado de cada uno

**Backup de base de datos:**
- Copiar el archivo `data/ocdi.db` a una carpeta segura, USB o nube
- Para restaurar: reemplazar ese archivo antes de iniciar el servidor

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

---

## 12. Archivos de referencia

| Archivo | Descripción |
|---------|-------------|
| `BASE EXPEDIENTES 2023U ORIGINAL 22-10-2025.xlsx` | Archivo de datos históricos importado. 243 expedientes en hoja `2023 - 2024`. Columnas 1–51 mapean a los 48 campos de la BD. |
| `CORRESPONDENCIA 2026.xlsx` / `Correspondencia_20260421.xlsx` | Archivo histórico de correspondencia. 302 registros. Desde v2.5 soporta formato de 19 columnas con SINPROC, TIPO_REQ, TERMINO y URL. |
| `SDS-CDO-FT-001_v4control_AUTOS1.xlsx` | Formato oficial de Control de Autos. Hoja "NUEVO", encabezados fila 7, datos desde fila 8, 6 columnas (B:G). Pie de página con glosario (filas 122+). |
| `INSTALACION.md` | Guía paso a paso para instalar Python y ejecutar el sistema en Windows. |
