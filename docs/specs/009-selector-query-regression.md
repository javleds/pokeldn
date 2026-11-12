# Búsqueda temporal de selectores: regresión de foco

## Causa comprobada
Flet 1.0.5, packages/flet/lib/src/controls/dropdown.dart, sincroniza el TextEditingController cuando cambia value; cambiar text solamente no limpia el campo visual. La prueba previa validaba Python, no el cliente Flutter.

## Contrato que debe conservarse
Entrar al selector buscable vacía la consulta, sin editar el borrador ni validar. data conserva la selección confirmada; value es temporal y pasa a None durante búsqueda. Elegir explícitamente o pulsar X confirma cambios; perder foco restaura data. Refresh de entrenador no debe sobrescribir la búsqueda activa. Menú acotado, controles reutilizados y filtros por caja permanecen vigentes.

## Cambio y validación
Modificar el helper portátil compartido, sin alterar escritorio. Cubrir búsqueda sin callback y refresh mientras está activa. Verificar visualmente a 800 × 480: campo vacío, escritura, selección y restauración al salir. No basta un test que compruebe text en Python.

## Resultado y límites de verificación
81 pruebas de vista/controlador/navegación aprobadas. Fixture de cliente Flet a 800 × 480: foco solicitado mediante la API nativa después del montaje vacía el campo, permite escribir y restaura Automático al salir con Tab sin seleccionar. Captura: `references/implemented-query-focus-demo-800x480.jpg`. Los clics automatizados de accesibilidad abrían el menú sin dar foco Flutter, por lo que esta prueba visual no certifica todas las combinaciones de ratón/táctil del dispositivo físico. No se añadió un wrapper de gestos ni se cambió el layout.
