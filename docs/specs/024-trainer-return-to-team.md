# Regreso a Equipo después de identificar entrenador

## Contexto
Volver a Equipo existe al final del contenido desplazable de identificación,
pero el usuario no lo encuentra. Pide retorno automático al finalizar con éxito
y mensaje con nombre, ID y SID. Cambios exclusivamente locales; no SSH.

## Objetivo
Acción visible de regreso y transición automática segura al editor de Equipo.

## Alcance
Vista de identificación de Team, mensaje de éxito y pruebas de comportamiento.

## Fuera de alcance
Protocolos, modalidades Received, recuperación de originales y despliegue remoto.

## Comportamiento esperado
Éxito requiere fase done, sin error ni sesión activa, entrenador identificado
y 1 confirmación o 2 si se pidió devolución. Mostrar Equipo y nombre/ID/SID
usando console_trainer.shown. Error/cancelación conserva pantalla y aviso.
Volver a Equipo aparece en fila fija; deshabilitado durante sesión.
El regreso manual no oculta advertencias de devolución pendiente.

## Decisiones técnicas
Transición de presentación en TeamView sin modificar el estado discovering del
controlador (necesario para validación tardía y return_pending). Reutilizar fila
de acciones y status_panel; no añadir filas ni cambiar dimensiones.

## Componentes afectados
TeamView y tests/test_portable_team_view.py.

## Backend
Sin cambios.

## Frontend
Botón fijo y mensaje específico que sustituye el éxito genérico.

## Persistencia
Sin cambios.

## API
Sin cambios.

## Validaciones
No volver automáticamente antes de la confirmación final y cierre real.

## Permisos y seguridad
No cerrar sesiones, reenviar Pokémon ni modificar claves. Sin SSH.

## Casos límite
Devolución pendiente, cancelación, error guardando perfil, validación asíncrona,
nueva identificación después del regreso manual.

## Estrategia de pruebas
Éxito con/sin devolución; espera de segunda confirmación; error/cancelación;
botón fijo, regreso manual y aviso pendiente conservado.

## Estrategia de validación
pytest focalizado con -W error y diff --check. Cliente real 800 × 480:
registrar evidencia o indicar pendiente; mocks no prueban layout Flutter.

## Estrategia de commits
Cambio cohesivo local de vista/pruebas/documentación; usuario publica y despliega.

## Archivos estimados a modificar
gui/portable_team_view.py, tests/test_portable_team_view.py, docs/ai/decisions.md.

## Riesgos
No confundir identificación confirmada con devolución confirmada.
No mutar discovering durante notify: el controlador aún programa validación.

## Preguntas abiertas
Verificación visual en cliente Pi tras actualización del usuario.

## Plan de implementación
1. Definir condición conservadora de éxito y presentación de datos.
2. Mover acción al área fija preservando advertencia pendiente y sesión.
3. Probar transiciones y documentar límites.

## Resultado
137 pruebas aprobadas de TeamView, Team, Received y ReceivedView con -W error;
git diff --check sin errores. Cubiertos éxito con/sin devolución, cierre aún
activo, retorno incompleto, error, cancelación y nueva sesión tras regreso manual.
Pendiente inspección del cliente Flet real a 800 × 480 en Pi: las pruebas de
controles no certifican layout Flutter. No se realizó acceso SSH ni despliegue.
