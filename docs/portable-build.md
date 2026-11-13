# pokeLDN portátil: compilar y ejecutar en Mac y Raspberry Pi 5

Revisado: 2026-11-13. Objetivo: Pi 5, Raspberry Pi OS **64 bits con escritorio**, Waveshare DSI 800 × 480 y XIAO ESP32-C6 por USB de datos.

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

Tiene Python en `.venv` y SDK local en `.tools/dotnet`; no hace falta reinstalarlos:

```sh
export DOTNET_ROOT="$PWD/.tools/dotnet"
export PATH="$DOTNET_ROOT:$PATH"
export DOTNET_CLI_HOME="$PWD/.tools/dotnet-home"
dotnet build -c Release services/pkhex -warnaserror
```

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

## ¿Cómo producir una app independiente?

El empaquetador existente `scripts/pack_app.py` es del escritorio upstream. Exige todas sus imágenes de firmware, cliente Flet personalizado (`build_client.py`, Flutter), Unicorn reducido (`build_unicorn.py`, CMake), PyInstaller y, en Mac, Xcode 26 para Icon Composer. Además publica PKHeX para la arquitectura del host. Procedimiento completo: [Build a desktop app](gui.md#build-a-desktop-app).

**Todavía no es un empaquetador específico Portable.** No basta ejecutar `flet build macos` o `flet build linux`: hay procesos auxiliares, archivos de protocolos, PKHeX y firmware que incluir. El icono upstream y el modo normal siguen siendo los predeterminados del packer; `POKELDN_PORTABLE=1` se evalúa al arrancar, no queda incrustado por exportarlo durante la compilación.

Para una distribución autónoma portátil falta adaptar y comprobar: entrada que active el perfil sin variables externas, nombre/identidad e ícono propios en bundle y cliente, assets incluidos explícitamente (el packer usa `git ls-files`), firmware C6 y auxiliares, build nativo separado macOS/ARM64 Linux, ejecución en equipo limpio, y firma/notarización si se distribuye en Mac. No modificar el cliente Flet compartido dentro de `~/.flet` para ponerle el ícono: afectaría otras aplicaciones.

## Ícono entregado

[PNG transparente](../gui/assets/portable/icon.png), 1254 × 1254, con [prompt y procedencia](../gui/assets/portable/README.md). Se conserva el ícono upstream. El PNG sirve para Linux y como maestro para producir el `.icns`/catálogo del futuro bundle macOS; **todavía no sustituye el ícono del Dock del cliente Flet**.

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
