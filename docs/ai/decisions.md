---
title: Decisiones del dispositivo portátil
nav_exclude: true
search_exclude: true
---
# Decisiones acordadas

Fecha de referencia: 2026-11-12. «Acordado» significa dirección del producto; no significa implementación o compatibilidad física probada.

## Hardware objetivo

| Elemento | Decisión | Validación pendiente |
|---|---|---|
| Computadora | **Raspberry Pi 5**, Linux de 64 bits | Despliegue y mediciones en dispositivo real |
| RAM | Sin capacidad definitiva | Comparar necesidades reales; 4 GB fue una estimación inicial, no mínimo documentado |
| Pantalla | **Waveshare 4.3inch DSI LCD (with case)** | Verificar revisión recibida, cable y montaje |
| Superficie de UI | **800 × 480 píxeles, horizontal**, IPS, táctil capacitivo | Escalado, legibilidad y foco en pantalla real |
| Interfaz de pantalla | MIPI DSI | Cable de pantalla compatible con conector de Pi 5; no asumir que está incluido |
| Radio | **Seeed Studio XIAO ESP32-C6**, conectado por USB/serial a la Pi | Firmware y sesión local de extremo a extremo |
| Controles | Teclado y **cruceta preferida**; táctil complementario | Modelo, conexión eléctrica y transporte de eventos |
| Carcasa | Integración portátil propia por definir | La carcasa comercial seleccionada está pensada para Pi 4B |
| Alimentación | Solución portátil pendiente | Batería, regulación, carga y autonomía medidas con todos los periféricos |

La publicación elegida identifica el modelo exacto, no una pantalla HDMI genérica:
[Mercado Libre](https://www.mercadolibre.com.mx/monitor-waveshare-43-touch-ips-para-raspberry-pi-4b/p/MLM2096907923).
Referencias: [ficha Waveshare](https://www.waveshare.com/product/raspberry-pi/4.3inch-dsi-lcd-with-case.htm), [instalación y Pi 5](https://www.waveshare.com/wiki/4.3inch_DSI_LCD).

El soporte documentado de la pantalla con Pi 5 no certifica el ajuste de la carcasa ni el contenido del paquete. La Pi se alimenta con corriente continua regulada por USB-C; no conectar una celda directamente ni inferir autonomía del valor nominal de una batería.

## Producto y prioridades

1. **Primera entrega:** abrir la app, generar, importar, validar y usar el banco local de Pokémon. Debe ser útil sin Switch ni ESP32 conectado.
2. **Siguiente entrega:** intercambios locales usando el núcleo y los protocolos de pokeldn, con la radio C6. Conservar el uso local de `prod.keys` por las rutas existentes.
3. **Opcional posterior:** raids locales; evaluar cada ruta y su carga antes de prometer soporte.

No se exige paridad con todos los features upstream. GTS, servicios por internet y automatización de botones de la Switch no son objetivos iniciales. Las funciones existentes de escritorio no se eliminan por ello.

La Pi ejecuta la app, PKHeX y la lógica de sesión. El ESP32-C6 aporta la radio LDN. La Switch ejecuta el juego. **No estamos construyendo un emulador completo de Switch.** El soporte de radio C6 no debe confundirse con soporte de firmware de mando; véanse [radio ESP32](../hardware_esp32.md) y [controladores](../hardware_pad.md).

## Interfaz y repositorio

Adaptar **la aplicación Python/Flet existente dentro del fork**, mediante un perfil portátil. No crear otro frontend independiente ni replicar generación, validación o protocolos. Mantener una experiencia normal de escritorio.

Diseñar para el espacio real de 800 × 480: una tarea principal por vista cuando sea necesario, formularios organizados, desplazamiento accesible, mensajes visibles y foco inequívoco. No reducir toda la interfaz mediante escalado para forzar que quepa.

Comenzar con teclado como simulación de cruceta: flechas, Enter y Escape. Respetar edición de campos, selección en listas y foco de diálogos. El mapeo eléctrico y los botones físicos definitivos siguen abiertos.

El mecanismo `POKELDN_PORTABLE=1` es una **propuesta del plan**, todavía no una variable implementada. Las dimensiones objetivo y el perfil separado son decisiones; la API concreta debe validarse durante el primer incremento.

## Incertidumbres que deben permanecer visibles

- No hay mediciones propias de RAM, tiempos, temperatura, consumo ni batería en Pi 5.
- No asegurar que 4 GB bastan ni que 8 GB garantizan todas las raids. Medir Python, cliente Flet, .NET y procesos de sesión juntos.
- Elegir juego y escenario para el primer intercambio real antes de esa etapa.
- Resolver ergonomía del selector de archivos y teclado en pantalla si se necesita.
- Desarrollo nativo en Mac y VM Linux ARM64 ayudan a probar UI/compatibilidad; no sustituyen validación de GPIO, pantalla, radio, potencia y rendimiento físico.
- El uso local necesita dependencias y recursos preparados previamente; auditar descargas de assets y actualizaciones antes de prometer funcionamiento completamente desconectado.
