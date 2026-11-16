# Primera validación física en Raspberry Pi

## Contexto
Pruebas reportadas por el usuario entre 2026-11-15 y 2026-11-16 en Raspberry Pi 5
con 8 GB, Debian 13 Trixie ARM64, Python 3.13.5, SDK .NET 10.0.404,
Flet 1.0.5 y ESP32-S3 DevKitC-1 N16R8 por USB nativo. Cooler oficial instalado.
Monitor auxiliar HDMI; Waveshare DSI pendiente. Fuente temporal de laptop,
modelo/perfil y cable no registrados; fuente oficial pendiente.

## Objetivo
Registrar evidencia real y límites sin convertir observaciones en certificación.

## Alcance
Compilación, arranque, identificación e intercambios reportados en Rojo Fuego/
Verde Hoja (familia), Let's Go y Leyendas Z-A. No se registró una matriz por
versión, rol y modalidad: no afirmar que todos fueron probados.

## Fuera de alcance
Certificar todos los juegos, RAM mínima, consumo eléctrico, batería, pantalla
DSI/táctil y funcionamiento de todas las modalidades.

## Comportamiento esperado
Conservar evidencias parciales y distinguirlas de mediciones controladas.

## Decisiones técnicas
Pruebas exitosas reportadas por usuario, no ejecutadas por el agente.
Build PKHeX linux-arm64 exitoso en 30.5 s. Temperatura máxima observada 53 °C,
incluyendo compilación e intercambio FR/LG. get_throttled=0x0 en controles
anteriores, no consta lectura final por cada juego.

## Componentes afectados
Documentación de estado, benchmark y desarrollo.

## Backend
Sin cambios.

## Frontend
El helper ? muestra RAM del sistema y RSS acumulado de la app por separado.
Usuario reporta ~1.1 GB, sin captura para distinguir esos campos ni GB/GiB.
No atribuir ese número exclusivamente a pokeLDN.
"4 CPU lógicas" es capacidad detectada, no 400% de uso ni cuatro CPU virtuales
consumidas; los porcentajes CPU/App son las medidas variables.

## Persistencia
Sin cambios ni datos personales archivados en el repositorio.

## API
Sin cambios.

## Validaciones
Pendientes SwSh, BDSP, PLA y versiones/roles/modalidades no especificados.
Magikarp sustituye la oferta nacional problemática (Flygon/Sharpedo); no se
registró aún matriz exhaustiva de regresión física.

## Permisos y seguridad
Solo lectura SSH del log solicitada expresamente; cambios y publicación locales.

## Casos límite
Errores nativos de cierre después de sesiones funcionales no invalidan el
intercambio confirmado, pero requieren investigación separada.

## Estrategia de pruebas
Registrar juego/versión/rol/modalidad, duración, RAM sistema/app, CPU sistema/app,
temperatura máxima y get_throttled por escenario.

## Estrategia de validación
Esta entrada recoge el reporte del usuario y lectura del log; no incluye
benchmark automático ni certificación del hardware económico hermano.

## Estrategia de commits
Commit documental independiente solicitado por el usuario.

## Archivos estimados a modificar
Esta spec, docs/ai/README.md, docs/ai/development.md y docs/portable-benchmark.md.

## Riesgos
Fuente temporal y conjunto HDMI no representan la futura configuración DSI.
Un pico no capturado no queda descartado por la temperatura observada.

## Preguntas abiertas
Identificar campo RAM y registrar tiempos/matriz de pruebas; repetir con DSI.

## Plan de implementación
Registrar evidencia, enlazar desde contexto y conservar historial previo.
