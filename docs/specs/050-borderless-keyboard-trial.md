# Prueba de ventana sin bordes y teclado

## Contexto
En Pi/labwc, usuario comprobó que ventana maximizada sin bordes muestra Squeekboard
y mantiene ambos campos de una prueba visibles. El dock reserva altura.
## Objetivo
Probar esta modalidad en formularios reales sin recortar contenido.
## Alcance
Opción POKELDN_PORTABLE_BORDERLESS=1 para Linux portátil nativo. Conservar fullscreen
predeterminado y alternancia F11/botón. No extender todavía al actualizador.
## Fuera de alcance
Ocultar dock, instalar teclado, modificar datos/protocolos y cambiar default antes
 de validación física.
## Comportamiento esperado
Arranca maximizada sin bordes. Alternar a fullscreen y volver conserva esta modalidad.
Canvas mínimo de 480 px: si el área útil es menor, scroll vertical y desplazamiento
al campo enfocado; con más altura ocupa el espacio disponible. No encoger controles.
## Decisiones técnicas
Reutilizar PortableView, su canvas y drag_scroll. Un viewport desplazable sólo en
la prueba, dimensionado por on_size_change (área útil), conserva los controles y foco.
Esta prueba permite scroll general cuando falta altura; contrato Básico sin scroll
se conserva a 800 × 480 completos. No inferir altura del teclado por valores fijos.
## Componentes afectados
PortableView/main, tests UI y documentación de ejecución.
## Backend
Sin cambios.
## Frontend
Mismo contenido con canvas de altura mínima y scroll de respaldo.
## Persistencia
Ninguna: variable por proceso.
## API
Variable opcional de entorno, sin cambios externos.
## Validaciones
Opción ignorada fuera de Linux nativo, guardas de fullscreen y cierre intactas.
## Permisos y seguridad
Previsualización con datos simulados, sin radio ni actualización.
## Casos límite
Altura menor por dock/teclado, eventos repetidos de tamaño, volver de fullscreen.
## Estrategia de pruebas
Arranque opt-in/default/plataforma; alternancia y resize sin recrear controles.
## Estrategia de validación
Pytest y cliente nativo con 800 × 480 y alturas reducidas. Pi/Squeekboard requieren
validación del usuario con formularios reales antes de cambiar defaults.
## Estrategia de commits
Un cambio acotado; commit no solicitado.
## Archivos estimados a modificar
Gui portable, tests portable_ui, docs/ai y portable-build.
## Riesgos
Auto-scroll de foco/teclado depende del cliente/compositor; Mac no certifica Pi.
Scroll general es alternativa al recorte, no rediseño responsive de cada formulario.
## Preguntas abiertas
Validación táctil en Pi, especialmente buscadores modales y campos inferiores.
## Plan de implementación
1. Añadir modo opt-in y restauración de maximizado al salir de fullscreen.
2. Envolver canvas conservando controles en viewport de altura adaptable.
3. Probar tamaños/foco en cliente, documentar comando de prueba y limitaciones.

## Evidencia (2026-11-23)
- 106 tests pasan: portable_ui, portable_team_view, portable_touch y portable_close
  con -q -W error. Incluyen opt-in/plataforma, retorno a maximizado, canvas sin
  reconstrucción al cambiar altura y comportamiento existente.
- Cliente Flet Mac con TeamView/PortableView reales y modelo simulado: 800 × 480
  muestra Básico completo. A 800 × 240, arrastre vertical revela campos y movimientos;
  selector abre, filtra «09», muestra resultado y Cancelar sin desbordar. Volver a
  480 restaura el formulario completo. La prueba fuerza sólo el wrapper experimental
  en Mac; no certifica maximización Linux ni auto-scroll con Squeekboard.
- No se generó ni guardó ningún Pokémon, ni se ejecutó radio. Teclado virtual,
  desplazamiento automático del foco y formularios restantes en Pi pendientes.

## Sustitución del opt-in
Por petición posterior del usuario, spec 051 adopta el modo como default en Linux
nativo y retira la variable experimental antes de publicar. La evidencia visual
y los límites anteriores siguen aplicando al viewport conservado.
