# Modalidades de recepción, edición y devolución

## Contexto
Equipo e identificación funcionan como base. El usuario autoriza implementar Evolución, Nivel, Naturaleza, EVs, Modificador y Validador, según spec 005, conservando los contratos de UI.
## Objetivo
Recibir un original, conservarlo, editar exclusivamente una copia cuando corresponda y devolver con confirmación de protocolo.
## Alcance
Selector de modalidades; configuración por modo; oferta inicial legal; tarjeta del recibido; Modificador abre editor automáticamente; informe completo en modal; logs/cancelación/retorno arriba. Infraestructura de devolución controlada no bloqueante donde el protocolo lo permita.
## Fuera de alcance
Raids, Mystery Gift, online, evolución artificial, modificación de entrenador original, envío de una copia ilegal.
## Comportamiento esperado
Evolución y Validador devuelven original intacto. Nivel 1–100, Naturaleza y EVs modifican una copia y validan; si falla, mostrar error y permitir devolver original. Modificador permite editar tras recibir y devolver solo copia legal o original intacto. Valores erróneos permanecen en formulario. Validador conserva todos los mensajes y tarjeta legal/ilegal sin scroll principal. Nunca se infiere éxito del código de salida.
## Decisiones técnicas
Reutilizar Team, runner, PKHeX, sprites y componentes de selección. Ampliar servicio con edición del registro existente, no Make que reconstruiría identidad. Devolución controlada debe dejar vivo heartbeat; no bloquear Rounds.done/current esperando UI. Cada adaptador nativo necesita respetar la espera antes de publicar el segundo ofrecimiento. Aislar intercambio mediante directorio/token; resultados obsoletos no cruzan sesiones.
## Componentes afectados
Controlador/vista portátil, helper PKHeX, protocolo interno Python, gate de devolución y adaptadores de juegos.
## Backend
Editar copia con allowlist de campos y validación final; original bytes separados. Gate publica recepción y espera selección de original/copia; volver a validar copia en el límite de transporte. No cambiar allow_illegal general. Conservar identidad y destinatario de la sesión activa.
## Frontend
800 × 480, componentes reutilizados, búsqueda temporal intacta, campos específicos antes de iniciar; recibo y edición automáticamente visibles. Acciones fijas arriba; modal de informe. No activar interacciones incompletas ni etiquetarlas como soportadas.
## Persistencia
Registro privado por sesión con original y estado de devolución; escritura atómica, sin migración de borradores Equipo. Conservar originales tras interrupción. No reenviar automáticamente después de reiniciar sin verificar destinatario; mostrar devolución pendiente y no perder datos.
## API
Comando interno de edición y mensajes locales de devolución; sin servicio público nuevo.
## Validaciones
Campos y límites, revisión del editor, hash del original, sesión y destinatario vinculados, legalidad de copia y confirmación de segunda ronda. Excepción legal solo original intacto del intercambio actual.
## Permisos y seguridad
Sin pruebas físicas automáticas. Mantener exclusión serial, paths privados, logs redactados. Datos de disco no pueden seleccionar archivos arbitrarios ni eludir validación.
## Casos límite
Original ilegal, edición imposible, respuesta tardía, cancelación mientras se edita, desconexión antes de devolver, archivo corrupto, error de PKHeX, cambio de juego/rol, formatos nativos diferentes.
## Estrategia de pruebas
Ediciones que preservan identidad, copia ilegal bloqueada/original permitido, gate no bloqueante, callbacks obsoletos, aislamiento por sesión, estados UI y regresiones Equipo. Pruebas simuladas de protocolos donde existan.
## Estrategia de validación
Compilar helper, pytest enfocado e integración, fixture UI 800 × 480 sin radio; documentar límites físicos.
## Estrategia de commits
Servicio/edición; transporte y tests; controlador/UI; documentación. No commits automáticos.
## Archivos estimados a modificar
services/pkhex/Program.cs, pokeldn/pokemon.py, gui/portable_team*.py, nuevos módulos de devolución y tests; adaptadores nativos enumerados durante inspección.
## Riesgos
Los hosts Switch admiten ofrecimiento pendiente; joiners y FRLG capturan inmediatamente el siguiente registro y requieren adaptación específica. No introducir esperas bloqueantes para aparentar paridad. Recuperación persistida no equivale a devolución automática segura.
## Preguntas abiertas
Cerrar el diseño de adaptadores join/FRLG antes de activarlos; comprobar todos los campos de edición soportados por PKHeX actual.
## Plan de implementación
1. Extender edición PKHeX preservando registro y cubrir identidad/legalidad.
2. Añadir gate no bloqueante, almacenamiento y adaptadores nativos con tests de espera/retorno.
3. Integrar controlador y modalidades/configuración/editor; conservar Equipo.
4. Verificar invariantes, UI y documentación; exponer solo combinaciones comprobadas por tests, indicar prueba física pendiente.

