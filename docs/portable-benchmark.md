# Portátil económico: primer benchmark y criterios

Fecha: 2026-11-13. **Exploración, no cambio del hardware aprobado ni certificación de placa mínima.** La Pi 5 ya adquirida servirá de referencia; el usuario aún no cuenta con alimentación/SD/periféricos para probarla.

## Qué medimos realmente

Mac ARM64, macOS 26.6.2, Python 3.13.7, 8 CPU lógicas, 24 GiB RAM; PKHeX compilado localmente. No se identificó el modelo exacto de SoC en esta pasada. Una ejecución por juego: no son medianas de múltiples arranques ni límites garantizados.

`benchmark_portable.py` instancia **Team y Service reales**, con datos temporales, sprite deshabilitado, sin clave ni radio. Carga catálogos y genera/valida Bulbasaur, Charmander, Squirtle, Pikachu, Eevee y Magikarp a nivel 100; luego mide cache, apodos y cambio a nivel 99. Todas las cajas quedaron legales en todas las etapas de los tres juegos.

RSS = suma muestreada del proceso Python y descendientes (incluido PKHeX), cada 100 ms más inicio/fin de etapa. Incluye instrumentación, puede contar memoria compartida dos veces y omitir picos breves. CPU observada incluye el muestreador y no sirve para inferir consumo eléctrico. Arranque de proceso nuevo **no** significa caché de disco fría. El script importa componentes GUI Python a través de Team, pero no inicia Flutter.

| Juego | Seis cajas: generación/validación inicial | Pico RSS muestreado de toda la ejecución | Cambio de nivel en las seis cajas |
|---|---:|---:|---:|
| Escarlata/Púrpura | 0.320 s | 189.5 MiB | 0.033 s |
| Rojo Fuego/Verde Hoja | 0.249 s | 188.8 MiB | 0.011 s |
| Espada/Escudo | 0.290 s | 186.6 MiB | 0.018 s |

Validar otra vez sin cambiar configuración tardó ~0.1 ms: verifica el atajo de cache del modelo, **no** la latencia de cambiar caja en Flutter. No generalizar a especies difíciles, shiny/restricciones complejas o generaciones de encuentros que requieren búsqueda larga.

### UI nativa: observación independiente

Instancia aislada nativa en 800 × 480 útiles. Equipo con **tres** Pokémon legales de demo, sprites deshabilitados y sin radio; 10 segundos inmóvil. No comparar su máximo directamente como diferencia causal con las seis cajas del benchmark de modelo.

| Proceso | RSS durante observación |
|---|---:|
| Python | 62.2 MiB |
| PKHeX | 116.7 MiB |
| Flet/Flutter | 292.2 MiB |
| Lanzador macOS `open` | 5.7 MiB |
| **Suma** | **476.7 MiB** |

CPU prácticamente inactiva durante ese intervalo (Flet ~0.002% de un núcleo); no mide interacción ni generación. Se incluyó explícitamente el cliente asociado al puerto aislado 8596 para no perderlo si macOS lo reasigna a otro padre. No incluye OS, WindowServer, GPU compartida, escritorio, navegador ni procesos de otras apps. El modelo de Equipo y la UI no iniciaron intercambios ni firmware.

## Interpretación

- **No hay evidencia de que la app necesite 4–8 GB por sí sola.** Tampoco se certifica que 512 MB o 1 GB alcancen: falta Linux ARM64 + OS + sesión real + margen.
- Flet es el proceso más grande de esta observación. Una interfaz alternativa ligera puede ahorrar más que reducir simplemente controles o píxeles; todavía hay que implementar y medir ese ahorro.
- Un framebuffer 800×480 RGBA ocupa ~1.46 MiB; 320×240 RGB565 ~0.15 MiB. Cambiar resolución no elimina por sí solo cientos de MiB del runtime, catálogos o framework. Puede reducir renderizado/ancho de banda y costo del display.
- PKHeX sigue siendo el requisito central: .NET y sus tablas/datos. Cambiar la pantalla no convierte el stack actual en firmware para ESP32.
- No medimos máximo de RAM, p95 de latencia, desgaste/uso de swap, batería, temperatura sostenida, raids, sprites reales, UI con seis cajas, ni intercambio físico. No extrapolar tiempos Mac a Cortex-A53/A72.

## Arquitecturas a evaluar

| Alternativa | Se conserva | Cambia | Situación |
|---|---|---|---|
| Linux ARM64 + Flet + C6 | Prácticamente toda la app | Placa con menos RAM | Primer candidato de bajo esfuerzo; medir 1–2 GB antes de comprar |
| Linux ARM64 + UI ligera + C6 | PKHeX, modelos, validación, transporte | Renderizado y navegación, posiblemente display SPI | Mejor hipótesis para reducir costo autónomo; no implementado |
| Panel económico + servidor local | Motor en Mac/servidor, radio cerca de Switch | Protocolo cliente/servidor y recuperación de sesión | Puede abaratar el panel, pero deja de ser autónomo; pendiente de preferencia |
| Solo ESP32-C6 | Radio existente | Reescritura/reemplazo del motor y GUI | No puede ejecutar el stack Python/.NET actual |

