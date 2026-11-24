# Contratos de UI portátil

Leer antes de modificar las vistas. Nuevas peticiones son incrementales: no anulan estos acuerdos salvo instrucción expresa. Detalle funcional en decisiones y specs 005–010.

| Área | Comportamiento que debe conservarse |
|---|---|
| Pantalla | 800 × 480, marco rojo, ajustes arriba; Básico sin scroll. No añadir altura al introducir atajos |
| Arranque | Checks válidos → juegos; requisitos pendientes → diagnóstico. Esperar comprobación compartida entre pestañas. Ajustes manuales permanecen abiertos |
| Galería | Una fila horizontal, avatares y nombres alineados, fallback Poké Ball |
| Selectores | Entrenador/especie/movimientos/opciones buscables: nombre/flecha abre TouchOptions mediante TouchSelector; consulta vacía al abrir; selección confirmada intacta hasta elegir o X. Foco no abre automáticamente (spec 048) |
| Búsqueda activa | Consulta temporal en el diálogo; refresh no la reemplaza. Cancelar/Escape conserva selección. Mantener navegación por teclado y tacto |
| Desplegable | Buscables: diálogo con contenido 400 × 248, búsqueda y lista arrastrable. No buscables: menú acotado 280 × 160. Anchos finitos; cierre sin elegir |
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

## Particularidad histórica de Flet 1.0.5

El Dropdown nativo sincronizaba su TextEditingController solo al cambiar value.
La spec 048 retira ese campo de los selectores buscables portátiles: TouchSelector
muestra la selección confirmada y TouchOptions mantiene la consulta separada.
No reintroducir una segunda ruta nativa al tocar el nombre. Conservar options,
value y data para los callbacks y caches compartidos.

Pruebas en test_portable_team_view.py y test_portable_touch.py cubren consulta,
confirmación, cancelación, opciones dinámicas y refresco del componente dedicado.
Complementar con cliente Flet real; propiedades Python no certifican su interacción.

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

Actualización spec 034: botón de conexión sin label redundante, conservando
105 × 40, contenido rol/código y alineación inferior de la cabecera.

Entrenador (spec 035): sin título de IDs ni botón de datos; selector + Encontrar
en fila de 40 px alineada con Conexión, dentro de cabecera de 60 px. Conservar
consulta temporal, identidad en opciones/tooltip y X hacia Base de pokeLDN.

Código visible (spec 036): guion central únicamente para presentación de más
de cuatro dígitos, preservando ceros y código original en modelo/transporte.

Movimientos Automático (spec 037): generación nueva completa huecos incluso con
manuales; cada manual se conserva y el resultado debe ser legal. Recibidos/Banco
usan el movimiento original del slot. No convertir Automático en borrado implícito
ni inventar cuatro movimientos cuando especie/nivel no los permite.

Contraste (spec 038): TextTheme portátil declara INK explícito. No usar previews
con un Theme simplificado como prueba del tema de producción. Verificar texto
normal, títulos, etiquetas y acciones sobre superficies claras con cliente real.

Filtros de bibliotecas (spec 039): menú flotante claro y opciones oscuras
explícitas; altura 160 con scroll. No heredar PANEL oscuro del helper desktop.

Flet 1.0.5: Dropdown.bgcolor prevalece sobre MenuStyle.bgcolor. Los filtros
portátiles deben fijar ambos claros; comprobar menú abierto, no solo campo.
Verificación nativa de ambos menús y selección completada (spec 039).

Actualización spec 041: en Equipo, Modificar y Banco → Editar, Automático ahora
solicita completar el slot, también si originalmente estaba vacío. Vacío es una
opción explícita distinta (0); nunca mostrar «0» como etiqueta de ese movimiento.
Conservar manuales/posiciones, búsqueda y X hacia Automático. No llenar Vacío
ni desplazar movimientos para ocultar ilegalidad. Selector compartido comprobado
en cliente nativo con fixture temporal a 800 × 480: menú legible y selección
Vacío ↔ Automático; servicio/controladores verificados por pruebas separadas.

