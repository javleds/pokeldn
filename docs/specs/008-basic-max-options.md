# Atajos de máximos en Básico

## Contexto
El usuario necesita EVs máximos y amistad máxima por Pokémon sin abrir otras secciones ni añadir altura.
## Objetivo
Añadir dos checkboxes compactos en la fila existente de pestañas, visibles en Básico para una caja ocupada.
## Alcance
Estado derivado de los valores de la caja; activar aplica el algoritmo existente de máximos, desactivar vuelve ese grupo a Automático. No afecta IVs.
## Fuera de alcance
Cambiar algoritmo de reparto, modo Equipo, protocolos o persistencia.
## Comportamiento esperado
Controles por caja, bloqueados durante intercambio. EVs/AVs/esfuerzo según metadatos del juego. Máximos requieren metadatos cargados. Validación y autoguardado existentes tras cada acción. No añade filas ni scroll.
## Decisiones técnicas
Reutilizar _max, modelo.edit, _commit y metadatos. Extraer cálculo para mostrar estado del checkbox sin duplicar reglas. No añadir flags persistidos ni prometer mantener máximo tras cambiar especie.
## Componentes afectados
TeamView y pruebas.
## Backend
Sin cambios.
## Frontend
Checkboxes a la derecha de Básico/EV-IV/Avanzado, antes de limpiar caja. Tooltip explica desactivar a Automático.
## Persistencia
Mismas opciones effort/friendship del borrador.
## API
Sin cambios.
## Validaciones
Legalidad final conservada, sin cambios durante sesión, sin reparto de EV sin metadatos.
## Permisos y seguridad
No iniciar intercambio físico.
## Casos límite
Caja vacía, cambiar caja, máximos manuales ya existentes, metadatos pendientes, reparto específico que no coincide con el atajo.
## Estrategia de pruebas
Activación, desactivación y sincronización por caja; bloqueo durante sesión.
## Estrategia de validación
pytest y vista simulada 800 × 480.
## Estrategia de commits
Cambio UI y tests juntos; sin commit automático.
## Archivos estimados a modificar
Gui portable_team_view.py, tests/test_portable_team_view.py y docs AI.
## Riesgos
Desactivar vuelve a Automático, no restaura un reparto previo; explicitar en tooltip. Cambiar especie no activa un modo persistente de maximización.
## Preguntas abiertas
Ninguna bloqueante.
## Plan de implementación
1. Reutilizar cálculo y añadir checkboxes a fila existente.
2. Probar acciones y cambio de caja; verificar resolución y reiniciar app.

## Resultado
Implementado en la fila existente de pestañas. 55 pruebas de controlador/vista aprobadas; fixture visual a 800 × 480 confirma que no añade altura ni scroll. Referencia: [Básico con checkboxes](references/implemented-basic-max-demo-800x480.jpg). Sin prueba física de intercambio.
