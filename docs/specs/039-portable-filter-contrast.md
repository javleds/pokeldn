# Contraste de filtros de juego

## Contexto
Captura del usuario: texto oscuro sobre menú oscuro en Entrenadores. Los filtros
reutilizan theme.dropdown del escritorio, cuyo MenuStyle fija PANEL oscuro.
## Objetivo
Menús legibles en Entrenadores y Banco con dimensiones portátiles.
## Alcance
Estilo local de ambos filtros. Equipo ya fija menú claro y límites.
## Fuera de alcance
Tema escritorio, datos, búsqueda y contratos de selección.
## Comportamiento esperado
Menú claro/texto oscuro y altura acotada; lista desplazable, mismo filtro.
## Decisiones técnicas
Sobrescribir MenuStyle, color y estilo de opciones en instancias portátiles.
## Componentes afectados
portable_trainers_view.py y portable_bank_view.py.
## Backend
Sin cambios.
## Frontend
PAPER/INK, menú 280 × 160 como selectores de Equipo. Campo cerrado conservado.
## Persistencia
Sin cambios.
## API
Sin cambios.
## Validaciones
Abrir ambos menús, seleccionar juego y comprobar filas filtradas.
## Permisos y seguridad
Fixtures locales sin hardware ni datos personales.
## Casos límite
Todos los juegos, lista vacía y selección tras scroll.
## Estrategia de pruebas
Pruebas existentes de filtro y revisión real mediante Computer Use.
## Estrategia de validación
pytest -W error, diff --check y Flet nativo 800 × 480.
## Estrategia de commits
Commit local independiente.
## Archivos estimados a modificar
Ambas vistas y docs/ai.
## Riesgos
Color del campo no determina color del menú flotante; revisar siempre abierto.
## Preguntas abiertas
Ninguna.
## Plan de implementación
1. Sobrescribir tema de los filtros portátiles.
2. Inspeccionar menús abiertos y selección.
3. Validar regresiones y commit.

## Resultado y límite
Causa confirmada por captura del usuario y MenuStyle del helper. Ambos filtros
fijan fondo/color de opciones y límites, preservando callback y valores.
Computer Use seleccionó una instancia anterior; un cliente aislado temporal
quedó en blanco. No se pudo certificar el renderizado corregido en este turno.
No se cerró la sesión del usuario. Verificación visual pendiente.
