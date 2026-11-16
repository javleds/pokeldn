# Portátil económico: auditoría y plan de viabilidad Rust / PKHeX AOT

Fecha: 2026-11-15. Estado: investigación; ninguna migración de producción implementada.

> Registro histórico cerrado al separar los proyectos el 2026-11-15. La investigación
> y el plan activo continúan en el repositorio independiente `pokemon-handheld`, en
> `docs/research/001-feasibility.md`. En la disposición local acordada está en
> `../pokemon-handheld` respecto a la raíz de este fork. Consultar allí para trabajo
> nuevo; este documento conserva la evidencia inicial y no se sincroniza automáticamente.

## Contexto y objetivo

El usuario propone un dispositivo autónomo de menos de $1,000 MXN en componentes,
alimentación y carcasa. El prototipo Pi 5 se conserva como referencia funcional.
El resumen actualizado reporta aproximadamente $13,000 MXN sin carcasa (antes se
habló de aproximadamente $12,000). No son cotizaciones comparables de fabricación.

Dirección acordada: host principalmente Rust, PKHeX.Core C# como fuente de reglas,
host Linux ARM64 candidato y ESP32-S3 como radio. Una pantalla pequeña, cruceta y
botones sustituyen la UI táctil; un Pokémon por operación. La autonomía excluye
depender de un teléfono/PC. No se acepta un catálogo pregenerado como motor final.

## Alcance y fuera de alcance

Auditar el código, definir límites de portabilidad, contrato y pruebas, y establecer
un proceso para seleccionar hardware. Siete familias: FRLG, LGPE, SwSh, BDSP, PLA,
SV y ZA; soporte por juego/rol/consola debe demostrarse. Raids, GTS, automatización
de botones y edición de partidas no son funciones objetivo iniciales.

Esta auditoría no crea un repositorio nuevo ni sustituye el fork Flet. No compra
hardware, no ejecuta intercambios, no modifica firmware ni distribuye claves.

## Evidencia y procedencia

- Fork auditado: `66995b5a8a3dbc971fd6b9a32fad7e5f08210fca`.
- Paquete NuGet PKHeX.Core `26.10.18`; SHA-256 del nupkg:
  `ec4344a49d90da826d23b21613bbb91f1aeb6e2e173ca6bf2f51567a5858d5e4`.
