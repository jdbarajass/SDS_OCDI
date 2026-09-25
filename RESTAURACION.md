# Plan de Continuidad y Restauración — Sistema OCDI

> **Para quién es:** la persona que tenga que volver a poner en funcionamiento el sistema OCDI en otro PC porque el servidor se dañó, se perdió o se reemplazó. No hace falta saber programar: basta con seguir los pasos en orden.
>
> Esta guía también está dentro del sistema en **http://localhost:8000/backup/restauracion**, pero si el servidor se cayó esa página no estará disponible. Por eso este archivo vive en GitHub.

---

## 1. Resumen en 30 segundos

| Pregunta | Respuesta |
|---|---|
| ¿Qué se necesita para recuperar todo? | (1) el código, desde GitHub; (2) el último backup `.zip`, desde Google Drive; (3) **la contraseña de cifrado de los backups** |
| ¿Cuánta información se puede perder? | Lo registrado desde el último backup. El automático corre de lunes a viernes a las 4:00 PM; el botón **"Hacer backup ahora"** del portal crea uno en cualquier momento |
| ¿Cuánto tarda la recuperación? | Unos 60 minutos en un PC con internet, la mayor parte instalando programas |
| ¿Está probado? | Sí. Simulacro completo el **2026-09-24**: 31/31 tablas restauradas con los mismos registros que el sistema en uso y 14/14 páginas funcionando (ver sección 6) |

---

## 2. Lo que DEBE estar guardado fuera del servidor (hacerlo hoy, no el día del desastre)

Si el disco del servidor se daña, todo lo que esté solo en ese disco se pierde. Revisa esta lista:

- [ ] **Contraseña de cifrado de los backups.** Está en el archivo `data\backup_password.key` del servidor. **Sin ella, ningún backup de Drive se puede abrir: no existe forma de recuperarla.** Guárdala en un gestor de contraseñas (Bitwarden, 1Password, etc.) y, de preferencia, también impresa en un sobre sellado en poder de la jefatura de la oficina.
  - No la guardes en la misma carpeta de Google Drive de los backups: así quien acceda al Drive no puede abrir los datos.
