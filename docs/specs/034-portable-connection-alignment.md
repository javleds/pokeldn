# Conexión sin label redundante

## Contexto
El botón ya muestra rol/código; el usuario solicita retirar el label Conexión.
## Objetivo
Simplificar y alinear el botón con los controles de la cabecera existente.
## Alcance
Solo presentación compartida de conexión.
## Fuera de alcance
Cambios de datos, protocolos o diálogo.
## Comportamiento esperado
Botón sin label, ancho 105 y alto 40; alineado abajo en cabecera de 60.
Tooltip conserva acción de configurar y datos.
## Decisiones técnicas
Reutilizar TextButton directamente con width explícito y alineación END de Row.
## Componentes afectados
TeamView._trade_header.
## Backend
Sin cambios.
## Frontend
Retirar únicamente wrapper labeled de Conexión.
## Persistencia
Sin cambios.
## API
Sin cambios.
## Validaciones
Conservar código, rol, tooltip y bloqueo durante sesión.
## Permisos y seguridad
Local, sin SSH/hardware.
## Casos límite
Con/sin código y modalidades compartidas.
## Estrategia de pruebas
Ejecutar regresiones existentes de cabecera; sin tests nuevos para cambio cosmético.
## Estrategia de validación
pytest, diff --check; inspección en cliente pendiente.
## Estrategia de commits
Commit local acotado de alineación.
## Archivos estimados a modificar
Vista y documentación de decisión/contratos.
## Riesgos
Validación visual pendiente en cliente del usuario; no modificar otras columnas.
## Preguntas abiertas
Ninguna.
## Plan de implementación
1. Sustituir wrapper por botón con ancho explícito.
2. Ejecutar pruebas existentes y registrar resultado.