Actualización (spec 042): icono dinámico inmediatamente a izquierda de Ajustes,
sin nueva fila de cabecera. Deshabilitado durante radio/check/flash/escrituras.
Confirmación antes de handoff; teclado/clics bloqueados mientras abre auxiliar.
Ajustes reutiliza la línea de estado inicial para actualización/reintento cuando
no hay check de hardware. El progreso de hardware mantiene prioridad.
Auxiliar nativo independiente 800 × 480: etapa/indicador, detalles acotados de logs,
error persistente y Cerrar disponible sólo al finalizar. Nueva UI no inicia checks
ni sesiones antes del handshake. Verificados icono, modal, progreso, detalles,
error y estado de Ajustes con Computer Use y fixtures temporales.
Galería mantiene ↑ hacia Ajustes aunque aparezca Actualizar; ←/→ navegan los
botones habilitados de cabecera y ↓ vuelve al juego. Comprobado en cliente nativo.

Carpeta de datos (spec 043): si hay dos ubicaciones pobladas y no hay selección ni
override explícito, mostrar selector antes de cargar configuración/radio. Rutas
completas, acción por carpeta y Cancelar; Tab/Enter y scroll mantienen acceso incluso
con rutas largas a 800 × 480. No mostrar contenido personal. Guardar sólo preferencia,
salir y continuar arranque principal; cancelar no crea perfil vacío. Errores de ruta
visibles, sin fallback silencioso. Verificado en cliente nativo con carpetas temporales.

Accesos directos (spec 044): icono antes de Update/Ajustes sin nueva fila.
Menú claro con dos acciones; deshabilitar durante actividad y escritura.
Conservar navegación de cabecera; el menú recibe sus propias flechas/Escape.
CUA a 800 × 480 con y sin Update: clic/Enter abre y Escape cierra sin salir
de galería. Resultado modal con ruta, datos y advertencias. Linux real pendiente.

Pantalla completa (spec 045): arranque portátil Linux nativo sin barras del
escritorio mediante fullscreen. F11 alterna en las vistas nativas, incluida Equipo;
web conserva el control del navegador. Escape no sale de fullscreen: mantiene su
función actual. Handoff y menú de accesos conservan su bloqueo de atajos.

Swipe (spec 046; acceso a selectores sustituido por 048): galería arrastrable horizontalmente, barra AUTO. Flecha de los
selectores buscables abre lista táctil adicional con búsqueda temporal y scroll
vertical. Arrastrar no elige, tocar opción habilitada confirma una sola vez;
Cancelar/Escape conserva elección. Campo nativo, consulta al foco y X conservados.
El diálogo no activa automáticamente el buscador/teclado; no reenvía atajos de
la vista de fondo mientras está abierto, salvo F11. Al cerrar restaura el handler.
Validado con cliente Mac a 800 × 480; Pi táctil y teclado virtual pendientes.

Pantalla completa táctil (spec 047): botón a izquierda de Ajustes; permanece visible
en cliente nativo incluso fuera de la galería. F11 y toque comparten acción; icono
y tooltip reflejan estado. ↑ sigue enfocando Ajustes, ← llega a fullscreen y ↓
vuelve a juegos. Sin filas nuevas ni cambios de datos al alternar.

Selectores dedicados (spec 048): toda la superficie nombre/flecha abre la misma
lista táctil; no queda Dropdown nativo debajo. X independiente; campo de 40 px,
selección visible y borde de foco. Búsqueda únicamente dentro del diálogo.
Evidencia visual y límites de teclado/Pi registrados en spec 048.

Actualizador fullscreen (spec 049): botón de 40 px al extremo derecho del título,
sin fila adicional; F11 comparte acción. Linux nativo inicia fullscreen; web oculta
botón. Alternar preserva progreso/logs y no cambia el bloqueo de Cerrar durante
instalación. Verificados entrada/salida por botón y detalles a 800 × 480 en Mac.

Prueba sin bordes (spec 050): sólo con POKELDN_PORTABLE_BORDERLESS=1 en Linux
nativo. Canvas mínimo 480 dentro de viewport con scroll/swipe cuando el área útil
es menor, conservando tamaños y referencias de controles. A 800 × 480 mantiene
Básico completo. Al volver de fullscreen por botón/F11, maximizar la ventana sin
bordes. No asumir que la prueba Mac certifica teclado/compositor de Pi.

Default sin bordes (spec 051, sustituye opt-in de 050 y arranque de 045): Linux
nativo abre maximizado sin bordes sin variable adicional. Mismo viewport adaptable;
botón/F11 entra en fullscreen y regresa a maximizado. El dock reserva espacio.
No se persiste estado. Actualizador conserva spec 049; otras plataformas intactas.

Estadísticas (spec 052): botón a derecha de Ajustes, sin nueva fila; clic y `?`
comparten estado e indicador cian. ↑ sigue llegando a Ajustes, → al monitor.
Disponible durante sesiones; muestreo sólo mientras visible y conectado.
