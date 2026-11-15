# Medición de recursos y hardware económico

## Contexto
El usuario recibió Pi 5 pero aún no tiene fuente/SD/teclado. Quiere explorar menor costo y UI sencilla.
## Objetivo
Medir prototipo real antes de recomendar RAM/placa mínima.
## Alcance
Benchmark local repetible del modelo Equipo, PKHeX, seis cajas, cache y ediciones. Propuesta de arquitectura y límites.
## Fuera de alcance
Cambiar UI aprobada, comprar hardware, certificar Pi sin medir, intercambios/firmware y raids.
## Comportamiento esperado
Datos temporales; métricas JSON con tiempo, RSS muestreado y CPU acumulada observada por etapa. Legalidad real, sin radio.
## Decisiones técnicas
Python y psutil existentes; muestrear proceso de benchmark y descendientes cada 100 ms. Modelo Team real y Service propio. RSS suma memoria compartida; no equivale a RAM mínima. No incluye Flutter ni OS. Comparar cold proceso vs warm; no afirmar caché de disco fría.
## Componentes afectados
Nuevo script benchmark y reporte.
## Backend
Solo reutilizar APIs existentes.
## Frontend
No rediseñar en esta etapa.
## Persistencia
TemporaryDirectory y POKELDN_DATA antes de imports; no datos personales.
## API
Sin cambios.
## Validaciones
Registrar estados legales; si hay error no presentarlo como generación exitosa.
## Permisos y seguridad
No start/trade, no claves, no puerto serie; resultados agregados sin Pokémon/personales.
## Casos límite
Helper ausente, acceso a procesos restringido, fallos de generación, variación RNG/OS.
## Estrategia de pruebas
Ejecutar piloto real; verificar JSON, limpieza y métricas. Script no sustituye pruebas de UI.
## Estrategia de validación
Baseline Mac y limitación explícita; repetir en Linux ARM64 para decisión real.
## Estrategia de commits
Benchmark y reporte sin commit automático.
## Archivos estimados a modificar
scripts/benchmark_portable.py, docs/portable-benchmark.md, docs/ai.
## Riesgos
Muestras omiten picos breves, CPU de procesos cortos puede omitirse; hardware diferente no extrapolable.
## Preguntas abiertas
Dispositivo autónomo o servidor local; no bloquear medidas comunes.
## Plan de implementación
1. Medir imports/catálogos/seis cajas/cache/ediciones sin render.
2. Observar memoria de UI abierta si es posible sin tocar sesiones.
3. Documentar resultados, candidatos y criterios de aceptación para Pi.

## Resultado
Benchmark real ejecutado secuencialmente para SV/FRLG/SwSh; todas las cajas legales y JSON agregados guardados. Muestreo 100 ms; primer intento de 20 ms descartado por sobrecosto observado de enumerar procesos en macOS. UI demo nativa observada 10 s con tres cajas y sin sprites, cerrada después sin trades. Script compila con py_compile, git diff --check limpio. Informe y cifras en docs/portable-benchmark.md. No se modificó la GUI ni se certificó hardware mínimo. CPU del harness no se interpreta como consumo del producto en reposo.
