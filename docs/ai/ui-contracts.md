# Contratos de UI portátil

Leer antes de modificar las vistas. Nuevas peticiones son incrementales: no anulan estos acuerdos salvo instrucción expresa. Detalle funcional en decisiones y specs 005–009.

| Área | Comportamiento que debe conservarse |
|---|---|
| Pantalla | 800 × 480, marco rojo, ajustes arriba; Básico sin scroll. No añadir altura al introducir atajos |
| Arranque | Checks válidos → juegos; requisitos pendientes → diagnóstico. Esperar comprobación compartida entre pestañas. Ajustes manuales permanecen abiertos |
| Galería | Una fila horizontal, avatares y nombres alineados, fallback Poké Ball |
| Selectores | Entrenador/especie/movimientos/opciones buscables: al recibir foco, consulta vacía; selección confirmada intacta hasta elegir o X; al salir restaurar selección. No validar por escribir consulta |
| Búsqueda activa | Refresh no repone el texto mientras se busca. Clic dentro de una consulta activa no debe borrarla de nuevo. Selección por teclado y tacto sigue disponible |
| Desplegable | Menú acotado 280 × 160; campo visible para escribir; cierre sin elegir. Ancho preferido finito, no infinito |
| X | Entrenador → Base de pokeLDN; movimiento → Automático; especie → sin selección |
| Cajas | Reutilizar controles; opciones/cache por configuración; cambiar caja no genera innecesariamente. Estado y primer error corresponden a caja activa |
| Legalidad | Editar no borra valores ilegales; validar al confirmar/salir del campo, no cada tecla. Equipo solo se envía si todas las ofertas actuales son legales; volver a comprobar bytes |
| Máximos | Checkboxes EV/amistad por caja en fila de pestañas; sin modificar IVs. Desmarcar → Automático. No son reglas persistentes para nuevas especies |
| Sesión | Edición bloqueada, loader, logs y cancelación con confirmación. Éxito depende de eventos, no solo salida del proceso |
| Identificación | Devolución opcional nativa del original, dos confirmaciones, perfil del primer intercambio. Cancelación entre rondas → devolución pendiente, sin promesa de recuperación automática |

## Particularidad de Flet 1.0.5

El cliente `Dropdown` solo sincroniza su TextEditingController al cambiar `value`, no al asignar únicamente `text`. Durante búsqueda, `value=None` es estado temporal del widget; `data` y el modelo conservan la elección confirmada. No eliminar esta separación para «simplificar» el componente. `portable_searching` evita que refresh de entrenador restaure prematuramente el valor. Fuente consultada: [implementación oficial 1.0.5](https://github.com/flet-dev/flet/blob/v1.0.5/packages/flet/lib/src/controls/dropdown.dart).

Pruebas: `test_focus_clears_query_without_changing_committed_option`, `test_trainer_refresh_does_not_replace_active_query`, `test_dynamically_populated_selector_keeps_bounded_menu`. Complementar con inspección visual: la primera versión del test de foco pasaba aunque el campo visible no se vaciaba.

## Registro mínimo por cambio

Registrar decisión, spec, componentes afectados, pruebas ejecutadas y límites. Al corregir una regresión, conservar su causa técnica aquí o en desarrollo y su reproducción en la spec; no afirmar una prueba visual que solo se hizo con mocks.
