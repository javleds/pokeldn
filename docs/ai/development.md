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

**Estado:** comandos comprobados contra archivos de configuración/documentación, todavía no ejecutados como validación de esta adaptación. Preparar herramientas y dependencias antes de reportar resultados.

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

La versión base compiló PKHeX sin advertencias ni errores. Sus 488 pruebas seleccionadas pasaron (cinco requirieron repetición fuera de las restricciones de sockets). La nueva configuración se verifica con tests portátiles y suites GUI/firmware. No se ha flasheado ni certificado un C6 real con estas vistas, ni se ha probado Pi 5. El inicio portátil posterior es informativo: banco, generación e intercambios con diseño propio no están implementados aún.
