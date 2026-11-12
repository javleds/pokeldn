# Identificar entrenador y devolver original

## Contexto
Identificación actual realiza una oferta legal y guarda el entrenador al confirmar la recepción. Upstream dispone de `--trade-back`, que devuelve bytes originales sin fresh PID.
## Objetivo
Añadir devolución opcional y una vista de recepción/devolución basada en el prototipo de Evolución.
## Alcance
Identificación con switch de devolución, dos confirmaciones, sprite/datos recibidos, logs, cancelar y resumen final.
## Fuera de alcance
Editar recibido, otras modalidades, recuperación automática entre procesos, pruebas físicas automáticas.
## Comportamiento esperado
Devolver original activado por defecto en el diálogo; puede desactivarse para conservar flujo previo. Oferta inicial legal. Tras recibir mostrar original y pedir segundo intercambio en consola. Contar devolución solo con segunda confirmación. Guardar entrenador del primer intercambio; nunca sustituirlo por el segundo. Cancelación o fallo tras recepción deja advertencia de devolución pendiente y archivo conservado; no prometer recuperación automática. Evoluciones propias de consola pueden ocurrir.
## Decisiones técnicas
Reutilizar Team, TeamView, runner, received.session_files, PKHeX check_bytes, Sprite y trade_back. No reconstruir ni validar como condición de envío el original en la devolución nativa. Equipo permanece estricto.
## Componentes afectados
Controlador y vista portátil, pruebas y docs AI.
## Backend
Pasar --trade-back solo para identificación solicitada y herramientas que lo soportan. Esperar dos confirmaciones. Capturar lectura de primer archivo recibido sin bloquear loop y proteger resultado por run_stamp. Mantener contador y perfil independientes.
## Frontend
Ocultar cajas/editor durante identificación; acciones superiores permanecen. Tarjeta de recibido, etapas y resumen final hasta cerrar. Sin scroll principal a 800 × 480.
## Persistencia
Archivos originales en Received mediante upstream; perfiles como antes. No nuevo formato ni borrado de archivos. Advertencia explícita: reanudación automática no implementada.
## API
Argumento opcional return_original en Team.start; sin HTTP nuevo.
## Validaciones
Original no se edita, oferta inicial legal, segunda confirmación obligatoria para éxito total; resultado tardío de lectura no cruza sesiones.
## Permisos y seguridad
No iniciar radio/flash como pruebas. No ampliar allow_illegal. Mantener exclusión de radio y cancelación con confirmación; logs redactados.
## Casos límite
Archivo aún ausente, PKHeX no puede leerlo, cancelación entre rondas, devolución confirmada con fallo de identificación, segundo entrenador distinto, herramienta sin trade-back.
## Estrategia de pruebas
Runner falso: flag, contador 1/2, perfil original, cancelación pendiente y rechazo de oferta ilegal. Vista: switch, acciones, bloqueo y resumen.
## Estrategia de validación
pytest enfocado, revisión visual simulada 800 × 480 sin radio; reiniciar app para prueba manual del usuario.
## Estrategia de commits
Controlador y tests; vista y tests; documentación. No commit automático.
## Archivos estimados a modificar
Gui portable_team.py / portable_team_view.py, tests correspondientes, docs/ai.
## Riesgos
La consola puede evolucionar el original; la cancelación no revierte recepción. Archivos guardados permiten conservar datos pero no constituyen recuperación segura al destinatario. No exponer botón de reenvío genérico que permita originales de otra sesión.
## Preguntas abiertas
Prueba física pendiente del usuario; recuperación posterior requiere diseño independiente.
## Plan de implementación
1. Verificar contrato trade-back y eventos; añadir estado y pruebas de dos rondas.
2. Leer recibido de la sesión y mostrar tarjeta/etapas con acciones existentes.
3. Probar regresiones y viewport, actualizar documentación y dejar app disponible sin iniciar intercambio.

## Resultado
Implementado el switch y la vista; acciones superiores, tarjeta de recibido, resumen y advertencia de devolución pendiente. Se reutiliza el retorno nativo y se detecta su aviso de original no conservado para solicitar cancelación, sin declarar éxito. El entrenador identificado se conserva frente a eventos posteriores. La identificación mantiene el requisito de evento compatible existente; no se promete detección en todos los juegos/roles.

117 pruebas de portátil/trade-back aprobadas con sockets locales; 53 pruebas de controlador/vista aprobadas después del último guard de error. Verificación visual simulada a 800 × 480, guardada en [referencia](references/implemented-trainer-return-demo-800x480.jpg). Aplicación real reiniciada en 8551 para prueba manual. No se inició intercambio ni flash como parte de la validación.
