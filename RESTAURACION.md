# Guía de Restauración — Sistema OCDI

> Sigue estos pasos exactamente en caso de que el PC falle o necesites instalar el sistema en un equipo nuevo.
> Esta misma guía está disponible dentro del sistema en: **http://localhost:8000/backup/restauracion**

---

## Requisitos previos

Instala lo siguiente en el PC nuevo antes de empezar:

1. **Python 3.10 o superior** → https://www.python.org/downloads/
   - Durante la instalación, marca ✅ "Add Python to PATH"
2. **Git** → https://git-scm.com/download/win
3. **Google Drive para escritorio** (para acceder a los backups) → https://drive.google.com/drive/download
   - Inicia sesión con la cuenta de Google de la oficina para que monte la unidad `G:`

---

## Paso 1 — Obtener el código fuente

Abre una terminal (CMD o PowerShell) y ejecuta:

```bash
git clone https://github.com/jdbarajass/SDS_OCDI.git
cd SDS_OCDI
```

---

## Paso 2 — Instalar dependencias

Dentro de la carpeta del proyecto:

```bash
pip install -r requirements.txt
```

---

## Paso 3 — Restaurar la base de datos y archivos de referencia

1. Abre la carpeta de backups en Google Drive:
   ```
   G:\Mi unidad\5) DOCUMENTOS PARA CONSEGUIR TRABAJO\Simo\Soportes_SDS\BACKUP_APP_OCDI\Backup_Automatico_OCDI\
   ```
2. Ordena los archivos ZIP por **fecha de modificación** (más reciente primero)
3. Descomprime el ZIP más reciente (`ocdi_backup_YYYYMMDD_HHMMSS.zip`) — contiene:
   - `ocdi.db` → base de datos completa
   - `Tipologias_Json.txt` → catálogo de tipologías
   - `EntidadesDependencias_Json.txt` → catálogo de entidades

4. Copia `ocdi.db` a la carpeta `data\` del proyecto:
   ```
   SDS_OCDI\data\ocdi.db
   ```
   ⚠️ El archivo debe llamarse exactamente `ocdi.db` (sin fecha).

5. Copia `Tipologias_Json.txt` y `EntidadesDependencias_Json.txt` a la raíz del proyecto:
   ```
   SDS_OCDI\Tipologias_Json.txt
   SDS_OCDI\EntidadesDependencias_Json.txt
   ```

Si la carpeta `data\` no existe, créala primero:
```bash
mkdir data
```

---

## Paso 4 — Arrancar el servidor

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Abre el navegador en: **http://localhost:8000**

Para que otros usuarios en la red accedan, usa la IP local del nuevo PC:
```
http://192.168.X.X:8000
```

---

## Paso 5 — Configurar el backup automático en el nuevo PC

Una vez que el sistema esté funcionando, activa el backup automático:

1. Ejecuta (doble clic) → `configurar_tarea_backup.bat`
2. El backup correrá automáticamente de **lunes a viernes a las 4:00 PM**
3. **Verifica que la tarea quedó realmente creada** — no basta con que el `.bat` haya dicho "exitosamente". Abre una consola y ejecuta:
   ```
   schtasks /query /tn "OCDI_Backup_Diario" /v /fo list
   ```
   Debe mostrar el nombre de la tarea, el horario (Lun-Vie 4PM) y `Ejecutar como usuario` con tu usuario de Windows. Si dice "no se puede encontrar el archivo especificado", la tarea NO se creó — vuelve a correr el `.bat` (como Administrador si hace falta).
4. Fuerza una ejecución de prueba para confirmar que la tarea programada (no solo el script manual) tiene acceso real a la unidad de Google Drive:
   ```
   schtasks /run /tn "OCDI_Backup_Diario"
   ```
   Espera unos segundos y revisa `backup_log.txt` en la carpeta de backup — debe tener una línea `OK` nueva.

> ⚠️ El 21 de agosto de 2026 se descubrió que esta tarea puede quedar sin crearse en un PC nuevo aunque el backup manual (paso "Verificación rápida" de abajo) funcione perfectamente — los backups manuales no dependen de que la tarea programada exista. Por eso los pasos 3 y 4 de arriba son obligatorios, no opcionales.

---

## Verificación rápida

| Qué revisar | Cómo |
|---|---|
| La app arranca | Abre http://localhost:8000 — debe mostrar el portal |
| Los datos están | Entra a Base Expedientes y revisa que aparezcan los expedientes |
| El backup funciona | Ejecuta `ejecutar_backup.bat` manualmente y verifica que cree un `.zip` en la carpeta de Google Drive |

---

## Estructura de backups

```
G:\Mi unidad\5) DOCUMENTOS PARA CONSEGUIR TRABAJO\
  Simo\Soportes_SDS\BACKUP_APP_OCDI\Backup_Automatico_OCDI\
    ocdi_backup_20260819_160000.zip   ← más reciente (contiene ocdi.db + JSONs)
    ocdi_backup_20260818_160000.zip
    ocdi_backup_20260815_160000.zip
    ...  (últimos 30 backups — lunes a viernes)
    backup_log.txt                    ← historial de backups
```

Cada ZIP contiene:
- `ocdi.db` — snapshot consistente de TODOS los datos de la plataforma
- `Tipologias_Json.txt` — catálogo de tipologías disciplinarias
- `EntidadesDependencias_Json.txt` — catálogo de entidades y dependencias

---

## Credenciales de acceso

Las credenciales de los usuarios están dentro de la base de datos (`ocdi.db`) — se restauran automáticamente con el backup.

Usuario administrador por defecto (si se inicia desde cero sin backup):
- **Usuario:** admin
- **Contraseña:** admin123

---

## Contacto

Sistema desarrollado para la Oficina de Control Disciplinario Interno — SDS Bogotá.
Repositorio: https://github.com/jdbarajass/SDS_OCDI
