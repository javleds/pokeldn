# Nombres legibles de juegos en bibliotecas

## Contexto
Columnas/filtros mostraban identificadores de carpetas como espada_escudo.
## Objetivo
Etiquetas compactas en español, como la galería.
## Alcance
Entrenadores/Banco: columnas, filtros y confirmación de eliminación de perfil.
## Fuera de alcance
Cambiar claves internas, exportaciones o datos persistidos.
## Comportamiento esperado
Rojo/Verde, Let's Go, Espada/Escudo, Diamante/Perla, Arceus, Escarlata/Púrpura, Z-A.
## Decisiones técnicas
Mapa GAME_LABELS separado de GAME_FOLDERS. Mantener ancho de columnas; tooltip
y ellipsis para nombres largos.
## Componentes afectados
Constantes compartidas y ambas vistas.
## Backend
Sin cambios funcionales.
## Frontend
Sustituir únicamente etiquetas de presentación.
## Persistencia
Identificadores/carpetas intactos.
## API
JSON sin cambios.
## Validaciones
Opciones conservan keys originales; exportación mantiene carpetas previas.
## Permisos y seguridad
Local, sin SSH.
## Casos límite
Etiquetas largas en columna compacta y acentos.
## Estrategia de pruebas
Regresiones existentes de bibliotecas/exportación/filtro.
## Estrategia de validación
pytest y diff --check.
## Estrategia de commits
Un commit local de etiquetas.
## Archivos estimados a modificar
portable_trainers.py, vistas y docs/ai.
## Riesgos
Etiquetas largas pueden truncarse en columna; tooltip conserva texto completo.
## Preguntas abiertas
Ninguna.
## Plan de implementación
1. Separar nombres visibles de carpetas.
2. Aplicar a ambas vistas y ejecutar regresiones.
