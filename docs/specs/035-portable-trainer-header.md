# Entrenador sin información repetida

## Contexto
El selector ya incluye OT/ID/SID/idioma; usuario autoriza retirar título y botón
de datos redundantes. El modal también mostraba género e idioma extendido.
## Objetivo
Cabecera compacta con selector y acción Encontrar mi entrenador.
## Alcance
TeamView compartido por modalidades; retirar modal sin efectos de escritura.
## Fuera de alcance
Perfiles persistidos y lógica de identificación.
## Comportamiento esperado
Selector completo para perfiles, tooltip completo, opción Base de pokeLDN y X
conservadas. Acción de búsqueda preservada. Sin etiqueta superior repetida.
## Decisiones técnicas
Row expandida de 40 px alineada al fondo de cabecera de 60 px. No cambiar
anchos de Modalidad/Conexión; espacio del icono retirado vuelve al selector.
## Componentes afectados
portable_team_view.py y tests de cabecera.
## Backend
Sin cambios.
## Frontend
Eliminar trainer_heading, trainer_info y su modal; conservar bloqueo de sesión.
## Persistencia
Género e idioma originales se conservan, aunque se elimina su modal de consulta.
## API
Sin cambios.
## Validaciones
Búsqueda temporal no modifica selección; foco y X mantienen contrato anterior.
## Permisos y seguridad
Sin SSH ni radio real.
## Casos límite
Base, perfiles importados, sesión ocupada y modos de recibidos.
## Estrategia de pruebas
Actualizar assertions de UI retirada y mantener pruebas de búsqueda y bloqueo.
## Estrategia de validación
pytest focalizado, diff --check; cliente real pendiente.
## Estrategia de commits
Commit local independiente.
## Archivos estimados a modificar
Vista, tests trainer/received y docs/ai.
## Riesgos
Inspección visual del cliente pendiente; no certificar layout por pruebas Python.
## Preguntas abiertas
Ninguna.
## Plan de implementación
1. Retirar elementos redundantes y conservar selector/acción.
2. Actualizar regresiones y documentar resultado.

## Resultado
67 pruebas focalizadas aprobadas: identidad, búsqueda, Equipo, recibidos, Banco
y conexión. diff --check limpio. Inspección del nuevo renderizado en cliente
Flet pendiente; no se hicieron cambios en Pi.
