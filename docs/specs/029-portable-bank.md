# Banco portátil de originales recibidos

## Contexto
El banco existente conserva bytes mediante deposit/_keep y deduplica por SHA256.
Su edición y oferta normales pueden transformar registros; no sirven para
mantener el archivo original inmutable. El portátil necesita archivo de recibidos.

## Objetivo
Listar, buscar, exportar y eliminar copias exactas de Pokémon recibidos, con
metadatos compactos de juego, especie, apodo y entrenador.

## Alcance
Backend PortableBank con formato de archivo reutilizado de pokeldn.app.bank.
Incluye recepción confirmada, listado en Ajustes, edición de copia y envío original.

## Fuera de alcance
Recuperación automática de devoluciones pendientes, protocolo nuevo, base de
datos SQL, importación de saves, conversión HOME y funcionalidades del repo hermano.

## Comportamiento esperado
Depósito conserva bytes exactos y deduplica por hash. Consultas no modifican datos.
Exportación individual/bulk es siempre JSON array, incluyendo base64 original y
SHA256. Borrar del banco no borra Received ni journals. No escanear históricos
automáticamente: los archivos eliminados no reaparecen por un backfill oculto.
El archivo del banco no se consume por enviar ni se sobrescribe al editar.

## Decisiones técnicas
Reutilizar bank._keep, entries, find, data y remove con carpeta aislada
DATA/portable/bank. Supplemental metadata guardado junto al registro existente.
JSON array schema 1 basta para preservar identidad binaria: no hace falta ZIP.
Los bytes son autoridad; legalidad/metadatos se verifican antes de enviar.

## Componentes afectados
gui/portable_bank*.py, gui/portable_team.py, gui/portable_received.py,
gui/portable.py, pokeldn/pokemon.py y sus pruebas.

## Backend
PortableBank(root=None): deposit/get/data/list/export/delete/delete_all.
No convertir registros, regenerar Pokémon ni aplicar cambios al original.

## Frontend
Listado filtrable, exportación y confirmaciones en Ajustes; reutiliza el editor
y transporte con un controlador de una sola copia, sin modificar Equipo.

## Persistencia
Archivos nativos pk3/pb7/pk8/pb8/pa8/pk9/pa9 más JSON lateral compatible con bank.
Sin migración destructiva; carpeta nueva creada al primer depósito.
Metadatos con OT, raw TID/SID, género, idioma y versión original si conocida.
El export no incluye rutas privadas.

## API
Sin HTTP; contrato JSON tipo pokeldn-portable-pokemon, schema 1, game/format,
original_base64/sha256 y metadata. Individual y bulk comparten formato.

## Validaciones
Juego entre siete familias, tamaño nativo por juego, hash de archivo al exportar
y enviar, IDs seleccionados existentes. No confiar en metadata legal para envío.

## Permisos y seguridad
Sin SSH ni operaciones sobre hardware. UI confirma borrados y bloquea mutaciones
durante sesión; el backend opera solo en su root y resuelve IDs por listado.

## Casos límite
Duplicados, archivo alterado después del depósito, registro ausente, export vacío,
nombres Unicode, caracteres de ruta y otros formatos con tamaños incompatibles.

## Estrategia de pruebas
Identidad byte a byte, roundtrip base64/hash, dedup, filtros por juego/texto,
metadatos originales, export individual/bulk, eliminación y rechazo de manipulación.

## Estrategia de validación
pytest -q -W error focalizado y regresiones existentes de bank; diff --check.
Pruebas físicas de intercambio y selector de archivos en Pi pendientes.

## Estrategia de commits
Un commit de feature Banco con backend/UI/pruebas y documentación, creado por
agente principal. No commits automáticos del subagente.

## Archivos estimados a modificar
Nuevo backend y pruebas de esta spec; integración añade archivos de UI/controladores.

## Riesgos
PKHeX puede considerar legal un original que un juego bloquee por progreso.
Exactitud del archivo no implica que todos los protocolos envíen sin mutaciones.
No extender la excepción de ilegalidad de trade-back a originales arbitrarios.

## Preguntas abiertas
Revisión física de edición/envío en cada juego y selector de exportación Flet.

## Plan de implementación
1. Encapsular almacenamiento existente con bytes y metadata inmutables.
2. Agregar búsqueda, JSON array y borrado explícito sin backfill.
3. Probar integridad y límites; integrar recepción/UI/envío fuera del backend.

## Resultado del backend
PortableBank implementado sin modificar archivos existentes. 64 pruebas aprobadas
(backend portátil y banco upstream) con -W error; incluye formatos de siete juegos,
roundtrip base64 exacto, duplicados concurrentes, filtros, borrado e integridad.
La exportación no usa serialización PKHeX: codifica los bytes originales.
Sin importación JSON de banco (no solicitada explícitamente), scans históricos,
SSH. Las pruebas de backend no certifican intercambio físico.

El backend permite enrich(id, info, owner) después de archivar bytes con metadatos
provisionales. Verifica SHA256 antes de reemplazar solo metadatos de presentación;
ID, juego, fecha, ruta, hash y archivo original permanecen intactos. Esto permite
no retrasar la devolución por análisis PKHeX. 67 pruebas backend/bank aprobadas.

## Integración y evidencia local
Captura únicamente archivos de la sesión actual con ordinal confirmado por
[done], o bytes del gate nativo de devolución. Reintenta escritura tardía y
escanea al salir del proceso; no archiva vistas previas de SwSh. Guarda antes
del análisis de metadatos, que ocurre en segundo plano sin bloquear devolución.

Editar conserva el original y su entrenador, valida una copia y mantiene la
conexión del juego. Enviar original verifica hash y legalidad, evitando cambios
de entrenador/plugins; la codificación de transporte propia del juego continúa.
No extiende la excepción de devolución de una sesión viva a archivos arbitrarios.
Cerrar el editor invalida trabajo pendiente y descarta sus temporales.

Cliente Flet nativo local comprobado a 800 × 480 útiles: listado con cuatro
acciones, búsqueda/filtro y confirmación de borrado masivo con cancelación visible.
Fixtures temporales, sin datos personales ni radio. Editor/envío físico, diálogo
de exportación Linux y cierre del cliente en Pi requieren comprobación allí.

Revisión final: cierre espera scans pendientes de persistencia antes de destruir
ventana; no espera enriquecimiento opcional. Regresiones de cierre inmediato y
dispose durante carga/validación cubiertas. Suite focalizada final: 161 pruebas
aprobadas con -W error (Banco, captura, editor, cierre, Equipo, recibidos y
exact-offer/opciones normales). diff --check limpio.
