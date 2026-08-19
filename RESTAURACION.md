# Guía de Restauración — Sistema OCDI

> Sigue estos pasos exactamente en caso de que el PC falle o necesites instalar el sistema en un equipo nuevo.

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

## Paso 3 — Restaurar la base de datos

1. Abre la carpeta de backups en Google Drive:
   ```
   G:\Mi unidad\OCDI_Backup\
   ```
2. Ordena los archivos por **fecha de modificación** (más reciente primero)
3. Copia el archivo más reciente (`ocdi_backup_YYYYMMDD_HHMMSS.db`) a:
   ```
   SDS_OCDI\data\ocdi.db
   ```
   ⚠️ El archivo debe llamarse exactamente `ocdi.db` (sin fecha).

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

Una vez que el sistema esté funcionando, activa el backup diario:

1. Ejecuta (doble clic) → `configurar_tarea_backup.bat`
2. Desde ese momento el backup correrá todos los días a las 8:00 AM

---

## Verificación rápida

| Qué revisar | Cómo |
|---|---|
| La app arranca | Abre http://localhost:8000 — debe mostrar el portal |
| Los datos están | Entra a Base Expedientes y revisa que aparezcan los expedientes |
| El backup funciona | Ejecuta `ejecutar_backup.bat` manualmente y verifica que cree un `.db` en `G:\Mi unidad\OCDI_Backup\` |

---

## Estructura de backups

```
G:\Mi unidad\OCDI_Backup\
  ocdi_backup_20260819_080000.db   ← más reciente
  ocdi_backup_20260818_080000.db
  ocdi_backup_20260817_080000.db
  ...  (últimos 30 días)
  backup_log.txt                   ← historial de backups
```

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
