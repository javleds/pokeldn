---
title: Decisiones del dispositivo portátil
nav_exclude: true
search_exclude: true
---
# Decisiones acordadas

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