## Implementación del controlador y UI

`ReceivedTeam` extiende la preparación de oferta/runner de Equipo, pero usa borrador de recibido separado y no escribe las seis cajas ni perfiles del equipo. `active` conserva la exclusión de radio durante toda la sesión; `busy` bloquea edición excepto en la pausa de revisión/Modificador. Reabrir una sesión web restaura la vista activa correspondiente.

`edit_received` trabaja sobre el registro recibido y devuelve legalidad, snapshot numérico editable e identidad. Se envían únicamente los campos cambiados; no se usa Make ni se cambia entrenador. Nivel puede disminuir si el resultado pasa legalidad. Naturaleza en formatos modernos usa naturaleza de estadísticas; cambios de shiny o naturaleza/sexo ligados al PID en Gen III pueden requerir cambiar PID explícitamente, y la legalidad decide si son posibles.

La copia se valida por revisión; cambios posteriores invalidan su envío. El envío comprueba otra vez los bytes y la sesión tras cada espera. Original usa los bytes conservados, nunca `data` de un informe PKHeX. Si no puede leerse el original, Evolución/Validador conservan el error en el informe y permiten su devolución intacta; no se inventa un resultado de legalidad.

El selector de modalidades está en la cabecera. Modificador abre Básico automáticamente al recibir; mantiene EV/IV y Avanzado, los checkboxes de máximos, original/copia/logs/cancelar arriba. Validador usa tarjeta neutra/verde/roja e informe modal completo. Después de terminar se puede «Configurar nuevo intercambio» sin perder los avisos de devolución pendiente.

## Registro de recuperación

Directorio privado por sesión `POKELDN_DATA/portable/returns/<stamp>/`: original.bin inmutable para el editor, request.json, journal.json y archivos de respuesta controlados. journal schema1 registra juego/modalidad/rol/versión/hash/recepción/devolución/fase; escrituras atómicas y privadas. No hay migración de borradores ni borrado automático. El arranque detecta originales pendientes incluso si se interrumpió antes de actualizar el journal. Una alerta no es reanudación: no reenviar en una nueva conexión sin diseñar verificación del destinatario.

## Verificación de UI y servicio

Helper Release compilado sin advertencias ni errores. 362 pruebas de servicio, controlador, vistas y configuración aprobadas, incluidas las seis modalidades sobre un registro PKHeX real y lectura de formatos nativos de los seis juegos. Fixtures visuales sin radio revisados a 800 × 480 para Modificador, EVs, Validador, informe y menú. Las pruebas de protocolo se registran al finalizar su suite; ninguna prueba visual o simulada acredita un intercambio físico ni rendimiento Pi.

## Resultado del transporte

Habilitados los seis juegos (frlg/lgpe/swsh/bdsp/pla/sv) como host y join. Cada adaptador retrasa la siguiente oferta mientras mantiene servicio de red. Directorio de sesión exclusivo y vínculos con identidad/época del participante evitan reutilizar una devolución en otra sesión; cambios de participante abortan en lugar de reenvío.

Pruebas del transporte: 41 aprobadas en suite amplia de trade-back/gate; 92 aprobadas y 4 omitidas en regresiones de anfitrión; verificaciones posteriores de guards 77 aprobadas, 4 omitidas y 2 excluidas en esa selección; simulaciones SWSH/BDSP con pausa de cinco segundos 2 aprobadas; FRLG completo con radio simulada con pérdida/reordenamiento 1 aprobada (ambas confirmaciones y salida limpia). Los conteos corresponden a selecciones superpuestas, no sumarlos como pruebas únicas. Auditoría independiente de aislamiento/lifecycle sin bloqueadores restantes observados. No se realizaron intercambios físicos ni flasheos.

