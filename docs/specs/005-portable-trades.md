# Intercambios portátiles: diseño aprobado e incremento Equipo

## Contexto
Diseño aprobado en la conversación del 12 de noviembre de 2026. Referencia interactiva: [wireframe](references/portable-trades-wireframe.html); fuente editable: [fragmento](references/portable-trades-wireframe.fragment.html). Es una simulación, no una aplicación funcional ni prueba de hardware. La implementación sigue siendo Python/Flet dentro del fork.

## Objetivo
Desde la galería abrir Intercambios / Equipo a 800 × 480. Reutilizar PKHeX, catálogo, transporte y runner existentes. Conservar UI de escritorio.

## Alcance
Este incremento implementa Equipo: seis borradores por juego, editor reactivo, legalidad estricta, selección de entrenador, conexión local y sesión con logs/cancelación. Documenta todos los otros modos, pero no los activa todavía. Los perfiles adicionales se guardan por juego sin sobrescribir al entrenador base; descubrimiento por intercambio explícito usa los eventos de entrenador existentes.

## Fuera de alcance
Raids, Mystery Gift, online, los otros seis modos funcionales, cambios de protocolos, emulación de Switch, certificación física Pi/C6/Switch. No realizar intercambios ni flasheos para probar automáticamente.

## Comportamiento esperado
### Navegación y editor
- Entrar al seleccionar un juego. Intercambios es la primera acción; estructura preparada para más acciones soportadas.
- Tipos futuros: Equipo, Evolución, Nivel, Naturaleza, EVs, Modificador y Validador. Una modalidad activa; sin acordeones vacíos. Solo Equipo visible mientras sea la única implementada.
- Marco rojo y ajustes existentes; UI española, controles con foco y teclado/táctil. No robar flechas dentro de inputs o búsquedas.
- Seis cajas con sprites (fallback si faltan), un séptimo botón de intercambio por icono. Las cajas vacías no son ofertas aleatorias. De una a seis ocupadas.
- Básico sin scroll a 800 × 480: Especie (búsqueda), Apodo vacío por defecto, Nivel, Variocolor como switch; cuatro movimientos buscables. Avatar y textos alineados.
- EV/IV en sección propia; Avanzado conserva naturaleza, habilidad, sexo, objeto, Poké Ball, amistad, encuentro y opciones específicas disponibles por juego. Atajos maximizar EV y amistad, NO maximizar IV. Usar límites/estadísticas de PKHeX y algoritmo upstream de maximizar esfuerzo.
- Guardar borradores automáticamente. Validar al confirmar selección, cambiar switch o salir de campo, no construir por cada tecla. Una edición invalida inmediatamente el resultado previo. No borrar ni corregir automáticamente valores ilegales. Primer error visible.
- Bloquear envío si falta artefacto validado, hay errores, validación en curso, borrador vacío o resultado obsoleto. Revalidar los bytes exactos antes de enviar; no heredar allow_illegal de escritorio como permiso.
- Vaciar una caja y vaciar equipo con confirmación. No borrar perfiles.
### Entrenadores
- Conservar perfil base de pokeLDN, selección de perfiles previamente usados por juego, resumen nombre/sexo/idioma/ID/SID. ID visible depende de generación; almacenar TID/SID originales de 16 bits.
- Encontrar: generar oferta aleatoria legal, iniciar intercambio explícito, recibir un Pokémon capturado por el jugador, identificar y guardar entrenador compatible, seleccionarlo y revalidar equipo. No tocar las seis cajas con el Pokémon de cortesía. No prometer detección si el recibido no permite reconocer al entrenador. No sobrescribir perfiles diferentes. Nombre y IDs se tratan como datos, nunca argumentos de shell.
### Sesión
- Solo local; no selector online/local. Anfitrión por defecto; Unirse solo cuando lo ofrece el catálogo. Código/versión cuando lo exija la herramienta, sin opción automática de papel.
- Al iniciar bloquear campos, selección, navegación y acciones de mutación; loader sustituye inicio. Cancelar (icono con confirmación) y Logs quedan disponibles arriba.
- En Equipo: esperar / en curso / enviado. Check verde de envío solo al recibir confirmación del protocolo, nunca por pasar legalidad o terminar con código 0. No inventar porcentajes.
- Logs visibles bajo demanda, acotados/redactados; abrir/cerrar no detiene sesión.
- Cancelar solicita cierre mediante runner.Process.stop; no equivale a revertir. Mantener bloqueo hasta on_exit. Upstream cierra stdin y puede terminar/matar tras tiempos de espera. No prometer salida siempre limpia ni entrega confirmada con un timeout.
### Otros modos acordados (posteriores)
- Evolución: recibir y devolver original; evolución por intercambio ocurre en consola si cumple requisitos. Upstream --trade-back ofrece los bytes recibidos, no genera una evolución nueva.
- Nivel: único campo 1–100, recibir original, modificar copia, validar y devolver copia legal.
- Naturaleza: naturaleza buscable; recibir, modificar copia, validar y devolver.
- EVs: seis valores con límites por atributo/total; mismo flujo.
- Modificador: oferta aleatoria legal; al recibir abre automáticamente editor (sin botón Editar); preservar identidad/entrenador original. Barra fija superior con devolver editado, devolver original, logs y cancelar. Solo editor se habilita durante pausa, se bloquea de nuevo al devolver.
- Validador: no modificar original, informe completo conservado en logs y modal. Tarjeta neutra pendiente, verde + Legal o roja + No legal; detalle accesible al finalizar análisis y devolución, sin scroll principal ni apertura automática del modal.
- EXCEPCIÓN AUTORIZADA: devolver exclusivamente el original intacto aunque sea ilegal, también como recuperación si falla una modificación. No autoriza enviar copias editadas ilegales ni aplica al modo Equipo.
- Original separado de copia editable, asociado al intercambio/participante de origen. Cancelar tras recibir deja devolución pendiente, no pérdida silenciosa. Recuperar requiere verificar destinatario. Diseñar persistencia de recuperación antes de activar modos de recepción.

