# Ciclo de vida del foco portátil

## Contexto
En Pi el usuario reporta demora al abrir después de compilar, sin procesos
residuales. Log: Task was destroyed but it is pending, PortableView.focus.
go descarta el Future de page.run_task; start duplica foco tras go(home).
La sesión Flet espera respuestas de métodos del cliente.

## Objetivo
Retener tareas de foco hasta su finalización y cancelarlas al cerrar/desconectar.

## Alcance
Ciclo de vida del foco automático y solicitud única al iniciar la galería.

## Fuera de alcance
Compilación PKHeX, firmware, drivers GTK, timeouts arbitrarios, despliegue SSH.
No afirmar que este cambio demuestra toda la causa de la demora física.

## Comportamiento esperado
Referencias fuertes a Futures pendientes; retirada al completar; cancelación
al desconectar/cerrar. No emitir foco automático desconectado. Reanudar permiso
al reconectar. Una única solicitud al entrar a home desde start.

## Decisiones técnicas
Reutilizar page.run_task con conjunto de Futures y callback de finalización.
Preservar gallery_navigation: selección espera respuesta antes de desmontar
controles para evitar regresión de sesión cerrada por respuestas tardías.

## Componentes afectados
PortableView, handlers de conexión/cierre y tests/test_portable_ui.py.

## Backend
Sin cambios a motor, radio ni sesiones de intercambio.

## Frontend
Sin cambios visuales ni controles; preservar teclado y foco del editor.

## Persistencia
Sin cambios.

## API
Sin cambios.

## Validaciones
Tarea esperando respuesta permanece viva incluso tras gc; limpieza al completar
y cancelación liberan lock. Arranque no duplica foco.

## Permisos y seguridad
No cancelar firmware/intercambio; solo tareas automáticas de presentación.
Cambios locales únicamente.

## Casos límite
Finalización inmediata, Future cancelado, desconexión con foco pendiente,
reconexión y arranque con navegación manual durante checks.

## Estrategia de pruebas
Reproducir tarea en espera sin referencia externa, forzar gc y comprobar que
permanece viva; cancelar y verificar que libera lock. Regresión galería existente.

## Estrategia de validación
pytest focalizado -W error y diff --check. Cliente Pi pendiente de prueba real,
no usar mocks como evidencia del comportamiento Flutter.

## Estrategia de commits
Cambio local cohesivo de lifecycle y regresiones, sin publicación automática.

## Archivos estimados a modificar
gui/portable.py, tests/test_portable_ui.py, docs/ai/decisions.md.

## Riesgos
Este aviso puede ser síntoma de desconexión previa; retener tareas no demuestra
la causa de todas las esperas del cliente. No retirar el lock de navegación.

## Preguntas abiertas
Reproducción de arranque/cierre en Pi tras aplicar y capturar logs completos.

## Plan de implementación
1. Mantener y limpiar Futures de foco automático.
2. Cancelarlos al cierre/desconexión y eliminar duplicación en start.
3. Probar lifecycle y navegación; registrar límites.

## Resultado
Reproductor local con Flet page.run_task equivalente (run_coroutine_threadsafe),
Future sin respuesta y gc.collect: implementación anterior emite exactamente
"Task was destroyed but it is pending!"; implementación retenida no lo emite.
85 pruebas Setup/UI/TeamView aprobadas con -W error; diff --check sin errores.
La prueba fuerza una espera aislada, no reproduce el transporte Flutter real.
Pendiente arranque y navegación a 800 × 480 en Pi; sin SSH ni despliegue.