- [ ] **Acceso a la cuenta de Google** donde está la carpeta de backups (usuario, contraseña y verificación en dos pasos).
- [ ] **Contraseña del usuario `Admin`** de la plataforma. Viaja dentro del backup y se restaura sola, pero hay que conocerla para entrar.
- [ ] Este documento: está en GitHub (https://github.com/jdbarajass/SDS_OCDI/blob/main/RESTAURACION.md).

---

## 3. Qué se respalda y dónde

**Backup automático:** `backup_diario.py`, ejecutado por la tarea programada de Windows `OCDI_Backup_Diario`, de lunes a viernes a las 4:00 PM. Si el PC estaba apagado a esa hora, corre al encenderlo. Se conservan los **últimos 30** backups.

**Carpeta en Google Drive:**
```
G:\Mi unidad\5) DOCUMENTOS PARA CONSEGUIR TRABAJO\Simo\Soportes_SDS\BACKUP_APP_OCDI\Backup_Automatico_OCDI\
    ocdi_backup_AAAAMMDD_HHMMSS.zip   ← un archivo por backup (cifrado AES-256)
    backup_log.txt                    ← historial: una línea OK/ERROR por backup
    simulacros_log.txt                ← historial de simulacros de restauración
```

**Contenido de cada ZIP:**

| Archivo | Qué es |
|---|---|
| `ocdi.db` | **Toda** la información del sistema: expedientes, seguimiento, autos, trámites internos, SDQS, digitales, sala, equipos, matriz, compensatorios, usuarios, contraseñas (cifradas), permisos, historial y papelera |
| `Tipologias_Json.txt`, `EntidadesDependencias_Json.txt` | Catálogos de referencia. También están en GitHub |

**Qué NO está en el ZIP (y por qué no hace falta):**
- El código de la aplicación está en GitHub.
- Los archivos que se procesan en Herramientas PDF no se guardan; la plataforma no almacena archivos subidos.
- La contraseña de cifrado no va en el ZIP a propósito (ver sección 2).

---

## 4. Procedimiento de restauración en un PC nuevo

### Paso 0 — Instalar los programas necesarios

1. **Python 3.10 o superior**: https://www.python.org/downloads/. En la primera pantalla del instalador marca ✅ **"Add Python to PATH"**.
2. **Git**: https://git-scm.com/download/win (opciones por defecto).
3. **Google Drive para escritorio**: https://drive.google.com/drive/download. Inicia sesión con la cuenta donde están los backups y espera a que aparezca la unidad `G:`.

Comprueba que quedaron instalados abriendo **Símbolo del sistema** (cmd):
```
python --version
git --version
```

### Paso 1 — Descargar el código

Elige una ubicación fija (por ejemplo `C:\SDS_OCDI`) y ejecuta en cmd:
```
cd C:\
git clone https://github.com/jdbarajass/SDS_OCDI.git
cd SDS_OCDI
```
> Si la red de la oficina bloquea GitHub, hazlo desde otra red (por ejemplo, datos del celular), o en github.com usa **Code → Download ZIP** y descomprímelo en `C:\SDS_OCDI`.

### Paso 2 — Instalar las dependencias
```
pip install -r requirements.txt
```
Tarda unos minutos y necesita internet. Debe terminar con `Successfully installed ...`.

### Paso 3 — Restaurar los datos (automático)

Con Google Drive ya sincronizado, en la carpeta del proyecto ejecuta:
```
python restaurar_backup.py
```
El script hace todo solo:
1. busca el ZIP **más reciente** en la carpeta de backups de Drive;
2. pide la **contraseña de cifrado** (sección 2). No se ve mientras escribes; pégala y presiona Enter;
3. coloca la base de datos en `data\ocdi.db` y los catálogos en la raíz;
4. guarda la contraseña en `data\backup_password.key`, para que los backups nuevos de este PC usen la **misma** contraseña que los anteriores;
5. comprueba la integridad, arranca la aplicación contra los datos restaurados y muestra cuántos registros hay por módulo.

Debe terminar con **`✅ RESTAURACIÓN COMPLETA`**.

**Variantes:**
- **Drive está en otra ruta o quieres un backup anterior:** pasa el ZIP directamente:
  ```
  python restaurar_backup.py "D:\ruta\ocdi_backup_20260924_160001.zip"
  ```
- **Restauración manual (sin el script):** abre el ZIP con **7-Zip** o **WinRAR** (el explorador de Windows no abre ZIP con AES-256) usando la contraseña. Copia `ocdi.db` a `C:\SDS_OCDI\data\ocdi.db` (crea la carpeta `data` si no existe) y crea el archivo de texto `data\backup_password.key` con la contraseña como único contenido.

### Paso 4 — Iniciar el servidor

Doble clic en **`iniciar.bat`**. Se abre una ventana negra: **no la cierres**, porque si se cierra el sistema se detiene. Cuando diga `Application startup complete`, abre http://localhost:8000 y entra con tu usuario de siempre.

### Paso 5 — Dar acceso a los demás equipos de la oficina

1. En cmd ejecuta `ipconfig` y anota la **Dirección IPv4** (ej. `192.168.1.15`).
2. Abre el puerto 8000 en el firewall. En cmd **como administrador**:
   ```
   netsh advfirewall firewall add rule name="OCDI 8000" dir=in action=allow protocol=TCP localport=8000
   ```
3. Avisa a todos que la nueva dirección es `http://<IP-nueva>:8000` (actualicen sus favoritos).
4. Recomendado: pide a TIC que le deje una **IP fija** a este PC, para que la dirección no cambie después.

### Paso 6 — Reactivar el backup automático (obligatorio)

1. Si Google Drive en este PC NO quedó en la misma ruta de la sección 3, indícale al backup la carpeta correcta (una sola vez, en cmd):
   ```
   setx OCDI_BACKUP_DIR "G:\Mi unidad\...\Backup_Automatico_OCDI"
   ```
   Cierra y vuelve a abrir cmd después.
2. Doble clic en **`configurar_tarea_backup.bat`** (clic derecho → *Ejecutar como administrador* si falla).
3. **Verifica que la tarea exista.** No basta con que el `.bat` diga "exitosamente":
   ```
   schtasks /query /tn "OCDI_Backup_Diario" /v /fo list
   ```
4. Fuerza una ejecución y confirma que aparece un ZIP nuevo y una línea `OK` nueva en `backup_log.txt`:
   ```
   schtasks /run /tn "OCDI_Backup_Diario"
   ```

> ⚠️ En agosto de 2026 se descubrió que la tarea programada nunca se había creado en el servidor, aunque la documentación decía que sí. Por eso los pasos 3 y 4 son obligatorios.

### Paso 7 — Verificación final

| Qué revisar | Cómo |
|---|---|
| Los datos están completos | El resumen del Paso 3 debe mostrar cifras similares a las de la sección 6 más lo registrado después |
| Los usuarios entran | Un abogado entra eligiendo su nombre; secretaría y admin con usuario y contraseña |
| Los demás equipos acceden | Desde otro PC: `http://<IP-nueva>:8000` |
| El backup funciona | Botón **"Hacer backup ahora"** del portal → debe decir *"Backup completado"* |
| El backup nuevo sí restaura | `python restaurar_backup.py --simulacro` → `✅ SIMULACRO EXITOSO` |

---

## 5. Simulacro periódico (recomendado cada mes)

Un backup que nunca se ha probado no es un backup confiable. Para probar el más reciente **sin tocar el sistema en uso**, en la carpeta del proyecto del servidor:
```
python restaurar_backup.py --simulacro
```
El script descifra el último ZIP en una carpeta temporal, verifica su integridad, compara tabla por tabla contra el sistema en uso, arranca la aplicación con esa copia y abre 14 páginas. Al final **borra la copia temporal**, porque contiene datos reales. El resultado queda en `simulacros_log.txt` de la carpeta de backups como evidencia.

Resultado esperado: `✅ SIMULACRO EXITOSO`. Si dice `❌ SIMULACRO FALLIDO`, revisa `backup_log.txt` y corrígelo antes de que haga falta de verdad.

---

## 6. Registro de pruebas realizadas

| Fecha | Prueba | Resultado |
|---|---|---|
| 2026-09-24 | Simulacro de desastre completo: clon limpio del repositorio + último ZIP de Drive (`ocdi_backup_20260924_164412.zip`) descifrado + aplicación arrancada desde la copia | ✅ 31/31 tablas con los mismos registros que el sistema en uso (262 expedientes, 257 autos, 581 trámites internos, 274 SDQS, 80 digitales, 116 eventos de sala, 15 usuarios, 137 permisos), contraseñas de usuarios intactas, 14/14 páginas y exportación a Excel funcionando |
| 2026-09-24 | `restaurar_backup.py` en un clon sin carpeta `data` (PC nuevo) y luego sobre una base de datos existente | ✅ Restauró todo, guardó la contraseña para los backups siguientes y, en el segundo caso, apartó la base anterior sin borrarla |
| 2026-09-24 | ZIP con contraseña incorrecta o sin contraseña | ✅ Rechazado (el cifrado funciona) |

---

## 7. Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `No se encontró la carpeta de backups` | Google Drive no ha terminado de sincronizar o quedó en otra letra/ruta. Espera o pasa la ruta del ZIP directamente (Paso 3, variantes) |
| `Contraseña incorrecta` / `Sin la contraseña correcta no es posible abrir el backup` | Usa la contraseña guardada según la sección 2. Si se perdió, **los backups cifrados no se pueden abrir**; solo quedaría otra copia no cifrada, si existe |
| `python no se reconoce como comando` | Reinstala Python marcando "Add Python to PATH" |
| `No module named ...` | Repite el Paso 2 |
| Otros equipos no conectan | Firewall (Paso 5.2), misma red, IP correcta |
| Los backups nuevos no aparecen en Drive | Paso 6 completo; revisa `backup_log.txt` |
| Se restauró un backup equivocado | La base anterior quedó como `data\ocdi_antes_de_restaurar_<fecha>.db`: renómbrala a `ocdi.db` con el servidor detenido |

---

## 8. Si NO existe ningún backup (último recurso)

Si arrancas sin `data\ocdi.db`, el sistema crea una base vacía con los 5 usuarios iniciales. Sus contraseñas se toman de las variables `OCDI_SEED_PWD_*` (ver `.env.example`); si no existen, se generan al azar y quedan escritas en `data\seed_passwords_iniciales.txt`. **Ya no existe una contraseña por defecto tipo `admin123`.** Los datos tendrían que volver a importarse desde los Excel de cada módulo.

---

Sistema OCDI — Oficina de Control Disciplinario Interno, Secretaría Distrital de Salud de Bogotá.
Repositorio: https://github.com/jdbarajass/SDS_OCDI