## Decisiones técnicas
Separar estado/borrador/controlador de la presentación Flet. Compartir controlador de sesión entre páginas web del proceso; una sola operación de radio y firmware. Reutilizar pokemon.Service.make/check, nombres/opciones localizados, sprites, command.build, runner.Process/environment y eventos existentes. Estado por revisión impide que respuestas lentas sobrescriban cambios recientes. No construir un segundo frontend.

## Componentes afectados
`gui/portable.py`, nuevos módulos de equipo/controlador, tests portátiles y docs/ai. `gui/portable_setup.py` para exclusión de radio durante sesiones.

## Backend
Oferta generada como archivo por PKHeX; comprobar bytes antes del envío, cola con tamaño exacto y herramientas board/local filtradas del catálogo. Eventos de progreso y entrenador existentes; salida de proceso distinta de confirmación por Pokémon.

## Frontend
Formulario estable: actualizaciones de estado no destruyen inputs ni foco. Diálogos para búsqueda extensa/ajustes/logs/perfiles. Controles de texto a 34–40 px; objetivos táctiles cuando el espacio permita. Validar visualmente.

## Persistencia
JSON versionado privado bajo POKELDN_DATA/portable, escritura atómica. Borradores y perfiles separados de settings upstream; no migración destructiva. No confiar en flags de legalidad guardados: restaurar como pendientes y revalidar. Nunca persistir claves. Mantener archivos corruptos para diagnóstico, no sobrescribirlos silenciosamente.

## API
Sin HTTP público ni cambio al contrato PKHeX; API interna Python.

## Validaciones
Campos numéricos, EV total, nivel, IDs, cola, rol permitido, versión, claves/radio, revisión del resultado y legalidad estricta. El error no limpia formulario.

## Permisos y seguridad
Inicio de intercambio solo por acción explícita; pruebas con fake runner, jamás con Switch real. No shell=True. No leer ni imprimir prod.keys. Bloqueo compartido entre páginas durante preparación/sesión/flasheo. Mantener logs redactados.

## Casos límite
Respuesta obsoleta, editar durante validación, doble clic de inicio, nueva sesión web, cerrar navegador en operación, fallo de servicio/puerto, cancelación en preparación o sesión, archivo alterado desde validación, selección de entrenador/version invalida artefactos.

## Estrategia de pruebas
Borradores recuperables, no enviar inválidos/pending/stale, resultados fuera de orden, cola de 1/6, vacíos, guardia de sesión, cancelación no desbloquea prematuramente, progreso solo confirmado. UI construye sin hardware; validación real PKHeX con datos de prueba y 800 × 480.

## Estrategia de validación
pytest focalizado y suites command/runner afectadas; compileall, diff --check, PKHeX build si cambia .NET (no previsto), preview local con datos aislados y comprobación visual. No afirmaciones de hardware sin evidencia.

