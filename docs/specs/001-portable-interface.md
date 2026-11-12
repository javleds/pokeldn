# Interfaz portátil de pokeldn

## Contexto

El fork `javleds/pokeldn` está clonado en `portpoke_inc/pokeldn` y contiene la aplicación completa. El Git vacío del directorio padre fue retirado por petición del usuario; el único repositorio de trabajo es el fork. Esta adaptación se desarrolla y versiona en `portpoke_inc/pokeldn`.

La pantalla seleccionada es Waveshare 4.3inch DSI LCD (with case), 800 × 480. El objetivo de hardware es Raspberry Pi 5 con XIAO ESP32-C6 para radio LDN. La carcasa de Pi 4B y el cable incluido requieren revisión para Pi 5. La memoria necesaria todavía no se ha medido: 4 GB es una hipótesis, no un requisito certificado.

## Objetivo

Adaptar la aplicación existente a pantalla horizontal de 800 × 480, táctil y navegación con cruceta/teclado, conservando generación, importación, validación y banco local. Integrar después intercambios locales mediante los protocolos existentes y ESP32.

## Alcance

1. Entorno reproducible y ejecución de la aplicación original.
2. Perfil portátil explícito, previsualizable en el equipo de desarrollo sin Raspberry Pi.
3. Navegación y formularios locales utilizables sin ratón.
4. Intercambios locales y configuración de radio/clave con los componentes existentes.
5. Evaluación posterior de raids locales y consumo real en Pi.

## Fuera de alcance

Emulador completo de Switch, control directo de sus botones, GTS/internet, implementación nueva de LDN, firmware de controles físicos, batería y carcasa. No eliminar funciones de escritorio para simplificar el modo portátil.

## Comportamiento esperado

- El modo normal conserva navegación, tamaño y funciones existentes.
- El modo portátil cabe en 800 × 480; formularios largos tienen desplazamiento y acciones accesibles.
- Flechas desplazan la selección; Enter activa y Escape vuelve/cierra. Tab sigue funcionando. Dentro de un campo las flechas conservan su función de edición; los diálogos retienen el foco y lo devuelven al cerrar.
- Táctil y teclado ejecutan las mismas acciones. La cruceta se simula inicialmente con flechas; su transporte físico queda pendiente.
- Generación/importación presentan resultados reales de PKHeX, errores y estados de carga, sin necesitar una Switch o ESP32 conectados.
- Cambiar de vista no pierde un formulario ni interrumpe silenciosamente una sesión.

## Decisiones técnicas

Mantener Python/Flet y el servicio .NET existentes. Introducir el perfil dentro de `gui/`, inicialmente en `gui/portable.py` si el tamaño de la responsabilidad lo justifica. No crear una aplicación hermana ni copiar el núcleo. Propuesta de activación: `POKELDN_PORTABLE=1`, independiente de detectar Linux o de reducir el ancho.

El recorrido actual parte de `gui/main.py`, crea `gui.app.App` y construye vistas bajo demanda. `PokemonPicker` usa `pokeldn.pokemon`; el banco está en `BankView`; los intercambios se lanzan desde Games mediante el runner existente. Reutilizar este recorrido.

El umbral compacto actual es 760 píxeles: 800 × 480 no lo activa automáticamente. La ventana solicita un mínimo inicial de 560 de alto antes de ajustarlo al monitor. Resolver ambos en el perfil, sin cambiar globalmente el umbral de escritorio.

## Componentes afectados

Reutilizar `App`, `PokemonPicker`, `BankView`, `GamesView`, `BoardView`, `SettingsView`, `gui.theme`, `gui.popups` y la localización existente. Revisar `page_key`, `DigitCode` y `KEY_TARGET` antes de introducir manejo adicional de teclas.

## Backend

Reutilizar `pokeldn/pokemon.py`, `services/pkhex/` y `pokeldn/app/runner.py`. Mantener operaciones lentas fuera del hilo de UI mediante los mecanismos existentes. No alterar formatos de intercambio ni el transporte ESP32 en la primera etapa.

## Frontend

Primero adaptar el contenedor de navegación y una ruta completa de generación local; después importación/banco y configuración/intercambio. Mantener colores, iconos, widgets, traducciones y mensajes existentes. Evitar barras laterales que consuman el espacio necesario para formularios. Validar foco con Flet real antes de escoger un registro manual de controles.

## Persistencia

Conservar banco, configuración y rutas existentes. El perfil inicial se activa por entorno y no requiere migración. Usar datos temporales en pruebas; no modificar el banco personal para verificar la interfaz.

## API

No agregar HTTP ni cambiar el contrato del servicio PKHeX. La UI llama a las operaciones existentes.

## Validaciones

Conservar validación de datos, legalidad, selección de juego y restricciones de sesión. Una interfaz reducida no debe ocultar errores ni convertir una validación fallida en éxito. Los controles deshabilitados no se activan por teclado.

## Permisos y seguridad

