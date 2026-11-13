# Pulido de UI y equipo secuencial

## Contexto y objetivo
Versión funcional aceptada por el usuario. Mejorar presentación y espacio útil a 800 × 480, sin modificar protocolos, legalidad ni conservación del original.

## Alcance y comportamiento esperado
- Cabecera compartida: volver/modalidad, selector buscable de entrenador + detalles + encontrar, conexión a la derecha. En recibidos, el perfil configura la oferta de cortesía; nunca sustituye al dueño del original.
- Equipo muestra Básico incluso vacío. No existe Crear Pokémon. Una caja cuenta como ocupada solamente al seleccionar especie; antes no genera ni valida.
- Cajas secuenciales: ocupadas y la primera vacía accesibles, posteriores bloqueadas. Borrar una caja o su especie compacta las siguientes. Conserva datos/estados válidos y protege frente a resultados asíncronos obsoletos.
- Capturar menú, configuración, Equipo, modalidades recibidas y estados relevantes con datos de demostración; separar capturas de estado simulado de pruebas físicas.
- Revisar jerarquía visual de vistas iniciales y proponer una señal de sesión claramente visible que diferencie preparación, proceso iniciado y errores; no confundir proceso iniciado con radio/consola conectada.

## Fuera de alcance
Rediseño del protocolo, firmware, nuevas modalidades, pruebas físicas automáticas, cambios de escritorio o reparación silenciosa de Pokémon.

## Decisiones técnicas / componentes / backend
Reutilizar Team, TeamView, ReceivedView, PortableView, selectores y sprites. Definir ocupación por especie. Compactar arrays y cachés por índice con revisiones monotónicas; validaciones pendientes no pueden escribir en el Pokémon desplazado. Mantener validación final antes de enviar.

## Frontend
Una fila superior compacta y controles con tooltips. Básico conserva campos y máximos sin scroll. Acciones de sesión siguen arriba. Reutilizar controles al cambiar caja. Auditar vistas con cliente Flet real.

## Persistencia
JSON privado schema 1, hasta seis borradores. Cargar ocupados en orden y después borradores sin especie, sin descartar sus campos; rellenar con None. Normalización en memoria, guardado mediante el reemplazo atómico existente. No migrar banco ni perfiles. No introducir base de datos.

## API, permisos y seguridad
Sin API nueva. No iniciar radio durante captura. Perfiles de ejemplo y sin rutas/claves personales en referencias. No modificar originales en modalidades recibidas.

## Validaciones y casos límite
Equipo vacío, seis ocupados, borrado primero/intermedio/último, quitar especie, borrador incompleto, guardado anterior con huecos, validación lenta durante borrado, sesión bloqueada, selección tras compactar y perfiles compartidos en recibidos. No habilitar intercambio por una validación antigua.

## Estrategia de pruebas y validación
Pruebas de modelo para secuencia/compactación/concurrencia y vistas para formulario vacío, bloqueo y cabecera. Suite portátil de Equipo/recibidos/UI. Capturas nativas 800 × 512 con ~800 × 480 útiles; revisión de superposición y foco. Registrar recomendaciones y límites observados.

## Estrategia de commits
Sin commits solicitados. Separación sugerida: modelo y regresiones; cabecera/formulario; auditoría visual y documentación.

## Archivos estimados
gui/portable_team.py, gui/portable_team_view.py, gui/portable_received_view.py, tests/test_portable_team.py, tests/test_portable_team_view.py, tests/test_portable_received_view.py, docs/ai/, esta spec y referencias.

## Riesgos y preguntas abiertas
Espacio limitado con nombres largos; usar ancho fijo y truncado, mantener búsqueda accesible. El runner no expone un evento uniforme de radio lista: no prometer búsqueda real solo por haber lanzado el proceso. Propuestas visuales adicionales se distinguen de cambios funcionales entregados.