## Estrategia de commits
Documentación/referencia, estado y validación, UI/sesión, tests/resultados. No commit ni push automático.

## Archivos estimados a modificar
Los módulos arriba descritos, `tests/test_portable_team*.py`, docs/ai y esta spec.

## Riesgos
Diferencias entre juegos, restricciones de generación, los protocolos pueden transformar registros para transporte; la comprobación estricta debe realizarse también en la preparación de oferta. Flet foco/teclado, cambios de idioma, sprites sin red, terminación forzada, eventos de progreso heterogéneos.

## Preguntas abiertas
Ninguna bloqueante para Equipo. Recuperación persistente de originales y comprobación de identidad en los modos posteriores requieren diseño antes de implementación. Prueba física de cada juego pendiente.

## Plan de implementación
1. Guardar fuente y exportación HTML del wireframe, acuerdos y alcance.
2. Implementar almacén y controlador de seis borradores/perfiles, validación por revisión y checks antes de envío; pruebas de invariantes.
3. Integrar vista Equipo en galería; básico/estadísticas/avanzado, búsquedas, sprites, selección y confirmaciones.
4. Conectar herramientas locales del catálogo y runner, progreso/logs/parada; integrar exclusión de radio.
5. Validar suites, arranque y pantalla 800 × 480; documentar evidencia y límites reales.

## Resultado del incremento

Equipo integrado en la galería con controlador independiente, persistencia privada por juego, editor básico/EV-IV/avanzado, búsquedas y sprites, perfiles, conexión local, logs y cancelación. Otras modalidades permanecen solo en el wireframe.

Validación: 272 pruebas focalizadas de portátil, servicio Pokémon y runner pasaron; generación real PKHeX de Arcanine en SV legal. En navegador a 800 × 480 se comprobó búsqueda, formulario sin scroll y nivel 101 conservado con error y envío bloqueado; corregirlo vuelve a validar. No se realizó intercambio ni flasheo real. Navegación actual por Tab/Shift+Tab y controles nativos; la ergonomía final de cruceta y teclado físico sigue pendiente en Pi.

### Ajuste de alineación y selectores

Entrenador, especie y movimientos usan dropdown editable con filtro, flecha de apertura y fondo neutro. Una consulta sin seleccionar restaura la opción válida anterior al perder foco. Base de pokeLDN es una opción real seleccionada inicialmente. Campos básicos alineados a 48 px, compensando densidad compacta de Flet; etiquetas y botones de entrenador alineados. Apodo muestra máximo 10 en Gen3 y 12 en Switch; se conserva validación sin borrar el texto inválido. Ver [captura corregida](references/implemented-team-aligned-800x480.jpg). Validación: 54 pruebas focalizadas y revisión visual a 800 × 480.

### Selectores compactos

Se reduce la altura de 48 a 40 px, incluyendo iconos internos y espacio de filas para evitar superposiciones a 800 × 480. La × limpia especie, restablece opciones opcionales a Automático y entrenador a Base de pokeLDN; respeta bloqueo de sesión y dispara la misma validación que una selección. 56 pruebas focalizadas aprobadas.

### Diagnóstico de Squirtle / FRLG

Se comparó make de escritorio y portátil con Squirtle (7), FR, nivel 100 y opciones vacías: ambos legales; 20 generaciones y checks con la configuración base actual también legales. Borrador persistido: caja 1 Squirtle legal, caja 2 incompleta. Corregido el mensaje global para identificar la caja de errores ajenos y eliminado el segundo flujo de carga de metadatos en _commit: validate ya carga opciones y controla errores por revisión. La causa exacta del rechazo de especie reportado no se reprodujo. Diferencia observada: escritorio reinicia forma/movimientos/encuentro/confite al cambiar especie; portátil conserva datos explícitos conforme al acuerdo de no limpiar automáticamente.

### Aclaración: validación por caja

El mensaje de legalidad corresponde exclusivamente a la caja seleccionada: primer error, validando, pendiente o éxito verde. Errores y validaciones de otras cajas no sustituyen ese mensaje. El botón de intercambio sigue exigiendo que todas las cajas ocupadas sean legales y actuales. Esta decisión reemplaza el aviso de errores ajenos identificado por número de caja.

### Búsqueda al enfocar

Los selectores buscables vacían solo la consulta al recibir foco (clic o teclado). Conservan la opción confirmada hasta una selección explícita o ×; al perder foco restauran su etiqueta. Aplica a entrenador, especie, movimientos y opciones avanzadas. Los selectores no editables conservan su comportamiento.
