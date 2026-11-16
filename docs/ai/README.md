---
title: Contexto de AI del fork portátil
nav_exclude: true
search_exclude: true
---
# Contexto para futuras iteraciones

Esta carpeta conserva los acuerdos del usuario para evitar redescubrir o desviar el proyecto. Es documentación de desarrollo del fork, no una descripción de funciones ya entregadas.

## Orden de lectura

- [Auditoría Rust / PKHeX AOT y portátil económico](../specs/021-rust-handheld-feasibility.md):
  registro histórico de la investigación autorizada el 2026-11-15. El trabajo activo
  continúa en el repositorio independiente `pokemon-handheld` (carpeta hermana local),
  en `docs/research/001-feasibility.md`. Este fork conserva Pi/Flet y sus correcciones.

- [Decisiones](decisions.md): hardware, alcance, experiencia de usuario y pendientes.
- [Contratos de UI](ui-contracts.md): comportamientos acordados y regresiones que los cambios posteriores deben preservar.
- [Desarrollo](development.md): componentes reales, comandos y criterios de validación.
- [Punto de pausa de la sesión](session-2026-11-12.md): avances, verificaciones y pendientes inmediatos.
- [Opciones por caja](../specs/006-portable-slot-options.md): reutilización de selectores, cachés y límites del filtro.
- [Especificación inicial](../specs/001-portable-interface.md): secuencia de implementación.
- [Arquitectura upstream](../architecture.md) y [guía GUI](../gui.md): comportamiento existente.

## Estado al 2026-11-12

Primer incremento de configuración portátil implementado: diagnóstico, claves, placa, progreso y logs. Entorno Mac preparado y PKHeX compilado; UI inspeccionada a 800 × 480. La demo es explícita y no toca hardware. Aún no se ha validado en Raspberry Pi ni flasheado un C6 real con estas vistas. La galería abre ahora Intercambios / Equipo: seis borradores, generación y validación reactiva, perfiles por juego y conexión al runner local. El intercambio físico sigue pendiente de prueba. Véase [spec 005](../specs/005-portable-trades.md). Véanse los comandos y límites en [desarrollo](development.md).

El repositorio de trabajo es `javleds/pokeldn`, derivado de `Decryptu/pokeldn`. El Git vacío del directorio padre fue retirado por petición del usuario; el fork y sus archivos permanecen intactos. La asociación visual de la conversación con un proyecto de Codex no cambia la raíz Git.

El punto de pausa conserva el cierre de la etapa de selectores. Después se implementó identificación con devolución opcional ([spec 007](../specs/007-trainer-return.md)) y, por petición expresa del usuario, las seis modalidades restantes: Evolución, Nivel, Naturaleza, EVs, Modificador y Validador ([spec 010](../specs/010-received-trade-modes.md)). Equipo permanece separado. Las nuevas modalidades tienen pruebas de registros/protocolos simulados y UI; su prueba física sigue pendiente.

## Cómo mantener este contexto

Pulido de interfaz, cabecera compartida, Equipo secuencial y auditoría visual: [spec 013](../specs/013-portable-ui-polish.md). El usuario considera funcionalmente satisfactoria la versión anterior; esta etapa se concentra en presentación y edición de cajas. [Galería de capturas](../specs/references/ui-polish/README.md).

Las decisiones expresas posteriores del usuario prevalecen sobre estos documentos. Al cambiar una, actualizar su estado y motivo en `decisions.md` y ajustar la especificación si corresponde. Registrar mediciones con hardware, versión, carga y método; no transformar estimaciones en requisitos comprobados.

No registrar claves, rutas personales innecesarias o transcripciones completas. Mantener aquí acuerdos y evidencia útil; el detalle funcional upstream permanece en su documentación original.

Leyendas Z-A incorporado a la galería y a los adaptadores portátiles de devolución: [spec 011](../specs/011-portable-za.md). Su validación contempla marcas Plus Move; una modificación de nivel ilegal no se repara cambiando movimientos de forma silenciosa. Prueba física pendiente.

## Compilación portátil e identidad

[Guía Mac / Raspberry Pi 5](../portable-build.md): compilación PKHeX, ejecución nativa, dependencias, rutas de datos, acceso Linux y límites del empaquetado. [Spec 016](../specs/016-portable-icon-build-guide.md). Ícono propio en `gui/assets/portable/icon.png`; aplicado al paquete con `./scripts/build_portable.sh --app` ([spec 020](../specs/020-portable-app-package.md)); el arranque desde fuente conserva el cliente de desarrollo. Pi pendiente de comprobación física.

Compilación habitual tras preparar el entorno: `./scripts/build_portable.sh` ([spec 017](../specs/017-portable-build-command.md)); resuelve directorio y SDK local automáticamente.
Arranque habitual: `./scripts/run_portable.sh` ([spec 018](../specs/018-portable-run-command.md)); no necesita exports y conserva los datos locales existentes.

[Benchmark y opciones de hardware económico](../portable-benchmark.md): primeras mediciones Mac, script aislado y criterios para Pi. Son resultados piloto, no certificación de placa/RAM mínima ni aprobación de reescritura de UI.

## Validación física inicial (2026-11-16)
El usuario completó pruebas en Pi 5 con S3, cooler oficial y monitor HDMI en
FR/LG, Let's Go y Z-A: ~1.1 GB de RAM reportados (campo no identificado),
temperatura observada ≤53 °C. No es validación de todos los roles/modalidades ni
de DSI. Evidencia y límites: [spec 026](../specs/026-pi-first-hardware-validation.md).
Errores del cliente Flutter/GTK al cerrar se investigan por separado.
