# Guía de trabajo del fork portátil

## Leer antes de implementar

1. [Contexto y estado](docs/ai/README.md).
2. [Decisiones de producto y hardware](docs/ai/decisions.md).
3. [Arquitectura y validación](docs/ai/development.md).
4. [Plan inicial](docs/specs/001-portable-interface.md) para cambios del modo portátil.
5. [Contratos de UI que deben preservarse](docs/ai/ui-contracts.md) antes de modificar formularios, selectores, navegación o sesiones.

## Disciplina contra regresiones

Cada decisión funcional nueva o modificada debe registrarse en `docs/ai/decisions.md` y su spec. Antes de cambiar una vista, identificar los contratos existentes que toca y conservarlos salvo petición explícita del usuario. Añadir o actualizar pruebas de comportamiento; para foco, búsqueda y layout, comprobar también el cliente Flet a 800 × 480. Un test de propiedades Python no demuestra el comportamiento del cliente Flutter. Documentar la evidencia y cualquier verificación pendiente; no sustituir decisiones anteriores por la última petición.

## Dirección del proyecto

Este fork adapta pokeldn a un dispositivo portátil: **Raspberry Pi 5**, pantalla **Waveshare 4.3inch DSI LCD (with case), 800 × 480 horizontal**, y **Seeed Studio XIAO ESP32-C6** como radio LDN. La UI debe funcionar con táctil, teclado y cruceta; la cruceta es preferida frente a joystick.

Prioridad: abrir la app y generar, importar, validar y guardar Pokémon localmente; después intercambios locales. Raids locales son opcionales posteriores. Internet/GTS y control directo de botones de Switch quedan fuera del alcance inicial. Conservar el funcionamiento de protocolos locales y `prod.keys`.

## Límites de implementación

- Trabajar en este fork, no en el directorio padre. No inicializar otro Git ni copiar el núcleo a una aplicación hermana.
- Extender la UI Python/Flet existente con un perfil portátil explícito; conservar el modo escritorio. No sustituir el stack ni reescribir protocolos sin una nueva decisión del usuario.
- Reutilizar widgets, localización, banco, runner y servicio PKHeX. Trazar la ejecución existente antes de crear abstracciones.
- Validar a **800 × 480**: no basta reducir el ancho ni probar solo en monitor de escritorio. Proteger foco, edición de texto, diálogos y acceso a acciones mediante teclado.
- No confundir emulación de protocolos LDN con emulación completa de una Switch o ejecución de sus juegos.
- No afirmar que 4 GB u 8 GB alcanzan para todas las funciones: falta medir el sistema completo en Pi 5.
- No versionar `prod.keys`, secretos ni datos personales del banco; usar fixtures temporales para validar.
- Separar decisiones acordadas, comportamiento observado y propuestas pendientes. Actualizar `docs/ai/` cuando cambie una decisión duradera; no presentar un plan como funcionalidad implementada.

## Mapa y comprobaciones

- `gui/main.py`: entrada GUI; `gui/app.py`: estado y coordinación.
- `gui/views/`: formularios, banco, juegos y placa; `gui/theme.py`: componentes compartidos.
- `pokeldn/pokemon.py` y `services/pkhex/`: preparación y validación.
- `pokeldn/app/runner.py` y `pokeldn/ldn/`: sesiones y transporte.
- `firmware/esp32/`: firmware existente; `tests/`: pruebas.

Usar los comandos documentados en [desarrollo](docs/ai/development.md), derivados de CI y de la guía del repositorio. Ejecutar las comprobaciones pertinentes al cambio y comunicar lo que no se pudo verificar. Una prueba en Mac o VM no certifica hardware, consumo o rendimiento de Pi.
