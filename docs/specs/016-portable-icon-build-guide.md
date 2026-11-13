# Ícono portátil y guía de compilación

## Contexto
La GUI portátil usa el núcleo del fork; sus scripts Pi existentes apuntan a hosting Wi-Fi/Mystery Gift, no al dispositivo ESP32-C6.
## Objetivo
Entregar un ícono propio y pasos verificables de preparación, compilación y ejecución en macOS y Pi 5.
## Alcance
PNG transparente en assets/portable, documentación en español y enlace desde docs/ai.
## Fuera de alcance
Nuevo empaquetador autónomo, firma/notarización, cambios de firmware o red, instalación remota en Pi.
## Comportamiento esperado
Ejecutar con POKELDN_PORTABLE=1. Distinguir compilar PKHeX, ejecutar Python y empaquetar distribución.
## Decisiones técnicas
Generación con imagegen integrado. Preservar ícono upstream. Python 3.13, Flet 1.0.5, SDK .NET 10; dependencias según manifests. Pi ARM64 con escritorio y cliente light.
## Componentes afectados
Assets y documentación.
## Backend
Sin cambios.
## Frontend
Asset preparado para launcher; no modificar cliente Flet compartido.
## Persistencia
Sin cambios; documentar ruta de datos explícita.
## API
Sin cambios.
## Validaciones
Compilación PKHeX local y revisión de comandos contra scripts/requirements.
## Permisos y seguridad
No incluir prod.keys; setup gráfico selecciona claves locales. No ejecutar scripts Wi-Fi como prerrequisito de C6.
## Casos límite
ARM64 vs x64, venv copiado entre OS, runtime PKHeX de otra plataforma, primer arranque sin internet, Pi sin escritorio.
## Estrategia de pruebas
Build local y comprobación de imports/versiones; no tests de layout por cambio documental.
## Estrategia de validación
Inspeccionar imagen; comprobar archivo en repo. Distinguir Mac probado y Pi pendiente.
## Estrategia de commits
Un incremento de assets/documentación sin commit automático.
## Archivos estimados a modificar
 gui/assets/portable/*, docs/portable-build.md, docs/ai/README.md y decisions.md.
## Riesgos
Paquetes del OS y disponibilidad de binarios ARM64; no certificar hardware sin ejecución real.
## Preguntas abiertas
Empaquetado autónomo portátil queda para etapa específica.
## Plan de implementación
1. Inspeccionar build, dependencias y documentación oficial.
2. Generar y guardar ícono con prompt/procedencia.
3. Documentar Mac/Pi, launchers y limitaciones del packer.
4. Compilar PKHeX en Mac, inspeccionar asset y enlazar guía.

## Resultado
- PNG inspeccionado: 1254 × 1254 y alpha, guardado en gui/assets/portable/icon.png con prompt íntegro.
- Guía docs/portable-build.md enlazada desde docs/ai, con fuentes oficiales .NET/Flet y alcance del packer comprobado contra código.
- Build Mac osx-arm64 ejecutado con SDK 10.0.404, `dotnet build -c Release services/pkhex -warnaserror --no-restore`: 0 errores y 0 advertencias. Se reutilizó restore local; instalación limpia/NuGet no probada en esta pasada.
- Imports comprobados: Flet 1.0.5, psutil 7.1.3, pyserial 3.5; Python 3.13.7.
- No se ejecutó setup Pi, instalación del launcher, empaquetado autónomo, firmware ni intercambio. Guía ARM64 propuesta y pendientes identificados explícitamente.
