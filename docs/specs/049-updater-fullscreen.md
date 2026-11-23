# Pantalla completa del actualizador

## Contexto
La ventana auxiliar de actualización todavía abre en ventana, sin alternancia táctil.
## Objetivo
Aplicar el comportamiento nativo de specs 045/047 al actualizador portátil.
## Alcance
Arranque fullscreen en Linux, botón en cabecera y F11 en cliente nativo.
## Fuera de alcance
Teclado virtual, motor de actualización, persistencia y UI escritorio upstream.
## Comportamiento esperado
Botón y F11 alternan sin interrumpir instalación ni perder logs. Icono y tooltip
reflejan estado, incluidos eventos del gestor. Cerrar permanece bloqueado hasta terminar.
## Decisiones técnicas
Reutilizar page.window.full_screen y el patrón de PortableView. Cabecera en una
fila, título expandido y botón de 40 px. No persistir estado; web oculta botón.
## Componentes afectados
UpdateWindow, configure y registro de teclado del helper.
## Backend
Sin cambios en apply, readiness, rollback ni handshake.
## Frontend
Iconos FULLSCREEN/FULLSCREEN_EXIT blancos en cabecera roja, como app principal.
## Persistencia
Sin cambios.
## API
Sin cambios externos.
## Validaciones
Linux nativo inicia fullscreen; Mac/Windows conservan ventana. Escape no cierra.
## Permisos y seguridad
Validación con fixture sin ejecutar actualización real ni acceder a datos personales.
## Casos límite
Alternancia durante progreso/error, eventos externos, desconexión y cliente web.
## Estrategia de pruebas
Tests de arranque por plataforma, botón/F11, eventos y guard de cierre durante trabajo.
## Estrategia de validación
Pytest -W error; cliente Flet real con área 800 × 480 y progreso simulado.
## Estrategia de commits
Cambio único; no se solicitó commit en este turno.
## Archivos estimados a modificar
Gui portable_updating, tests correspondientes, docs/ai y esta spec.
## Riesgos
La primera actualización usa el helper de la versión instalada; el cambio aplica
cuando se ejecute un helper que ya lo incluya. Validación de labwc en Pi pendiente.
## Preguntas abiertas
Ninguna para implementar; comportamiento físico pendiente de prueba.
## Plan de implementación
1. Añadir cabecera y alternancia en UpdateWindow siguiendo PortableView.
2. Configurar fullscreen Linux y registrar teclado sin cambiar ciclo del worker.
3. Probar estados, verificar cliente y documentar evidencia y límites.

## Evidencia (2026-11-23)
- 80 pruebas pasan con -q -W error: portable_updating, portable_update_control,
  portable_ui. Cubren arranque por plataforma, botón/F11, eventos externos,
  progreso conservado, cierre bloqueado y ciclo existente del worker.
- Cliente nativo Mac con fixture de UpdateWindow real y progreso simulado:
  área 800 × 480, botón visible, entrada/salida de fullscreen por clic y detalles
  de logs accesibles al volver a ventana; Cerrar sigue deshabilitado.
- No se ejecutó instalación real. F11 verificado automáticamente; labwc/Pi y
  arranque físico Linux pendientes. Git diff --check sin errores.
