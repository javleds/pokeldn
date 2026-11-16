# Movimientos automáticos mezclados con manuales

## Contexto
El portátil compacta huecos antes de enviar options.moves. Upstream define esa
lista como conjunto exacto: Wish rellena ceros y Learned no actúa con manuales.
La etiqueta Automático del portátil promete completar, no vaciar.
## Objetivo
Completar huecos al generar Pokémon nuevos sin sustituir movimientos elegidos.
## Alcance
Opt-in de generación portátil y servicio PKHeX compartido, con contrato legacy intacto.
## Fuera de alcance
Cambiar recibidos/Banco: Automático allí conserva el movimiento original del slot.
## Comportamiento esperado
Todo auto conserva generación actual; mezcla completa huecos con movimientos
legales, únicos y compatibles. Cuatro manuales conserva lista exacta. Especies
con pocos movimientos pueden tener menos de cuatro; nunca inventar legalidad.
## Decisiones técnicas
options.auto_move_slots de cuatro IDs (0=auto), separado de options.moves legacy.
Conservar intención posicional; completar candidato después de generación legal.
Comprobar legalidad completa y restricciones explícitas antes de aceptar relleno.
## Componentes afectados
Team._validate, Program.cs Make y pruebas de servicio/controlador.
## Backend
Solo Make interpreta opt-in; no modifica prepare/edit_received ni originales.
## Frontend
Sin cambios de layout ni etiquetas; Automático cumple su significado.
## Persistencia
Borradores existentes permanecen; no migración ni cambios de bytes recibidos.
## API
Nueva opción aditiva interna JSON de servicio; consumidores previos sin cambios.
## Validaciones
Cuatro entradas válidas, movimientos manuales sin duplicados y dentro de límites.
## Permisos y seguridad
Cambios y compilación locales, sin SSH ni despliegue.
## Casos límite
Manual en slot segundo/cuarto, duplicados, ilegales, eventos, bajo nivel y juegos distintos.
## Estrategia de pruebas
Contrato exacto upstream, mezcla legal, intención de slots, no mutación borrador,
recibidos intactos y generación en familias soportadas.
## Estrategia de validación
Build C# con warnings como errores y pytest focalizado con PKHeX real.
## Estrategia de commits
Un commit local de corrección con pruebas y documentación.
## Archivos estimados a modificar
gui/portable_team.py, services/pkhex/Program.cs, pruebas nuevas, docs/ai.
## Riesgos
Sugerencias pueden ser incompatibles con encuentro; aceptar solo conjuntos legales.
No garantizar cuatro movimientos para toda especie/nivel.
## Preguntas abiertas
Ninguna para implementación; comprobar intercambio físico posteriormente.
## Plan de implementación
1. Llevar intención de huecos de Team al nuevo opt-in sin alterar normalized compartido.
2. Completar candidato del servicio conservando restricciones y contrato exacto.
3. Compilar y probar generación/recibidos antes del commit.

## Resultado
Build C# Release osx-arm64 con cero errores/advertencias. Suite integrada de
servicio PKHeX completo y controladores portátiles: 320 pruebas aprobadas con
-W error. Incluye 19 nuevas pruebas reales en siete familias, uno/dos/cuatro
manuales, posiciones 2/4, Magikarp con pocos movimientos, contrato legacy exacto
y entradas inválidas. Revisión independiente sin bloqueantes.

PLA/Z-A pueden rechazar conjuntos incompletos: se prueba primero conjunto
completo preferido y luego adiciones legales incrementales, máximo 64 intentos.
No es búsqueda combinatoria exhaustiva; no se fuerza un conjunto de cuatro.
Si faltan movimientos disponibles se compactan huecos solo por legalidad.
No cambios de layout ni de originales recibidos. Intercambio físico pendiente.
Recompilar PKHeX en Pi con scripts/build_portable.sh tras actualizar fuentes.
