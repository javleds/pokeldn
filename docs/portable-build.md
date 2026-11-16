# pokeLDN portátil: compilar y ejecutar en Mac y Raspberry Pi 5

Revisado: 2026-11-13. Objetivo: Pi 5, Raspberry Pi OS **64 bits con escritorio**, Waveshare DSI 800 × 480 y XIAO ESP32-C6 por USB de datos.

## Comando habitual (entorno ya preparado)

Desde la raíz del fork:

```sh
./scripts/build_portable.sh
```

Detecta el SDK .NET 10 local o instalado, prepara las variables, entra a la raíz correcta y compila PKHeX. Restaura dependencias automáticamente cuando hace falta. También puede invocarse por su ruta absoluta desde otro directorio. No instala Python/.NET ni crea un paquete autónomo; la preparación inicial de abajo se hace una sola vez por equipo.

En este Mac, desde cualquier terminal:

```sh
/Users/javleds/dev/javleds/portpoke_inc/pokeldn/scripts/build_portable.sh
```

`--help` muestra el alcance; `--no-restore` es opcional cuando ya se restauraron dependencias. No necesitas recordar los exports para compilar. Los comandos manuales de abajo se conservan como explicación y diagnóstico.

## Abrir la app (entorno ya preparado)

```sh
./scripts/run_portable.sh
```

Para compilar primero y abrir solo si la compilación termina correctamente:

```sh
./scripts/run_portable.sh --build
```

No requiere exports ni activar el venv. Abre la GUI nativa, elimina variables web/demo heredadas y usa `.local-preview/portable` del checkout para conservar las pruebas existentes. Respeta `POKELDN_DATA` si ya definiste otra ruta (por ejemplo, la recomendada para instalación Pi). Puerto local 8590 por defecto, configurable con `FLET_SERVER_PORT`. Cerrar la instancia anterior; sin `--build` no compila. No instala dependencias. Se puede invocar por ruta absoluta desde otro directorio.

## Qué se compila y qué se ejecuta

- **Python/Flet:** la GUI se ejecuta desde el fork completo; no basta copiar `portable*.py`.
- **PKHeX/.NET:** se compila el motor de generación, lectura y legalidad.
- **Firmware C6:** es independiente. No hace falta compilarlo para abrir la GUI; la configuración gestiona su instalación con las imágenes compatibles del proyecto.
- **Paquete autónomo `.app`/Linux:** es otra etapa. Los pasos siguientes producen una instalación desde fuente, no un instalador independiente.

Mac nativo ya probado en este proyecto. **Esta guía de Pi aún no se ha ejecutado en hardware:** pantalla, cliente ARM64, conexión C6 y consumo requieren comprobación allí. No copiar `.venv`, `.tools`, `services/pkhex/bin`, `obj` o `dist` desde el Mac a la Pi.

## Versiones

| Componente | Referencia del fork |
|---|---|
| Python | 3.13 (Mac comprobado: 3.13.7) |
| Flet | 1.0.5, fijado en `gui/requirements.txt` |
| .NET SDK | 10.0 (Mac comprobado: 10.0.404) |
| PKHeX.Core | 26.10.18, fijado en `services/pkhex/pkhex.csproj` |
| Dependencias Python | `gui/requirements.txt`, incluye `requirements.txt` y `vendor/LDN` |

Ejecutar comandos desde la **raíz del fork** que contiene `gui/`, `services/` y `vendor/`, no desde el directorio padre. En un equipo nuevo:

```sh
git clone https://github.com/javleds/pokeldn.git
cd pokeldn
```

Usar la revisión que contenga los cambios portátiles; si aún no están publicados, transferir el código revisado, no los entornos ni datos privados. La instalación inicial necesita red para paquetes, NuGet, cliente Flet e imágenes de firmware.

## macOS

