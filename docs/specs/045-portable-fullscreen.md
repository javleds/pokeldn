# Pantalla completa portátil

## Contexto
El usuario reporta que panel y título del escritorio restan altura a la pantalla
DSI 800 × 480 y vuelven inutilizable Equipo. La ventana portátil solicita 800 × 480
exteriores sin activar pantalla completa.

## Objetivo
Recuperar la superficie disponible de la pantalla al iniciar en Raspberry Pi.

## Alcance
Arranque principal portátil Linux y alternancia con F11 en cliente nativo.

## Fuera de alcance
Rediseñar Equipo, configurar el escritorio, cambiar escalado, modo escritorio y
ventanas auxiliares de actualización/selección de datos.

## Comportamiento esperado
Linux nativo abre a pantalla completa. F11 alterna ventana/pantalla completa en
las vistas del cliente nativo. Escape mantiene navegación y cierre de menús.
Se conserva el botón Cerrar y las protecciones durante sesiones/handoff.
Web no cambia de ventana; macOS y Windows conservan su arranque actual.

## Decisiones técnicas
Usar `page.window.full_screen` de Flet 1.0.5. Reutilizar `PortableView.key`,
el botón de cierre y las dimensiones existentes al volver a ventana.
El menú de accesos y el handoff conservan su bloqueo de atajos.

## Componentes afectados
`gui/portable.py`, tests de UI y documentación portátil.

## Backend
Sin cambios.

## Frontend
Sin filas adicionales ni reducción de fuentes; conservar contratos de Equipo.

## Persistencia
Sin preferencias nuevas; cada arranque Linux vuelve a pantalla completa.

## API
Sin cambios.

## Validaciones
Comprobar arranque por plataforma, F11 en Equipo/Banco/Entrenadores y web.

## Permisos y seguridad
Sin cambios de sistema ni acceso a datos/radio para validar.

## Casos límite
Web, otras plataformas y handoff/menú abierto no deben sufrir cambios inesperados.
La superficie lógica final depende también del escalado del compositor Linux.

## Estrategia de pruebas
Tests del arranque real con servicios simulados y del comportamiento del atajo;
regresión de UI y Equipo con advertencias como errores.

## Estrategia de validación
Inspección del cliente Flet local a 800 × 480 cuando sea posible. La eliminación
del panel y título en DSI requiere comprobación física en Pi; Mac no la certifica.

## Estrategia de commits
Un commit en main con implementación, regresiones y documentación, autorizado
por el usuario. Sin push solicitado.

## Archivos estimados a modificar
`gui/portable.py`, `tests/test_portable_ui.py`, esta spec,
`docs/ai/decisions.md`, `docs/ai/ui-contracts.md`, `docs/portable-build.md`.

## Riesgos
Diferencias entre gestores de ventanas Linux; F11 requiere teclado.

## Preguntas abiertas
Validar superficie útil y ergonomía en el dispositivo del usuario.

## Plan de implementación
1. Activar fullscreen al iniciar Linux nativo y añadir F11 antes del guard de vistas.
2. Probar arranque y alternancia, respetando bloqueos existentes.
3. Documentar operación, evidencia y límites; revisar diff y crear commit.

## Evidencia (2026-11-22)
- `.venv/bin/python -m pytest tests/test_portable_ui.py tests/test_portable_team_view.py -q -W error`: 74 passed.
- Cliente nativo Flet 1.0.5 en Mac con demo y datos temporales: configuración y
  galería visibles en ventana de 800 × 512 exteriores (800 × 480 útiles).
  F11 entró a pantalla completa sin título y otro F11 restauró la ventana.
  Se cerró la demo mediante su botón de cierre.
- El recorrido local no permitió comprobar Equipo sin completar requisitos de
  configuración. La prueba visual de Equipo/menús en DSI Linux queda pendiente;
  sus pruebas automatizadas pasaron, pero no sustituyen esa comprobación.
- No se modificaron el escritorio del sistema ni datos del usuario. Sin prueba
  física Pi, radio ni certificación de escalado/compositor Linux.
- Al cerrar el cliente, el proceso terminó con código 0 y una advertencia
  `Task was destroyed but it is pending` en `PortableView.focus`. No se investigó
  su origen en esta corrección; no se afirma cierre libre de advertencias.
