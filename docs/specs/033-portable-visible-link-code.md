# Código visible en Conexión

## Contexto
La cabecera reserva 105 × 40 para el botón de conexión y solo muestra el rol.
## Objetivo
Mostrar código actual sin cambiar anchura, altura ni filas de la cabecera.
## Alcance
Contenido compacto del botón compartido por Equipo, recibidos y Banco.
## Fuera de alcance
Cambiar códigos, protocolos o diálogo de conexión.
## Comportamiento esperado
Rol y código en dos líneas dentro del botón existente; ceros preservados.
Sin código para campos vacíos admitidos; solo rol si el juego no usa código.
Tooltip incluye rol y código completo. Visible también durante sesión bloqueada.
## Decisiones técnicas
Reutilizar TextButton de 40 px y catálogo de campos ya usado por el diálogo.
## Componentes afectados
TeamView.refresh y pruebas de cabecera.
## Backend
Sin cambios.
## Frontend
Texto compacto centrado, sin nuevos controles de navegación.
## Persistencia
Sin cambios.
## API
Sin cambios.
## Validaciones
Código literal del modelo, sin convertirlo a entero.
## Permisos y seguridad
Local, sin hardware ni SSH.
## Casos límite
Tres/ocho dígitos, opcional vacío, juego sin código, sesión activa.
## Estrategia de pruebas
Comprobar contenido para códigos y roles, dimensiones conservadas.
## Estrategia de validación
pytest y cliente Flet 800 × 480.
## Estrategia de commits
Un commit local acotado.
## Archivos estimados a modificar
portable_team_view.py, pruebas, decisiones/contratos.
## Riesgos
Legibilidad de ocho dígitos en espacio de 105 px; inspección nativa requerida.
## Preguntas abiertas
Ninguna.
## Plan de implementación
1. Actualizar contenido y tooltip sin cambiar geometría.
2. Verificar códigos y sesión activa con pruebas.
3. Inspeccionar cabecera nativa y documentar.

## Resultado
61 pruebas focalizadas aprobadas (cabecera, Equipo, recibidos y Banco).
Dimensiones existentes conservadas y código visible en estado bloqueado.
Inspección nativa pendiente: la herramienta seleccionó otra instancia previa
de Flet y no permitió verificar la vista de prueba; no se modificó esa sesión.
