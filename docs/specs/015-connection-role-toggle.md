# Selector directo de papel

## Contexto
Continuación del pulido de modales (014): dos papeles no necesitan desplegable.
## Objetivo
Elegir Anfitrión/Unirse con un selector segmentado visible.
## Alcance
Conexión de Equipo y modalidades heredadas.
## Fuera de alcance
Protocolos, código, versiones y comparación.
## Comportamiento esperado
Solo segmentos soportados por tools; exactamente uno seleccionado, nunca selección vacía. Juego sin Unirse muestra Anfitrión seleccionado. Edición local hasta Guardar; Cancelar no persiste.
## Decisiones técnicas
Reutilizar Flet SegmentedButton 1.0.5 y callbacks actuales de _connection. Colores verde seleccionado y blanco para el resto; misma altura de 40.
## Componentes afectados
TeamView._connection, heredado por ReceivedView.
## Backend
Sin cambios.
## Frontend
Sustituir dropdown por SegmentedButton.
## Persistencia
Sin cambios de esquema ni reglas.
## API
Sin cambios.
## Validaciones
configure mantiene comprobación de papel disponible.
## Permisos y seguridad
No iniciar sesiones durante revisión.
## Casos límite
Un solo papel; reabrir con Unirse guardado; cancelar cambio.
## Estrategia de pruebas
Prueba de guardar selección y cancelar sin modificar; suites existentes de vistas.
## Estrategia de validación
Inspección nativa 800 × 480 y pruebas Python.
## Estrategia de commits
Cambio cohesivo sin commit automático.
## Archivos estimados a modificar
portable_team_view.py, test_portable_team_view.py y docs/ai.
## Riesgos
Etiquetas deben caber en media fila de modal.
## Preguntas abiertas
Ninguna.
## Plan de implementación
1. Sustituir selector usando herramientas soportadas como fuente.
2. Comprobar guardado y cancelación mediante tests.
3. Revisar tamaño real, guardar captura y decisión.

## Resultado
Implementado; 49 pruebas de vistas aprobadas. Verificación nativa a 800 × 480 en LGPE: cambio visual a Unirse y Cancelar conserva Anfitrión. Caso de papel único cubierto por test, no comprobado en cliente en esta pasada. No se iniciaron intercambios. [Captura](references/ui-polish/28-selector-papel.png).

## Corrección visual posterior
Revisión del usuario: altura y relleno discordantes. Observado en cliente: segmento seleccionado pinta menos alto que su contorno y TextField usa 48 px más contador frente a 40 del selector. Plan: densidad estándar explícita del segmentado; código denso 40 px con contador oculto (conserva max_length), bordes grises/foco cian y texto 16. Validar cliente y actualizar captura; sin cambiar selección ni guardado.

Corrección comprobada en cliente: densidad STANDARD elimina franja inferior del segmentado. Código con texto 16/padding vertical 12, altura total 48 y contador oculto produce borde visible de 40 px, alineado arriba y abajo con el selector. Bordes grises y foco cian; sin contador 3/3 redundante. [Resultado visual](references/ui-polish/29-conexion-alturas-alineadas.png). 49 tests de vistas aprobados tras ajuste. App normal abierta en la modal para revisión, sin guardar ni iniciar intercambio.
