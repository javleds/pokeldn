# Compilación portátil en un comando

## Contexto
Recordar directorio, SDK local y exports ocasiona errores de compilación.
## Objetivo
Ejecutar scripts/build_portable.sh desde cualquier directorio.
## Alcance
Resolver raíz y SDK .NET 10; compilar PKHeX Release con warnings como errores.
## Fuera de alcance
Instalar dependencias, ejecutar GUI, empaquetar .app, alterar SDK global.
## Comportamiento esperado
Preferir SDK local del checkout, luego DOTNET_ROOT, instalación Pi documentada y PATH. Usar candidato que incluya SDK 10. Fallar con mensaje útil si falta. Restaurar por defecto; permitir argumentos adicionales de dotnet build.
## Decisiones técnicas
Bash con set -euo pipefail y rutas citadas. No requiere activar venv ni privilegios. CLI_HOME local al checkout.
## Componentes afectados
Nuevo script y guía.
## Backend
Motor existente, sin cambios.
## Frontend
Sin cambios.
## Persistencia
Solo artefactos de compilación y caché local ignorados por Git.
## API
Sin cambios.
## Validaciones
Detección del SDK 10 y propagación del código de salida del build.
## Permisos y seguridad
Sin sudo ni instalación automática. No tocar claves o perfiles.
## Casos límite
Ruta con espacios, ejecución desde otro cwd, SDK global antiguo, ausencia de SDK 10.
## Estrategia de pruebas
bash -n y ejecución real desde fuera del repo; detección aislada con herramientas simuladas.
## Estrategia de validación
Build local sin restore para entorno ya preparado; primer restore requiere red.
## Estrategia de commits
Un cambio de script y documentación; no commit automático.
## Archivos estimados a modificar
scripts/build_portable.sh, docs/portable-build.md y docs/ai.
## Riesgos
Disponibilidad de NuGet en primer restore; no equivale a crear paquete autónomo.
## Preguntas abiertas
Ninguna.
## Plan de implementación
1. Crear script usando SDKs existentes, sin instalar.
2. Comprobar sintaxis y build desde otro cwd.
3. Poner comando corto al inicio de guía y registrar alcance.

## Resultado
Script ejecutable implementado. `bash -n` correcto; comprobaciones con SDK simulado cubren ausencia, rutas con espacios, argumentos y propagación de fallo. Ejecución real desde /private/tmp con --no-restore: SDK local 10.0.404, build correcto, 0 warnings/0 errores. Restauración inicial con red y ejecución en Pi no repetidas en esta etapa. Documentación actualizada con comando habitual.
