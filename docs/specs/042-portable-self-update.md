# Actualización portátil desde main

## Contexto
La Pi ejecuta desde fuente. El updater upstream instala releases empaquetadas de
Decryptu; no sirve como actualización del fork. El usuario autoriza integrar
feature/custom-device en main y usar main como fuente del portátil.
## Objetivo
Detectar actualizaciones sin bloquear y actualizar con progreso independiente,
reinicio automático y recuperación, preservando datos y versión funcional.
## Alcance
Checkout portátil Linux/macOS, fuente fija HTTPS javleds/pokeldn main, botón a
izquierda de Ajustes, helper independiente, versiones preparadas y launcher estable.
## Fuera de alcance
Firmware, sudo/apt, escritorio upstream/empaquetados, migraciones de datos,
reescribir cambios locales, editar Pi vía SSH, publicación automática de Git.
## Comportamiento esperado
Check en background al abrir; icono solo si remoto es descendiente de HEAD.
Confirmación explícita. Bloquear sesiones, firmware/checks y escrituras pendientes.
Helper confirma ventana lista antes de cerrar principal; espera fin de proceso.
Prepara checkout y venv propios, instala deps fijadas, compila PKHeX y smoke test.
Activa referencia atómica, abre UI con datos absolutos originales, espera handshake.
Si falla preparación deja versión previa; si falla arranque revierte referencia y
no abre dos procesos que puedan usar radio. Error/log permanecen visibles.
## Decisiones técnicas
Reutilizar patrón ready/outcome de update.py, no su downloader upstream.
Versiones bajo .portable-updates en instalación estable; nunca mover un venv.
Launcher original resuelve referencia activa. No git pull sobre código ejecutado.
Guardar PID/estado/log en job; bloqueo exclusivo impide dos updates simultáneos.
## Componentes afectados
pokeldn/app/portable_update.py, gui/portable.py, gui/portable_updating.py,
scripts/run_portable.sh y dispatcher Python stdlib, tests y guía.
## Backend
Git fetch explícito de fuente fija con timeout, comparación de ancestros y SHA
inmutable; rechazar árbol sucio/divergencia y versiones sin contrato de arranque.
Preparación con comandos argv sin shell y límites de tiempo. Entorno limpio de
selección de motor heredada, conservación de SDK y display.
## Frontend
IconButton descargar blanco, tamaño de cabecera conservado; modal informativo.
Auxiliar 800 × 480 con etapa, indicador, detalles acotados, log y cierre al terminar.
## Persistencia
Datos originales no se migran ni borran. POKELDN_DATA absoluto se fija antes de
redirigir el launcher. Puntero/estado actualizador separados de perfiles/banco.
## API
Contrato interno del helper mediante request JSON local, ready/commit/startup files;
no endpoints públicos. UI sólo coordina; engine no depende de Flet.
## Validaciones
SHA remoto, ancestro, origen esperado, árbol limpio, espacio/escritura, locks,
timeouts, scripts esperados, import UI y consulta real motor antes de activación.
## Permisos y seguridad
Código remoto únicamente del fork fijo main. No sudo, credenciales en logs ni
comandos shell interpolados. No secretos en fixtures. Preparación no toca datos.
## Casos límite
Offline, remoto forzado, local adelantado, rama feature ante migración, cambios
locales, build/pip fallido, doble clic, cierre helper, arranque sin handshake,
reinicio eléctrico: puntero siempre versión completa; retener versiones anteriores.
## Estrategia de pruebas
Git temporal/remote local inyectado sólo en tests, timeout/fallo en cada etapa,
rollback/lock, datos preservados, guards UI, launcher estable/SDK/datos, legacy.
## Estrategia de validación
pytest relevante warnings-as-errors, compilación Python, bash -n, diff check,
Computer Use 800 × 480 con datos y update simulado sin tocar instalación real.
## Estrategia de commits
Integración local fast-forward a main; commit funcional independiente del updater
con tests/docs. Mantener política del usuario de publicar y desplegar por su cuenta.
## Archivos estimados a modificar
Los componentes anteriores, .gitignore, docs/ai y docs/portable-build.md.
## Riesgos
Descarga/venv requieren disco/red; primera actualización tarda más que pull/build.
No prometer reversión de datos escritos por versiones futuras; handshake antes de
permitir sesiones y sin migraciones destructivas. Hardware Pi requiere prueba propia.
## Preguntas abiertas
Ninguna bloqueante; main local necesita publicación por usuario para detección remota.
## Plan de implementación
1. Integrar main local; definir contrato de updater/launcher y pruebas aisladas.
2. Implementar preparación/activación/rollback con versiones y venv estables.
3. Añadir helper visible y handshakes, botón/guards y coordinación de cierre.
4. Probar fallos y éxito, validar UI, documentar operación/recuperación y commit.

## Resultado y evidencia
Implementado y rama integrada localmente a main. Backend separado del helper y
controlador UI; source fijo sin override de entorno. Preparación en rutas definitivas,
puerto auxiliar efímero, puntero sólo tras ventana lista, commit final libera radio.
Revisión independiente corrigió carrera ready/lock, activación prematura y rollback
posterior al commit; el cliente huérfano se termina por grupo de procesos propio.
Ajustes muestra errores de consulta y permite reintentar sin nueva fila de cabecera.

Validación: suite `tests/test_portable*.py tests/test_app_update.py -q -W error`:
465 aprobadas. Después de añadir cobertura de handshake/fallo/estado y corregir
navegación ↑ Ajustes / ← Actualizar, suite controles+UI+cierre: 52 aprobadas.
Git temporal real para detección/clone/checkout, subprocess de launcher con rutas
con espacios; pip/build/smoke de staging sustituidos por fixtures. Bash -n,
compilación Python y diff-check limpios. No dependencias nuevas.
Computer Use a 800 × 480 con cliente Flet: botón/modal, auxiliar con indicador,
detalles de build y fallo, estado de Ajustes sin recortar acciones y entrada por
teclado. No ejecutado un self-update real desde GitHub en Pi ni una instalación de
pip/build completa del release preparado; requiere prueba física tras publicar main.
Versiones previas/fallidas retenidas, sin limpieza automática. Datos no migrados.
