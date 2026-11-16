# Accesos desde el portátil

## Contexto
Accesos creados manualmente pueden apuntar a ruta incorrecta o abrir otros datos.
## Objetivo
Crear accesos de menú/escritorio desde la app Linux con rutas correctas.
## Alcance
Submenú de dos opciones a izquierda de Update/Ajustes en modo fuente Linux nativo.
## Fuera de alcance
Autoinicio, sudo, /usr/share, macOS/Windows, paquetes frozen, SSH, commit/push.
## Comportamiento esperado
Agregar al menú / Agregar al escritorio generan archivo .desktop real del usuario.
Lanzar stableRoot/scripts/run_portable.sh sin build, preservando DATA activo y root.
Mostrar resultado/ruta y errores sin bloquear UI; deshabilitar durante actividad.
## Decisiones técnicas
ContextMenu nativo con IconButton enfocable; texto INK y tema claro.
Tab/Enter, cruceta en cabecera y flechas nativas del menú; no interceptar
teclas del menú abierto. Mantener ↑ Ajustes. Resolución XDG de escritorio sin shell,
no asumir nombre Desktop ni crear carpeta si escritorio está deshabilitado.
## Componentes afectados
Módulo stdlib de accesos, controlador UI, cabecera PortableView, pruebas y docs.
## Backend
Desktop Entry spec: escapes Exec/string, argumentos sin shell. Escritura atómica,
permisos ejecutables escritorio, respaldo único antes de reemplazar archivo distinto.
No seguir symlink de destino; reemplazar acceso conservando copia del enlace.
## Frontend
Botón de icono y dos opciones exactas, feedback modal. Menú sólo Linux fuente.
## Persistencia
Sólo .desktop y respaldo en carpeta del usuario. No cambios de preferencias/datos.
## API
install_shortcut(kind, root, data) devuelve ruta y advertencias/respaldo.
## Validaciones
Root estable, launcher/icono existentes, rutas absolutas, XDG directorios válidos,
prohibir caracteres control en rutas. Repetición idempotente.
## Permisos y seguridad
Sin sudo ni ejecución de .desktop durante instalación. gio metadata::trusted como
best effort para escritorio, informar si requiere permitir lanzamiento manual.
## Casos límite
Rutas con espacios/símbolos, Desktop localizado/deshabilitado, archivo previo,
enlace roto, permisos, instalación actualizada en release, falta gio/xdg utility.
## Estrategia de pruebas
Fixtures temporales Linux simuladas; destinos/escaping/symlink/backups/datos; guards/UI.
## Estrategia de validación
pytest, py_compile, diff-check y Computer Use 800 × 480 con instalación simulada.
## Estrategia de commits
Ninguno por petición expresa; dejar cambios visibles sin stage/commit.
## Archivos estimados a modificar
portable_shortcuts backend/control, portable.py, tests y docs.
## Riesgos
Confianza del launcher depende del escritorio; no prometer bypass universal de avisos.
## Preguntas abiertas
Ninguna bloqueante.
## Plan de implementación
1. Generar/instalar entradas XDG seguras e idempotentes.
2. Integrar popup y feedback preservando layout/teclado.
3. Validar con fixtures y cliente nativo; entregar diff sin commit.

## Implementación y evidencia
Backend stdlib y controlador Flet, sincronizando navegación cuando Update cambia.
CUA a 800 × 480: ambos estados de Update, menú legible, resultado simulado visible,
Enter abre y Escape cierra sin salir de galería. No se registraron accesos reales
en Mac ni se modificó la Raspberry. Pendiente integración y confianza en la Pi.
Referencia: https://specifications.freedesktop.org/desktop-entry/latest/exec-variables.html
y https://specifications.freedesktop.org/desktop-entry/latest/value-types.html.
