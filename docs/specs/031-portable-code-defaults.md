# Códigos de conexión portátiles por defecto

## Contexto
El controlador portátil inicializa vacío el código, aunque PLA y Z-A requieren
ocho dígitos en el catálogo. Let's Go ya usa tres pictogramas representados por
dígitos. El usuario solicita relleno de ceros donde el código sea necesario.

## Objetivo
Mostrar un código utilizable por defecto sin modificar los valores elegidos.

## Alcance
Inicialización de Team y configuración de conexión por papel host/join.

## Fuera de alcance
Cambiar protocolos, hacer obligatorio un código opcional o configurar escritorio.

## Comportamiento esperado
Let's Go conserva 000. Los campos code cuyo catálogo exige valor (required o
default no vacío) usan ceros según length. Los juegos/papeles sin código y los
códigos opcionales permanecen vacíos. Borrar explícitamente el código de Let's Go
sigue siendo inválido; el valor inicial 000 evita la necesidad de hacerlo. Se preservan códigos guardados no vacíos,
incluso inválidos, para permitir corrección visible.

## Decisiones técnicas
Reutilizar local_tools y Field.kind/required/default/length. Resolver el valor al
cargar y al guardar configuración vacía para el papel seleccionado.

## Componentes afectados
gui/portable_team.py y tests/test_portable_code_defaults.py.

## Backend
Helper pequeño compartido por inicialización/configure; validación existente intacta.

## Frontend
Sin nuevos controles: el formulario existente recibe el valor del controlador.

## Persistencia
Sin migración. Se conserva el borrador original hasta guardarlo por acciones existentes.

## API
Sin cambios.

## Validaciones
Códigos obligatorios válidos para command.code_error; opciones vacías preservadas.

## Permisos y seguridad
No iniciar sesiones ni acceder por SSH; cambios locales.

## Casos límite
Cambio de papel, código existente, borrador antiguo vacío y código inválido existente.

## Estrategia de pruebas
Matriz de siete juegos y ambos papeles disponibles, conservación de valores,
configuración vacía y Field de longitud distinta para evitar hardcode ocho.

## Estrategia de validación
pytest focalizado con -W error y regresiones Team/UI.

## Estrategia de commits
Un commit de defaults, pruebas y esta spec; el agente principal crea el commit.

## Archivos estimados a modificar
gui/portable_team.py, tests/test_portable_code_defaults.py, esta spec.

## Riesgos
Field.required no es el único indicador: un default no vacío también exige código
en command.code_error. Mantener esos dos casos consistentes.

## Preguntas abiertas
Ninguna para esta política.

## Plan de implementación
1. Derivar defaults del catálogo manteniendo el contrato de Let's Go.
2. Aplicar solo a códigos vacíos al cargar/configurar.
3. Probar matriz y regresiones, sin cambiar UI ni transporte.

## Resultado
Implementado. 105 pruebas aprobadas (defaults, Team y TeamView) con -W error;
git diff --check sin errores. PLA y Z-A obtienen 00000000 en ambos papeles;
Let's Go conserva 000. FR/LG, SW/SH, BD/SP y SV mantienen los códigos opcionales
o ausentes sin relleno obligatorio. Prueba visual de cliente real pendiente;
no cambia estructura ni dimensiones de controles. Sin SSH ni commit del subagente.
