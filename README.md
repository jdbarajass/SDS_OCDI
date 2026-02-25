# OCDI - Sistema de Gestión Disciplinaria
### Secretaría Distrital de Salud (SDS) — Oficina de Control Disciplinario Interno

---

## Tabla de contenido
1. [Contexto del proyecto](#1-contexto-del-proyecto)
2. [Problema actual](#2-problema-actual)
3. [Solución propuesta](#3-solución-propuesta)
4. [Arquitectura técnica](#4-arquitectura-técnica)
5. [Estructura de datos](#5-estructura-de-datos)
6. [Flujo del proceso disciplinario](#6-flujo-del-proceso-disciplinario)
7. [Módulos del sistema](#7-módulos-del-sistema)
8. [Archivos de referencia](#8-archivos-de-referencia)
9. [Estado del proyecto](#9-estado-del-proyecto)
10. [Decisiones tomadas](#10-decisiones-tomadas)

---

## 1. Contexto del proyecto

**Entidad:** Secretaría Distrital de Salud (SDS) de Bogotá
**Dependencia:** Oficina de Control Disciplinario Interno (OCDI)
**Fecha de inicio:** 24 de febrero de 2026
**Usuarios:** 11 personas dentro de la misma oficina

---

## 2. Problema actual

- La oficina maneja su base de datos en **archivos Excel alojados en SharePoint**.
- Existe un archivo **"padre"** (el formato general con todos los campos) y varios archivos **"hijos"** más pequeños, uno por cada abogado asignado.
- El proceso actual consiste en que cada persona llena su archivo hijo y luego **copia y pega** la información al archivo padre, lo cual es manual, propenso a errores e ineficiente.
- El archivo padre tiene **226 columnas**, de las cuales ~66 son campos reales y el resto son columnas vacías/sin usar.
- No existe un sistema centralizado que permita visualizar, filtrar ni hacer seguimiento de los expedientes de forma ágil.

---

## 3. Solución propuesta

Construir una **aplicación de escritorio/web local** que:

- Centralice toda la información en una **base de datos local** en un PC de la oficina.
- Permita a las 11 personas **ingresar y consultar información** desde sus propios equipos a través de la red local (LAN), sin necesidad de internet.
- Tenga **lógica condicional** en el formulario de registro: si un expediente no avanza a cierta etapa (ej. no va a Investigación Disciplinaria), no se muestran esos campos.
- Permita **importar masivamente** el Excel existente para migrar la información histórica.
- Permita **exportar reportes en Excel** con el mismo formato del archivo padre original.
- Sea **completamente gratuito** — sin servidores pagos, sin dominios, sin suscripciones.

---

## 4. Arquitectura técnica

### Stack tecnológico

| Componente | Tecnología | Justificación |
|------------|-----------|---------------|
| Backend | Python + FastAPI | Ligero, rápido, gratuito, fácil de mantener |
| Base de datos | SQLite | Archivo único, fácil backup, soporta 11 usuarios concurrentes |
| Frontend | HTML + CSS + JavaScript | Accesible desde cualquier navegador sin instalar nada |
| Servidor | Un PC de la oficina | El PC "servidor" corre la app; los demás se conectan por red |

### Diagrama de red

```
[PC Servidor] ← corre Python + FastAPI + SQLite
     |
  [Red LAN - Cable SDS]
     |
[PC Usuario 1] → Abre Chrome → http://192.168.X.X:8000
[PC Usuario 2] → Abre Chrome → http://192.168.X.X:8000
...
[PC Usuario 11] → Abre Chrome → http://192.168.X.X:8000
```

### Características de despliegue
- **Sin instalación en PCs clientes:** solo necesitan un navegador (Chrome o Edge, que ya tienen).
- **Sin internet requerido:** todo corre dentro de la red local de la SDS.
- **Backup:** la base de datos es un único archivo `.db` que se puede copiar a un USB o carpeta compartida.
- **Costo total:** $0

---

## 5. Estructura de datos

Basada en el análisis del archivo `Informe de actuaciones procesales.xlsx`, hoja **ENCABEZADO**.

### Hojas del Excel original

| Hoja | Descripción |
|------|-------------|
| `ENCABEZADO` | Hoja principal con todos los campos (226 col, ~66 útiles) |
| `SEGUIMIENTO` | Seguimiento mensual de actuaciones por expediente |
| `AUTOS 2025` | Conteo de autos por tipo y mes (año 2025) |
| `AUTOS 206` | Conteo de autos por tipo, mes y abogado (año 2026) |

### Campos principales del expediente (hoja ENCABEZADO)

#### Bloque 1 — Identificación del expediente
| Campo | Tipo | Notas |
|-------|------|-------|
| N. Expediente | Número | Identificador principal |
| Año | Número | Año del expediente |
| Mes | Texto | Mes de ingreso |
| Origen del proceso | Texto | Ej: SDQS |
| N. Radicado comunicación inicial | Número | |
| Fecha radicado | Fecha | |
| Fecha SIIAS | Fecha | |
| Ingreso plataforma SIIAS | Sí/No | |
| Ingreso plataforma SIAD (Personería) | Sí/No | |
| Fecha ingreso SIAD | Fecha | |
| Ingreso plataforma SID4 | Sí/No | |

#### Bloque 2 — Asignación y partes
| Campo | Tipo | Notas |
|-------|------|-------|
| Nombre Abogado | Texto | Abogado asignado |
| Impedimento | Sí/No | |
| Investigado | Texto | Nombre o "En averiguación de responsables" |
| Perfil del indagado/investigado | Texto | |
| Entidad origen del proceso | Texto | |
| Quejoso y/o informante | Texto | |

#### Bloque 3 — Asunto y tipología
| Campo | Tipo | Notas |
|-------|------|-------|
| Asunto | Texto largo | Descripción del caso |
| Tipología | Texto | Tipo de falta |
| Descripción tipologías específicas | Texto largo | |
| Relacionado siniestro o pérdida | Sí/No | |
| Responsable del bien siniestro | Texto | Condicional |
| Relacionado maltrato o acoso laboral | Sí/No | |
| Responsable del acoso | Texto | Condicional |
| Relacionado hecho de corrupción | Sí/No | |
| Valores institucionales comprometidos | Texto | |
| Fecha de los hechos | Fecha/Texto | |

#### Bloque 4 — Indagación Previa
| Campo | Tipo | Notas |
|-------|------|-------|
| Fecha apertura indagación | Fecha | |
| Número de auto de apertura | Texto | Ej: 010-2023 |
| Fecha apertura de auto | Fecha | |
| Plazo | Número | En días |
| Fecha vencimiento | Fecha | Calculada automáticamente |
| Alertas vencimiento expediente | Número | Días restantes (negativo = vencido) |
| Número auto de traslado | Texto | |
| Fecha auto traslado | Fecha | |
| Número auto de archivo | Texto | |
| Fecha auto de archivo | Fecha | |

#### Bloque 5 — Investigación Disciplinaria (condicional)
| Campo | Tipo | Notas |
|-------|------|-------|
| Fecha apertura investigación | Fecha | Solo si aplica |
| Número de auto de apertura | Texto | |
| Fecha apertura de auto | Fecha | |
| Plazo | Número | En días |
| Fecha vencimiento | Fecha | Calculada |
| Alertas vencimiento | Número | |
| Número auto de traslado | Texto | |
| Fecha auto traslado | Fecha | |
| Número auto de archivo | Texto | |
| Fecha auto archivo | Fecha | |

#### Bloque 6 — Cierre
| Campo | Tipo | Notas |
|-------|------|-------|
| Estado del proceso | Texto | Ej: AUTO DE ARCHIVO, INVESTIGACIÓN DISCIPLINARIA |
| Observaciones finales | Texto largo | |

#### Bloque 7 — Escaneo y folio (múltiples registros)
| Campo | Tipo | Notas |
|-------|------|-------|
| Fecha escáner | Fecha | Repetido por cada lote de escaneo |
| Folio | Texto/Número | |
| Responsable | Texto | |

---

## 6. Flujo del proceso disciplinario

Basado en el diagrama de flujo (`Diagarama de Flujo OCDI.jpg`):

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

**Regla de negocio clave:** Los campos de Investigación Disciplinaria solo se deben mostrar/llenar si el expediente avanzó a esa etapa. Si fue archivado en Indagación Previa, esos campos quedan vacíos.

---

## 7. Módulos del sistema

| # | Módulo | Descripción | Estado |
|---|--------|-------------|--------|
| 1 | **Dashboard** | Totales, estadísticas por etapa/abogado/año, alertas de vencimiento, últimos registrados | ✅ Fase 2 — 2026-02-25 |
| 2 | **Gestión de expedientes** | Crear, ver, editar con formulario de 7 bloques y lógica condicional | ✅ Fase 1 — 2026-02-25 |
| 3 | **Seguimiento mensual** | Tabla interactiva de actuaciones por expediente y mes con modal de edición | ✅ Fase 2 — 2026-02-25 |
| 4 | **Control de autos** | Tabla de autos por tipo × mes y por abogado, con exportación a Excel | ✅ Fase 2 — 2026-02-25 |
| 5 | **Importar desde Excel** | Cargue masivo del archivo padre, detecta duplicados automáticamente | ✅ Fase 1 — 2026-02-25 |
| 6 | **Exportar reporte completo** | Exporta todos los expedientes con formato y colores de alerta | ✅ Fase 1 — 2026-02-25 |
| 6b | **Exportar reporte filtrado** | Filtros por año, abogado, etapa, estado, fechas, vencimientos + selección de bloques de columnas | ✅ Fase 2 — 2026-02-25 |
| 7 | **Gestión de usuarios/login** | Autenticación por usuario con roles | Pendiente (Fase 3) |

---

## 8. Archivos de referencia

| Archivo | Descripción |
|---------|-------------|
| `Informe de actuaciones procesales.xlsx` | Excel padre con toda la estructura de datos. Hojas: ENCABEZADO, SEGUIMIENTO, AUTOS 2025, AUTOS 206 |
| `Diagarama de Flujo OCDI.jpg` | Diagrama de flujo del proceso disciplinario interno |
| `CONTROL DISCIPLINARIO_V10.pdf` | Documento normativo/procedimiento de control disciplinario |
| `Decreto_641_de_2025.pdf` | Decreto de referencia legal |
| `procedimientoa ctual.pdf` | Descripción del procedimiento actual |
| `WhatsApp Image 2026-02-23 at 12.25.38.jpeg` | Organigrama de la Secretaría Distrital de Salud |
| `Prompt SDS.txt` | Descripción original del requerimiento |

---

## 9. Estado del proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| 0 | Levantamiento de requerimientos | ✅ Completado |
| 1 | Análisis del Excel y flujo de datos | ✅ Completado |
| 2 | Definición de arquitectura | ✅ Completado |
| 3 | Fase 1 — Gestión de expedientes + Importar/Exportar Excel | ✅ Completado — 2026-02-25 |
| 4 | Fase 2 — Dashboard + Seguimiento + Control de Autos + Exportar filtrado | ✅ Completado — 2026-02-25 |
| 5 | Fase 3 — Pruebas con usuarios reales + ajustes | Pendiente |
| 6 | Fase 4 — Gestión de usuarios/login + despliegue en red local SDS | Pendiente |

---

## 10. Decisiones tomadas

| Fecha | Decisión | Justificación |
|-------|----------|---------------|
| 2026-02-24 | Usar SQLite como base de datos | Gratuito, sin instalación, archivo único fácil de respaldar. 11 usuarios concurrentes es manejable. |
| 2026-02-24 | Interfaz web (no app de escritorio nativa) | Los clientes solo necesitan un navegador. Sin instalación en los 10 PCs usuarios. |
| 2026-02-24 | Python + FastAPI como backend | Ecosistema maduro, fácil de instalar en Windows, muchas librerías para Excel (openpyxl). |
| 2026-02-24 | Un PC como servidor en la red LAN | No requiere servidores externos ni pagos. Usa la red de cable ya existente de la SDS. |
| 2026-02-24 | Lógica condicional por etapa en el formulario | Evitar que se llenen campos irrelevantes según el estado del expediente. |
| 2026-02-25 | Construir por fases empezando con módulos 2 y 5 | El prototipo (gestión de expedientes + importar Excel) es la base definitiva. El esquema de BD y la arquitectura se diseñan desde el inicio pensando en el sistema completo. Los módulos restantes se añaden encima sin reescribir lo existente. |

---

## 11. Estrategia de construcción por fases

### Por qué el prototipo NO se descarta

El prototipo construye los cimientos que todos los módulos comparten:

```
FASE 1 — Prototipo (Módulos 2 y 5)
├── Base de datos SQLite  → esquema completo diseñado desde el inicio
├── Backend FastAPI       → estructura modular (nuevos módulos = nuevas rutas)
└── Frontend HTML/JS      → plantilla base con menú y layout compartido

FASE 2 — Se añaden módulos encima (sin reescribir)
├── Módulo 1: Dashboard         → nueva vista + consultas a BD existente
├── Módulo 3: Seguimiento       → nueva tabla en BD + nueva página
├── Módulo 4: Control de autos  → nueva tabla en BD + nueva página
├── Módulo 6: Exportar Excel    → nueva ruta API + lógica openpyxl
└── Módulo 7: Usuarios          → nueva tabla en BD + nueva página
```

### Lo que podría ajustarse entre fases
- Cambios visuales o de flujo del formulario (esperados y bienvenidos — es el propósito del prototipo).
- Campos nuevos que no estaban en el Excel (se agregan a la BD con una migración simple).
- Nada de la arquitectura base cambia.

---

## 12. Estructura de archivos del proyecto

```
SDS_OCDI/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, monta rutas y archivos estáticos
│   ├── database.py              # Esquema SQLite, conexión, helpers
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── expedientes.py       # CRUD + exportar Excel
│   │   └── importar.py          # Importación masiva desde Excel
│   ├── static/
│   │   ├── css/style.css        # Estilos (no requiere internet)
│   │   └── js/app.js            # Lógica de formulario y UI
│   └── templates/
│       ├── base.html            # Plantilla base (sidebar + layout)
│       ├── lista.html           # Listado con filtros
│       ├── form.html            # Formulario crear/editar (7 secciones)
│       ├── detalle.html         # Vista detalle de un expediente
│       └── importar.html        # Página de importación Excel
├── data/
│   └── ocdi.db                  # Base de datos SQLite (generada al iniciar)
├── iniciar.bat                  # Script Windows para arrancar el servidor
├── requirements.txt             # Dependencias Python
└── README.md                    # Este archivo
```

### Tablas de la base de datos

| Tabla | Descripción |
|-------|-------------|
| `expedientes` | Tabla principal — todos los campos del proceso disciplinario |
| `escaneos` | Registros de escaneo por expediente (relación 1:N) |
| `actuaciones` | Actuaciones mensuales por expediente — para Fase 2 |

### Cómo iniciar el sistema

1. **En el PC servidor**, hacer doble clic en `iniciar.bat`
2. Esperar a que aparezca el mensaje `Uvicorn running on http://0.0.0.0:8000`
3. **En cualquier PC de la red**, abrir Chrome/Edge y escribir: `http://<IP-del-servidor>:8000`
   - Ejemplo: `http://192.168.1.15:8000`
4. Para conocer la IP del servidor: ejecutar `ipconfig` en la consola de Windows

### Dependencias instaladas

| Paquete | Versión | Uso |
|---------|---------|-----|
| fastapi | 0.115+ | Framework web backend |
| uvicorn | 0.30+ | Servidor ASGI |
| jinja2 | 3.1+ | Motor de plantillas HTML |
| python-multipart | 0.0.9+ | Subida de archivos |
| openpyxl | 3.1.5 | Leer/escribir archivos Excel |
| aiofiles | 23.2+ | Archivos estáticos asíncronos |
