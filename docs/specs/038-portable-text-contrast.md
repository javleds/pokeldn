# Contraste del tema portátil

## Contexto
Computer Use reprodujo texto blanco en Entrenadores/Banco con portable.main
real. El preview anterior usaba un Theme simplificado y no exponía el defecto.
TextTheme personalizado declara todos los estilos sin color; el cliente usa
blanco para textos que no fijan color propio, incluso en ThemeMode.LIGHT.
## Objetivo
Texto legible sobre superficies claras del portátil.
## Alcance
Color INK explícito en estilos del tema portátil; conserva colores específicos.
## Fuera de alcance
Cambiar tema escritorio, datos, navegación y layout.
## Comportamiento esperado
Listas, títulos, mensajes y etiquetas usan texto oscuro por defecto. Header rojo
y botones oscuros conservan blanco explícito.
## Decisiones técnicas
Corregir tema de origen en vez de duplicar colores en cada Text de las listas.
## Componentes afectados
portable.main y prueba de arranque.
## Backend
Sin cambios.
## Frontend
Mismo ThemeMode.LIGHT, dimensiones y familia tipográfica.
## Persistencia
Sin cambios.
## API
Sin cambios.
## Validaciones
Revisar cliente nativo real a 800 × 480, Entrenadores/Banco e identificación.
## Permisos y seguridad
Datos simulados en carpeta temporal, sin radio ni secretos.
## Casos límite
Textos con colores propios, confirmaciones y texto explicativo de entrenador.
## Estrategia de pruebas
Regresión de tema al inicializar main y tests existentes de facilities.
## Estrategia de validación
pytest y Computer Use antes/después con el mismo arranque real.
## Estrategia de commits
Un commit local de contraste.
## Archivos estimados a modificar
portable.py, pruebas de arranque, docs/ai.
## Riesgos
No extrapolar mock o tema simplificado a apariencia Flutter real.
## Preguntas abiertas
Ninguna.
## Plan de implementación
1. Fijar color de TextTheme.
2. Reiniciar preview real y revisar listas/diálogo.
3. Ejecutar regresión y guardar commit.

## Resultado visual
Computer Use reprodujo blanco sobre claro en ambas listas antes del cambio.
Tras fijar INK, verificó títulos/filas de Entrenadores y Banco, mensaje inicial
y diálogo Encontrar mi entrenador con explicación, switch y acciones legibles.
Cliente nativo macOS a 800 × 480 útiles, arranque portable.main real y fixtures
temporales sin claves/radio. Colores blancos explícitos de header y acciones
oscuras permanecen. No prueba física en Raspberry Pi.
