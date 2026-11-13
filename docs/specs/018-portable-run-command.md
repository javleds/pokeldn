# Arranque portátil en un comando

## Contexto
El arranque nativo requiere variables que el usuario no quiere repetir.
## Objetivo
Abrir la app mediante scripts/run_portable.sh.
## Alcance
Launcher Bash, raíz independiente del cwd, Python del venv y datos actuales.
## Fuera de alcance
Compilar, instalar dependencias, matar procesos o crear paquete autónomo.
## Comportamiento esperado
Modo portátil nativo; omitir variables de web/demo. POKELDN_DATA existente se respeta; por defecto .local-preview/portable para conservar configuración de esta sesión. Loopback y puerto 8590 por defecto (puerto configurable). SDK local si existe, o instalación Pi documentada.
## Decisiones técnicas
Reutilizar gui/main.py mediante exec; rutas citadas y errores claros.
## Componentes afectados
Nuevo script y documentación.
## Backend
Sin cambios.
## Frontend
Sin cambios.
## Persistencia
Misma ruta de datos; no borrar ni migrar.
## API
Sin cambios.
## Validaciones
Venv presente; propagación de código de salida de Python.
## Permisos y seguridad
No sudo, no iniciar intercambios; servidor limitado a localhost.
## Casos límite
Otro cwd, rutas con espacios, entorno web heredado, puerto ocupado, datos personalizados.
## Estrategia de pruebas
bash -n y Python simulado que comprueba argumentos/entorno sin iniciar otra instancia real.
## Estrategia de validación
Verificar defaults, overrides, ausencia de venv y salida del proceso.
## Estrategia de commits
Un cambio cohesivo, sin commit automático.
## Archivos estimados a modificar
scripts/run_portable.sh y docs de uso/AI.
## Riesgos
Instancia anterior puede ocupar el puerto: cerrar antes, no matar automáticamente.
## Preguntas abiertas
Ninguna.
## Plan de implementación
1. Crear launcher con defaults del comando ya entregado.
2. Verificar entorno y rutas mediante fixture temporal.
3. Documentar comando y overrides.

## Resultado
Script ejecutable; bash -n correcto. Fixture de ejecución desde /tmp con ruta con espacios comprobó ausencia de venv, flags nativos, limpieza web/demo, loopback, defaults, overrides de datos/puerto y propagación de salida. No se lanzó otra instancia real para evitar interferir con la app abierta.

## Extensión: --build
Petición posterior: admitir `run_portable.sh --build`. Plan: reutilizar build_portable.sh antes de lanzar Python, detener el arranque si falla, mantener ejecución sin argumentos sin build y rechazar argumentos desconocidos. Verificar orden, éxito y fallo con procesos simulados; actualizar ayuda y guía. No instala dependencias ni crea paquetes autónomos.

Extensión implementada. bash -n y fixture verifican arranque sin build, orden build→app, fallo de build propagado sin abrir app y rechazo de argumentos desconocidos. Sin iniciar otra instancia real.
