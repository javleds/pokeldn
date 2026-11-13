# Navegación nativa y respuestas de foco pendientes

Problema reproducido: seleccionar un juego inicia scroll desde on_focus y desmonta la galería antes de recibir la respuesta. Flet 1.0.5 rechaza la respuesta del control no registrado, cierra la sesión y reconecta dejando un modal visible sin sus callbacks.

Plan: reutilizar la galería y Equipo, serializando foco/desplazamiento y selección mediante un lock asíncrono de la vista. Ignorar foco tardío de una galería ya abandonada. No cambiar protocolos ni Guardar/Cancelar. Evitar que el diagnóstico inicial sobrescriba una navegación explícita. Añadir pruebas de selección durante scroll pendiente y navegación durante diagnóstico; verificar abrir/cancelar/guardar Conexión en cliente nativo a 800 × 480 útiles.

Implementado en `PortableView`: selección asíncrona coordinada con foco y scroll; eventos tardíos de foco no operan fuera de home. El arranque respeta la navegación explícita realizada mientras esperaba los checks.

Evidencia: el transporte registró `Error handling invoke method results. Control with ID 176 is not registered`, seguido de cierre de sesión y reconexión. Después del cambio se verificaron abrir/cancelar y abrir/guardar Conexión de Let’s Go en app nativa macOS de 800 × 512 (aproximadamente 800 × 480 útiles). Ambos botones cierran el modal y mantienen Equipo. No se inició intercambio.

Validación: 114 pruebas de UI, Equipo y vistas de recibido; incluye selección esperando respuesta de scroll y conservación de navegación durante checks. La prueba física de intercambio queda fuera de este ajuste.
