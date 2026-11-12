# Reinstalación opcional del firmware

## Contexto y objetivo
Permitir probar progreso y logs en una placa C6 que ya responde con firmware compatible, sin forzar una actualización automática.

## Alcance y comportamiento esperado
Acceso a Módulo desde diagnóstico/inicio; acción secundaria Reinstalar firmware en placa lista; pantalla de confirmación con puerto, Cancelar y Confirmar reinstalación. Cancelar/Escape no escribe. Confirmar utiliza el instalador y logs existentes.

## Fuera de alcance
Flashear hardware durante desarrollo, borrar claves, seleccionar firmware arbitrario o actualizar automáticamente.

## Decisiones técnicas / componentes afectados
`Setup.install(reinstall=False)` conserva su protección actual. Solo el opt-in explícito permite estado ready; estados ausente, ocupado o chip incorrecto continúan bloqueados. UI en `gui/portable.py`; reutilizar comprobación física previa y posterior.

## Backend, frontend, persistencia y API
Cambio acotado al controlador y sus vistas. Sin nueva persistencia ni API externa. Confirmación diseñada para 800 × 480 y teclado; foco inicial en Cancelar.

## Validaciones, permisos y seguridad
No iniciar instalación al abrir la confirmación. Revalidar puerto/chip antes de escribir como en el flujo actual. No interrumpir procesos activos al reiniciar el servidor de desarrollo.

## Casos límite y riesgos
Desconexión tras confirmación, doble activación, cambio de placa, error de escritura y pérdida de conexión web: conservar protecciones y logs del flujo existente.

## Estrategia de pruebas y validación
Probar ready con y sin opt-in, estados rechazados, confirmación/cancelación sin efectos y navegación. Verificar UI real sin confirmar un flash físico.

## Plan de implementación / archivos estimados
1. Añadir opt-in en `gui/portable_setup.py` y tests.
2. Añadir acceso y confirmación en `gui/portable.py`; tests de UI.
3. Ejecutar suites portátiles, recompilar y abrir el servidor actualizado si no hay instalación activa.

## Estrategia de commits
Un cambio funcional acotado con tests y documentación. No realizar commits por ahora.

## Preguntas abiertas
Ninguna para implementar. La prueba física la inicia el usuario desde la confirmación.
