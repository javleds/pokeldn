# Ventana sin bordes por defecto

## Contexto
Tras preparar spec 050, el usuario pide adoptar esta modalidad como default.
## Objetivo
Linux portátil nativo abre maximizado sin bordes sin variable adicional.
## Alcance
App principal y viewport adaptable ya implementado; botón/F11 conservados.
## Fuera de alcance
Actualizador (conserva spec 049), desktop upstream, dock y teclado del sistema.
## Comportamiento esperado
Arranque sin fullscreen, maximizado sin bordes. Botón/F11 entra en fullscreen y
regresa a maximizado sin bordes. Menor altura permite desplazamiento vertical.
## Decisiones técnicas
Retirar opción experimental de entorno y renombrar estado a borderless_mode.
Reutilizar canvas/viewport de spec 050 sin cambios visuales adicionales.
## Componentes afectados
PortableView, main, pruebas de arranque y guía de ejecución.
## Backend
Sin cambios.
## Frontend
El mismo modo de spec 050 pasa a ser predeterminado en Linux nativo.
## Persistencia
Ninguna; alternancia no persistida.
## API
Retirar variable experimental aún no publicada; comando habitual suficiente.
## Validaciones
Mac, Windows y web mantienen comportamiento previo. Cierre y handoff intactos.
## Permisos y seguridad
Sin acceso a datos ni radio para validar.
## Casos límite
Volver de fullscreen; ventanas pequeñas; ejecución web sobre Linux.
## Estrategia de pruebas
Actualizar tests de default y mantener tests de alternancia/resize y bloqueos.
## Estrategia de validación
Pytest -W error y diff --check; evidencia visual 050 aplicable al mismo viewport.
## Estrategia de commits
No solicitado en este turno; cambios continúan locales junto a spec 050.
## Archivos estimados a modificar
Gui portable, tests portable_ui, docs/ai y portable-build.
## Riesgos
La adopción por petición del usuario no certifica Squeekboard en formularios reales.
## Preguntas abiertas
Validación física de formularios en Pi sigue pendiente.
## Plan de implementación
1. Quitar opt-in y mantener condición Linux nativo.
2. Actualizar tests de arranque sin variable y documentación vigente.
3. Ejecutar regresión enfocada y registrar resultados.

## Resultado
123 pruebas pasan con -q -W error: portable_ui, portable_team_view,
portable_touch, portable_close y portable_updating. Diff --check sin errores.
No se alteró el viewport probado visualmente en spec 050; el cambio selecciona
ese modo por plataforma sin opt-in. Pi/Squeekboard en formularios reales pendiente.
