# Botón de estadísticas portátil

## Contexto
El monitor CPU/RAM/temperatura existente se alterna con `?` (spec 010).

## Objetivo
Ofrecer el mismo interruptor mediante botón junto a Ajustes.

## Alcance
Cabecera portátil y navegación por teclado, con indicador de estado activo.

## Fuera de alcance
Cambiar métricas, escritorio, protocolos o sensores.

## Comportamiento esperado
Botón después de Ajustes, visible también en diagnóstico y durante sesiones.
Arranca apagado; clic y `?` alternan el mismo estado. Navegar conserva el estado.
Tooltip indica Mostrar/Ocultar estadísticas; color cian cuando está activo.

## Decisiones técnicas
Reutilizar ResourceOverlay.toggle y el registro de navegación de PortableView.
Conservar la altura de cabecera y el muestreo únicamente visible/conectado.

## Componentes afectados
PortableView, pruebas de UI y documentación de contratos.

## Backend
Sin cambios al muestreador existente.

## Frontend
IconButton de monitor, estilo de foco compartido con Ajustes.

## Persistencia
Sin preferencia persistida, como el monitor actual.

## API
Sin cambios.

## Validaciones
Preservar bloqueos de actualización y menú de accesos directos.

## Permisos y seguridad
Sin nuevos permisos ni acceso a datos personales.

## Casos límite
Alternar por teclado tras clic; navegación; sesión activa; sensor ausente.

## Estrategia de pruebas
Comprobar clic, atajo, estado visual, cancelación de muestreo y foco desde Ajustes.

## Estrategia de validación
Pytest focalizado con warnings como errores; inspección Flet a 800 × 480.
Registrar explícitamente cualquier validación visual o de hardware pendiente.

## Estrategia de commits
Un cambio cohesivo de UI, pruebas y documentación; sin commit automático.

## Archivos estimados a modificar
gui/portable.py, tests/test_portable_ui.py, docs/ai/decisions.md,
docs/ai/ui-contracts.md y esta spec.

## Riesgos
Espacio horizontal de cabecera y diferencias del foco Flutter respecto al harness.

## Preguntas abiertas
Ninguna para implementar este interruptor.

## Plan de implementación
1. Añadir botón y acción compartida en PortableView; reutilizar overlay y foco.
2. Probar activación combinada, navegación y lifecycle con suites portátiles.
3. Revisar cliente a 800 × 480 y registrar evidencia y límites.

## Resultado y evidencia
Implementado botón y acción común con `?`, conservando el overlay existente.
Validación: 88 pruebas aprobadas con `-q -W error` en test_portable_ui,
test_portable_resources, test_portable_shortcut_menu y test_portable_update_control.
La demo nativa se lanzó con datos temporales; la herramienta de inspección
visual falló con «unknown or expired node_repl continuation». Queda pendiente
comprobar layout y foco en cliente Flet a 800 × 480 y en Pi; las pruebas Python
no certifican ese comportamiento del cliente.
