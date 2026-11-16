# Comprobación inicial visible

## Contexto
Configuración muestra texto estático durante detección sin firmware. USB, PKHeX
y esptool ya usan asyncio.to_thread; no se confirmó bloqueo del event loop.
## Objetivo
Mostrar actividad y permitir consultar bibliotecas locales mientras se comprueba.
## Alcance
Estado por etapa, indicador animado, aviso tras ocho segundos y botones coherentes.
## Fuera de alcance
Cambiar protocolos, firmware o cancelar forzosamente threads de acceso serie.
## Comportamiento esperado
Motor, radio y detección de chip indican su etapa; comprobación lenta avisa.
Revisar/configurar/instalar permanecen bloqueados; listas locales accesibles.
## Decisiones técnicas
Reutilizar Setup.notify, status y ProgressRing. Watchdog asíncrono cancelado en
finally. Mantener timeouts/reintentos del transporte/esptool; no liberar radio
con wait_for sobre un thread que sigue ejecutándose.
## Componentes afectados
portable_setup.py, portable.py y pruebas.
## Backend
Campos check_detail/check_slow y notificaciones por etapa.
## Frontend
Indicador en filas checking y texto de etapa en diagnóstico, sin modal bloqueante.
## Persistencia
Sin cambios.
## API
Sin cambios externos.
## Validaciones
No comprobaciones duplicadas ni acceso concurrente a instalación/intercambio.
## Permisos y seguridad
Cambios locales, sin SSH ni radio real.
## Casos límite
Error, chip sin firmware, salida de ajustes, check lento y reintento.
## Estrategia de pruebas
Event loop avanza durante detección bloqueante simulada, aviso lento y limpieza,
botones y estados; regresiones de onboarding.
## Estrategia de validación
pytest -W error, diff --check y cliente Flet 800 × 480.
## Estrategia de commits
Un séptimo commit independiente.
## Archivos estimados a modificar
Setup, vista, pruebas y docs/ai.
## Riesgos
Driver atascado no se cancela de forma segura desde Python. No afirmar que un
spinner corrige congelamiento nativo Flutter sin reproducción en Pi.
## Preguntas abiertas
Confirmar comportamiento con S3 sin firmware en Pi.
## Plan de implementación
1. Añadir etapas/aviso en Setup sin alterar exclusión serie.
2. Renderizar actividad y habilitar consulta local.
3. Probar y documentar evidencia antes del commit.

## Resultado
33 pruebas focalizadas aprobadas, incluyendo detector bloqueante simulado con
event loop receptivo, aviso y limpieza. Cliente Flet local a 800 × 480: etapa
lenta, indicador y acciones caben; navegación a Entrenadores durante check
comprobada. No se reprodujo un congelamiento nativo ni se probó S3 físico;
validación en Pi pendiente.
