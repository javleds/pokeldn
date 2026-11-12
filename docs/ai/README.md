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
- [Especificación inicial](../specs/001-portable-interface.md): secuencia de implementación.
- [Arquitectura upstream](../architecture.md) y [guía GUI](../gui.md): comportamiento existente.

## Estado al 2026-11-12

Primer incremento de configuración portátil implementado: diagnóstico, claves, placa, progreso y logs. Entorno Mac preparado y PKHeX compilado; UI inspeccionada a 800 × 480. La demo es explícita y no toca hardware. Aún no se ha validado en Raspberry Pi ni flasheado un C6 real con estas vistas. Banco, generación e intercambios con la nueva UI son la siguiente etapa. Véanse los comandos y límites en [desarrollo](development.md).

El repositorio de trabajo es `javleds/pokeldn`, derivado de `Decryptu/pokeldn`. El Git vacío del directorio padre fue retirado por petición del usuario; el fork y sus archivos permanecen intactos. La asociación visual de la conversación con un proyecto de Codex no cambia la raíz Git.

## Cómo mantener este contexto

Las decisiones expresas posteriores del usuario prevalecen sobre estos documentos. Al cambiar una, actualizar su estado y motivo en `decisions.md` y ajustar la especificación si corresponde. Registrar mediciones con hardware, versión, carga y método; no transformar estimaciones en requisitos comprobados.

No registrar claves, rutas personales innecesarias o transcripciones completas. Mantener aquí acuerdos y evidencia útil; el detalle funcional upstream permanece en su documentación original.
