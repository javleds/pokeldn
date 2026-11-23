# Botón de pantalla completa

## Contexto
F11 ya alterna fullscreen, pero el usuario necesita hacerlo con la pantalla táctil.
## Objetivo
Agregar un botón inmediatamente a la izquierda de Ajustes.
## Alcance
Cabecera portátil nativa, todas las vistas; icono/tooltip según estado real.
## Fuera de alcance
Cambiar arranque Linux, parchear Squeekboard, redimensionar formularios o UI web.
## Comportamiento esperado
Toque alterna ventana/fullscreen sin cambiar vista ni datos. F11 usa la misma acción.
El botón permanece disponible aunque Ajustes esté oculto. Web lo oculta.
## Decisiones técnicas
Reutilizar page.window.full_screen y PortableView.key. Sin nueva fila de cabecera.
Sin preferencias persistidas. Actualizar icono al recibir eventos nativos fullscreen.
## Componentes afectados
PortableView, pruebas UI, documentación de decisiones y contratos.
## Backend
Sin cambios.
## Frontend
Icono FULLSCREEN/FULLSCREEN_EXIT, tooltip y borde de foco de la cabecera existente.
## Persistencia
Sin cambios.
## API
Sin cambios.
## Validaciones
Respetar cierre, handoff y menú de accesos. Mantener ↑ hacia Ajustes y ←/→ en cabecera.
## Permisos y seguridad
Sin operaciones de radio ni datos para la validación visual.
## Casos límite
Web sin window, fullscreen iniciado por Linux y alternancia externa del escritorio.
## Estrategia de pruebas
Toque/F11, web, bloqueos, icono/tooltip y navegación de cabecera.
## Estrategia de validación
Pytest -W error y cliente Flet con superficie 800 × 480. Pi física pendiente.
## Estrategia de commits
Cambio acotado; esta petición no solicita un nuevo commit.
## Archivos estimados a modificar
Gui portable, tests/test_portable_ui.py, docs/ai y esta spec.
## Riesgos
Estado asíncrono del gestor de ventanas. Fullscreen sigue ocultando Squeekboard en
la configuración labwc reportada; este botón permite volver a ventana con tacto.
## Preguntas abiertas
Sin decisiones pendientes para implementar el botón.
## Plan de implementación
1. Añadir botón junto a Ajustes y compartir acción con F11.
2. Sincronizar icono/tooltip y registro de foco sin filas adicionales.
3. Probar y documentar evidencia y límites.

## Evidencia (2026-11-22)
- 161 pruebas pasan con -q -W error: UI, Equipo, shortcuts, touch, cierre,
  actualización y control de actualización. Fixtures de ventana declaran fullscreen;
  navegación de Update actualizada para atravesar el nuevo botón en ambos sentidos.
- Cliente Flet nativo Mac con fixture sin radio: botón junto a Ajustes a 800 × 480,
  entrada a fullscreen por clic, salida por clic y vista Equipo con cabecera visible.
- Pi física y Squeekboard pendientes; no se afirma corregida su superposición.
