# Modales portátiles: entrenador y conexión

## Contexto
Las columnas de ambos diálogos expanden su altura y dejan espacio vacío. Comparación es la referencia aprobada: datos alineados y acciones accesibles.
## Objetivo
Mejorar jerarquía y distribución en 800 × 480.
## Alcance
Ficha de entrenador y configuración local compartidas por Equipo y recibidos.
## Fuera de alcance
Comparación, protocolos, legalidad, nuevos campos y rediseño de otras modales.
## Comportamiento esperado
Ficha con identidad destacada, sexo/idioma e IDs alineados. Conexión con papel/versión agrupados, código y ayuda local; Guardar primario y Cancelar secundario. Altura ajustada al contenido. Conservar errores y traducción LGPE.
## Decisiones técnicas
Reutilizar AlertDialog, TeamView.dropdown, labeled, paleta PAPER/INK/GREEN y callbacks actuales. Ampliar _dialog con opciones de ancho/icono únicamente para estas vistas; columnas tight. No cambiar comparación.
## Componentes afectados
TeamView; ReceivedView hereda ambas vistas.
## Backend
Sin cambios.
## Frontend
Cabecera con icono, tarjetas de fondo blanco y bordes suaves, acciones diferenciadas. Conexión LGPE conserva leyenda y preview.
## Persistencia
Sin cambios.
## API
Sin cambios.
## Validaciones
Conservar configure/validate_all y errores; Cancelar no escribe.
## Permisos y seguridad
No iniciar intercambios ni tocar placa durante revisión; capturas con perfiles demo.
## Casos límite
Nombre largo, español latinoamericano, juego con versión y sin código, LGPE tres dígitos y error visible.
## Estrategia de pruebas
Suites existentes de vistas y modelos; cambio visual reversible no requiere tests de estructura.
## Estrategia de validación
Cliente nativo 800 × 480: abrir/cerrar, campos visibles, cancelar, LGPE y error. Capturas en references/ui-polish.
## Estrategia de commits
Un cambio cohesivo de UI y documentación; no commit automático.
## Archivos estimados a modificar
 gui/portable_team_view.py; docs/ai/decisions.md; docs/ai/ui-contracts.md; esta spec y capturas.
## Riesgos
Altura de contador/error de TextField y menús Flutter. Revisar cliente real.
## Preguntas abiertas
Ninguna bloqueante.
## Plan de implementación
1. Registrar spec y revisar callbacks compartidos.
2. Ajustar presentación de _trainer_info y _connection, sin alterar datos ni guardado.
3. Ejecutar suites de vistas y revisar ambas modales en cliente; guardar evidencia y decisiones.

## Resultado y evidencia
Implementado. Papel/código comparten fila si no hay versión; en los demás casos papel/versión comparten fila. Altura intrínseca, ficha de identidad y dos IDs alineados. Comparador intacto.

47 pruebas de TeamView/ReceivedView aprobadas (`pytest ... -q -W error`). Inspección nativa macOS 800 × 480 útiles con demo: ficha base, cierre, conexión SV, LGPE con preview y error de dos dígitos, Cancelar y Guardar. Sin hardware ni cambios de protocolo. Variante FRLG y nombres muy largos no inspeccionados visualmente en esta pasada.

Capturas: [entrenador](references/ui-polish/24-modal-entrenador.png), [conexión](references/ui-polish/25-modal-conexion.png), [LGPE](references/ui-polish/26-modal-conexion-lgpe.png), [error](references/ui-polish/27-modal-conexion-error.png).
