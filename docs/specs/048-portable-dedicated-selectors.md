# Selectores dedicados en toda la superficie

## Contexto
La spec 046 dejó el campo Dropdown nativo con un acceso adicional en su flecha.
El usuario reporta que los selectores siguen sin usar el componente dedicado.
## Objetivo
Abrir TouchOptions desde toda la superficie del selector buscable.
## Alcance
Selectores compartidos de Equipo, Banco/Editar y modos recibidos: especie,
movimientos, entrenador y opciones buscables. Mantener selectores no buscables.
## Fuera de alcance
Teclado del sistema, fullscreen, protocolos y UI escritorio.
## Comportamiento esperado
Nombre/flecha y Enter abren una única lista con consulta inicialmente vacía.
La selección confirmada permanece visible y no cambia al buscar o cancelar.
X conserva Base/Automático/sin selección. Refrescar no reemplaza consulta activa.
## Decisiones técnicas
Reutilizar TouchOptions con un TouchSelector basado en Container/TextButton,
sin Dropdown nativo debajo. Mantener options/value/data para los callbacks y caches
existentes. Reutilizar controles al navegar cajas. No abrir automáticamente al foco.
Esta decisión sustituye para buscables la búsqueda dentro del campo y el menú
280 × 160 de specs anteriores; se mantiene el diálogo acotado de spec 046.
## Componentes afectados
portable_touch, TeamView.dropdown, tests de selectores y docs/ai.
## Backend
Sin cambios; confirmación mediante callbacks existentes.
## Frontend
Campo de 40 px, X independiente y botón accesible con nombre/flecha.
## Persistencia
Sin cambios.
## API
Sin cambios externos.
## Validaciones
No abrir duplicados ni elegir controles/opciones deshabilitados.
## Permisos y seguridad
Fixtures sin radio ni datos personales.
## Casos límite
Opciones cambiadas, búsqueda sin resultados, reapertura, refresh, sesión bloqueada.
## Estrategia de pruebas
Reemplazar tests del contrato nativo retirado por apertura, consulta temporal,
confirmación, cancelación y refresh del componente dedicado. Mantener tests de X.
## Estrategia de validación
Pytest -W error y cliente Flet a 800 × 480, tocando centro y flecha, no solo flecha.
## Estrategia de commits
Corrección acotada; no hay petición de commit en este turno.
## Archivos estimados a modificar
Componentes anteriores, tests de Equipo/recibidos/entrenador y documentación.
## Riesgos
Regresión de selección por sustituir el widget; comprobar callback real y teclado.
## Preguntas abiertas
Validación física del dedo y teclado virtual en Pi continúa pendiente.
## Plan de implementación
1. Introducir TouchSelector reutilizando diálogo y lista de spec 046.
2. Integrar únicamente selectores buscables; preservar caches y callbacks.
3. Actualizar tests de comportamiento, validar cliente y documentar evidencia.

## Resultado y evidencia
Implementado TouchSelector en la fábrica compartida de selectores buscables.
202 pruebas pasan con -W error: portable_team_view, portable_received_view,
portable_trainer_label, portable_touch, portable_bank, portable_ui y gui_layout.
Cliente Flet nativo Mac, área 800 × 480, fixture temporal con vistas de producción
y modelo simulado: centro y flecha abren el diálogo; arrastre vertical desplaza
opciones sin confirmar; Escape cierra; Tab muestra borde de foco en el selector.
La sesión se cerró durante la comprobación de Enter y no se pudo completar esa
validación. No se certifica activación por teclado ni interacción física en Pi.
Confirmación/cancelación y callbacks comprobados mediante pruebas automatizadas;
el fixture visual no genera ni guarda Pokémon.
