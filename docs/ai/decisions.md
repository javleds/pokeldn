---
title: Decisiones del dispositivo portátil
nav_exclude: true
search_exclude: true
---
# Decisiones acordadas

## Investigación de portátil económico (2026-11-15)

Separación posterior autorizada: repositorio local independiente `pokemon-handheld`,
hermano de este fork, con Git e instrucciones propios. Se trasladó una copia inicial
de la auditoría y evidencia; allí continúa el plan activo. La spec 021 de este fork
queda como registro histórico. No compartir archivos mediante symlinks ni adoptar
cambios automáticamente. Pi/Flet continúa su desarrollo y fixes de forma independiente.
El nuevo repositorio fija la revisión PokeLDN de referencia; actualizaciones de
protocolos/firmware/helper requieren revisión y pruebas explícitas. No se creó un
tercer repositorio común ni se copiaron fuentes de aplicación en el bootstrap.

Nueva dirección de investigación autorizada por el usuario: producto autónomo con
host principalmente Rust, PKHeX.Core C# conservado mediante Native AOT si supera
validación, Linux ARM64 candidato y ESP32-S3 dedicado a radio. Presupuesto objetivo
menor a $1,000 MXN incluyendo electrónica, alimentación y carcasa; no es costo
demostrado. Pi 5 y este fork permanecen como referencia funcional. No se inicia
otro repositorio ni se sustituye la UI actual durante la auditoría.

Se prioriza un Pokémon a la vez, pantalla pequeña y cruceta/botones; siete familias
de juegos, identificación de entrenador y modificaciones/devoluciones. No se acepta
catálogo pregenerado como reemplazo final de PKHeX. Se acepta trabajar con licencias
upstream y posible comercialización futura, sin decisión de distribuir todavía.
Actualizaciones automáticas deben pasar regresiones antes de promoción.

Auditoría, evidencia y plan: [spec 021](../specs/021-rust-handheld-feasibility.md).
PKHeX AOT compiló en Mac ARM64; 205 pruebas de servicio y 102 adicionales de
recibidos/banco pasaron, con integración real y casos simulados. Linux, RAM mínima,
BOM y consumo siguen pendientes. 128/256/512 MB son escenarios de prueba; 1 GB no
es un mínimo medido. S3 usa USB nativo en el firmware auditado; UART necesita trabajo
adicional. No prometer Switch 2 ni todos los roles por las pruebas de Mac.

Fecha de referencia: 2026-11-12. «Acordado» significa dirección del producto; no significa implementación o compatibilidad física probada.

## Hardware objetivo

| Elemento | Decisión | Validación pendiente |
|---|---|---|
| Computadora | **Raspberry Pi 5**, Linux de 64 bits | Despliegue y mediciones en dispositivo real |
| RAM | Sin capacidad definitiva | Comparar necesidades reales; 4 GB fue una estimación inicial, no mínimo documentado |
| Pantalla | **Waveshare 4.3inch DSI LCD (with case)** | Verificar revisión recibida, cable y montaje |
| Superficie de UI | **800 × 480 píxeles, horizontal**, IPS, táctil capacitivo | Escalado, legibilidad y foco en pantalla real |
| Interfaz de pantalla | MIPI DSI | Cable de pantalla compatible con conector de Pi 5; no asumir que está incluido |
| Radio | **Seeed Studio XIAO ESP32-C6**, conectado por USB/serial a la Pi | Firmware y sesión local de extremo a extremo |
| Controles | Teclado y **cruceta preferida**; táctil complementario | Modelo, conexión eléctrica y transporte de eventos |
| Carcasa | Integración portátil propia por definir | La carcasa comercial seleccionada está pensada para Pi 4B |
| Alimentación | Solución portátil pendiente | Batería, regulación, carga y autonomía medidas con todos los periféricos |

