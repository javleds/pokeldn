---
title: Desarrollo y validación del fork portátil
nav_exclude: true
search_exclude: true
---
# Base observada y ruta de desarrollo

## Evidencia del repositorio

| Responsabilidad | Implementación existente |
|---|---|
| Arranque, vistas y tamaño de ventana | `gui/main.py`, `gui/screen.py` |
| Estado, servicios y coordinación | `gui/app.py` |
| Estilos y widgets reutilizables | `gui/theme.py`, `gui/views/widgets.py`, `gui/popups.py` |
| Preparación del Pokémon | `gui/views/pokemon.py` (`PokemonPicker`), `pokeldn/pokemon.py` |
| Banco e importación | `gui/views/bank.py` (`BankView`), `pokeldn/app/bank.py` |
| Sesiones y radio | `gui/views/games.py`, `pokeldn/app/runner.py`, `pokeldn/ldn/esp32_wlan.py` |
| Firmware | `firmware/esp32/`, documentado en `docs/hardware_esp32.md` |
| Validación PKHeX | `services/pkhex/`, proyecto .NET 10 |

La GUI y CLI comparten lógica de preparación y sesiones. Mantener esa separación: los formularios no implementan legalidad ni protocolos. Preservar coordinación de sesión/puerto y flash según `App` y el runner; no lanzar procesos paralelos sobre la misma placa desde el nuevo menú.

Hallazgos concretos del layout: `COMPACT_WIDTH` vale 760, por lo que 800 píxeles no activa por sí solo el modo compacto. El arranque propone 1440 × 900 con mínimo de 380 × 560 antes del ajuste al monitor. Adaptar también la altura y los diálogos; no modificar globalmente el umbral para resolver solo este dispositivo.

## Entorno y comandos existentes

