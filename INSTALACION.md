# OCDI — Guía de Instalación y Ejecución

**Sistema de Gestión Disciplinaria**
Secretaría Distrital de Salud — Oficina de Control Disciplinario Interno

---

## Requisitos previos

- Windows 10 o superior
- Conexión a internet **solo para la instalación inicial** (para descargar Python)
- Los demás equipos de la red solo necesitan un navegador (Chrome, Edge, Firefox)

---

## PASO 1 — Instalar Python

1. Abrir el navegador e ir a: **https://www.python.org/downloads/**
2. Descargar la versión más reciente de Python 3 (botón amarillo "Download Python 3.x.x")
3. Ejecutar el instalador descargado
4. **MUY IMPORTANTE:** en la primera pantalla del instalador, marcar la casilla **"Add Python to PATH"** antes de hacer clic en "Install Now"
5. Esperar a que termine la instalación y cerrar el instalador

**Verificar la instalación:**
Abrir el menú Inicio, buscar "cmd" y abrir el Símbolo del sistema. Escribir:
```
python --version
```
Debe mostrar algo como: `Python 3.x.x`

---

## PASO 2 — Copiar los archivos del proyecto

1. Copiar la carpeta completa **SDS_OCDI** al PC servidor (puede ser por USB, red local, o descargando desde GitHub)
2. Colocarla en una ubicación fija, por ejemplo: `C:\SDS_OCDI\`
3. Asegurarse de que la estructura de carpetas quede así:

```
C:\SDS_OCDI\
├── app\
│   ├── routers\
│   ├── static\
│   ├── templates\
│   ├── database.py
│   └── main.py
├── iniciar.bat
├── requirements.txt
└── INSTALACION.md
```

---

## PASO 3 — Instalar las dependencias

1. Abrir la carpeta `SDS_OCDI` en el explorador de archivos
2. En la barra de direcciones del explorador, escribir `cmd` y presionar Enter
   (esto abre el Símbolo del sistema directamente en esa carpeta)
3. Escribir el siguiente comando y presionar Enter:

```
pip install -r requirements.txt
```

4. Esperar a que termine (descarga e instala todos los paquetes necesarios)
5. Al finalizar debe aparecer algo como: `Successfully installed fastapi uvicorn ...`

> **Solo se hace una vez.** En ejecuciones posteriores no es necesario repetir este paso.

---

## PASO 4 — Iniciar el servidor

1. Hacer **doble clic** en el archivo **`iniciar.bat`**
2. Aparecerá una ventana negra de comandos — **no la cierre**, el servidor se detiene si la cierra
3. Cuando aparezca el mensaje `Application startup complete`, el sistema está listo

**Acceso local (en el mismo PC servidor):**
```
http://localhost:8000
```

**Acceso desde otros equipos de la red:**
```
http://<IP-del-servidor>:8000
```

Para conocer la IP del servidor: abrir cmd y escribir `ipconfig`, buscar la línea "Dirección IPv4" (ejemplo: `192.168.1.15`). Los demás usuarios deben ingresar `http://192.168.1.15:8000` en su navegador.

---

## PASO 5 — Importar los datos existentes (primer uso)

Si tiene el archivo Excel del "archivo padre":

1. Ingresar al sistema en el navegador
2. En el menú izquierdo, hacer clic en **Importar Excel**
3. Seleccionar el archivo Excel con los expedientes existentes
4. Hacer clic en **Importar**
5. El sistema importará todos los registros automáticamente (omite duplicados)

---

## Uso diario

1. El PC que actúa como servidor debe estar encendido
2. Hacer doble clic en **`iniciar.bat`**
3. Los 11 usuarios abren su navegador y acceden a la IP del servidor

Para detener el servidor: hacer clic en la ventana negra de comandos y presionar **Ctrl + C**.

---

## Solución de problemas frecuentes

### "El puerto 8000 ya está en uso"
El archivo `iniciar.bat` libera automáticamente el puerto antes de iniciar. Si persiste el error, reiniciar el PC servidor.

### "python no se reconoce como comando"
Python no quedó agregado al PATH. Reinstalar Python marcando la casilla "Add Python to PATH".

### "No module named ..."
Las dependencias no están instaladas. Repetir el Paso 3.

### Otro equipo no puede conectarse
- Verificar que el firewall de Windows no esté bloqueando el puerto 8000
- Verificar que ambos equipos estén en la misma red
- Verificar la IP del servidor con `ipconfig`

Para permitir el puerto 8000 en el firewall:
Inicio → Seguridad de Windows → Firewall → Configuración avanzada → Nueva regla de entrada → Puerto 8000 → Permitir

---

## Información técnica

| Componente | Detalle |
|------------|---------|
| Lenguaje | Python 3 |
| Framework | FastAPI |
| Base de datos | SQLite (archivo local en `data/ocdi.db`) |
| Interfaz | Navegador web (HTML/CSS/JS) |
| Puerto | 8000 |
| Acceso | LAN (red local), sin internet |

La base de datos se guarda en `data/ocdi.db`. **Hacer copias de seguridad periódicas de este archivo** para no perder la información.

---

*SDS · OCDI v2.0 — 2025*