`prod.keys` sigue el mecanismo local existente; nunca incorporarla al repositorio, fixtures o capturas. No habilitar servidores públicos ni disparar intercambios automáticamente al abrir la app. Preservar las restricciones de una sesión sobre un puerto serial.

## Casos límite

Pantalla sin espacio vertical, escalado de texto, nombres largos/traducciones, diálogo sobre formulario, foco en lista vacía, importación inválida o duplicada, PKHeX ausente, ESP32 desconectado/ocupado, cambio de vista durante trabajo y cierre durante sesión.

## Estrategia de pruebas

Añadir pruebas de comportamiento para activación del perfil, navegación, restauración del foco, edición de campos y controles deshabilitados donde el harness de Flet lo permita. Reutilizar `tests/test_gui_layout.py`, `test_gui_views.py`, `test_bank.py` y `test_pokemon_service.py`. No reemplazar validación visual con pruebas que solo inspeccionan estructura del código.

## Estrategia de validación

La guía y CI usan Python 3.13, .NET 10 y dependencias de `gui/requirements.txt`. Preparar un entorno virtual dentro del fork y compilar `dotnet build -c Release services/pkhex -warnaserror`. Ejecutar primero los tests afectados con `python -m pytest ... -q -W error`; para integración, el comando de CI es `python -m pytest tests/ -q -W error -n auto --dist worksteal` con dependencias de pruebas instaladas.

Verificar visualmente el cliente Flet a 800 × 480 y escritorio; completar crear, validar, importar y recuperar del banco con teclado y táctil simulado. En Pi real medir memoria del conjunto Python/cliente/.NET, latencia y estabilidad con ESP32. La VM ARM64 verifica compatibilidad, no certifica rendimiento ni batería.

## Estrategia de commits

1. Documentar alcance y arquitectura portátil.
2. Agregar perfil y navegación inicial con pruebas relevantes.
3. Adaptar generación/validación local.
4. Adaptar importación y banco.
5. Integrar configuración e intercambios locales.
6. Documentar instalación y mediciones ARM64.

Usar una rama `codex/…` para implementación; no hacer push ni modificar remotos en esta etapa de planeación.

## Archivos estimados a modificar

`gui/main.py`, `gui/screen.py`, `gui/theme.py`, posiblemente `gui/portable.py`, `gui/views/widgets.py`, `gui/views/pokemon.py`, `gui/views/bank.py`, `gui/views/games.py`, `gui/views/boards.py`, pruebas GUI y `docs/gui.md`. La lista se acota por etapa; no implica modificar todos los archivos inmediatamente.

## Riesgos

Conflictos con actualizaciones del upstream, diferencias de foco entre clientes Flet, diálogos nativos de archivos poco cómodos con cruceta, falta de release Linux ARM64 y versiones de dependencias. No asumir que cambiar dimensiones vuelve usable toda la interfaz.

## Preguntas abiertas

- Elegir el primer juego para la prueba real de intercambio antes de esa etapa.
- Definir cómo el hardware de cruceta emitirá eventos antes de integrarlo; para desarrollo usar teclado.
- Resolver mediante prototipo si el selector nativo de archivos permite navegación suficiente o requiere un explorador interno acotado.
- Decidir 4 u 8 GB a partir de mediciones representativas; raids no forma parte del primer criterio de aceptación.

## Plan de implementación

1. **Base ejecutable:** comprobar herramientas locales, instalar dependencias aisladas y compilar PKHeX siguiendo `docs/gui.md`; ejecutar app original y tests de las rutas locales. Resultado: línea base documentada sin cambios funcionales.
2. **Perfil portátil:** modificar arranque y contenedor en `gui/main.py` usando widgets de `gui/theme.py`; activar 800 × 480 explícitamente. Depende de la base; comprobar que escritorio conserva comportamiento y que todas las acciones del contenedor son visibles.
3. **Controles:** integrar acciones con `page_key` respetando edición, `DigitCode`, diálogos y atajos existentes. Depende del perfil; probar navegación, Escape, foco restaurado y activación única. Resultado: recorrido completo del contenedor sin ratón.
4. **Flujo local:** adaptar `PokemonPicker` y `BankView` en incrementos pequeños reutilizando servicio y almacenamiento. Depende de navegación; generar/validar y realizar importación y lectura del banco con fixtures temporales, además de inspección visual real.
5. **Intercambio:** adaptar configuración en Board/Settings y sesión en Games sin duplicar runner. Depende del flujo local y del juego elegido; comprobar errores sin hardware y completar una sesión real con C6/Switch antes de declarar compatibilidad.
6. **Pi y raids:** desplegar desde fuente en Pi OS de 64 bits, verificar pantalla/entrada y medir cargas locales e intercambio. Evaluar raids separadamente con pruebas reales y registrar límites; no prometer rendimiento a partir del Mac.

Estado: planeación inicial. No se han instalado dependencias ni implementado el perfil; el primer incremento de código comienza por la base ejecutable y la navegación.
