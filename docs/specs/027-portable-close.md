# Cierre idempotente del cliente portátil

## Contexto
Tras pruebas satisfactorias en Pi, el log de cierre muestra FlutterEngineRemoveView
con vista implícita, handlers sin engine y referencias GTK/FlView inválidas.
No contiene traceback Python ni evidencia de fallo de radio. Dos rutas llaman
destroy y el monitor continúa hasta el evento de desconexión.

## Objetivo
Cerrar una sola vez, deteniendo tareas y notificaciones de UI antes de destruir
la ventana, sin interrumpir una sesión o instalación de firmware.

## Alcance
PortableView.close, notificaciones de configuración y eventos de ventana/conexión.

## Fuera de alcance
Cambiar Flet/Flutter, protocolos, firmware o prometer solución al fallo del embedder.
Sin cambios por SSH ni despliegue.

## Comportamiento esperado
Cerrar durante intercambio no hace nada; durante flasheo mantiene progreso.
Cerrar inactivo marca closing, cancela foco/monitor y desacopla listeners antes
de destruir. Peticiones repetidas y refresh tardíos no actualizan la ventana.
El botón y el evento CLOSE usan la misma ruta.

## Decisiones técnicas
Bandera closing establecida antes del primer await; reutilizar disconnect_focus,
ResourceOverlay.sync y TeamView.dispose. Conservar API window.destroy actual.

## Componentes afectados
gui/portable.py; nuevo tests/test_portable_close.py.

## Backend
No detener radio, motor ni procesos de intercambio por efecto de la limpieza UI.

## Frontend
Sin cambio visual ni dimensiones. Mantener guardas busy/session_busy.

## Persistencia
Sin cambios.

## API
Sin cambios.

## Validaciones
Una sola llamada destroy, limpieza anterior, rechazo de cierre durante sesiones,
notificaciones y reconexiones tardías ignoradas.

## Permisos y seguridad
Solo local. No borrar datos ni detener procesos externos.

## Casos límite
Doble clic, CLOSE concurrente, monitor activo, refresh ya encolado, desconexión
posterior y reconexión emitida durante cierre.

## Estrategia de pruebas
Mocks de ventana y barrera de destroy para cierre concurrente; recurso activo;
listeners de configuración y Team; guardas busy y refresh después de closing.

## Estrategia de validación
pytest focalizado -W error y diff --check. El cliente real Pi necesita repetir el
cierre y capturar log; estas pruebas no reproducen ni certifican Flutter/GTK.

## Estrategia de commits
Un commit de cierre, pruebas y spec; el agente principal crea el commit.

## Archivos estimados a modificar
gui/portable.py, tests/test_portable_close.py, esta spec.

## Riesgos
Los avisos pueden originarse en el embedder; ordenar nuestro cierre elimina
productores locales de eventos pero no demuestra la corrección del runtime.

## Preguntas abiertas
¿Persisten los critical del cliente Linux ARM64 tras esta limpieza?

## Plan de implementación
1. Unificar la ruta y hacerla idempotente.
2. Detener productores locales de UI y proteger refresh/reconexión.
3. Probar orden y concurrencia; documentar límites.

## Resultado
44 pruebas aprobadas (cierre, PortableView y recursos) con -W error. Cubren
cierre repetido/concurrente, cancelación de productores antes de destroy,
protección de sesiones/flasheo y eventos tardíos de refresh/conexión.
La corrección ordena el cierre de la aplicación; aún no reproduce ni demuestra
resuelto el error FlutterEngineRemoveView/GTK de Linux ARM64. Pendiente cerrar
el cliente real en Pi y comparar el log, mediante actualización del usuario.