La publicación elegida identifica el modelo exacto, no una pantalla HDMI genérica:
[Mercado Libre](https://www.mercadolibre.com.mx/monitor-waveshare-43-touch-ips-para-raspberry-pi-4b/p/MLM2096907923).
Referencias: [ficha Waveshare](https://www.waveshare.com/product/raspberry-pi/4.3inch-dsi-lcd-with-case.htm), [instalación y Pi 5](https://www.waveshare.com/wiki/4.3inch_DSI_LCD).

El soporte documentado de la pantalla con Pi 5 no certifica el ajuste de la carcasa ni el contenido del paquete. La Pi se alimenta con corriente continua regulada por USB-C; no conectar una celda directamente ni inferir autonomía del valor nominal de una batería.

## Producto y prioridades

1. **Primera entrega:** abrir la app, generar, importar, validar y usar el banco local de Pokémon. Debe ser útil sin Switch ni ESP32 conectado.
2. **Siguiente entrega:** intercambios locales usando el núcleo y los protocolos de pokeldn, con la radio C6. Conservar el uso local de `prod.keys` por las rutas existentes.
3. **Opcional posterior:** raids locales; evaluar cada ruta y su carga antes de prometer soporte.

No se exige paridad con todos los features upstream. GTS, servicios por internet y automatización de botones de la Switch no son objetivos iniciales. Las funciones existentes de escritorio no se eliminan por ello.

La Pi ejecuta la app, PKHeX y la lógica de sesión. El ESP32-C6 aporta la radio LDN. La Switch ejecuta el juego. **No estamos construyendo un emulador completo de Switch.** El soporte de radio C6 no debe confundirse con soporte de firmware de mando; véanse [radio ESP32](../hardware_esp32.md) y [controladores](../hardware_pad.md).

## Interfaz y repositorio

Adaptar **la aplicación Python/Flet existente dentro del fork**, mediante un perfil portátil. No crear otro frontend independiente ni replicar generación, validación o protocolos. Mantener una experiencia normal de escritorio.

Diseñar para el espacio real de 800 × 480: una tarea principal por vista cuando sea necesario, formularios organizados, desplazamiento accesible, mensajes visibles y foco inequívoco. No reducir toda la interfaz mediante escalado para forzar que quepa.

Comenzar con teclado como simulación de cruceta: flechas, Enter y Escape. Respetar edición de campos, selección en listas y foco de diálogos. El mapeo eléctrico y los botones físicos definitivos siguen abiertos.

El mecanismo `POKELDN_PORTABLE=1` activa el asistente portátil implementado. `POKELDN_PORTABLE_DEMO=1` añade una demo visual explícita sin hardware. Ver [desarrollo](development.md) para comandos y límites del primer incremento.

## Incertidumbres que deben permanecer visibles

- No hay mediciones propias de RAM, tiempos, temperatura, consumo ni batería en Pi 5.
- No asegurar que 4 GB bastan ni que 8 GB garantizan todas las raids. Medir Python, cliente Flet, .NET y procesos de sesión juntos.
- Elegir juego y escenario para el primer intercambio real antes de esa etapa.
- Resolver ergonomía del selector de archivos y teclado en pantalla si se necesita.
- Desarrollo nativo en Mac y VM Linux ARM64 ayudan a probar UI/compatibilidad; no sustituyen validación de GPIO, pantalla, radio, potencia y rendimiento físico.
- El uso local necesita dependencias y recursos preparados previamente; auditar descargas de assets y actualizaciones antes de prometer funcionamiento completamente desconectado.

El arranque portátil entra directamente a la Pokédex cuando todas las comprobaciones están listas, también al abrir una nueva sesión web. La configuración permanece accesible desde el engranaje; si hay requisitos pendientes se muestra el diagnóstico, y una instalación en curso conserva su vista de progreso.

El inicio muestra una galería de una sola fila con scroll horizontal, avatares circulares y nombres debajo. Se reutilizan los grupos del catálogo estable desde Rojo Fuego/Verde Hoja hasta Escarlata/Púrpura; imágenes locales con Poké Ball de respaldo. La selección abre Intercambios / Equipo.

## Intercambios portátiles

El diseño aprobado y las modalidades futuras se conservan en [spec 005](../specs/005-portable-trades.md), junto con el wireframe interactivo. Equipo es el primer modo implementado: seis cajas, autoguardado, build y validación al confirmar cambios, primer error visible, envío bloqueado hasta tener todas las ofertas legales actuales. Perfil base intacto y perfiles adicionales por juego. Solo conexión local; anfitrión/unirse según catálogo. Durante sesión se bloquea edición, se muestran progreso confirmado, logs y cancelación con confirmación.

Para los modos de recepción se autoriza devolver el original intacto aunque sea ilegal; la excepción nunca permite enviar una copia editada ilegal ni ofertas ilegales de Equipo. Validador usa tarjeta de estado y modal de informe, sin scroll principal. Modificador abre el editor automáticamente al recibir, manteniendo acciones arriba.

### Editor y selectores de Equipo

- El mensaje de legalidad corresponde a la caja seleccionada: primer error de esa caja o estado válido. Los errores de otras cajas no sustituyen ese mensaje, pero sí bloquean el envío del equipo completo.
- Entrenador es un selector buscable con «Base de pokeLDN» como opción válida inicial. Especie y movimientos también permiten búsqueda y limpieza mediante X.
- La búsqueda es temporal: escribir o cerrar el menú no confirma otro valor. Solo seleccionar una opción o usar X cambia la selección. Limpiar entrenador restaura el perfil base; movimientos vuelven a Automático.
- Apodo permanece en Básico, vacío por defecto; límite de 10 caracteres para Gen III y 12 para los juegos Switch soportados. Variocolor permanece como switch.
- Cambiar caja reutiliza los controles y opciones ya calculadas. Solo los cambios de configuración pertinentes recalculan opciones; salir de un campo sin editar no vuelve a generar.
- Los candidatos de movimientos se filtran por configuración de caja. El filtro no garantiza legalidad conjunta ni exhaustividad de orígenes posibles: PKHeX sigue validando el resultado final. Conservar visibles los valores elegidos que queden fuera del filtro; no borrarlos automáticamente.
- Los desplegables deben dejar visible el campo de búsqueda y poder cerrarse sin elegir. El límite actual es 280 × 160 dentro de la pantalla 800 × 480.
- El salto automático al menú de juegos se aplica al arranque, incluso si otra sesión completa los checks. Abrir Ajustes manualmente no debe provocar un salto de vuelta por una notificación de estado.

### Identificar entrenador con devolución

Se añade «Devolver Pokémon original» al diálogo de identificación; inicialmente activado, puede desactivarse para usar la recepción única anterior. Reutiliza trade-back nativo: oferta inicial legal, recepción y segundo intercambio para devolver bytes intactos. La excepción de original ilegal se aplica aquí sin ampliar permisos de Equipo. La consola puede aplicar evolución por intercambio.

La pantalla muestra etapas, sprite/datos recibidos, entrenador identificado, logs y cancelación. Solo una segunda confirmación permite marcar el original devuelto. El perfil del primer intercambio no se reemplaza con el del segundo. Si la sesión se corta tras recibir, se advierte devolución pendiente; los archivos guardados por upstream se conservan, pero no existe reanudación automática ni reenvío genérico. Véase spec 007.

### Máximos en el formulario básico

Por petición del usuario, EVs máximos y amistad máxima están disponibles por Pokémon como checkboxes compactos en la fila de pestañas existente, sin nueva fila ni scroll. Activar reutiliza el reparto upstream según estadísticas base y límites del juego; no maximiza IVs. Desactivar devuelve esa opción a Automático (no recupera el valor previo). El estado se deriva de los valores guardados de cada caja, no es una regla persistente para futuras especies. Se bloquean durante sesiones; EVs espera metadatos. Ver spec 008.

### Preservación de decisiones y búsqueda (spec 009)

El usuario pide documentar cada decisión para evitar regresiones al incorporar nuevas instrucciones. AGENTS exige leer los contratos de UI y registrar acuerdos/pruebas. Se reafirma que el foco vacía la consulta sin alterar la elección del modelo. En Flet 1.0.5 se debe limpiar también el valor temporal del widget, conservando la elección en data/modelo; asignar text solamente no basta. Las comprobaciones Python deben complementarse con el cliente real.

### Modalidades de recepción activadas

El usuario autorizó continuar las seis modalidades descritas en spec 005. Implementación en spec 010: menú en cabecera, oferta inicial aleatoria legal, original separado de copia y devolución dentro de la misma sesión nativa. Nivel, Naturaleza y EVs devuelven automáticamente la copia si pasa legalidad; si falla, muestran el primer error y permiten devolver el original. Modificador abre automáticamente el editor y requiere elegir devolver copia legal u original intacto. Validador conserva el informe completo en logs/modal y devuelve original, incluso si es ilegal. Evolución devuelve original; la consola decide la evolución según requisitos.

La opción de máximos en Modificador vuelve al valor del original al desmarcar, porque allí no se genera otro Pokémon. En Equipo sigue volviendo a Automático. No sobrescribir entrenador ni origen al editar; algunos cambios explícitos ligados al PID pueden resultar imposibles legalmente. No reparar el formulario ni sustituir el original silenciosamente.

Se conserva un registro privado de originales y devoluciones pendientes. Al reiniciar/configurar otra sesión no se reenvían automáticamente: es necesario verificar destinatario y la recuperación automática sigue fuera de alcance. La exclusión de radio permanece activa aunque el formulario de Modificador esté habilitado.

### Identificación por Pokémon recibido (Espada/Escudo)
- La identificación portátil usa también `Service.owner` y `console_trainer.own`, igual que `Find mine` de escritorio. No depende exclusivamente de eventos `[trainer]`.
- Solo el primer recibido de la sesión confirmada puede aportar el perfil: sin huevo, handler original y versión del juego compatible. No se adopta el OT de un Pokémon ajeno ni el del segundo intercambio de devolución.
- El cierre espera la lectura final antes de declarar identificación fallida y liberar la sesión; resultados tardíos no cruzan `run_stamp`. Se conserva la prioridad del entrenador ya identificado por protocolo.

### Validación de recibidos y opciones de movimientos
Los modos que editan un recibido reutilizan `Team.load_moves(index, draft, owner, version)` con el borrador y entrenador capturados para la validación. Las pruebas de estos flujos deben ejecutar el cargador compartido real, sin reemplazarlo por un mock permisivo que oculte incompatibilidades de argumentos. Se conservan validación final y devolución exacta del original como excepción.

### Inspección del recibido para pruebas
Las vistas de un solo recibido incorporan comparación de los campos expuestos por PKHeX entre original y copia actual. La tarjeta resume cambios y nivel; un icono abre el detalle con diferencias resaltadas, sin desplazar el editor ni añadir scroll principal. Los resultados de una revisión anterior no se presentan como actuales. TID/SID se rotulan como 16 bits; los catálogos disponibles muestran nombre e ID. Esta comparación no garantiza identidad binaria ni observa cambios posteriores hechos por la consola.

El comparador prioriza identidad y procedencia sobre estadísticas. Incluye género/idioma del entrenador y datos de encuentro/huevo extraídos de PKHeX, sin habilitar su edición. Ausencia de fecha no se transforma en una fecha inventada.

### Monitor portátil de recursos (`?`)
Superposición opcional, fija abajo a la derecha, transparente a clics y sin foco propio. `?` alterna en todas las pantallas portátiles. Muestra RAM usada/total y porcentaje del sistema, RSS sumado de app+descendientes en MiB y porcentaje de RAM, CPU del sistema y de app+descendientes normalizada por CPU lógicas, y temperatura CPU cuando psutil expone sensor compatible. En web no incluye navegador. RSS puede contar memoria compartida varias veces; procesos breves entre muestras pueden no verse. Muestreo cada segundo solo visible/conectado; primera lectura CPU pendiente. No persistir preferencia.
Bandas orientativas de temperatura: <60 °C fresco, 60–74 templado, >=75 caliente; no son límites certificados de throttling. Sin sensor: N/D. Pi 5 pendiente de validación física. Se añade psutil 7.1.3 como dependencia multiplataforma.

### Área útil en escritorio macOS
La ventana nativa de Flet incluye ~32 píxeles de barra de título en el alto configurado. Se abre a 800 × 512 (mínimo igual) en macOS para conservar ~800 × 480 útiles, evitando que el estado de Equipo invada los movimientos. Web y Linux conservan su configuración previa; no se reduce el tamaño de los campos ni se agrega scroll al formulario básico.

### Leyendas Z-A en portátil
Se añade ZA después de Escarlata/Púrpura. Reutiliza generación/validación PA9 y herramientas locales host/join existentes. La devolución controlada adapta su oferta de 354 bytes, espera sin enviar la oferta previa y vincula el retorno a la sesión nativa; reconexiones no reutilizan originales.
Una diferencia comprobada de ZA son las marcas Plus Move: cambiar solo nivel puede dejar una copia ilegal. No reparar silenciosamente movimientos/marcas. Mostrar el informe, bloquear copia y permitir original intacto conforme al contrato existente. Prueba física del usuario pendiente. Véase spec 011.

ZA admite idioma 11 (español latinoamericano) en identificación y perfiles portátiles. Conservar ese valor y mostrar su nombre; no reemplazarlo por español 7 ni usar el catálogo antiguo de Settings para rechazarlo. Los demás juegos conservan sus restricciones. Causa y cobertura en spec 011.

### Código visual de Let’s Go
Configuración portátil usa exactamente tres dígitos ASCII, mostrando los tres Pokémon en orden y la leyenda del CODE_PICKER upstream: 0 Pikachu, 1 Eevee, 2 Bulbasaur, 3 Charmander, 4 Squirtle, 5 Pidgey, 6 Caterpie, 7 Rattata, 8 Jigglypuff, 9 Diglett. Se conservan ceros iniciales; inicial 000. Anfitrión convierte a `0,0,0` para el campo `linkcode` (antes el portátil no pasaba ese tipo al runner). Unirse conserva la búsqueda upstream sin filtro de código; se indica explícitamente en el diálogo. No se modifica el protocolo.

### Selección de juego y foco nativo
No desmontar la galería al seleccionar un juego mientras haya llamadas de foco/scroll pendientes: Flet 1.0.5 cierra la sesión ante respuestas de controles desmontados, dejando diálogos visibles sin callbacks. Selección y foco comparten coordinación asíncrona; no convertir de nuevo la selección en un callback síncrono que navegue inmediatamente. El arranque tampoco debe sobrescribir una navegación explícita durante los checks. Reproducción, corrección y verificación de Cancelar/Guardar en spec 012.

### Pulido de interfaz y Equipo secuencial (spec 013)
- Entrenador, datos y encontrar pasan a la cabecera, entre modalidad y conexión, en todas las modalidades. Recibidos comparte perfiles del Equipo del juego para la oferta de cortesía; estos nunca sustituyen al entrenador original recibido. Encontrar desde recibidos abre el flujo existente de identificación en Equipo, con confirmación antes del intercambio.
- El formulario Básico existe desde la caja vacía, sin Crear Pokémon. Solo elegir especie ocupa una caja e inicia validación; los demás campos se habilitan entonces. Entrar a una caja vacía desde Avanzado vuelve a Básico para poder elegir especie.
- Se habilitan las ocupadas y la primera vacía. Borrar una caja o quitar su especie desplaza las posteriores. Conserva resultados/cachés actuales y aumenta revisiones posicionales para rechazar respuestas anteriores. La validación final y el bloqueo de copias ilegales no cambian.
- Borradores antiguos con huecos se ordenan al cargar: ocupados en orden, después borradores sin especie conservando sus campos. No se borra el archivo original al leer ni se cambia schema 1; el siguiente guardado usa reemplazo atómico existente.
- Recibidos muestra tarjeta introductoria con icono, explicación y parámetros; actividad en franja fija con logs/cancelación. Identificación comparte la franja; Equipo usa una tarjeta de proceso y progreso por caja. Color y texto distinguen preparación, proceso iniciado y error. No hay evento universal de radio lista: nunca interpretar iniciar el proceso como consola conectada.
- Auditoría y 23 capturas de demostración en spec 013 y referencias/ui-polish. Recomendaciones adicionales separadas de lo implementado. No se hicieron intercambios físicos ni flasheo para esta revisión.

### Modales de entrenador y conexión (spec 014)
Altura ajustada al contenido, cabecera con icono, tarjetas y acción principal verde. Entrenador destaca nombre/sexo/idioma y dos IDs visibles, sin cambiar conversiones. Conexión agrupa papel/código en fila cuando no requiere versión; con versión agrupa papel/versión. Conserva leyenda, preview, validación LGPE y Cancelar sin guardar. Comparación permanece intacta. Capturas 24–27 en references/ui-polish; comprobación nativa con datos demo, sin intercambios.

### Papel con selector segmentado (spec 015)
Anfitrión/Unirse se elige directamente en botones mutuamente exclusivos, con selección verde. Solo mostrar papeles disponibles en tools; si solo existe Anfitrión, permanece seleccionado y no puede vaciarse. Mantener edición local hasta Guardar y descarte al Cancelar.

Revisión visual del selector de papel: igualar alturas visibles, bordes suaves y radios; eliminar franja inferior del segmento activo y contador redundante LGPE. Se conserva límite de tres caracteres. Verificación nativa y captura 29 en spec 015.

### Ícono y compilación portátil (2026-11-13)
Ícono PNG transparente generado con imagegen en gui/assets/portable, separado del upstream. La guía docs/portable-build.md es la referencia de preparación Mac/Pi con C6: compilar PKHeX y ejecutar GUI desde fuente. No confundir setup/preflight/deploy_pi del servidor Wi-Fi/Mystery Gift con requisitos de esta GUI. Estado inicial de spec 016: empaquetador autónomo portátil e integración de ícono macOS pendientes (actualizado por spec 020); no afirmar que exportar POKELDN_PORTABLE al compilar queda incrustado en una app. Compilar por plataforma/arquitectura; nunca copiar venv ni binarios Mac a Pi. Mac build comprobado; Pi y launcher Linux aún no ejecutados en hardware.

### Comando habitual de compilación (spec 017)
`./scripts/build_portable.sh` detecta SDK .NET 10 existente, configura entorno local y compila PKHeX Release con restauración por defecto. Independiente del cwd; no instala dependencias, no modifica SDK global ni empaqueta una .app. Guía portátil prioriza este comando sobre recordar exports.

### Arranque en un comando (spec 018)
`./scripts/run_portable.sh` abre modo nativo, limpia entorno web/demo y conserva `.local-preview/portable` como default para este checkout. Respeta POKELDN_DATA personalizado y puerto configurable; siempre loopback. No compila, instala ni detiene otras instancias. Detecta SDK local/instalación Pi y usa venv del fork.

El launcher admite `--build`: reutiliza build_portable.sh y abre únicamente si termina correctamente. Sin argumento mantiene arranque directo; no duplicar lógica del SDK ni continuar tras fallo de compilación.

### Exploración de hardware económico (2026-11-13)
El usuario recibió Pi 5 y aún no tiene alimentación/SD/teclado; propone estudiar interfaz más sencilla y placa menor. Es exploración, no sustitución aprobada de Flet/hardware. Benchmark piloto real en Mac: modelo Equipo+PKHeX seis cajas ~187–190 MiB RSS, UI nativa demo tres cajas sin sprites ~477 MiB (cliente Flet ~292 MiB). No inferir mínimo de RAM ni velocidad Pi de esos valores; OS, GPU y sesión física excluidos. Script reproducible y límites en docs/portable-benchmark.md / spec 019. Autonomía vs servidor local pendiente de respuesta. Mantener Pi5 como banco de pruebas ya adquirido; no comprar otra placa solo por precios base.

### Paquete Portable con identidad propia (spec 020)
`build_portable.sh --app` reutiliza `pack_app.py --portable`: bundle separado, nombre pokeLDN Portable, ícono PNG existente convertido a icns para bundle y viewer macOS, firma ad hoc local y perfil nativo integrado antes de importar configuración/rutas. No requiere exports ni copia datos personales. Respeta POKELDN_DATA explícito; default por usuario pokeldn-portable, separado del escritorio y del preview del checkout. Sin builds opcionales permite cliente Flet estándar (sin arrastre) y Unicorn wheel; escritorio conserva requisitos anteriores. No cambia el ícono de run_portable.sh desde fuente. Pi/equipo limpio y notarización pendientes; evidencia concreta en spec 020.

## Radio S3 en Pi (2026-11-15)

Se amplía el asistente portátil a ESP32-S3 además de C6, por la placa DevKitC-1
N16R8 del usuario. Se conserva USB nativo, instalación explícita y verificación
del chip/firmware. El bloqueo anterior era exclusivo del asistente; el núcleo
ya soporta S3. Spec 022. Intercambio físico y selector de archivos Flet en Pi
pendientes; no atribuir el cierre Flutter a la radio sin reproducción.

## Oferta de cortesía regional en todos los juegos (2026-11-15)

Tras bloqueos de devolución reportados con Flygon y Sharpedo en Rojo Fuego,
la identificación y las modalidades de recibido portátiles usarán Magikarp
generado legalmente para el juego/versión. Se aplica a las siete familias.
No habrá fallback a especies aleatorias nacionales. La oferta manual de Equipo
permanece intacta. No se alteran originales ni se recuperan devoluciones de forma
automática. Spec 023; pruebas físicas de ida/vuelta pendientes. Legalidad PKHeX
no demuestra requisitos de progreso de la partida.

## Identificación: regreso a Equipo (2026-11-15)

Tras identificación exitosa y cierre confirmado, volver automáticamente al editor
de Equipo mostrando nombre, ID y SID según formato del juego. Si se solicitó
devolución, esperar ambos intercambios. Error/cancelación mantiene el diagnóstico;
Volver a Equipo queda en fila fija y deshabilitado durante sesión. Conservar
advertencia de devolución pendiente al volver manualmente. Spec 024.
Por instrucción del usuario, cambios y validaciones locales; él publica y actualiza
la Pi. No editar por SSH ni desplegar automáticamente.

## Tareas de foco y desconexión portátil (2026-11-15)

Retener Futures de foco automático hasta completarlos y cancelarlos al
cerrar/desconectar; evitar el segundo foco de start después de go(home).
Conservar el lock que impide desmontar galería con scroll/foco en vuelo.
Spec 025 reproduce localmente el aviso de tarea destruida reportado en Pi.
No atribuirlo a build, fuente ni radio; confirmar por prueba física si resuelve
también la demora de arranque. Cambios locales sin despliegue SSH.

## Códigos iniciales de conexión (2026-11-16)
Los códigos requeridos usan ceros según longitud del catálogo: 000 para Let's Go,
00000000 para PLA/Z-A. Códigos opcionales o inexistentes no se fuerzan. Se conservan
valores elegidos y guardados no vacíos. Spec 031.

## Identidad compacta en cabeceras (2026-11-16)
Todas las modalidades comparten OT completo, ID/SID según formato del juego e
idioma abreviado, sin hashes en las opciones. Se conserva Base de pokeLDN y
búsqueda temporal que no cambia selección. Spec 030.

## Cierre nativo en Pi (2026-11-16)
Log posterior a pruebas funcionales muestra FlutterEngineRemoveView y accesos
GTK/FlBinaryMessenger después de destruir motor. No hay evidencia de fallo de
radio o PKHeX. Cierre idempotente compartido detiene monitor/foco y listeners
antes de destruir ventana; no asegura corregir bug interno del cliente Linux.
Spec 027, comparación física pendiente; no actualizar Flet a ciegas.

## Facility Entrenadores (2026-11-16)
Ajustes del fork Pi/Flet incorpora lista global filtrable/buscable de perfiles
por juego, con eliminación confirmada y JSON array individual/bulk. Se preservan
IDs originales de 16 bits, género, idioma y versión conocida; nombres exportados
seguros y carpeta por familia de juego. Reutiliza TeamStore y selectores.
No toca el repositorio económico. Spec 028.

## Facility Banco (2026-11-16)
Ajustes del fork Pi/Flet archiva originales de intercambios confirmados, separados
de borradores. JSON array con Base64 y SHA256 conserva los bytes completos; no
necesita ZIP. Editar prepara copia y enviar original verifica integridad/
legalidad sin aplicar transformaciones de oferta. Borrado confirmado no elimina
Received ni journals. Sin importación histórica automática: algunos adaptadores
escriben vistas previas antes de confirmar intercambio. Spec 029.

## Comprobación inicial visible (2026-11-16)
Setup ya ejecuta USB/PKHeX/esptool fuera del event loop. Se añade indicador
animado, etapa y aviso tras ocho segundos, sin liberar acceso serie mientras
sigue una operación. Listas locales y Modo local (motor listo) accesibles;
instalación/revisión/intercambios siguen bloqueados. Se conservan reintentos y
timeouts existentes; no se introduce cancelación insegura de threads. Spec 032.

## Código visible en Conexión (2026-11-16)
Mostrar rol y código en dos líneas dentro del botón existente de 105 × 40, sin
modificar altura de cabecera. Preservar ceros; Sin código para opcional vacío y
solo rol sin campo de código. Shared TeamView cubre todas las modalidades. Spec 033.

## Conexión sin label (2026-11-16)
Por solicitud del usuario, retirar label Conexión: rol y código identifican el
botón. Conservar 105 × 40 y alineación inferior con controles de cabecera;
tooltip explica configuración. Actualiza spec 033 mediante spec 034.

## Entrenador sin duplicados (2026-11-16)
Usuario autoriza retirar cabecera de IDs y botón Datos del entrenador. Mantener
selector con identidad completa, tooltip y Encontrar mi entrenador. Base de
pokeLDN conserva nombre/opción X y detalles en tooltip. No eliminar género ni
idioma persistidos aunque desaparezca el modal. Spec 035 actualiza spec 030.

## Separador visual de código (2026-11-16)
Más de cuatro dígitos se presentan con guion central (0000-0000, 000-000);
hasta cuatro sin guion. Código guardado/enviado intacto. Spec 036.

## Automático mezclado con movimientos manuales (2026-11-16)
En upstream options.moves es una lista exacta; vacíos no significan completar.
El portátil envía intención adicional auto_move_slots solo al generar con mezcla
de manuales y Automático. PKHeX completa con candidatos legales sin sustituir
manuales ni duplicarlos. Todo automático y listas explícitas mantienen contrato.
Recibidos/Banco siguen preservando el movimiento original de cada slot automático.
Si una especie tiene pocos movimientos legales, no se fuerzan cuatro; se compacta
solo si los huecos vuelven inválido el registro. Spec 037.

## Contraste de tema portátil (2026-11-16)
Reproducido por Computer Use con portable.main real: TextTheme personalizado sin
color dejaba filas/títulos blancos sobre fondos claros. Fijar INK en cada estilo
del tema, conservando colores explícitos. No modificar tema de escritorio.
Entrenadores, Banco y diálogo de identificación verificados en cliente nativo
a 800 × 480. Los previews futuros deben usar el tema/arranque real. Spec 038.

## Menús de filtros claros (2026-11-16)
Los filtros de Entrenadores/Banco heredaban MenuStyle oscuro del helper desktop.
Sobrescribir menú PAPER y texto INK con límites 280 × 160 solo en estas vistas.
Equipo ya declara menú claro. Spec 039.

Corrección de spec 039: MenuStyle no bastaba; el cliente Flet sobrescribe su
fondo con Dropdown.bgcolor. Fijados ambos en filtros. Computer Use confirmó
menús abiertos legibles y filtrado funcional en Entrenadores y Banco.

## Etiquetas de juegos en bibliotecas (2026-11-16)
Columnas/filtros usan nombres compactos en español (Rojo/Verde, Espada/Escudo,
etc.). GAME_LABELS separado de GAME_FOLDERS; no renombrar exports/IDs. Spec 040.

## Automático y Vacío en los tres editores (2026-11-16)
Equipo, Modificar y Banco → Editar comparten la distinción: Automático solicita
completar un movimiento compatible; Vacío conserva cero. Esto sustituye la
decisión de spec 037 de restaurar el movimiento original en slots automáticos
de Recibidos/Banco. Los ceros originales permanecen Vacío hasta cambiarlos.
El contrato interno aditivo move_slots usa null/0/ID; moves y auto_move_slots
legacy mantienen comportamiento. No compactar sobre un Vacío explícito ni
reparar estadísticas ajenas para conseguir legalidad (incluidos AVs de Let's Go).
La validación puede rechazar un conjunto vacío/ilegal. Fuente archivada e
identidad se conservan; edición sobre copia. Spec 041.

## Main y actualización portátil desde fuente (2026-11-16)
El usuario autoriza integrar feature/custom-device en main y usar exclusivamente
https://github.com/javleds/pokeldn.git, rama main, como fuente del self-update.
Integración local fast-forward; publicación/despliegue sigue a cargo del usuario.
El modo fuente ofrece icono a izquierda de Ajustes sólo para un descendiente
remoto, sin bloqueo de UI. Ajustes muestra fallos de consulta/cambios locales y
permite reintentar. No usar el updater de releases upstream para este fork.
Helper independiente con ventana/progreso/logs: requiere ventana y bloqueo listos
antes de cerrar principal. Preparar clone+venv+PKHeX separados; activar referencia
atómica tras smoke y ventana nueva lista. Mantener UI nueva sin radio/interacción
hasta commit de arranque. Si falla antes, detener proceso nuevo y reabrir anterior.
El launcher estable preserva ruta absoluta de datos, SDK y contexto gráfico.
No actualizar durante sesión/flash/check/escritura del banco. No reset/stash,
sudo, firmware automático ni borrado de versiones/datos. Retener releases fallidas
para diagnóstico; requieren espacio y limpieza manual. Spec 042.

## Resolución única de datos portátiles (2026-11-16)
Spec 043 sustituye los defaults distintos de launcher y paquete. Antes de importar
paths/settings, resolver: override POKELDN_DATA explícito (sin persistir), elección
por usuario, detección de carpeta estándar y legacy de la instalación estable.
Una poblada: conservar; ninguna: crear estándar; dos: selector nativo independiente.
Persistir sólo ruta absoluta, sin copiar/mover/fusionar datos. Error visible si la
preferencia es inválida o la carpeta guardada desaparece. Perfil desktop intacto.
Los workers --run/--module resuelven sin selector si no heredan ruta; ante conflicto
fallan explícitamente, nunca usan otro perfil. Overrides temporales no cambian la
preferencia global. El updater sigue heredando la carpeta efectiva de la sesión.
El launcher estable 042 sintetizaba POKELDN_DATA sin marcador de procedencia; no es
posible distinguirlo de un override real. Necesita actualizar manualmente una vez
el checkout original (shell y dispatcher), sin borrar pointer ni datos. No aplicar
heurísticas que cambien un override explícito por parecerse a la ruta antigua.

## Accesos directos (2026-11-16)
Spec 044: Linux nativo desde fuente ofrece Agregar al menú y Agregar al escritorio
a izquierda de Update/Ajustes. Archivos reales por usuario, root estable y DATA
actual explícitos, sin build al abrir. Resolver escritorio por XDG, sin sudo.
Respaldar entradas distintas antes de reemplazar. Si cambia la carpeta de datos,
registrar de nuevo: la ruta capturada tiene prioridad sobre la preferencia global.

## Pantalla completa portátil (2026-11-22)
El usuario reporta pérdida de espacio por panel del escritorio y título en la
pantalla DSI instalada, especialmente en Equipo. Se autoriza corregirlo en main:
Linux nativo inicia a pantalla completa; F11 alterna con ventana en el cliente
nativo, conservando Cerrar y Escape. Sin escalado ni cambios de formularios o modo
escritorio. Validación física del compositor/DSI pendiente. Spec 045.

## Navegación por swipe (2026-11-22)
El usuario autoriza implementar navegación táctil y un commit (spec 046).
La galería permite arrastre horizontal y la barra aparece durante scroll. La flecha
junto a X en selectores buscables abre un diálogo con búsqueda temporal y lista
vertical arrastrable; el campo conserva su desplegable nativo para edición directa
y teclado. Cancelar/Escape no confirma. No se cambian formatos ni generación.
Este acceso adicional no sustituye el menú nativo 280 × 160 ni cambia el significado
de X. No se modifica fullscreen ni se instala/parchea Squeekboard. En Pi se observó
que Flet mínimo abre teclado en ventana, pero no en fullscreen con labwc
0.20.2-1~bpo13+1 / Squeekboard 1.43.1-1+rpt1, incluso con Visible=true.
Validación nativa Mac a 800 × 480 y tests en spec 046; dedo físico en Pi pendiente.

## Alternancia táctil de pantalla completa (2026-11-22)
Botón nativo inmediatamente a izquierda de Ajustes, sin nueva fila, disponible en
las vistas portátiles incluso cuando Ajustes esté oculto. Comparte acción con F11,
icono/tooltip de entrar/salir y navegación de cabecera. Web lo oculta. Se conserva
el arranque Linux en fullscreen; no se persiste preferencia. Spec 047.

## Selectores dedicados completos (2026-11-22)
El usuario señala que los selectores siguen usando el desplegable nativo. Spec 048
sustituye el acceso adicional de 046: toda la superficie de nombre/flecha de los
selectores buscables abre TouchOptions, mediante TouchSelector. X sigue separado
y conserva Base/Automático/sin selección. La consulta vive únicamente en el diálogo,
se inicia vacía y no altera la selección confirmada al cancelar o refrescar.
El foco no abre automáticamente el diálogo. Selectores no buscables y escritorio
conservan sus controles. Pruebas y límites de validación en spec 048.

## Pantalla completa del actualizador (2026-11-23)
Spec 049 extiende 045/047 al helper independiente: Linux nativo inicia fullscreen;
botón en cabecera y F11 alternan durante progreso o resultado, sin interrumpir
el worker ni habilitar cierre prematuro. Icono/tooltip siguen eventos nativos.
No se persiste preferencia. El helper instalado debe incluir el cambio para verlo;
la actualización que lo instala todavía usa el helper anterior.

## Prueba opt-in de ventana sin bordes (2026-11-23)
Usuario confirmó en Pi/labwc que una prueba Flet maximizada sin bordes muestra
Squeekboard y ambos campos permanecen visibles, aunque el dock reserva altura.
Autoriza probarlo en app si el contenido se adapta. Spec 050 añade
POKELDN_PORTABLE_BORDERLESS=1 sólo para Linux nativo: maximizada sin bordes,
con botón/F11 conservados. El default sigue siendo fullscreen hasta validar Pi.
Canvas de al menos 480 px dentro de viewport desplazable cuando falta altura;
no encoger botones ni reconstruir formularios al cambiar tamaño. La adaptación
es mediante scroll de respaldo, no redistribución de campos. No cambiar dock
ni el helper de actualización. Validación real de Squeekboard en la app pendiente.

## Ventana sin bordes predeterminada (2026-11-23)
El usuario pide que el modo de spec 050 sea el default. Spec 051 sustituye su
opt-in: Linux portátil nativo arranca maximizado sin bordes, sin variable de
entorno. Se conserva viewport adaptable, botón/F11 y regreso a maximizado.
Este acuerdo sustituye el arranque fullscreen de 045 sólo para app principal;
actualizador conserva 049. Mac/Windows/web no cambian. La petición autoriza
adoptarlo, pero la validación de Squeekboard en formularios reales sigue pendiente.