## Corrección: opciones de movimientos al validar una copia
Nivel, Naturaleza, EVs y Modificador llamaban a `Team.load_moves` sin los argumentos requeridos, provocando un TypeError y bloqueando una copia legal. Se pasa el borrador normalizado, una copia del entrenador original y la versión, siguiendo el contrato de Equipo.

La fixture de pruebas deja de sustituir `load_moves`: se ejecuta la implementación compartida, incluso en los seis casos con registros reales de PKHeX. Antes de la corrección fallaban cinco pruebas; con ella se verifican devolución automática de las modificaciones legales y edición manual sin reconstruir al entrenador. No cambia la excepción de devolución del original intacto.

Resultado de esta corrección: 80 pruebas aprobadas de controlador recibido, vista recibida y Equipo, con warnings tratados como errores. Prueba física pendiente del usuario.

## Comparación de datos para pruebas
Objetivo: observar el original y la copia calculada en los modos de un solo recibido, sin modificar el protocolo ni añadir scroll a la pantalla principal.
Plan: reutilizar `received_info.editable/identity` como original y `results[0]` como resultado, solo si corresponde a la revisión actual. Añadir resumen de diferencias a la tarjeta e icono de comparación disponible también durante edición/retorno. Modal con columnas Campo/Original/Copia, diferencias destacadas, scroll interno y valores desconocidos explícitos. Incluir todos los campos expuestos por el servicio; no afirmar igualdad binaria ni confirmar cambios realizados posteriormente por la consola. Probar ausencia de copia, revisión obsoleta, cambio exclusivo de nivel y conservación de identidad; inspeccionar a 800 × 480 con fixture sin radio.

Implementado el resumen y modal de comparación. 44 pruebas de controlador/vista aprobadas, incluyendo copia obsoleta y cambio exclusivo de nivel. Modal inspeccionado a 800 × 480 con fixture sin radio; referencia `references/implemented-received-comparison-demo-800x480.jpg`. Los detalles usan scroll interno para preservar espacio de edición y acciones.

### Identidad y procedencia al inicio del comparador
Se prioriza la sección de identidad (OT, TID/SID de 16 bits, PID, EC, tracker y encuentro) antes de estadísticas. Se amplía la lectura de PKHeX con género del entrenador, idioma, fecha de encuentro, lugar/fecha de huevo y banderas de huevo. Son datos de lectura, no nuevos campos editables. Fechas ausentes se muestran como no disponibles; IDs de catálogos permanecen explícitos. La igualdad compara campos extraídos, no certifica captura legítima ni unicidad global.
Verificación de extracción ampliada: compilación Release sin warnings/errores y 39 pruebas aprobadas de edición de recibidos y comparador, incluyendo los seis formatos de juego. No se realizaron intercambios físicos.

## Indicador de recursos portátil
Plan: módulo de medición con psutil, suma RSS y tiempos CPU del proceso Python y descendientes; CPU normalizada por CPUs lógicas, intervalo real monotónico. Superposición fija inferior derecha, transparente a puntero y sin controles enfocables. `?` alterna antes de delegar navegación de Equipo. Muestreo cada segundo solamente visible, cancelar al ocultar/desconectar y reanudar al reconectar. Mostrar lectura no disponible ante error; no detener operaciones de intercambio. Pruebas de diferencias de CPU y árbol cambiante; verificar toggle y clics a 800 × 480. En web excluye navegador; RSS sumado puede contar memoria compartida más de una vez. Sin persistencia de preferencia.

Implementado monitor ampliado con sistema y app: RAM usada/total, porcentajes, CPU normalizada, núcleos lógicos y temperatura. Verificados `?` para mostrar/ocultar y clic sobre botón Revisar a través del overlay en cliente Flet a 800 × 480. Pruebas de cálculo, lifecycle y bandas incluidas. En macOS de prueba el sensor informa N/D; validación física Pi 5 pendiente. Captura: `references/implemented-resources-demo-800x480.jpg`.