Fuente: [Run from source](../gui.md#run-from-source), `gui/requirements.txt`, `services/pkhex/pkhex.csproj` y `.github/workflows/check.yml`. Versiones observadas: Python 3.13 en guía/CI, Flet 1.0.5 y .NET 10. Reconsultar manifiestos antes de instalar: estos datos no sustituyen el pin del repositorio.

Desde la raíz del fork, con Python 3.13 seleccionado:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r gui/requirements.txt
dotnet build -c Release services/pkhex -warnaserror
python gui/main.py
```

El cliente personalizado para arrastrar archivos es opcional y requiere Flutter; no es prerrequisito para comenzar la adaptación. La guía indica ejecución desde fuente en Raspberry Pi por falta de release Linux ARM64. Su nota piwheels cita Flet Web 1.0.2, diferente del pin actual 1.0.5: no aplicar ese downgrade automáticamente.

CI instala `pytest==9.2.0` y `pytest-xdist==3.8.0`. Comando completo existente, una vez instaladas sus dependencias:

```sh
python -m pytest tests/ -q -W error -n auto --dist worksteal
```

Selección inicial para cambios que afecten UI y flujos locales, ampliable según alcance:

```sh
python -m pytest tests/test_gui_layout.py tests/test_gui_views.py tests/test_bank.py tests/test_pokemon_service.py -q -W error
```

**Estado:** los comandos anteriores describen la ruta general y CI, no certifican que se haya ejecutado toda la suite para cada cambio. Las ejecuciones concretas y sus límites se registran abajo y en el [punto de pausa](session-2026-11-12.md).

## Criterios por etapa

1. Arrancar la app original y establecer una línea base reproducible.
2. Activar el perfil portátil y verificar 800 × 480, sin regresión del modo escritorio.
3. Completar navegación con flechas/Enter/Escape y Tab: foco visible, desplazamiento, controles deshabilitados, edición, cierre de diálogos y restauración de foco.
4. Generar, validar e importar datos reales de prueba; persistir y recuperar del banco temporal sin requerir radio. Mostrar fallos y carga sin bloquear la UI.
5. Verificar ausencia/desconexión de C6 y completar un intercambio real en el juego elegido antes de declarar soporte en Pi.
6. Medir cargas representativas en Pi 5; evaluar raids por separado.

Las pruebas estructurales de layout no prueban ergonomía. Añadir pruebas de comportamiento cuando aporten cobertura real y comprobar el cliente visualmente con tamaño objetivo. No ejecutar intercambios o modificar datos personales como efecto de pruebas ordinarias.

## Registro mínimo de mediciones futuras

Registrar revisión del código, modelo/RAM de Pi, OS, versiones, firmware C6, pantalla/escalado, operación y tamaño de datos, duración y método. Medir memoria del conjunto de procesos, errores y latencia; consumo físico cuando se elija batería. Diferenciar medición real de simulación y estimación.

## Primer incremento portátil (2026-11-12)

Implementados en `gui/portable.py` y `gui/portable_setup.py`: diagnóstico, importación y validación de claves, comprobación de C6, instalación explícita con el CLI existente, progreso, logs acotados/redactados y confirmación. El arranque de escritorio no cambia. Los mockups aprobados están en [referencias](../specs/references/README.md).

Desde la raíz del fork, con el entorno virtual activo:

```sh
POKELDN_PORTABLE=1 python gui/main.py
```

Previsualización local (el archivo elegido en el navegador se envía a este servidor):

```sh
POKELDN_PORTABLE=1 POKELDN_GUI_WEB=8551 FLET_SERVER_IP=127.0.0.1 FLET_FORCE_WEB_SERVER=true python gui/main.py
```

Añadir `POKELDN_PORTABLE_DEMO=1` para una demo explícita: la selección de claves y la instalación son simuladas, no hay IO de placa ni escritura de configuración del controlador. Este modo no debe usarse para validar hardware. En el despliegue normal omitir esa variable. No exponer la previsualización en una interfaz pública.

En el Mac de desarrollo se instalaron Python 3.13.7 y .NET SDK 10.0.404 en `.tools/`, con dependencias en `.venv/`. Para usar ese SDK local:

```sh
export DOTNET_ROOT="$PWD/.tools/dotnet"
export PATH="$DOTNET_ROOT:$PATH"
source .venv/bin/activate
```

La versión base compiló PKHeX sin advertencias ni errores. Sus 488 pruebas seleccionadas pasaron (cinco requirieron repetición fuera de las restricciones de sockets). La nueva configuración se verifica con tests portátiles y suites GUI/firmware. No se ha flasheado ni certificado un C6 real con estas vistas, ni se ha probado Pi 5. La galería abre Equipo mediante gui/portable_team_view.py; gui/portable_team.py mantiene borradores, validación por revisión y sesiones locales. El banco portátil sigue pendiente; las modalidades de recepción se añadieron después, según spec 010. Equipo reutiliza PKHeX y runner; no se ha certificado el intercambio físico.

### Fuentes de la vista web portátil

El tema portátil registra FONT_ASSETS y sus fallbacks locales, como escritorio. Con no_cdn=True, Flutter solicita Noto Sans Symbols en assets/fonts/notosanssymbols/v43/….woff2; Flet sirve los assets de aplicación desde la raíz, por lo que ese archivo se distribuye en gui/assets/assets/fonts/notosanssymbols. Incluye licencia OFL y procedencia. No quitar el nivel assets adicional: reproduce la URL del motor. Se comprobó HTTP 200 (69 116 bytes) donde antes respondía 404 y generaba advertencias repetidas. Revisar esta ruta al actualizar Flet/Flutter.

### Caché de opciones de Equipo
Ver spec 006: catálogos compartidos, metadatos por dependencias y candidatos PKHeX por configuración de caja. El nuevo comando interno move_options requiere recompilar services/pkhex. La vista básica reutiliza controles al cambiar caja; navegar no construye Pokémon. Los filtros orientan según un origen de referencia, sin reemplazar la validación de la combinación ni el check de bytes previo al intercambio.

### Regresiones corregidas y cobertura

`theme.dropdown` elimina `menu_height` para listas iniciales cortas. Los selectores reutilizados se pueblan después: fijar el límite en `TeamView.dropdown` después de invocar ese helper. No usar ancho infinito en el campo: Flutter lo propagaba al menú. Se usa ancho preferido finito de 280, límite de menú 280 × 160 y columnas restringidas por el formulario. Prueba de regresión: `test_dynamically_populated_selector_keeps_bounded_menu`.

`Setup.check()` retorna inmediatamente si otra sesión está comprobando. `PortableView.startup_pending` permite que `changed()` complete la navegación cuando llegan los resultados compartidos; `go()` desactiva esa transición al navegar explícitamente. Pruebas: `test_start_waits_for_checks_owned_by_another_session` (éxito y fallo) y `test_manual_settings_stay_open_after_successful_checks`. La comprobación fallida conserva diagnóstico; no interpretar la petición como omitir requisitos ausentes.

Suite enfocada reproducible, con el SDK local exportado como arriba:

```sh
.venv/bin/python -m pytest tests/test_pokemon_service.py tests/test_portable_team.py tests/test_portable_team_view.py tests/test_portable_ui.py tests/test_portable_setup.py -q -W error
```

Para repetir la previsualización de esta sesión sin mezclar datos con la configuración normal, añadir `POKELDN_DATA="$PWD/.local-preview/portable"` al comando web. No borrar ese directorio al retomar ni versionar sus datos. La última corrección de arranque tiene cobertura automatizada; queda pendiente repetir su prueba visual con varias pestañas.

### Identificación y devolución (spec 007)

`Team.start(discover=True, return_original=True)` habilita `--trade-back` únicamente en identificación y exige dos eventos `[done]`. La oferta inicial conserva check estricto y `allow_illegal=False`; la devolución se realiza dentro de `pokeldn.trade_back`, sin generar una copia ni cambiar PID. La UI no envía los datos que obtiene de PKHeX para la tarjeta.

`_watch_received` consulta los archivos de la sesión usando `run_stamp`, lee el primero y obtiene metadatos fuera del loop de UI. Una lectura tardía no debe cruzar sesiones; un fallo de lectura no detiene la devolución nativa. El perfil sigue dependiendo de un evento de entrenador compatible y recepción confirmada, como en el flujo anterior. No certificar identificación para todas las combinaciones de juego/rol sin prueba real.

Validación: 117 pruebas de portátil y trade-back aprobadas (las simulaciones con UDP necesitaron permiso de sockets locales); tras añadir detección del aviso nativo de original no conservado, 53 pruebas de controlador/vista aprobadas. Vista de recepción inspeccionada a 800 × 480 mediante fixture sin radio. Referencia: `docs/specs/references/implemented-trainer-return-demo-800x480.jpg`. Sin intercambio físico ni certificación de recuperación tras interrupción.


### Modalidades de recibido y transporte controlado (spec 010)

`gui/portable_received.py` coordina las modalidades y su journal; `gui/portable_received_view.py` reutiliza selectores y editor de Equipo. El helper incluye `edit_received`: edita una copia del registro con allowlist, devuelve snapshot e informe; no usa Make ni cambia entrenador. El original se conserva aparte, porque la serialización de un informe PKHeX no es garantía de bytes idénticos.

`pokeldn/portable_return.py` mantiene un gate no bloqueante por sesión nativa. La UI publica `response.json` con acción/hash y, para copia, `edited.bin` con hash. El transporte vuelve a validar y convertir la copia al formato nativo; únicamente el original en memoria puede omitir legalidad. No acepta rutas arbitrarias. `native.claim` impide reutilizar directorio; los adaptadores ligan la devolución a participante/sesión y abortan si cambia. Una ausencia de ofrecimiento durante edición no debe detener heartbeat ni enviar el original por accidente.

Los modos nuevos usan las mismas herramientas host/join de los seis juegos; activar combinaciones solo según `portable_return.supports`. Sin variables `POKELDN_RETURN_*`, el flujo previo de Equipo/identificación y escritorio conserva sus rutas. Tests de protocolos simulados y resultados se registran en spec 010; pruebas físicas de pausas largas y desconexión siguen pendientes.

La sesión activa puede tener `busy=False` durante edición: no usar ese flag para liberar radio o permitir cambiar modo. `active` y `setup.session_busy` siguen verdaderos hasta salida real. Las respuestas tardías se comprueban contra run_stamp/directorio/revisión. Fallos de journal no deben impedir cancelar ni liberar la radio al salir.

Suite nueva de servicio/controlador/vistas: 362 pruebas aprobadas; inspección visual con fixtures sin radio a 800 × 480. Comando de regresión del transporte (necesita sockets locales para simulación):

```sh
.venv/bin/python -m pytest tests/test_trade_back*.py tests/test_portable_return.py -q -W error
```

### Reapertura nativa de Flet en macOS
Si al relanzar el cliente queda en «Working…» con `RuntimeError: Session closed` durante foco/scroll, cerrar la instancia anterior y probar `FLET_SERVER_PORT=8590 FLET_SERVER_IP=127.0.0.1` conservando `POKELDN_PORTABLE=1` y sin `POKELDN_GUI_WEB` ni `FLET_FORCE_WEB_SERVER`. Sigue siendo cliente nativo; cambia el transporte local del socket temporal a TCP. Esta alternativa permitió abrir la galería en esta sesión. No se determinó aún la causa raíz del fallo del socket temporal.