## Plan de implementación
1. Ocupación/compactación en Team y pruebas de revisiones; conservar persistencia atómica.
2. Formulario vacío y cajas secuenciales en TeamView; conservar selectores/cache.
3. Cabecera de entrenador compartida con ReceivedView, sin alterar dueño original.
4. Capturas y recomendaciones de jerarquía/estado de sesión; verificar cliente real.
5. Actualizar contratos, decisiones y resultados de pruebas.

## Resultado implementado

Cabecera común y perfil de cortesía compartido, formulario vacío sin creación explícita, bloqueo secuencial, compactación con revisiones seguras, tarjetas introductorias de las seis modalidades, indicadores visibles de preparación/proceso/error e identificación. Las cajas bloqueadas tienen menor opacidad y candado. Acciones no disponibles se atenúan.

Los resultados legales de Pokémon desplazados se conservan sin regenerarlos. Se vuelven a validar los pendientes mediante el flujo existente. No hay edición de protocolos, datos originales ni política de legalidad.

## Evidencia y validación

Cliente nativo macOS, ventana 800 × 512 (~800 × 480 útiles), capturas Retina 1600 × 1024. Datos aislados y marca DEMO. 23 capturas originales, sin claves ni perfiles personales, en [galería](references/ui-polish/README.md). Firmware, espera y recepción son estados simulados: no prueban radio ni consola.

Verificado en UI: formulario vacío visible, caja posterior bloqueada; selección de Pikachu en la siguiente caja habilita la posterior; borrado de Charmander en caja 2 mueve Squirtle de caja 3 a caja 2 y conserva su estado legal. Menú de especie permite escribir con lista acotada. Formulario principal, EVs y Modificador recibido caben sin solapamientos; logs mantienen scroll propio.

Validación automatizada: 214 pruebas portátiles y de edición de recibidos cubiertas. Una prueba de retorno BDSP falló inicialmente por bloqueo del socket UDP local del sandbox; al repetirla con permiso de socket, pasó junto con las 26 pruebas de vista Equipo. La modificación final de retorno a Básico en caja vacía quedó incluida en esa última ejecución. `git diff --check` limpio.

## Auditoría: recomendaciones siguientes (no implementadas)

| Prioridad | Observación en captura | Recomendación |
|---|---|---|
| Alta | 06/17/20: sin sprites descargados aparecen signos de interrogación; galería 01 usa imágenes pixeladas ampliadas | Distribuir un paquete local de imágenes y tamaños coherentes. Mantener fallback gráfico neutro, sin depender de Internet para el aspecto final |
| Alta | 15: el proceso puede arrancar sin llegar a encontrar consola | Añadir eventos uniformes del runner: radio lista, buscando, consola encontrada, confirmación y error. Mostrar tiempo transcurrido y sugerencia de revisar código tras una espera prolongada; no usar un timeout como prueba de fallo |
| Media | 02: todos los checks están verdes pero el título dice Preparando, y Abrir mi Pokédex / Modo local compiten | Titular Configuración o Todo listo según contexto y dejar una acción principal; conservar acceso explícito al módulo |
| Media | 23: el modal de conexión ocupa casi toda la altura con pocos campos | Ajustar diálogos al contenido y limitar altura solo donde sea necesario; alinear campos y acciones. Comprobar también Let’s Go y perfiles largos |
| Media | 01/05/09: pie de teclado y marco tienen mucho peso visual | Reducir la jerarquía del pie (11–12 px, color más suave), sin quitar accesibilidad ni el marco Pokédex. Acortar textos repetidos |
| Media | 17: Validador muestra Copia aún no calculada aunque no debe crear una | Usar mensajes específicos para operaciones de solo retorno, sin referencia a copia. Evitar repetir especie como título y subtítulo si no hay apodo |
| Baja | 03: indicador largo de paso + DEMO puede recortarse | Reservar ancho del indicador o usar 1/2; mantener marca de demo explícita en capturas |

Orden sugerido: imágenes locales y señales reales del runner; después configuración/diálogos; al final tipografía y textos secundarios. No hacen falta más controles en la pantalla principal.
