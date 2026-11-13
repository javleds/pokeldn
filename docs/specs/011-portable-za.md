# Integración portátil de Leyendas Z-A

## Objetivo y alcance
Añadir ZA al final de la galería, con Equipo, identificación y modalidades de recibido. Reutilizar generación/validación PA9 y herramientas locales existentes, sin habilitar internet.

## Diferencias observadas
ZA transmite una oferta de 354 bytes con cabecera y marca, mientras PKHeX trabaja con PA9. `pokemon.entity_bytes/offer_bytes` ya convierten ese formato. El anfitrión usa TradeBack compartido; el joiner debe esperar una respuesta del ReturnGate sin emitir la oferta anterior y mantener ACK/retransmisiones. El gate necesita vincularse a la sesión y rechazar reconexiones.

## Plan
1. Añadir nombre a galería y pruebas de catálogo.
2. Integrar Rounds.controlled, espera/reanudación de ofertas y vinculación de sesión en ZA.
3. Habilitar ZA en el gate solo junto a su adaptador; conservar validación final y original exacto.
4. Ejecutar pruebas ZA host/join, gate, controlador y PKHeX con formato ZA. Probar espera antes de devolución y rechazo de cambio de sesión.
5. Actualizar docs y abrir la app sin iniciar radio.

## Invariantes y límites
Original inmutable, copia legal antes de enviarse, sin fresh PID al devolver, dos confirmaciones y exclusión de radio. El modo Evolución devuelve el original y la consola decide el resultado. Prueba física ZA pendiente; las simulaciones no certifican compatibilidad con una versión de juego instalada.

## Resultado y diferencia de legalidad
Implementados galería, soporte de gate host/join, espera de respuesta del editor y validación de PA9 antes de reencapsular a 354 bytes. Las simulaciones de host y join cubren devolución exacta tras cinco segundos de espera; el joiner rechaza cambio de identificador de sesión. Se prueba una copia editada contra PKHeX real y la conservación de identidad.
El caso de Nivel con Pikachu detectó `Plus Move flag for Spark must be set` al subir a 100: el modo conserva ese error y no cambia movimientos/marcas para corregirlo. Se prueba bloqueo de copia y devolución del original. Las otras modalidades se prueban también con registros ZA reales.

Validación: 188 pruebas aprobadas del conjunto portátil/ZA/retorno (3 casos largos excluidos de esta última repetición); la regresión BDSP excluida pasó por separado con sockets locales. La ejecución amplia previa aprobó 183 casos, incluidos los restantes protocolos, y falló únicamente por la restricción de sockets de BDSP, resuelta al repetir con permiso. Compilación Python y diff-check correctos. No se usó radio ni se enviaron Pokémon durante estas pruebas.

Comprobación visual: galería desplazada hasta ZA y apertura de Equipo en cliente nativo macOS, con entrenador Base de pokeLDN y seis cajas. Referencia: `references/implemented-za-native.png`. Fue necesario cerrar y reabrir una instancia Flet que quedó reconectando; la instancia limpia abrió correctamente. No se inició un intercambio físico.

## Identificación con español latinoamericano
Causa confirmada: el evento de sesión ZA tiene `language=11` (español latinoamericano, documentado en `docs/za.md`). Equipo portátil recibía el evento pero rechazaba el perfil al persistir porque validaba solo los idiomas 1–10 admitidos por Settings. Settings/Find mine toma nombre e IDs aunque no admita el idioma; no equivale a conservarlo.
Se admite 11 exclusivamente en perfiles ZA y se muestra su nombre en el resumen de entrenador. No se convierte a 7 ni se amplía el catálogo de idiomas de otros juegos. Pruebas: evento, guardado/recarga, rechazo de 12 y de 11 en SV, y generación legal con PKHeX conservando idioma 11 e IDs originales.