La UI ligera podría mostrar una caja cada vez, contador 1/6, menús cortos por cruceta, sprite estático y páginas básicas/avanzadas. Se conservarían validación por caja, bloqueo de copias ilegales, excepción de devolución exacta del original, cancelación segura y perfiles. Renderizar bajo demanda evitaría animación continua. Explorar SDL/framebuffer o LVGL es una propuesta arquitectónica, no una decisión tomada ni garantía de rendimiento.

## Placas candidatas, no recomendaciones de compra todavía

- **Pi 4 de 1–2 GB:** candidato conservador para conservar Linux y el motor, con USB y DSI. La familia ofrece variantes de poca RAM; el mínimo de esta app aún no se conoce. [Fabricante](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/).
- **Pi Zero 2 W, 512 MB:** candidato agresivo para experimentar con UI ligera. CPU ARM64 Cortex-A53 1 GHz, memoria limitada; no prometer funcionamiento de Flet completo. Tiene USB OTG y **no DSI**, por lo que la pantalla DSI seleccionada no se conecta directamente; habría que considerar HDMI/SPI y adaptadores. [Fabricante](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/).
- **XIAO ESP32-C6:** 512 KB SRAM y 4 MB flash; se mantiene como radio. No equivale a una placa Linux de 512 MB. [Seeed](https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/).

Los precios base publicados no son cotizaciones finales en México. Comparar placa + pantalla + alimentación + microSD + USB/adaptadores + controles + refrigeración/carcasa y tiempo de adaptación. Como Pi 5 ya está comprada, terminar su preparación puede ser más económico que comprar otra placa para la primera unidad.

## Repetir las medidas

Con el motor compilado y venv preparado, desde el fork:

```sh
.venv/bin/python scripts/benchmark_portable.py --game sv --output /tmp/benchmark-sv.json
.venv/bin/python scripts/benchmark_portable.py --game frlg --output /tmp/benchmark-frlg.json
.venv/bin/python scripts/benchmark_portable.py --game swsh --output /tmp/benchmark-swsh.json
```

Si el apphost del SDK local lo necesita, definir `DOTNET_ROOT` como en la guía de compilación. El script sobrescribe únicamente el JSON indicado, elimina los Pokémon temporales y devuelve error si alguna caja no queda legal. No usa perfiles propios, no inicia sesión LDN. En un sandbox que no permita lectura de procesos no se puede medir; ejecutarlo en terminal local con permisos normales.

La observación UI de esta pasada se hizo aparte con harness temporal y procesos Flet nativos; el comando anterior **no reproduce ese escenario visual**. Para repetirlo: abrir una instancia demo aislada, poblar tres Pokémon legales sin sprites, observar durante 10 s la suma RSS de Python, helper y cliente, incluyendo el viewer aunque su padre sea LaunchServices. No comparar con otras cargas sin registrar pantalla, número de cajas, sprites, tiempo y procesos incluidos.

## Siguiente ensayo en Pi 5

1. Registrar OS/arquitectura, RAM, modelo, pantalla y versión exacta del código.
2. Ejecutar benchmark sin GUI y luego GUI con las seis cajas, sprites y menús. Repetir 10 veces cada carga tras calentamiento y registrar p50/p95, errores y picos.
3. Observar proceso completo **y** sistema: PSS en Linux, MemAvailable, swap, CPU, temperatura y eventos de throttling. Medir potencia con equipo externo si importa autonomía.
4. Ensayo de 30 minutos de edición y sesión real supervisada. Separar generación local de transporte; la Pi5 no simula la CPU de una Zero.
5. Ensayar límites de memoria en entorno aislado (p. ej. cgroups) para descartar presupuestos insuficientes. Un límite RAM/CPU en Pi5 o VM no reproduce latencia, GPU, I/O ni potencia de otra placa.
6. Solo después probar una placa candidata real.

Criterios propuestos, pendientes de acordar: cambio de caja <100 ms p95, respuesta de edición habitual <1 s p95, sin swap sostenido/crecimiento de memoria, sin desconexiones y al menos 25% de RAM disponible al pico de la carga prevista. No son resultados ya obtenidos en Pi.

## Evidencia

- [SV](specs/references/benchmarks/mac-sv-2026-11-13.json)
- [FRLG](specs/references/benchmarks/mac-frlg-2026-11-13.json)
- [SwSh](specs/references/benchmarks/mac-swsh-2026-11-13.json)
- [UI nativa en reposo](specs/references/benchmarks/mac-ui-idle-2026-11-13.json)