- Fuente upstream inspeccionada: [tag 26.10.18](https://github.com/kwsch/PKHeX/tree/26.10.18).
  Archivo descargado SHA-256 `ae07dc48ddbc2d982ad3d69bb28a39285e7cccc4f3753f1e528828fb5a583ddd`.
  El nuspec declara revisión `261019055404`, que no se trata como SHA Git verificado.
  Coincidir en versión no prueba identidad reproducible entre fuente y DLL.
- SDK local .NET `10.0.404`, runtime `10.0.15`, destino `osx-arm64`.
- Publicación AOT del helper existente sin modificar fuentes: exit 0;
  ejecutable de 25,984,304 bytes (24.78 MiB), sin contar símbolos.
  SHA-256 `23e983d8dac552dfac5f133496ec2c290526e5bdec2a1646535c6c2ca0aba2de`.
- `test_pokemon_service.py`: **205 passed en 2.99 s** con override AOT.
- `test_received_edits.py test_portable_received.py test_bank.py`:
  **102 passed en 1.00 s** con override AOT.
  Estas suites combinan integración con el helper real y casos simulados; no son
  307 pruebas físicas ni un certificado exhaustivo de todas las rutas PKHeX.
- No se midió RAM AOT, energía, Linux ARM64, S3 físico ni Switch 2 en esta auditoría.

La estimación de 1 GB del resumen no es un mínimo demostrado. El
[benchmark anterior](../portable-benchmark.md) documenta ~187–190 MiB de Python
y helper en cargas de modelo, y una observación separada de 116.7 MiB para PKHeX
en Mac. Ni esas cifras ni el tamaño del binario establecen RAM mínima en Linux.

## Ruta actual y mapa de portabilidad

`pokeldn/app/catalog.py:270` selecciona herramientas; `command.py:184,324` arma
argumentos/prepara ofertas; `runner.py:89` inicia el launcher y coordina eventos.
Los archivos `bin/*` contienen orquestación sustantiva: portar sólo carpetas de juego
perdería comportamiento. `pokeldn/ldn/api.py` delega descubrimiento/asociación al
LDN vendorizado, que debe formar parte del análisis y corpus Rust.

| Capa | Fuente actual | Acción propuesta |
|---|---|---|
| Coordinación | `app/runner.py`, `app/command.py`, launchers | Eventos tipados; sin parsing de logs para dominio |
| Radio | `ldn/esp32.py`, firmware `main/wire.c`, `radio.c` | Portar cliente, conservar firmware/versiones |
| WLAN / autenticación LDN | `ldn/esp32_wlan.py`, `vendor/LDN/ldn` | Preservar EtherType 0x88B7 y separación management/data |
| IP de usuario | `ldn/userspace_ip.py` | ARP, IPv4, UDP, fragmentación/reensamblado con límites |
| Pia | `ldn/crypto.py`, `pia3/4/5/6.py`, `host_pia.py`, `reliable*.py` | Codecs por variante, timers, ACK, ventanas y seguridad |
| Sesión de juego | `pokeldn/<game>`, `bin/` | Adaptadores propios con estados observables |
| Entrenador / devolución | `console_trainer.py`, `trade_back.py`, `portable_return.py` | Procedencia del perfil y journal de devolución |
| Preparación | `pokemon.py`, `services/pkhex/Program.cs` | Conservar lógica C# del helper, sustituir cliente Python |

`requirements.txt` mezcla dependencias de todos los modos. Migrar contratos de
pyserial, Trio, criptografía y Zstd; no arrastrar Flet, websockets/GTS, BLE,
psutil ni Unicorn como requisito del intercambio USB. Separar alcance por
comportamiento, no copiar indiscriminadamente todos los imports.

El helper C# tampoco es sólo un proxy: `Program.cs:130,488` selecciona encuentros,
aplica restricciones y busca resultados. En upstream, `Legality/LegalityAnalysis.cs:109`
coordina verificadores, origen y encuentros. Ambos niveles deben conservarse.

## Contrato radio y red

Referencia: `pokeldn/ldn/esp32.py:140`, `firmware/esp32/main/wire.h`, `wire.c`.
Frame = COBS(tipo u8 + payload + CRC32 ISO-HDLC little-endian) + delimitador 00.
CRC cubre tipo/payload; payload máximo 1600 bytes. Acotar también bytes recibidos
sin delimitador: el parser Python actual no es un modelo de límites a copiar.

HELLO 01 / INFO 81 negocia protocolo 1, MAC STA/AP, revisión e identificación firmware.
HELLO resetea contadores; no hacerlo arbitrariamente con datos en vuelo. RESULT 82
contiene comando e `esp_err_t` i32 LE, sin ID general: serializar solicitudes y
rechazar respuestas obsoletas. CHANNEL/STA_JOIN/AP_START/STOP/ETH_TX/RAW_TX/STATUS/ALIVE
y eventos LINK/RX/STA_JOINED/STA_LEFT son el contrato mínimo a preservar.

Ventana host: 8192 **bytes codificados**, crédito acumulado u32; CREDIT se emite
cada 1024 bytes e idle. Probar wrap, crédito que llega durante write, crédito viejo,
frame parcial, pérdidas y silencio. Write timeout 1 s; STATUS tras 1 s sin frame
válido; enlace termina tras 3 s sin respuesta; ALIVE cada 1 s y watchdog firmware
5 s cuando está armado. Estos valores pertenecen a la versión auditada.
TX_DONE confirma ACK radio, nunca un trade.

S3 usa USB Serial/JTAG (`wire.c:7`); cambiar baud no cambia su velocidad USB.
Host actual limita cola TX a 512; firmware cola 384 y protege heap restante.
Rust necesita backpressure, métricas de drops y cancelación, no colas ilimitadas.

Conservar particularidad S3 de broadcasts CCMP ya descifrados con cabecera/bit
Protected aún presentes (`esp32_wlan.py:175`). El firmware no ofrece control
arbitrario de Wi-Fi: existen restricciones de asociación/raw TX y beacons stock.
`gift_ldn.c`/`gift_pia.c` son offloads específicos de regalos, no un motor autónomo
general de siete juegos. Las cifras de memoria de esos offloads no dimensionan éste.

## Matriz de juegos y protocolo

LDN requiere su propio corpus criptográfico, además de Pia. En
`vendor/LDN/ldn/__init__.py:178` se derivan claves con AES y SHA-256; advertisements
admiten formatos plain/CTR/GCM; challenges validan HMAC-SHA256 (`:634,699`) y
autenticación GCM (`:796`). `connect/create_network` (`:1936,1968`) generan aleatorios
y configuran claves WLAN. `wlan.py:851,878` implementa CCMP con AES-CCM. Probar
rechazo de autenticación, tamaños, nonce/contador y claves sintéticas por variante;
no copiar secretos a vectores. La elección del backend ESP32 sustituye operaciones
WLAN, no elimina estas responsabilidades del host.

Existe también `pokeldn/ldn/ldnrs.py` y `tests/test_ldnrs.py`, con vectores de
protocolo de daemon ldnrs 0.0.3. Es una referencia adicional de interoperabilidad;
no se auditó el repositorio externo ldnrs ni se afirma que sustituya el host S3/Pia.

| Familia | Launchers en `bin/` (sin extensión) | Base observada / diferencia |
|---|---|---|
| FRLG | `frlg_trade_host`, `frlg_trade_join` | Pia moderno `crypto/host_pia/reliable`, enlace GBA/RFU y bloques sincronizados |
| LGPE | `lgpe_host`, `lgpe_join` | Pia3 wire v3, reliability/mesh/station y mensajes alineados propios |
| SwSh | `swsh_host`, `swsh_connect` | Pia4 wire v4, tag GCM 16 bytes, broadcast/mesh |
| BDSP | `bdsp_host`, `bdsp_join` | Pia5 **wire v9**, header 32 bytes, variable IDs, room/session |
| PLA | `pla_host`, `pla_join` | Pia6 **wire v11**, header 28 bytes, reliable5, data exchange/trade box |
| SV | `sv_host`, `sv_join` | Pia6/reliable5, port2/streams/game channel; excluir union circle de alcance inicial |
| ZA | `za_host`, `za_join` | Pia moderno, streams y rondas de preview/pick/confirm |

Nombres de archivo Pia no equivalen a versión wire. `crypto.py` incluye AES-ECB
para derivación, AES-GCM con tag 8 bytes y Zstd con normalización de encabezado;
otras variantes cambian tag, IV, padding y footer autenticado. Elegir librerías Rust
contra vectores y requisitos concretos. Nonces, wrapping, endian, ventana de recepción
y retransmisiones requieren pruebas con reloj simulado y paquetes perdidos/reordenados.

Identificación de entrenador: FRLG usa LinkPlayer; en otros casos se combina evidencia
de sesión y registro. `console_trainer.py` comprueba propiedad, handler y versión.
OT de un Pokémon ajeno no identifica necesariamente al usuario de la consola.
TID/SID internos de 16 bits no son los números de presentación de Switch.

## Decisiones técnicas propuestas

Conservar al principio el helper como proceso local persistente, JSON por stdin/stdout,
una solicitud activa y cola acotada. Rust conserva el control de radio, sesión y UI.
El helper nunca participa en el procesamiento de cada paquete de radio. Preparar
la oferta antes de conectar; editar recibidos en una tarea separada mientras siguen
heartbeat, retransmisiones y cancelación. Un fallo del helper no debe matar el transporte.

Reutilizar primero el firmware S3 por USB nativo. UART requiere una evaluación y
adaptación explícitas, no cambiar solamente el dispositivo serial del host.

No introducir una FFI al inicio: el proceso mantiene aislamiento, permite finalizar
una operación bloqueada y conserva el contrato comprobado. La biblioteca iOS en
`services/pkhex/Library.cs` y `examples/ios/build.py` demuestra otra forma de integración,
pero comparte Console global y no es una API reentrante lista para múltiples instancias.

## Contrato Rust–PKHeX propuesto

El helper actual usa `cmd`, `game`, JSON por línea, bytes base64 y `ok/error`.
No tiene handshake de capacidades ni versión del protocolo. Añadir un adaptador
versionado; conservar el contrato interno existente mientras se migra.

| Operación | Ruta existente | Resultado requerido |
|---|---|---|
| `hello` | Nueva | Versión de esquema/helper/PKHeX, juegos, operaciones, hash de build |
| Catálogos | `species`, `names`, `options`, `encounters`, `move_options` | IDs estables, etiquetas localizadas, restricciones y candidatos |
| Generar | `make` | Registro, formato, identidad, análisis y opciones efectivamente satisfechas |
| Inspeccionar | `owner`, `edit_received` sin cambios | Identidad y campos, sin convertir lectura en autorización |
| Validar | `check` | Análisis completo/incompleto, validez estricta y aceptación de política separadas |
| Editar copia | `edit_received` | Copia e informe; original conserva bytes exactos |
| Convertir | `convert` / `move` | Ruta compatible explícita, registro e informe; rechazar rutas incompatibles |

Separar semánticamente `validate` de `prepare_offer`: el `check` actual puede editar
campos, refrescar PID/estadísticas/checksum y serializar. Sus bytes de salida no
reemplazan el original destinado a devolución exacta, aunque el análisis sea válido.

Propuesta de envelope: `schema_version`, `request_id`, `operation`, `game`, `payload`.
Respuesta: mismo ID, estado de operación, datos o código de error estable; diagnóstico
humano separado. Una operación correctamente ejecutada puede producir un Pokémon
ilegal: `ok` no significa legalidad. Incluir `analysis_complete`, `pkhex_valid`,
`policy_accepted`, `policy_id` y advertencias de HOME. No analizar texto traducido
para decidir si se autoriza enviar.

Registros simples: límite actual 768 bytes, verificar tamaño real por formato antes
de enviar. Acotar por operación el JSON/base64 y las respuestas de catálogos; no
usar el límite del registro para un catálogo. El bridge no acepta rutas arbitrarias
ni controla el almacenamiento del host. Declarar tipo de representación: registro
PKM, party/stored, cifrado/descifrado y oferta de protocolo son cosas diferentes.

Deadline y cancelación para **todas** las operaciones, con lectura asíncrona,
límites de salida y stderr separado. Hoy `_exchange` en `pokeldn/pokemon.py` sólo
lanza hilo para `check`; otras llamadas bloquean en `readline` antes del timeout.
Tras timeout, terminar/reiniciar helper e invalidar petición; nunca reintentar
automáticamente un intercambio. Identificar respuestas con revisión de edición
y sesión para descartar resultados tardíos. No persistir datos privados en logs.

## Native AOT: alcance real y pendientes

La publicación funciona en Mac y las pruebas anteriores pasan. Linux ARM64 es
destino soportado por .NET, pero no fue publicado ni probado aquí. El ESP32-S3
Xtensa no es destino Native AOT: la arquitectura de dos placas evita esa barrera.
Native AOT incluye runtime reducido y GC; no elimina la necesidad de RAM del motor.

La compilación con advertencias visibles señala:

1. JSON genérico y `Deserialize` en el helper: IL2026/IL3050. Sustituir rutas por
   nodos/tipos explícitos o generación de contexto, con tests de roundtrip.
2. Reflexión de `EncountersWC3` y `Encounters9`: existen `DynamicDependency`, pero
   aún hay diagnósticos. Preservar campos requeridos y probar acceso tras trimming.
3. `EntityConverter.ConvertToType` alcanza una ruta de conversión incompatible por
   `TransferPropertiesWithReflection`. En fuente, ésta está condicionada por
   `AllowIncompatibleConversion`; excluirla explícitamente del contrato y probar
   las conversiones admitidas. No confundir el warning con fallo de toda conversión.
4. Batch editing / ReflectUtil: IL2046, IL2070, IL2111. Delimitar alcanzabilidad;
   no silenciar globalmente para considerar el build seguro.
5. Tres `PrintMembers` de bloques de guardado Gen3 se anuncian como métodos que
   siempre lanzarían excepción. No se activaron en las suites; investigar por separado
   si esos tipos participan en una operación que se conserve.

`PKHeX.Core` contiene recursos embebidos, tablas estáticas y cachés. Retirar el
endpoint de raids no permite retirar indiscriminadamente encuentros raid necesarios
para validar Pokémon. Un build con funciones seleccionadas debe preservar todas las
reglas de los registros soportados. No se propone extraer reglas declarativas como
reemplazo de los algoritmos upstream.

Fuentes de plataforma: [Native AOT](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/)
y [compilación cruzada](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/cross-compile).
Publicar Linux desde Linux; Mac ARM64 no certifica compatibilidad de libc/kernel/CPU Linux.

## Estrategia de benchmarks y selección de hardware

Comparar sobre el mismo corpus, versión y destino: build actual .NET, AOT helper
completo y AOT con operaciones seleccionadas. Medir primero helper solo y después
host Rust + UI + helper + sesión. El harness `scripts/benchmark_portable.py` actual
carga Team/Flet Python y seis cajas: sirve de referencia, no aísla el costo futuro.

| Carga | Qué revela |
|---|---|
| Arranque hasta primera respuesta, luego inactividad | Costo de proceso/runtime y residencia basal |
| Primer catálogo por juego y catálogos repetidos | Inicialización y crecimiento de cachés |
| Generación simple y restricciones difíciles | Búsqueda, latencia extrema y picos |
| Pokémon legal, corrupto, ilegal y análisis incompleto | Errores y comportamiento bajo carga adversa |
| Lectura/edición/devolución en los siete formatos | Preservación de identidad y reglas específicas |
| Conversiones permitidas y rechazadas | Dependencias cruzadas y rutas AOT |
| Cambiar entre siete juegos sin reiniciar | Acumulación de tablas y cachés |
| Sesión activa mientras se valida/edita | Cumplimiento de plazos del protocolo |
| Reinicio helper / cancelación / almacenamiento lleno | Recuperación y estados pendientes |

Linux: RSS, PSS, VmHWM, `memory.peak` de cgroup para conjunto, MemAvailable,
swap/OOM, fallos de página, tiempo CPU, latencias p50/p95/máximo, tamaño de binario,
recursos y símbolos por separado. Muestreo complementado con máximos del kernel;
100 ms puede omitir picos. Separar arranque de proceso de caché de disco fría.
Repetir al menos 30 arranques/casos y una sesión de 30 minutos; registrar semillas
cuando existan, CPU/OS/ABI, builds, workload y errores. Aleatoriedad de generación
impide exigir igualdad binaria de dos ejecuciones: comparar invariantes y legalidad.

Ensayar límites de 128/256/512 MiB con swap deshabilitada, primero como descarte
en cgroups. Un límite de proceso no incluye automáticamente el costo del sistema
ni reproduce CPU, radio o alimentación de una placa más débil. No declarar capacidad
suficiente hasta medir imagen Linux final en hardware real.

Criterios propuestos: cero OOM y cero intercambio incorrecto, memoria sin crecimiento
no acotado, heartbeat sin pérdidas atribuibles a generación, margen de RAM del sistema
de al menos 25% bajo carga máxima ensayada, navegación p95 <100 ms. Acordar latencia
de generación normal/difícil antes de convertirla en requisito de compra. Medir W
en reposo, navegación, generación e intercambio; Wh útiles y eficiencia antes de
elegir batería. No inferir autonomía sólo de mAh.

La BOM debe incluir host, RAM/almacenamiento, S3, pantalla, controles, batería,
carga/protección/regulación, conectores, PCB, carcasa, impuestos/envío prorrateado
y margen de materiales. Registrar cantidades y fecha: precio por volumen no es
precio de una unidad. Presupuesto de host = $1,000 menos el resto de la BOM y margen.
Rechazar placa sin Linux/ABI utilizable, USB host real, interfaces de pantalla/controles,
soporte de arranque/almacenamiento y recursos medidos. No hay selección ni cotización
de placa demostrada en esta auditoría; 128–256 MB sigue siendo hipótesis.

## Actualizaciones

Mantener versión y hash de NuGet fijados; una detección automática abre un candidato,
no actualiza dispositivos directamente. Pipeline: descargar/verificar procedencia,
compilar .NET y AOT Linux ARM64, revisar nuevos diagnósticos, ejecutar corpus diferencial,
tests de transporte y paquete, probar dispositivo canario y aprobar promoción.

En un mismo PKHeX, exigir equivalencia semántica JIT/AOT con corpus fijo. Entre
versiones, cambios de legalidad pueden ser correcciones legítimas: generar informe
de diferencias esperado/aprobado; no exigir ciegamente resultados idénticos ni
aprobar toda diferencia. Mantener casos por encuentro, formato y error, incluidas
excepciones HOME y ZA Plus Move.

Manifiesto versionado y firmado: arquitectura, ABI mínima, hashes, versión puente,
PKHeX, firmware compatible, esquema de datos. Descargar/verificar en staging,
activar atómicamente fuera de sesión/flash, conservar paquete anterior y rollback
ante fallo de healthcheck. Corte de energía y almacenamiento insuficiente deben
preservar la versión utilizable. Actualización sin conexión mediante paquete local
y actualización conectada comparten verificación. Red es necesaria para obtener
novedades, no para efectuar intercambios una vez preparados los recursos.

## Plan de implementación y validación por etapa

| Paso | Módulos / cambio | Dependencia | Evidencia para avanzar |
|---|---|---|---|
| 1. Congelar oráculo | Contratos, corpus sintético y manifest de versiones | Esta auditoría | Vectores regenerables desde Python, sin claves privadas |
| 2. Endurecer bridge | `services/pkhex`, futuro `pkhex-client` | Contrato versionado | JIT/AOT equivalentes en corpus; timeout/error/reinicio; diagnóstico AOT clasificado |
| 3. Medir motor | Harness helper aislado + Linux ARM64 | Build comparable | CSV/JSON con latencia, RAM, errores y límites 128/256/512; decisión continuar/revisar alcance |
| 4. Transporte Rust | `radio-transport` + red usuario | Corpus radio | Codecs idénticos, simulador con fallos, HELLO/STATUS/STOP y soak S3 real |
| 5. LDN/Pia FRLG | Autenticación, crypto, reliable, enlace GBA | Transporte aprobado | Vectores, fake clock, reordenamiento/pérdidas, sesión host real |
| 6. Primer flujo completo | FRLG host y después join, bridge, perfil y journal | 2 y 5 | Generar, validar, intercambiar, identificar y devolver original; cancelación sin falsa confirmación |
| 7. Extender juegos | ZA; PLA/SV; BDSP; SwSh; LGPE | Núcleo estable | Cada juego/rol: codecs, simulación, sesión física, edición/devolución y regresión anteriores |
| 8. UI / host candidato | Formulario por pasos, botones, almacenamiento | Recursos medidos | Prototipo resolución real, input sin bloquear radio, benchmark sistema completo |
| 9. Dispositivo | Imagen Linux, paquete, alimentación y carcasa | BOM y placa comprobadas | Actualización/corte de energía/rollback, autonomía medida, BOM final y matriz interoperabilidad |

FRLG es la prioridad indicada por el usuario, no se presenta como el protocolo más
sencillo. Orden posterior por reutilización técnica propuesto, modificable por
disponibilidad de consolas/juegos. No crear siete crates vacíos ni construir UI
definitiva antes de probar generación y trade. El primer slice puede consumir un
archivo preparado por PKHeX, pero el siguiente debe integrar el motor original.

Corpus y oráculos existentes:

- `tests/test_esp32.py`, `test_esp32_soak.py`: COBS/CRC, crédito, partial write,
  silencio, watchdog, ARP/UDP y reensamblado. `esp32_sim` permite fallos reproducibles.
- `test_pia4.py`, `test_pia5.py`, `test_pia6.py`, `test_pia_bundled.py` y
  `tests/data/pia_bundled_packets.json`: variantes y framing; preservar bytes cero válidos.
- `test_host_pia.py`, `test_pia_host_session.py`, `test_host_hole_guard.py`,
  `test_reliable5.py`: retransmisión y ventana sin producir datos fuera de capacidad.
- `test_trade_back.py`, `test_trade_back_*_join.py`, `test_portable_return.py`:
  original inmutable, autorización de copia, sesión/participante y doble confirmación.
- `test_console_trainer.py`: procedencia de perfil; no aceptar OT ajeno.
- `test_pokemon_service.py`, `test_received_edits.py`, `test_bank.py`: generación,
  formato, legalidad y conversiones. Casos de banco ayudan a verificar motor aunque
  la UI de banco completa quede fuera del alcance inicial.

Rust: `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test`
y corpus diferencial, una vez exista el workspace. Fuzzing acotado de parsers,
límites y payload malformado; sanitización de fixtures y claves sintéticas. Las
pruebas existentes son material de referencia, no pruebas Rust ya implementadas.

## Reproducción AOT de esta auditoría

Desde la raíz con SDK .NET 10 disponible (usar `DOTNET_ROOT`/PATH locales según
`docs/portable-build.md`):

```sh
dotnet publish services/pkhex/pkhex.csproj -c Release -r osx-arm64 \
  --artifacts-path /tmp/pokeldn-aot-audit/artifacts \
  -o /tmp/pokeldn-aot-audit/publish \
  -p:PublishAot=true -p:PublishSingleFile=false \
  -p:EnableCompressionInSingleFile=false \
  -p:SuppressTrimAnalysisWarnings=false -p:TrimmerSingleWarn=false

POKELDN_PKHEX=/tmp/pokeldn-aot-audit/publish/pokeldn-pkhex \
  .venv/bin/python -m pytest tests/test_pokemon_service.py -q -W error

POKELDN_PKHEX=/tmp/pokeldn-aot-audit/publish/pokeldn-pkhex \
  .venv/bin/python -m pytest tests/test_received_edits.py \
  tests/test_portable_received.py tests/test_bank.py -q -W error
```

Las fixtures aíslan archivos temporales. No usar `-warnaserror` en la primera
auditoría de diagnósticos: primero registrar y clasificar; después establecer
baseline revisado y bloquear nuevos warnings. Logs sanitizados en
`references/aot-audit-2026-11-15/`. No son evidencia de Linux ni benchmark comparativo.

## Backend, frontend, persistencia y permisos

Backend propuesto: máquina de estados Rust independiente de pantalla, actor dueño
de radio, puente PKHeX y adaptadores por juego. Evitar un crate por archivo o imponer
Pia a protocolos que no lo usan. Comenzar con pocos módulos y extraer límites estables.

Frontend propuesto: selección de juego, entrenador, formulario de un Pokémon por
pasos, revisión y sesión. Cruceta/aceptar/volver; edición de OT/apodo y códigos requiere
prototipo real a resolución candidata. 128×64 no está aprobado como suficiente.

Persistencia: configuración y perfiles separados por juego, borrador versionado,
original recibido inmutable, journal de devolución pendiente, escrituras atómicas.
Una reconexión no autoriza reenviar un original a otro participante. Usuario puede
cancelar sin que el programa declare devuelto algo no confirmado.

Permisos: claves locales provistas por usuario, nunca fixtures/versionado/paquetes;
acceso serial restringido, sin root para operación normal cuando el OS lo permita.
Revisar licencias y procedencia antes de redistribuir. El nuspec inspeccionado declara
GPL-3.0-or-later; esto registra metadatos, no resuelve el análisis de distribución.

## Componentes afectados y estrategia de commits

Esta entrega modifica sólo esta spec y `docs/ai/` para preservar las decisiones.
Implementación futura: módulos Rust, bridge C#, harness de benchmarks, fixtures
sintéticos y CI; repositorio/destino del nuevo producto pendiente de acordar.

Commits propuestos: (1) contratos y corpus; (2) bridge AOT/diagnósticos; (3) benchmark;
(4) transporte Rust; (5) primer juego; (6) adaptadores siguientes uno por uno;
(7) UI y paquetes; (8) despliegue hardware. Cada incremento debe mantener un camino
funcional y pruebas ejecutables. No se realizan commits automáticamente en esta auditoría.

## Preguntas abiertas y condición de cierre

Faltan: placa/imagen Linux, RAM real, autonomía objetivo, pantalla, latencias aceptables,
roles por juego y consolas/versiones de software físicas disponibles. La compatibilidad
Switch 2 es objetivo pendiente, no consecuencia automática de compartir protocolos.

La auditoría se considera base para ejecutar pruebas de viabilidad; el producto sólo
es viable cuando pasa interoperabilidad por juego/rol, benchmark del sistema final,
actualización/rollback y BOM completa inferior a $1,000 MXN. Aprobar compilación Rust
o AOT por separado no satisface ese criterio.
