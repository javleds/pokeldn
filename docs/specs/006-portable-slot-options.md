# Opciones por caja y navegación rápida

## Contexto
Cambiar caja reconstruye catálogos y repite consultas; blur vuelve a generar borradores intactos.
## Objetivo
Reutilizar selectores y cachear opciones por configuración, sin relajar legalidad.
## Alcance
Equipo: formulario básico estable, catálogos compartidos, metadatos y candidatos de movimientos por caja; validación por revisión.
## Fuera de alcance
Cambios de protocolo, otros modos, demostrar legalidad de todas las combinaciones mediante un filtro.
## Comportamiento esperado
Cambiar caja restaura valores y filtros ya cargados. Solo cambios pertinentes invalidan opciones. Los valores elegidos que queden fuera del filtro se conservan visibles; la validación bloquea ofertas ilegales.
## Decisiones técnicas
Reutilizar Team, TeamView, pokemon.Service y PKHeX. Cachés en memoria acotadas a las seis cajas. PKHeX calcula candidatos de movimientos sobre un registro y su historia de aprendizaje; no generar un Pokémon por candidato. La lista orienta y no sustituye make/check final.
## Componentes afectados
Controller, vista, adaptador PKHeX, helper C# y pruebas.
## Backend
Consulta de candidatos basada en registro validado/generado; separar metadatos de especie/forma/versión/entrenador de la revisión completa. No repetir validación de una revisión terminada.
## Frontend
Reutilizar controles básicos y actualizar valores/opciones solo cuando difieran. Evitar callbacks con índice antiguo al cambiar caja. Mantener dimensiones 800 × 480 y búsqueda temporal.
## Persistencia
Sin cambio de formato; cachés no persistentes.
## API
Extensión aditiva del protocolo interno JSON del helper para candidatos de movimientos.
## Validaciones
Resultados obsoletos no pueden sobrescribir caja nueva; validar bytes antes del intercambio como hasta ahora.
## Permisos y seguridad
No probar intercambios físicos; no exponer datos de entrenador en logs.
## Casos límite
Caja vacía, error de generación, cambios rápidos, cambio de entrenador/versión/forma, valores fuera de filtro, borrador incompleto.
## Estrategia de pruebas
Contadores de llamadas, identidad de controles, invalidación selectiva, respuestas obsoletas, filtros distintos por caja, pruebas reales PKHeX.
## Estrategia de validación
pytest, compilación .NET, smoke local y revisión 800 × 480. Medir tiempos sin prometer rendimiento Pi.
## Estrategia de commits
Separar servicio, caché y vista; no hacer commit automáticamente.
## Archivos estimados a modificar
services/pkhex/Program.cs, pokeldn/pokemon.py, gui/portable_team.py, gui/portable_team_view.py, tests y docs.
## Riesgos
Un filtro según encuentro concreto puede omitir opciones de otro origen. Identificarlo como candidatos del registro; conservar validación de combinación y no descartar selecciones automáticamente.
## Preguntas abiertas
Ninguna bloqueante; comprobar API exacta de candidatos en la versión instalada.
## Plan de implementación
1. Inspeccionar API PKHeX y añadir candidatos; compilar y probar.
2. Cachear metadatos y validaciones por dependencia/revisión; probar llamadas e invalidaciones.
3. Reutilizar controles básicos y filtrar por caja; probar navegación y callbacks.
4. Medir con servicio real, verificar UI y registrar límites.

## Resultado y límites comprobados
Corrección de desplegables: el helper de escritorio retiraba la altura máxima cuando la lista inicial era corta; al poblarla después, el menú ocupaba toda la pantalla. Los selectores portátiles fijan el límite de 280 × 160 después del helper y usan un ancho preferido finito para evitar que Flutter expanda también el menú. Verificado a 800 × 480: escritura, filtrado y cierre al pulsar fuera sin seleccionar. Referencia: `references/implemented-dropdown-bounded-800x480.jpg`.

Implementado move_options con LearnPossible.Get sobre una referencia generada sin movimientos explícitos. El filtro depende de especie, forma, nivel, versión, entrenador y opciones de origen; apodo y selección de movimientos reutilizan candidatos. No evalúa la compatibilidad conjunta de todos los movimientos ni enumera todos los orígenes alternativos: make/check final continúa siendo obligatorio. Un fallo al obtener candidatos no sustituye la decisión del validador final. Selecciones fuera de lista se conservan visibles.

Metadatos se cachean por especie/forma/versión/entrenador; resultados tardíos no reemplazan revisiones nuevas. Formulario básico mantiene sus controles y cambia valores/opciones; EV/IV y avanzado conservan vistas por caja y configuración. Blur sin edición no valida.

Validación: compilación Release .NET sin errores/advertencias; prueba real de candidatos en frlg/lgpe/swsh/bdsp/pla/sv; Squirtle FR nivel 5 excluye Burbuja, nivel 10 la incluye y excluye Lanzallamas. 100 cambios de caja en Python (sin render navegador) = 108,5 ms, controles idénticos y cero tareas PKHeX por navegación. Revisión en navegador a 800 × 480; captura en references/implemented-team-filtered-800x480.jpg. No se realizaron intercambios físicos ni mediciones en Pi.
