# Contratos de UI portátil

Leer antes de modificar las vistas. Nuevas peticiones son incrementales: no anulan estos acuerdos salvo instrucción expresa. Detalle funcional en decisiones y specs 005–010.

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
| Equipo secuencial | Básico visible sin Crear Pokémon. Solo especie hace que una caja cuente como oferta y habilite la siguiente. Ocupadas + primera vacía accesibles; borrar caja o especie compacta a la izquierda, preservando datos y resultados actuales. Una respuesta asíncrona antigua nunca se aplica a otro índice |
| Cabecera de intercambio | Modalidad, grupo de entrenador (búsqueda + datos + encontrar) y conexión en una fila compartida. Recibidos usa el perfil para cortesía; conserva siempre el dueño original. Grupo bloqueado durante toda la sesión, incluida edición manual |
| Actividad visible | Preparación explícita antes del lanzamiento, proceso iniciado separado de consola conectada, error destacado en rojo. No afirmar radio lista o jugador encontrado sin evento que lo confirme. Logs y cancelación permanecen accesibles |
| Legalidad | Editar no borra valores ilegales; validar al confirmar/salir del campo, no cada tecla. Equipo solo se envía si todas las ofertas actuales son legales; volver a comprobar bytes |
| Máximos | Checkboxes EV/amistad por caja en fila de pestañas; sin modificar IVs. Desmarcar → Automático. No son reglas persistentes para nuevas especies |
| Sesión | Edición bloqueada, loader, logs y cancelación con confirmación. Éxito depende de eventos, no solo salida del proceso |
| Identificación | Devolución opcional nativa del original, dos confirmaciones, perfil del primer intercambio. Cancelación entre rondas → devolución pendiente, sin promesa de recuperación automática |
| Modalidades recibidas | Evolución/Nivel/Naturaleza/EVs/Modificador/Validador desde cabecera; no borrar Equipo. Original separado; copia ilegal bloqueada; original intacto permitido |
| Modificador | Abrir editor al recibir, acciones devolver original/copia/logs/cancelar arriba. Editar no libera radio ni habilita cambiar juego/rol/modo. No generar otro Pokémon para aplicar cambios |
| Validador | Tarjeta verde/roja/neutra; informe completo en modal y logs, sin scroll principal. Informe persiste después de devolver |
| Nuevo intercambio | Acción explícita de configuración tras terminar; conserva aviso y archivos de devoluciones pendientes. No reenvío automático en otra sesión |

## Particularidad de Flet 1.0.5

El cliente `Dropdown` solo sincroniza su TextEditingController al cambiar `value`, no al asignar únicamente `text`. Durante búsqueda, `value=None` es estado temporal del widget; `data` y el modelo conservan la elección confirmada. No eliminar esta separación para «simplificar» el componente. `portable_searching` evita que refresh de entrenador restaure prematuramente el valor. Fuente consultada: [implementación oficial 1.0.5](https://github.com/flet-dev/flet/blob/v1.0.5/packages/flet/lib/src/controls/dropdown.dart).

Pruebas: `test_focus_clears_query_without_changing_committed_option`, `test_trainer_refresh_does_not_replace_active_query`, `test_dynamically_populated_selector_keeps_bounded_menu`. Complementar con inspección visual: la primera versión del test de foco pasaba aunque el campo visible no se vaciaba.

## Registro mínimo por cambio

Registrar decisión, spec, componentes afectados, pruebas ejecutadas y límites. Al corregir una regresión, conservar su causa técnica aquí o en desarrollo y su reproducción en la spec; no afirmar una prueba visual que solo se hizo con mocks.

Modales de entrenador/conexión: columnas ajustadas (`tight=True`), acciones siempre visibles a 800 × 480 incluso con error LGPE. Mantener datos agrupados y Guardar/Listo primario; Cancelar no persiste. No expandir la columna verticalmente ni trasladar este estilo automáticamente al comparador aprobado (spec 014).
Papel en conexión: selector segmentado, una selección obligatoria, solo opciones admitidas por el juego. Sin Unirse disponible se muestra únicamente Anfitrión seleccionado. Cambiar segmento no guarda hasta confirmar (spec 015).
Alturas de conexión (Flet 1.0.5): segmentado con densidad STANDARD para que el fondo seleccionado llene sus 40 px. Código denso, texto 16, padding vertical 12 y contador oculto: 48 px totales producen borde visible de 40 px en el cliente actual. No igualar únicamente height sin revisar los bordes en captura; Flutter reserva espacio de contador. Borde gris y foco cian, misma esquina de 8 px.

Facilities de Ajustes (specs 028/029): Entrenadores y Banco mantienen búsqueda
y filtro por juego, acciones por fila y confirmación de borrado. Bulk abarca
todos los registros, incluso ocultos por filtros. Exportar nunca sobreescribe
un archivo existente. Banco conserva fuente inmutable; editar usa una copia
y salir invalida validaciones pendientes. Listas y confirmaciones comprobadas
en cliente Flet local a 800 × 480 con fixtures temporales (2026-11-16).

Comprobación inicial (spec 032): indicador animado y etapa visibles; aviso lento
tras ocho segundos. Radio sigue reservada hasta finalizar; Entrenadores/Banco
pueden consultarse y exportarse durante el check. Mutaciones conservan sus guards.

Conexión (spec 033): código literal visible debajo del rol en el mismo botón,
105 × 40, cabecera de 60 px. No añadir filas externas ni quitarlo durante sesión.
