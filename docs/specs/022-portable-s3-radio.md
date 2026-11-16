# Radio ESP32-S3 en el asistente portátil

## Contexto
El núcleo soporta S3, pero Setup rechaza cualquier chip diferente del C6.
En Pi ARM64 el usuario detectó S3 en bootloader y encontró ese bloqueo.
El cierre FlutterEngineRemoveView tras elegir claves es un problema separado sin causa confirmada.

## Objetivo
Aceptar S3 y C6 por USB nativo en diagnóstico, instalación y reinstalación.

## Alcance
Asistente portátil, etiquetas de placa y regresiones de instalación.

## Fuera de alcance
Cambios de protocolo, soporte adicional C3/clásico, arreglos especulativos de Flutter,
publicación y certificación de intercambios físicos.

## Comportamiento esperado
Ambos chips pueden estar listos o necesitar firmware. Rechazar UART, chips no
admitidos y sustitución de placa. No declarar listo sin respuesta compatible.

## Decisiones técnicas
Reutilizar board.bundled_firmware, detect_chip, identify y CLI existente.
Seleccionar imagen por chip recién detectado y comprobar coincidencia con el
diagnóstico anterior. Mostrar chip detectado en las tarjetas actuales.

## Componentes afectados
Setup, vistas de configuración y pruebas portátiles.

## Backend
Mantener exclusión durante sesiones y flasheo; verificar USB nativo nuevamente
antes de escribir y comprobar el mismo chip después de reiniciar.

## Frontend
Mismas tarjetas, acciones y dimensiones; etiquetas S3/C6 dinámicas.

## Persistencia
Sin cambio de formato, rutas ni claves guardadas.

## API
Sin cambios.

## Validaciones
Chip admitido, identidad serie, puerto nativo, firmware correcto y respuesta final.

## Permisos y seguridad
Instalar/reinstalar sigue siendo explícito. No leer ni copiar claves privadas.

## Casos límite
Sustitución C6/S3, UART, firmware ausente, escritura exitosa sin respuesta,
varias placas, sesión activa y demo.

## Estrategia de pruebas
Parametrizar C6/S3: diagnóstico, firmware ausente, reinstalación y verificación.
Cubrir rechazo UART y sustitución antes de escribir.

## Estrategia de validación
pytest focalizado con -W error, diff --check. Inspección Flet a 800 × 480 y
prueba física Pi pendientes si el entorno no permite reproducirlas.

## Estrategia de commits
Un cambio cohesivo de soporte S3, pruebas y documentación. No publicar automáticamente.

## Archivos estimados a modificar
gui/portable_setup.py, gui/portable.py, gui/portable_team.py,
tests/test_portable_setup.py, docs/ai/decisions.md y esta spec.

## Riesgos
La enumeración USB no garantiza firmware funcional. El nombre comercial de una
placa no certifica intercambios ni compatibilidad de todos sus periféricos.

## Preguntas abiertas
Reproducción del fallo del selector nativo en Pi y prueba física de radio.

## Plan de implementación
1. Ampliar allowlist a S3/C6 y seleccionar firmware con helper existente.
2. Conservar comprobaciones de identidad y actualizar etiquetas sin alterar layout.
3. Ejecutar regresiones de Setup/UI y documentar resultados y límites.

## Resultado
Implementado soporte C6/S3 con imagen seleccionada por chip y etiquetas dinámicas.
50 pruebas Setup/UI aprobadas con -W error. Sin prueba visual del cliente Flutter
a 800 × 480 ni flasheo real en este entorno; verificar en la Pi antes de certificarlo.
Se prepara parche de código/pruebas para el checkout 66995b5a sin publicar commits.
