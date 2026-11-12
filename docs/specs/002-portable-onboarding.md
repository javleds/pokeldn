# Arranque y configuración Pokédex

## Contexto
El usuario aprobó una UI propia, sin barra lateral, basada en dos mockups. Esta entrega construye diagnóstico, claves, radio, progreso y logs a 800 × 480. Referencias visuales en `references/` junto a esta especificación.

## Objetivo
Convertir los mockups en vistas Flet operativas reutilizando validación y firmware existentes.

## Alcance
Perfil `POKELDN_PORTABLE=1`; diagnóstico PKHeX/claves/radio; selector de prod.keys; identificación de C6; instalación explícita, progreso y logs; confirmación y entrada local. Demo optativa separada para inspección sin hardware.

## Fuera de alcance
Nuevo banco/editor/intercambios portátiles, plugins, GTS, cambio del escritorio y flasheo real durante desarrollo sin petición del usuario.

## Comportamiento esperado
Comprobar al abrir; no instalar ni actualizar automáticamente una radio compatible. Guardar claves válidas y puerto mediante configuración existente. No elegir arbitrariamente entre varias placas. Progreso y logs comparten una operación: cambiar de vista no la cancela. Durante escritura solo se permite cambiar entre esas vistas. Si falla, conservar logs y permitir reintentar. Si falta radio/claves, permitir entrada local cuando el motor funcione. El inicio posterior de esta entrega indica honestamente que las funciones portátiles de Pokémon aún no están implementadas.

## Decisiones técnicas
Entrada temprana desde `gui/main.py` antes de crear `App` de escritorio. Controlador asíncrono independiente de controles Flet en `gui/portable_setup.py`; UI en `gui/portable.py`. Reutilizar `gui.app.keys_problem`, `gui.board`, `runner.command`, `pokemon.Service`, `settings` y `Redactor`. Evitar inicializar plugins y servicios de escritorio. Todas las operaciones lentas fuera del loop de UI. Compartir controlador real entre sesiones web para impedir instalaciones concurrentes dentro del servidor.

## Componentes afectados
`gui/main.py`, nuevos módulos portátiles, tests y docs/ai. Sin cambios en protocolos, imágenes de firmware ni formatos PKHeX.

## Backend
Identificación real y detección de chip con `gui.board`; instalación en subproceso con su CLI existente y validación de imágenes/checksums upstream. Reidentificar tras reinicio y solo declarar éxito con protocolo compatible. Selección conservadora de C6; falla ante ambigüedad.

## Frontend
Marco rojo, lente cian, panel claro, tipografía grande, botones con foco cian, sin navegación lateral. Enter/Tab nativos, flechas para foco y Escape para volver; en logs flechas desplazan el registro. Textos nuevos usan la función de localización existente con fallback español. Selector nativo; en web se lee el archivo elegido y se guarda localmente en el servidor de previsualización, con aviso explícito.

## Persistencia
Usar `settings.keys` y `settings.radio_port`. Copia importada de claves en DATA, con permisos restrictivos, validada antes de reemplazarla. Sin migración o nuevo esquema. Demo nunca escribe configuración ni hardware.

## API
Sin API pública nueva. Perfil web solo para localhost; reutiliza eventos Flet.

## Validaciones
No aceptar nombre como prueba de clave válida. Limitar tamaño del archivo y manejar datos inválidos. Verificar C6 antes de instalar; conservar protección de imágenes del instalador existente. Porcentaje solo si el proceso emite uno.

## Permisos y seguridad
No registrar contenido de claves. Sanitizar logs con Redactor, acotar historial. Instalación requiere acción explícita. Evitar cerrar ventana nativa durante escritura; no cancelar al cerrar detalles. No prometer recuperación ante corte de energía o terminación del proceso.

## Casos límite
Motor ausente, claves ilegibles, archivo cancelado, USB ausente/ocupado, varias placas, chip distinto, descarga fallida, proceso no cero, reinicio con puerto distinto, reconexión web y logs extensos.

## Estrategia de pruebas
Tests con servicios simulados para claves inválidas, selección de placa, demo sin efectos, doble instalación, progreso/logs, fallo y comprobación posterior. Tests de construcción de todas las vistas. Suites existentes GUI y firmware para regresiones.

## Estrategia de validación
Compilación Python, pytest de alcance y revisión visual en navegador 800 × 480 de vistas reales sin placa y demo. El hardware real queda pendiente.

## Estrategia de commits
Referencias y especificación; controlador y pruebas; UI e integración; documentación. No realizar commits sin petición.

## Archivos estimados a modificar
Los módulos y documentos listados arriba, `tests/test_portable_setup.py`, `tests/test_portable_ui.py`.

## Riesgos
Foco/selector diferente en web y escritorio; interrupción física del flash; identificación USB compartida por chips; dependencia de internet solo si falta firmware local. La maqueta no es un asset de runtime.

## Preguntas abiertas
Prueba en Pi/C6 y diseño del inicio funcional posterior. No bloquean esta entrega.

## Plan de implementación
1. Guardar los dos mockups originales; verificar archivos y enlaces.
2. Crear controlador con servicios existentes y estados; probar sin hardware.
3. Construir vistas y activar perfil sin alterar escritorio; revisar a 800 × 480.
4. Añadir demo explícita para progreso/logs sin efectos; verificar separación.
5. Ejecutar pruebas y documentar comandos, resultados y límites.

## Resultado del primer incremento

Implementados perfil, controlador, vistas y demo explícita. Ambos mockups originales se conservaron en [referencias](references/README.md), junto con capturas de la UI real a 800 × 480. Se comprobó PKHeX en el diagnóstico real y el recorrido de configuración/progreso/logs con teclado en demo. No se ejecutó un flash físico. El menú funcional de Pokémon sigue fuera de este incremento; su pantalla de entrada indica esa limitación.

### Ajuste de navegación acordado

En inicio/confirmación, «Revisar configuración» se sustituye por un engranaje **Ajustes** en la esquina superior derecha. En cliente nativo aparece antes de Cerrar; en web no se ofrece cierre de ventana. Ambos controles participan en navegación por teclado y el cierre se bloquea durante instalación.

El inicio no muestra un acceso directo a «Módulo inalámbrico»: la gestión de la placa se alcanza mediante el engranaje y la vista de configuración.