1. Instalar Python 3.13 desde [Python](https://www.python.org/downloads/macos/) y SDK .NET **10**, no solo runtime, desde [Microsoft](https://dotnet.microsoft.com/en-us/download/dotnet/10.0). Elegir Arm64 para Apple Silicon o x64 para Intel. Si se requieren compiladores: `xcode-select --install`.
2. Verificar arquitectura y versiones:

```sh
uname -m
python3.13 --version
dotnet --info
```

3. Preparar dependencias y compilar:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r gui/requirements.txt
dotnet build -c Release services/pkhex -warnaserror
```

4. Abrir en modo app, desde esa misma terminal:

```sh
unset POKELDN_GUI_WEB FLET_FORCE_WEB_SERVER POKELDN_PORTABLE_DEMO
export POKELDN_PORTABLE=1
export POKELDN_DATA="$HOME/Library/Application Support/pokeldn-portable"
export FLET_SERVER_IP=127.0.0.1
export FLET_SERVER_PORT=8590
.venv/bin/python gui/main.py
```

Es una ventana nativa; TCP aquí es transporte **local** entre Python y el cliente Flet, no una página web. Abrir solo una instancia en ese puerto. En Mac usamos 800 × 512 exteriores para conservar unos 800 × 480 útiles bajo la barra de título.

### Este checkout de desarrollo

En este Mac, primero entrar en `/Users/javleds/dev/javleds/portpoke_inc/pokeldn` (el directorio padre no contiene `services/pkhex`). Los `export` siguientes deben ejecutarse en la misma terminal que el build; la configuración de una sesión de Codex no se propaga a otras terminales.

Tiene Python en `.venv` y SDK local en `.tools/dotnet`; no hace falta reinstalarlos:

```sh
export DOTNET_ROOT="$PWD/.tools/dotnet"
export PATH="$DOTNET_ROOT:$PATH"
export DOTNET_CLI_HOME="$PWD/.tools/dotnet-home"
dotnet build -c Release services/pkhex -warnaserror
```

`--no-restore` se usó únicamente para verificar un entorno que ya tenía las dependencias restauradas. Omitirlo en la preparación inicial permite a `dotnet build` descargar las dependencias necesarias. Un SDK global distinto del local puede producir otro resultado; comprobar `command -v dotnet` y `dotnet --version` después de los exports.

Para conservar los perfiles usados durante las pruebas de esta conversación, sustituir la ruta nueva de datos por `export POKELDN_DATA="$PWD/.local-preview/portable"`. Elegir una ruta estable; cambiarla hace que la app parezca recién instalada. No versionar su contenido.

## Raspberry Pi 5: preparación nativa ARM64

Base propuesta: **Raspberry Pi OS con escritorio, basado en Debian 13/Trixie, 64 bits**, con Python 3.13 del sistema. No usar OS de 32 bits ni Lite sin preparar una sesión gráfica. Para Bookworm cambian Python y algunos nombres de paquetes; no mezclar los comandos Trixie con otro OS.

```sh
uname -m
cat /etc/os-release
python3 --version
```

Esperado: `aarch64`, base Trixie y Python 3.13. Configurar primero la pantalla horizontal 800 × 480 usando las instrucciones del modelo Waveshare exacto; esta guía no modifica overlays DSI.

### Dependencias del sistema

Desde la Pi:

```sh
sudo apt update
sudo apt install -y git curl ca-certificates python3 python3-venv python3-dev \
  build-essential pkg-config libgtk-3-0t64 libstdc++6 libsecret-1-0 \
  libglu1-mesa libasound2t64 libssl3t64 zlib1g libicu76 fontconfig
```

Flet ofrece cliente Linux ARM64 y usa `light` por defecto en Linux; se fija explícitamente abajo. Esta GUI no requiere reproductores de vídeo. Si se cambia a `full`, consultar sus dependencias multimedia en la [instalación de Flet](https://flet.dev/docs/getting-started/installation/). El cliente se descarga según glibc; disponibilidad y carga real en esta Pi siguen pendientes de validar.

### Instalar SDK .NET 10 Arm64

Ruta local del usuario para no mezclar repositorios APT. El script oficial instala SDK, pero no las bibliotecas del sistema:

```sh
curl --fail --location https://dot.net/v1/dotnet-install.sh -o /tmp/pokeldn-dotnet-install.sh
bash /tmp/pokeldn-dotnet-install.sh --channel 10.0 --architecture arm64 \
  --install-dir "$HOME/.local/share/pokeldn-dotnet"
export DOTNET_ROOT="$HOME/.local/share/pokeldn-dotnet"
export PATH="$DOTNET_ROOT:$PATH"
dotnet --info
```

Fuente: [instalación oficial mediante script](https://learn.microsoft.com/en-us/dotnet/core/install/linux-scripted-manual), [dependencias Debian](https://learn.microsoft.com/en-us/dotnet/core/install/linux-debian). El canal 10.0 instala el parche disponible; registrar `dotnet --version` para reproducirlo después con `--version`.

### Instalar la GUI y compilar el motor

Dentro del fork en la Pi:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r gui/requirements.txt
dotnet build -c Release services/pkhex -warnaserror
```

No instalar globalmente con `sudo pip`. Si alguna dependencia nativa no tiene wheel ARM64, revisar el error de compilación y la arquitectura antes de cambiar versiones fijadas.

### Permiso del puerto y arranque

Conectar el C6 mediante USB de datos. Para acceso serie del usuario:

```sh
sudo usermod -aG dialout "$USER"
```

Cerrar sesión y volver a entrar para aplicar el grupo. No ejecutar toda la GUI con `sudo`. En una terminal **de la sesión gráfica de la Pi**, desde el fork:

```sh
export DOTNET_ROOT="$HOME/.local/share/pokeldn-dotnet"
export PATH="$DOTNET_ROOT:$PATH"
unset POKELDN_GUI_WEB FLET_FORCE_WEB_SERVER POKELDN_PORTABLE_DEMO
export POKELDN_PORTABLE=1
export POKELDN_DATA="$HOME/.local/share/pokeldn-portable"
export FLET_DESKTOP_FLAVOR=light
.venv/bin/python gui/main.py
```

Una sesión SSH sin pantalla no equivale al escritorio local. No fijar `DISPLAY=:0` a ciegas: depende de X11/Wayland y del usuario de la sesión.

### Acceso desde el menú con el nuevo ícono

Crear `~/.local/share/applications/pokeldn-portable.desktop`, sustituyendo **todas** las rutas de ejemplo por las absolutas reales (el formato `.desktop` no expande `$HOME` ni `~`):

```ini
[Desktop Entry]
Type=Application
Name=pokeLDN Portable
Comment=Taller Pokémon portátil
Path=/home/USUARIO/pokeldn
Exec=env -u POKELDN_GUI_WEB -u FLET_FORCE_WEB_SERVER -u POKELDN_PORTABLE_DEMO POKELDN_PORTABLE=1 FLET_DESKTOP_FLAVOR=light DOTNET_ROOT=/home/USUARIO/.local/share/pokeldn-dotnet POKELDN_DATA=/home/USUARIO/.local/share/pokeldn-portable /home/USUARIO/pokeldn/.venv/bin/python /home/USUARIO/pokeldn/gui/main.py
Icon=/home/USUARIO/pokeldn/gui/assets/portable/icon.png
Terminal=false
Categories=Game;
```

Ejemplo pensado para rutas sin espacios. Si las hay, citar cada argumento/ruta según la especificación `.desktop`. El ícono del acceso queda definido; la asociación de la ventana al ícono en el panel depende del compositor/cliente y aún debe comprobarse en Pi. No se instala autoinicio en esta etapa.

## Primera comprobación

- Seleccionar `prod.keys` en configuración; nunca copiarla al repo.
- Confirmar que motor, claves y placa quedan listos; si falta firmware, usar la instalación explícita de la UI. Si faltan imágenes, consultar la descarga verificada del proyecto descrita en [GUI](gui.md#run-from-source); no usar un firmware C6 genérico.
- Probar teclado, foco, menús y modales a 800 × 480; crear/validar un Pokémon local.
- Probar intercambio físico y devolución antes de dar el dispositivo por validado.
- Usar `?` para RAM/CPU/temperatura; N/D significa que no hay sensor accesible. Registrar resultados, no inferirlos del Mac.

## Actualizar y reconstruir

Cerrar la app y terminar las sesiones de intercambio. Con checkout limpio y cambios propios ya preservados:

```sh
git pull --ff-only
.venv/bin/python -m pip install -r gui/requirements.txt
dotnet build -c Release services/pkhex -warnaserror
```

Volver a arrancar con las mismas variables y ruta de datos. No borrar perfiles para actualizar. Si se transfiere código entre plataformas, usar checkout limpio y reconstruir: el motor elige el ejecutable más reciente entre `dist` y `bin/Release`, incluso si se copió uno incompatible. `POKELDN_PKHEX` permite fijar explícitamente un ejecutable correcto.

## Crear la app con su ícono

Con el entorno preparado, desde cualquier directorio:

```sh
./scripts/build_portable.sh --app
```

Publica PKHeX para el host y reutiliza el empaquetador existente con `--portable`. En macOS produce `dist/pokeldn-portable.app`, con nombre visible **pokeLDN Portable**, identificador propio e ícono portátil tanto en el bundle como en el cliente que muestra la ventana y el Dock. Convierte el PNG a `.icns` con `sips`/`iconutil`; no requiere Icon Composer. Firma ad hoc local, sin notarización Apple.

El perfil portátil queda incorporado mediante un runtime hook (TCP local, puerto 8590 por defecto, configurable con `FLET_SERVER_PORT`; cerrar la instancia anterior): no necesita exports, ignora variables web/demo heredadas y conserva `POKELDN_DATA` si se indicó. Sin esa variable usa la resolución compartida y la elección guardada descritas en «Carpeta de datos compartida». No copia ni fusiona automáticamente datos de `.local-preview/portable`.

Requiere SDK .NET 10, `.venv` con `gui/requirements.txt`, herramientas de compilación nativas y los diez archivos de firmware del empaquetador. El primer publish/cliente puede requerir red. Incluye Python, PKHeX, assets y firmware; no incluye `prod.keys`, bancos personales ni el entorno `.venv`. No se instala ni se abre automáticamente.

Si existen cliente personalizado y Unicorn reducido, los reutiliza. Si faltan, Portable permite cliente Flet estándar y Unicorn del wheel: el paquete puede ser mayor y no admite arrastre de archivos desde escritorio; los selectores normales permanecen disponibles. El cliente compartido de `~/.flet` no se modifica: se personaliza una copia durante el empaquetado.

`./scripts/build_portable.sh` sin `--app` conserva su función de compilar únicamente PKHeX. `scripts/run_portable.sh` sigue ejecutando desde fuente y no cambia el ícono del cliente de desarrollo. `python scripts/pack_app.py` sin `--portable` conserva el paquete de escritorio upstream y sus requisitos.

La distribución Linux ARM64 debe construirse y validarse en ese host; una app de Mac no sirve en Pi. Firma/notarización Apple, ejecución en equipo limpio e integración del ícono en el panel Pi requieren validación propia.

## Ícono entregado

[PNG transparente](../gui/assets/portable/icon.png), 1254 × 1254, con [prompt y procedencia](../gui/assets/portable/README.md). Se conserva el ícono upstream. El empaquetado Portable aplica este PNG; ejecutar desde fuente conserva la identidad del cliente Flet de desarrollo.

## Solución de problemas

| Síntoma | Revisar |
|---|---|
| Abre escritorio original | Exportar `POKELDN_PORTABLE=1` en el proceso que arranca |
| Abre navegador | Eliminar `POKELDN_GUI_WEB` y `FLET_FORCE_WEB_SERVER` |
| Claves/perfiles desaparecidos | Misma ruta `POKELDN_DATA` que antes |
| Motor ausente | SDK 10, build Release y arquitectura del ejecutable |
| `Exec format error` | Binario Mac/x64 copiado a Pi; reconstruir en ARM64 |
| `cannot open display` | Ejecutar desde escritorio local y usuario correcto |
| Puerto serie sin permiso | Grupo dialout, nueva sesión, cable USB de datos y puerto libre |
| Mac atascado al abrir cliente | Cerrar instancia anterior; transporte local 127.0.0.1:8590 como arriba |
| Flet web sin web root | No aplicar el downgrade antiguo a 1.0.2; reinstalar `flet-web==1.0.5` desde PyPI oficial si se usa previsualización web |

Los scripts `setup_pi.sh`, `preflight_pi.sh` y `deploy_pi.sh` de este repo se orientan al host Wi-Fi/Mystery Gift y pueden configurar NetworkManager, adaptadores o servicios. **No son requisitos para esta GUI con radio C6**.

## Actualización desde la app

El perfil portátil ejecutado desde fuente consulta `main` de
`https://github.com/javleds/pokeldn.git` al abrir, en segundo plano. Si hay un commit
posterior compatible con el historial local, aparece el icono de actualización a
la izquierda de Ajustes. Ajustes muestra el estado y permite repetir la consulta.
No se ofrece este flujo en la app empaquetada ni en vista web/demo.

La primera instalación del actualizador necesita actualizar este checkout de forma
manual. La rama main del fork debe estar publicada; integrar main localmente no
publica cambios. Después, seguir abriendo `scripts/run_portable.sh` del directorio
original, también desde el acceso `.desktop`. No apuntar accesos a carpetas internas
de versiones. No hace falta `--build` para uso habitual.

Al confirmar, un proceso auxiliar abre una ventana y obtiene un bloqueo exclusivo.
La app principal se cierra; el auxiliar espera su salida, descarga el commit exacto,
crea un entorno Python, instala dependencias, compila PKHeX y comprueba imports y
los siete formatos del motor. Después abre una instancia de prueba sin permitir
intercambios/check de radio, activa la versión al confirmar su ventana y libera la
UI. Si falla antes de completar, conserva/restituye la referencia anterior e intenta
reabrirla; la ventana de error y los logs permanecen disponibles.

La preparación requiere Internet, SDK .NET 10 y espacio adicional para cada clone,
venv y build. El mínimo preventivo es 2 GiB libres, no una garantía de que cualquier
actualización quepa. Las versiones anteriores y fallidas se conservan; no hay
limpieza automática en esta primera versión. No instala paquetes apt ni usa sudo.
Firmware no se actualiza automáticamente: mantiene su flujo explícito habitual.

### Datos y cambios locales

El arranque resuelve `POKELDN_DATA` absoluto **antes** de cargar configuración y
conserva `POKELDN_INSTALL_ROOT` para localizar datos legacy de la instalación original.
El updater hereda esa carpeta efectiva al reiniciar, sin migrar ni copiar claves,
entrenadores o banco al release nuevo. No borres datos ni reimportes claves para
resolver un cambio de ruta. Consulta la resolución compartida más abajo.

La comprobación rechaza archivos modificados y archivos nuevos no ignorados: no
hace `reset`, `stash` ni sobrescritura. Un `log.txt` sin seguimiento puede bloquearla;
conserva ese archivo fuera del checkout, o usa una ruta de log ignorada como `logs/`.
`git status --short` explica lo pendiente. Historial divergente requiere revisión
manual; si el local está adelantado respecto a main, no se degrada.

### Archivos y recuperación

Bajo la instalación original:

- `.portable-updates/current.json`: referencia a la versión activa preparada.
- `.portable-updates/releases/`: versiones con checkout y venv propios, rutas fijas.
- `.portable-updates/jobs/<id>/`: solicitud, estado y logs `update.log`, `app.log`
  y `helper.log` (dependencias/build, arranque y coordinación respectivamente).

No mover un release: el venv contiene rutas absolutas. No borrar la versión activa
ni la anterior mientras se actualiza. Una preparación fallida no modifica el
checkout original. Si un puntero se daña, el launcher falla explícitamente en vez
de abrir una ruta arbitraria. Para volver al checkout original manualmente, con
app y helper cerrados, renombra `current.json` a un nombre de respaldo y abre el
launcher original; no es necesario borrar releases ni datos. El rollback de código
no revierte datos escritos por versiones futuras: los cambios de formato de datos
necesitan una estrategia propia antes de publicarse.

La verificación local usa repositorios Git temporales, fallos simulados y cliente
Flet real a 800 × 480. No equivale a una actualización completa de red/pip/build en
Raspberry Pi; esa primera validación en hardware sigue pendiente.

## Carpeta de datos compartida

Terminal, acceso directo y paquete portátil resuelven la carpeta con estas prioridades:

1. `POKELDN_DATA` explícito: override de esa ejecución, no cambia la preferencia.
2. Ruta guardada para el usuario.
3. Detección de carpeta estándar y `<instalación original>/.local-preview/portable`.

La carpeta estándar es `~/.local/share/pokeldn-portable` en Linux (respeta
`XDG_DATA_HOME`), `~/Library/Application Support/pokeldn-portable` en Mac y
`%APPDATA%/pokeldn-portable` en Windows. Si sólo una candidata contiene archivos,
se reutiliza. Si ninguna contiene datos, se crea la estándar. Si ambas contienen
archivos, aparece un selector antes de abrir configuración o radio; elegir no mueve
ni mezcla datos. Las rutas equivalentes por symlink cuentan como una sola. No se
escanea el disco ni se adoptan carpetas del perfil desktop.

La elección se guarda en `~/.config/pokeldn-portable/portable-data.json` en Linux
(respeta `XDG_CONFIG_HOME`), `~/Library/Application Support/pokeldn-portable-config/portable-data.json`
en Mac, y `%APPDATA%/pokeldn-portable/portable-data.json` en Windows. Este archivo
contiene únicamente versión del formato y ruta absoluta. Para volver a elegir,
cierra la app y renombra **ese archivo de preferencia** a un respaldo distinto;
no borres la carpeta de datos. Si sólo queda una candidata poblada, se selecciona
automáticamente. Una ruta guardada desaparecida o configuración corrupta produce
un aviso y no inicia con un perfil vacío.

Si quieres usar la selección recordada, evita exports persistentes de `POKELDN_DATA`
en shell o en `Exec=` del acceso: los overrides deliberados siguen teniendo prioridad.
Una ruta personalizada fuera de las dos candidatas puede mantenerse con ese override.
Los tests y ejecuciones aisladas con override no modifican la elección personal.

### Actualización única del launcher anterior

El launcher de spec 042 exportaba un default legacy antes de abrir la versión activa.
Una versión nueva no puede distinguir ese valor de un export explícito del usuario.
Para habilitar la nueva resolución actualiza una vez **el checkout original**, con
la app cerrada, después de publicar main:

```sh
cd ~/pokeldn
git pull --ff-only
./scripts/run_portable.sh
```

Esto actualiza juntos `run_portable.sh` y `portable_launch.py`; no borres
`.portable-updates/current.json` ni los datos. Si ya tienes un release activo, éste
también debe contener la corrección; el self-update puede obtenerlo. Mientras el
launcher estable sea el anterior, el override que genera seguirá siendo respetado.
Este cambio sólo afecta Python/arranque: no necesita recompilar PKHeX.

### Crear accesos desde la app

En Linux, abre **Accesos directos** (a izquierda de Update o Ajustes) y elige
**Agregar al menú** o **Agregar al escritorio**. Se crea un archivo del usuario
con icono y launcher estable; abrirlo no recompila. Se respeta el escritorio XDG.
El acceso captura la carpeta de datos activa explícitamente, conservando claves,
entrenadores y banco. Si cambias de carpeta, vuelve a agregar los accesos.
Una entrada anterior distinta se respalda con sufijo .bak; repetir sin cambios
no crea copias adicionales. El diálogo muestra ruta y advertencias.
El escritorio puede exigir **Permitir ejecutar/lanzar** en su menú contextual.
No requiere sudo. Disponible sólo en modo portátil Linux desde fuente.
