# Oferta de cortesía compatible con la Pokédex regional

## Contexto
El usuario observó devolución bloqueada en Rojo Fuego con Flygon y Sharpedo,
aunque la identificación funcionó. La selección actual acepta cualquier especie
legal del catálogo; legalidad no demuestra intercambiabilidad según progreso.
El usuario requiere protección en todos los juegos, no solo FR/LG.

## Objetivo
Evitar ofertas de cortesía fuera de la Pokédex regional en identificación y
modalidades de devolución de los siete juegos portátiles.

## Alcance
Oferta automática portátil: Magikarp (129), generado para el juego/versión y
entrenador elegidos, validado por PKHeX. Sin fallback aleatorio irrestricto.

## Fuera de alcance
Ofertas manuales de Equipo, selector aleatorio general de escritorio, desbloquear
progreso del juego, recuperar automáticamente devoluciones pendientes y protocolos.

## Comportamiento esperado
Identificación y todas las modalidades de recibido utilizan el mismo generador
de cortesía. Si no puede producir una oferta legal de la especie elegida, abortar
antes de abrir sesión. Conservar original y confirmaciones de devolución.
Magikarp no evoluciona por intercambio y pertenece a las Pokédex regionales de los
juegos portátiles. No afirmar que elimina todos los requisitos de progreso.

## Decisiones técnicas
Añadir command.courtesy_offer y sustituir solo la llamada discovery de Team;
Received hereda esa ruta. Reutilizar SERVICE.make y summary; conservar la
revalidación de bytes previa al lanzamiento.

## Componentes afectados
pokeldn/app/command.py, gui/portable_team.py y pruebas de cortesía/Team.

## Backend
Validar legal=True, species_id=129 y form_id=0. Generación normal sin opciones de huevo.
Probar bytes reales con el helper para cada juego/versión.

## Frontend
Sin cambios de layout ni formularios; mismos errores y estados de sesión.

## Persistencia
Sin migración ni cambios de originales, perfiles, claves o journal.

## API
Sin cambios HTTP ni del helper PKHeX.

## Validaciones
Generación legal y especie esperada; revalidación existente de los bytes de oferta.

## Permisos y seguridad
No iniciar sesiones ni devolver originales automáticamente. No tocar la sesión
activa de la Pi al preparar la corrección.

## Casos límite
Helper falla o devuelve ilegal/otra especie; todos los juegos y versiones;
identificación con y sin devolución; modalidades Received.

## Estrategia de pruebas
Pruebas unitarias del rechazo sin fallback y generación por juego/versión.
Integración PKHeX de los siete juegos y versiones pareadas. Regresiones de Team
y Received preservan identificación, legalidad y devolución exacta.

## Estrategia de validación
pytest -q -W error, diff --check. Prueba física en FR/LG y resto de juegos
pendiente del usuario; no sustituirla con legalidad PKHeX.

## Estrategia de commits
Un cambio cohesivo de política de cortesía, pruebas y documentación.
No publicar automáticamente.

## Archivos estimados a modificar
command.py, portable_team.py, test_portable_team.py, nuevo test_courtesy_offer.py,
decisions.md y esta spec.

## Riesgos
Legalidad no certifica todas las restricciones de progreso de una consola.
Cambiar la oferta de futuras sesiones no resuelve una devolución ya bloqueada.

## Preguntas abiertas
Confirmar en consola la devolución de Magikarp y el mensaje exacto del fallo anterior.

## Plan de implementación
1. Añadir generador conservador y conectar la ruta compartida portátil.
2. Probar rechazo y bytes reales para todos los juegos.
3. Preparar parche independiente y documentar límites antes de transferirlo.

## Resultado de validación
109 pruebas aprobadas (-W error): cortesía, Team e identificación/modalidades
Received. Incluye servicio PKHeX real para FR, LG, GP, GE, SW, SH, BD, SP, PLA,
SL, VL y ZA: bytes legales, especie 129, forma 0, sin objeto y no huevo.
No certifica la aceptación en consola ni los requisitos de progreso.
