# Navegación portátil por arrastre

## Contexto
La Pi muestra barras de scroll, pero el usuario no puede arrastrar el contenido.
Flet 1.0.5 no expone el scroll interno de Dropdown a Python. No se ha determinado
si el dispositivo entrega touch o mouse. La prueba de teclado separada confirma
que Squeekboard funciona en ventana y queda invisible en fullscreen con labwc.

## Objetivo
Permitir explorar juegos y opciones sin arrastrar barras, conservando teclado.

## Alcance
Galería horizontal y acceso táctil a los selectores buscables compartidos de Equipo,
Modificador y Banco. La flecha abre un diálogo con consulta temporal y lista vertical.
El campo desplegable existente conserva edición directa y navegación nativa.

## Fuera de alcance
Cambiar fullscreen, teclado virtual, paquetes de Linux, protocolos o UI desktop.

## Comportamiento esperado
Arrastrar mueve la lista sin seleccionar; tocar confirma una opción. Cancelar no
modifica el modelo. La consulta del diálogo no genera ni valida Pokémon. X conserva
su significado. Flechas, Tab y Enter existentes permanecen disponibles.

## Decisiones técnicas
Reutilizar ListView, GestureDetector, Dropdown, show_dialog/pop_dialog y callbacks
existentes. Un contenedor compartido traduce arrastres en scroll; el arbitraje de gestos de
Flutter distingue el arrastre del toque. También reconoce desplazamiento entre
pointer-down y drag-start, necesario para gestos rápidos sin eventos update. Los selectores táctiles reutilizan opciones actuales,
con búsqueda local, filas de 40 px y acciones de cierre. No requieren cliente custom.

## Componentes afectados
`gui/portable.py`, `gui/portable_team_view.py`, nuevo `gui/portable_touch.py`.

## Backend
Sin cambios; callbacks existentes confirman elecciones.

## Frontend
Galería con barra automática; flecha táctil abre selector en diálogo acotado.

## Persistencia
Sin cambios de formato ni almacenamiento.

## API
Sin cambios externos ni dependencias nuevas.

## Validaciones
Ignorar apertura/selección en controles deshabilitados. No seleccionar durante drag.

## Permisos y seguridad
Fixtures temporales, sin radio ni claves personales.

## Casos límite
Sin coincidencias, opciones deshabilitadas, consulta cancelada, scroll en extremos,
cambio de vista, controles desmontados, selección invalidada mientras el diálogo abre.

## Estrategia de pruebas
Tests del adaptador de arrastre y confirmación/cancelación/búsqueda del selector;
regresiones de galería y formularios portátiles.

## Estrategia de validación
Pytest con -W error y cliente Flet a 800 × 480. Prueba física de dedo en Pi pendiente
hasta despliegue; no equiparar arrastre de ratón con certificación táctil.

## Estrategia de commits
Un commit funcional con documentación y pruebas; sin push solicitado.

## Archivos estimados a modificar
Los componentes anteriores, tests enfocados, docs/ai/decisions.md y ui-contracts.md.

## Riesgos
Latencia del puente Python en gestos gestionados por el adaptador; no se añade
inercia propia. El nuevo diálogo es
un acceso táctil adicional: no reemplaza el menú de búsqueda directa 280 × 160.

## Preguntas abiertas
Entrada real de la pantalla Pi y ergonomía con teclado virtual en ventana.

## Plan de implementación
1. Adaptador de mouse drag sobre ListView, conservando touch nativo; tests de dirección.
2. Galería reutiliza adaptador y barra AUTO; comprobar selección y teclado.
3. Flechas buscables abren diálogo compartido; comprobar filtrado y cancelación.
4. Ejecutar regresiones y prueba visual; documentar evidencia y crear commit.

## Evidencia de validación (2026-11-22)
- 187 tests pasan con `-q -W error`: portable_touch, portable_ui,
  portable_team_view, portable_received_view, portable_bank y gui_layout.
- Cliente nativo Flet en Mac, superficie 800 × 480 (ventana 800 × 512 por título),
  fixtures sin radio: arrastre horizontal, apertura con flechas/Enter, apertura del
  selector desde la flecha, arrastre vertical sobre filas, búsqueda tras desplazar,
  clic de confirmación y Escape sin salir del editor. El fixture no genera Pokémon;
  la persistencia/confirmación se cubre en tests de callbacks.
- Se detectó que un gesto rápido puede entregar down/start sin update; el adaptador
  ahora incluye ese tramo. No reconstruye la página completa por cada movimiento.
- Pendiente: dedo real en Pi, latencia con catálogo completo, teclado virtual y
  adaptación del layout al teclado. Fullscreen/labwc/Squeekboard sigue separado.
