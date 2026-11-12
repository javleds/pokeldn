# Galería portátil de juegos

## Contexto
El inicio portátil es informativo. Se conserva el marco rojo, ajustes y diagnóstico existentes.
## Objetivo
Elegir juego en una fila horizontal de avatares circulares a 800 × 480.
## Alcance
Grupos disponibles en el catálogo base desde FRLG hasta SV, en orden del catálogo. Nombre debajo con área fija de 72 píxeles alineada arriba para mantener todos los avatares y textos a la misma altura, imagen existente y Poké Ball ante ausencia/error. Selección con clic, tacto o Enter; flechas y scroll horizontal.
## Fuera de alcance
Herramientas del juego, plugins, Z-A, títulos no presentes en catálogo estable y persistencia de selección.
## Comportamiento esperado
Foco cian visible; desplazamiento mantiene visible el juego enfocado. Selección explícita resaltada con fondo rojo oscuro y nombre blanco, sin label redundante; foco cian independiente de la selección. Selección y conservada al visitar ajustes durante la sesión. Arriba/abajo permiten acceder al engranaje. No iniciar operaciones al elegir juego.
## Decisiones técnicas
Reutilizar GAMES de pokeldn.app.catalog, claves originales e imágenes games/<key>.png. Flet ListView horizontal, Button y Image.error_content. Filtrar claves del alcance sin modificar catálogo ni escritorio.
## Componentes afectados
PortableView y pruebas portátiles.
## Backend
Sin cambios; conservar objeto Game seleccionado para siguientes vistas.
## Frontend
Tarjetas de 170 píxeles con avatar circular de 128; fila desplazable y barra visible, marco y ajustes actuales.
## Persistencia
Solo estado en memoria de la vista.
## API
Sin cambios.
## Validaciones
Seleccionar únicamente entradas del catálogo portátil.
## Permisos y seguridad
Ninguna operación serial, instalación, intercambio o descarga disparada por la selección.
## Casos límite
Imágenes ausentes o corruptas, nombres largos, extremos de la fila, retorno desde ajustes y navegación al engranaje.
## Estrategia de pruebas
Orden y claves, fallback, selección, foco y scroll, conservación al cambiar de vista; suites portátiles existentes.
## Estrategia de validación
pytest UI/setup, diff --check, ejecución web e inspección a 800 × 480.
## Estrategia de commits
Un incremento cohesivo de galería y pruebas; sin commit automático.
## Archivos estimados a modificar
gui/portable.py, tests/test_portable_ui.py y docs/ai/decisions.md.
## Riesgos
Foco de Flet en listas; comprobar visibilidad real al navegar. No presentar selección como herramientas ya implementadas.
## Preguntas abiertas
Resuelta: el usuario eligió fila horizontal, no cuadrícula vertical.
## Plan de implementación
1. Integrar catálogo filtrado y avatares en PortableView, conservando estructura existente.
2. Implementar selección en memoria, foco y scroll; comprobar pruebas de comportamiento.
3. Reiniciar preview sin interrumpir firmware y verificar visualmente resolución y extremos de fila.
