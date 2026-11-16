# Separador visual del código

## Contexto
Usuario solicita 000, 0000-0000 y 000-000 en Conexión.
## Objetivo
Facilitar lectura sin modificar el código real.
## Alcance
Texto y tooltip del botón compartido.
## Fuera de alcance
Validación, persistencia y transporte.
## Comportamiento esperado
Hasta cuatro dígitos sin separador; más de cuatro se divide por la mitad.
Longitud impar: primer grupo menor (cinco → 00-000). Vacío sigue Sin código.
## Decisiones técnicas
Formatear variable local de presentación, sin modificar modelo.
## Componentes afectados
TeamView.refresh y test de código.
## Backend
Sin cambios.
## Frontend
Guion literal, dimensiones existentes.
## Persistencia
Código original intacto.
## API
Sin cambios.
## Validaciones
Aplicar solo a dígitos; conservar ceros iniciales.
## Permisos y seguridad
Local, sin SSH.
## Casos límite
Tres, cuatro, cinco, seis, ocho dígitos y vacío.
## Estrategia de pruebas
Actualizar casos existentes y verificar que modelo no se modifica.
## Estrategia de validación
pytest focalizado y diff --check. Renderizado físico pendiente.
## Estrategia de commits
Commit local independiente.
## Archivos estimados a modificar
Vista, pruebas, decisiones y contratos.
## Riesgos
Guion añade un carácter al texto de ocho dígitos.
## Preguntas abiertas
Ninguna.
## Plan de implementación
1. Formatear copia local.
2. Verificar límites y código original.
