# Paquete autónomo Portable

## Contexto
build_portable.sh compila PKHeX, pero no incorpora identidad de aplicación.
## Objetivo
Empaquetar pokeLDN Portable con ícono propio y perfil activado sin exports.
## Alcance
Opción --portable en pack_app.py y --app en build_portable.sh; macOS local como primera validación.
## Fuera de alcance
Firma Apple/notarización, certificación Pi, rediseño de UI y protocolos.
## Comportamiento esperado
Bundle distinto de escritorio, ícono PNG existente convertido a icns para bundle y viewer; inicio portátil nativo. Conserva POKELDN_DATA explícito; default privado pokeldn-portable. No incorpora claves ni datos personales.
## Decisiones técnicas
Reutilizar pack_app.py, pack_flet.py, gui/main.py y runtime hook PyInstaller. Portable permite cliente Flet instalado y Unicorn del wheel si faltan builds personalizados. Conserva firmware existente completo para compatibilidad. Assets portátiles explícitos aunque no estén staged en Git.
## Componentes afectados
Scripts de empaquetado, hook portátil y documentación.
## Backend
PKHeX publish nativo existente.
## Frontend
Misma GUI portátil, sin cambios de formularios/foco. Cliente estándar sin arrastre de archivos si no hay build personalizado.
## Persistencia
Datos por usuario fuera del bundle; sin migración o copia del preview.
## API
Sin cambios.
## Validaciones
CLI, identidad, contenido del paquete, firma ad hoc y arranque local; no equivalen a prueba en equipo limpio.
## Permisos y seguridad
Sin prod.keys ni datos locales; no modificar cliente Flet compartido. Firma ad hoc local.
## Casos límite
Sin Flutter/builds opcionales, assets no staged, entorno web/demo heredado, rutas con espacios y ejecución de auxiliares.
## Estrategia de pruebas
Tests del hook y selección de assets; compilación real y revisión del bundle/viewer.
## Estrategia de validación
pytest focalizado, bash -n, compileall, empaquetado Mac e inspección de firma/íconos. Registrar impedimentos reales.
## Estrategia de commits
Un incremento revisable; no commit automático.
## Archivos estimados a modificar
scripts/pack_app.py, scripts/build_portable.sh, scripts/portable_runtime.py, tests/test_portable_package.py, docs/portable-build.md, docs/ai/.
## Riesgos
Disponibilidad del cliente Flet y restore NuGet; wheel Unicorn mayor; Linux/Windows requieren validación propia.
## Preguntas abiertas
Certificación física Pi y distribución firmada quedan pendientes.
## Plan de implementación
1. Añadir identidad, conversión PNG e inclusión explícita de assets al packer existente.
2. Activar perfil antes de imports mediante hook, conservar auxiliares y escritorio.
3. Exponer --app reutilizando detección SDK existente.
4. Ejecutar tests y build nativo; documentar evidencia y límites.

## Evidencia de validación (2026-11-15)
- 4 pruebas nuevas de empaquetado correctas; 245 pruebas GUI/layout correctas en total. Cinco pruebas GUI fallaron dentro del sandbox y pasaron al repetirlas fuera de sus restricciones de sockets/entorno.
- `bash -n`, compileall y `git diff --check` correctos.
- Publicación PKHeX y empaquetado real en Mac Apple Silicon. Bundle `dist/pokeldn-portable.app`, ~197 MiB, firma ad hoc verificada con `codesign --verify --deep --strict`.
- Info.plist del viewer con nombre pokeLDN Portable, identificador propio y CFBundleIconFile AppIcon.icns; sin CFBundleIconName que priorice el catálogo anterior. Bytes del icns del bundle y del viewer idénticos.
- Arranque real con datos temporales y TCP explícito: pantalla portátil de configuración a 800 × 480 útiles, Motor Pokémon Listo, claves pendientes y conexión por revisar. Sin flasheo ni intercambio.
- Primer intento de inspección mostró una ventana vacía; tras reiniciar prueba y recuperar la herramienta de escritorio se comprobó la pantalla real. No se atribuye una causa no demostrada. El hook final limpia cliente externo/web/demo y usa TCP local 8590 por defecto, configurable.
- Inspección visual directa del Dock bloqueada por timeout de la herramienta; se verificaron su cliente y los archivos/metadatos del ícono. Equipo limpio, macOS Intel, Windows, Linux ARM64/Pi y notarización no probados.
- Compilación final terminada correctamente: se extrajo el bytecode del runtime hook del ejecutable y se comprobó que incorpora 127.0.0.1 y puerto 8590. Firma estricta e igualdad de íconos bundle/viewer repetidas correctamente sobre ese artefacto final.
