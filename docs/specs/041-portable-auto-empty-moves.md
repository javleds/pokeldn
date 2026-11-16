# Automático y Vacío en todos los editores

## Contexto
Equipo completa huecos pero editores individuales trataban Automático como
restaurar el movimiento original; un cero aparecía como etiqueta numérica.
Usuario amplía a Equipo, Modificar y Banco → Editar.
## Objetivo
Distinguir completar un movimiento de dejar el slot explícitamente vacío.
## Alcance
Selector compartido, controladores de generación/edición y servicio PKHeX.
## Fuera de alcance
Mutar original archivado o devolver original con cambios; protocolos y layout.
## Comportamiento esperado
Automático (null) pide relleno legal; Vacío (0) conserva ausencia; ID positivo
conserva elección manual. Los ceros leídos se muestran Vacío. Vacío es seleccionable
pero no garantiza que el conjunto sea legal: conservar error sin corregirlo ocultamente.
## Decisiones técnicas
Contrato nuevo move_slots en Make.options/EditReceived.fields, cuatro entradas.
Conservar contracts legacy moves y auto_move_slots. Edición clona fuente, sin Make.
## Componentes afectados
TeamView, Team, ReceivedTeam, BankTeam, Program.cs y pruebas.
## Backend
Candidatos legales sobre mismo registro, explícitos y vacíos respetados. Rechazar
combinaciones imposibles; nunca desplazar manual sobre Vacío para ocultar ilegalidad.
## Frontend
Opciones Automático y Vacío separadas; X mantiene Automático, búsqueda intacta.
## Persistencia
Borradores continúan usando None/0/ID. No migración ni cambios de archivos originales.
## API
move_slots=[null,85,0,null]; nueva opción aditiva interna. No campos de identidad.
## Validaciones
Cuatro slots, tipos/IDs válidos, sin manuales duplicados; legalidad final.
## Permisos y seguridad
Local, sin SSH/hardware; fixtures para pruebas.
## Casos límite
Original con ceros, cuatro vacíos, nulos mezclados con cero/manual, juegos que
requieren cuatro movimientos y registros con identidad de encuentro restringida.
## Estrategia de pruebas
Tres controladores, lectura UI de cero, contrato servicio real Make/edit, fuente
inmutable, identidad conservada, ilegalidad visible y regresiones legacy.
## Estrategia de validación
Build C# warnings-as-errors, pytest, Computer Use a 800 × 480.
## Estrategia de commits
Un commit local funcional con docs/pruebas.
## Archivos estimados a modificar
Tres modelos, vista compartida, servicio y tests de movimientos.
## Riesgos
Una opción Vacío válida en UI puede producir un Pokémon ilegal; no habilitar envío.
## Preguntas abiertas
Ninguna.
## Plan de implementación
1. Añadir selector Vacío y preservar intención en los tres modelos.
2. Implementar contrato común y relleno seguro sobre copia.
3. Validar comportamiento/identidad y representación nativa antes del commit.

## Resultado y evidencia
Implementado en los tres controladores y selector compartido. Servicio conserva
contratos anteriores, identidad y originales. La revisión detectó reparación
accidental de AVs PB7 al evaluar candidatos: sustituida por análisis sin reparar
estadísticas; cinco regresiones Let's Go cubren AVs legales e ilegales.
Build local sin errores ni advertencias. Computer Use verificó menú abierto y
cambio Vacío ↔ Automático en cliente Flet nativo con tema real y modelo de prueba
a 800 × 480. Esta comprobación visual no ejecutó intercambio ni certifica Pi.
Recompilar PKHeX en Raspberry Pi después de actualizar.

Suite final: 434 pruebas aprobadas con warnings-as-errors, incluyendo servicio
PKHeX real, generación/edición en siete juegos, los tres controladores, selectores
y contratos legacy. `git diff --check` limpio.
