---
title: Contexto de AI del fork portátil
nav_exclude: true
search_exclude: true
---
# Contexto para futuras iteraciones

Esta carpeta conserva los acuerdos del usuario para evitar redescubrir o desviar el proyecto. Es documentación de desarrollo del fork, no una descripción de funciones ya entregadas.

## Orden de lectura

- [Decisiones](decisions.md): hardware, alcance, experiencia de usuario y pendientes.
- [Desarrollo](development.md): componentes reales, comandos y criterios de validación.
- [Punto de pausa de la sesión](session-2026-11-12.md): avances, verificaciones y pendientes inmediatos.
- [Opciones por caja](../specs/006-portable-slot-options.md): reutilización de selectores, cachés y límites del filtro.
- [Especificación inicial](../specs/001-portable-interface.md): secuencia de implementación.
- [Arquitectura upstream](../architecture.md) y [guía GUI](../gui.md): comportamiento existente.

## Estado al 2026-11-12

Primer incremento de configuración portátil implementado: diagnóstico, claves, placa, progreso y logs. Entorno Mac preparado y PKHeX compilado; UI inspeccionada a 800 × 480. La demo es explícita y no toca hardware. Aún no se ha validado en Raspberry Pi ni flasheado un C6 real con estas vistas. La galería abre ahora Intercambios / Equipo: seis borradores, generación y validación reactiva, perfiles por juego y conexión al runner local. El intercambio físico sigue pendiente de prueba. Véase [spec 005](../specs/005-portable-trades.md). Véanse los comandos y límites en [desarrollo](development.md).

El repositorio de trabajo es `javleds/pokeldn`, derivado de `Decryptu/pokeldn`. El Git vacío del directorio padre fue retirado por petición del usuario; el fork y sus archivos permanecen intactos. La asociación visual de la conversación con un proyecto de Codex no cambia la raíz Git.

El punto de pausa conserva el cierre de la etapa de selectores. Después, el usuario autorizó identificar entrenador con devolución opcional del original: implementado mediante trade-back y una vista de recepción/devolución, documentado en [spec 007](../specs/007-trainer-return.md). No activa las otras modalidades. La prueba física sigue pendiente.

## Cómo mantener este contexto

Las decisiones expresas posteriores del usuario prevalecen sobre estos documentos. Al cambiar una, actualizar su estado y motivo en `decisions.md` y ajustar la especificación si corresponde. Registrar mediciones con hardware, versión, carga y método; no transformar estimaciones en requisitos comprobados.

No registrar claves, rutas personales innecesarias o transcripciones completas. Mantener aquí acuerdos y evidencia útil; el detalle funcional upstream permanece en su documentación original.
