# Biblioteca portátil de entrenadores

## Contexto
Los perfiles identificados viven en TeamStore por juego. No crear otra base de datos.

## Objetivo
Listar, buscar, filtrar, exportar, importar y eliminar perfiles portátiles.

## Alcance
Backend TrainerLibrary sobre equipos compartidos. UI de Ajustes integra sus métodos.

## Fuera de alcance
Cambiar entrenador base, protocolos, proyecto Rust o despliegue remoto.

## Comportamiento esperado
JSON siempre array, individual o bulk. Cada registro lleva schema/type/game,
versión conocida o null, OT, IDs crudos de 16 bits, género e idioma. Búsqueda por
OT/IDs mostrados/idioma/juego. Eliminar seleccionado restaura base e invalida
ofertas calculadas. Importar no cambia selección ni borradores.

## Decisiones técnicas
Reutilizar TeamStore/save y clave SHA256 del perfil usada por identificación.
Versión desconocida no se infiere del juego actualmente elegido. Nombre exportado
ASCII seguro en carpeta por familia de juego.

## Componentes afectados
gui/portable_trainers.py y tests/test_portable_trainers.py; UI integrada por tarea principal.

## Backend
Validación completa de array antes de mutar; límites 2 MiB/2000 perfiles; campos
estrictos y tipos sin aceptar booleanos como enteros. Guardado atómico por juego
existente; notificar selectores compartidos tras cambios.

## Frontend
Consume entries/export_json/import_json/delete; confirmación pertenece a UI.

## Persistencia
Schema TeamStore 1 conservado. Campo opcional game_version dentro de perfil
importado conserva procedencia; clave de identidad solo usa campos básicos.
No modificar archivos ilegibles ni migrar borradores.

## API
JSON schema 1, type pokeldn.portable.trainer, game, game_version, profile.
Ningún formato HTTP nuevo.

## Validaciones
Juego, versión, OT/longitud/codificación Gen III, IDs 0..65535, género e idiomas.
Los idiomas chinos no se aceptan en Gen III.

## Permisos y seguridad
Mutaciones bloqueadas mientras configuración, comprobaciones o sesión están activas.
No exportar rutas, claves ni identificadores internos arbitrarios.

## Casos límite
Duplicados, perfil base, JSON incorrecto, nombres Unicode, versión incompatible,
borrador corrupto y eliminación del perfil seleccionado.

## Estrategia de pruebas
Roundtrip individual/bulk, IDs crudos, deduplicación, validación previa, búsqueda,
bloqueos, borrado seleccionado y preservación de borradores.

## Estrategia de validación
pytest focalizado -W error y diff --check; UI 800 × 480 validada separadamente.

## Estrategia de commits
Un commit de facility Entrenadores con backend/UI/pruebas por tarea principal.

## Archivos estimados a modificar
Este documento, gui/portable_trainers.py y tests/test_portable_trainers.py.

## Riesgos
Un bulk cruza varios archivos atómicos; error de disco entre juegos puede dejar
importación parcial. Se informa y reimportar es idempotente; no prometer transacción
global ni deshacer escrituras durables de otros procesos.

## Preguntas abiertas
Ninguna para backend; ruta de exportación seleccionada en UI.

## Plan de implementación
1. Reutilizar equipos compartidos y definir esquema.
2. Validar/importar y operar perfiles sin tocar borradores.
3. Cubrir regresiones y reportar validaciones.

## Resultado de validación backend
29 pruebas focalizadas aprobadas con -W error. Cubren roundtrip JSON individual/
bulk, deduplicación con perfiles identificados, IDs crudos, búsqueda/filtro,
nombres de archivo seguros, conservación de borradores, límites/tipos/idiomas,
bloqueos de sesión, borrado seleccionado y error de escritura.
No prueba visual de UI realizada por este módulo; integración a cargo de la vista.

## Interfaz integrada
Acceso desde Ajustes, búsqueda y filtro de juego; listado compacto con columnas
Juego/OT/ID/SID/Idioma, eliminar con confirmación y exportar por fila.
Importar JSON y Exportar todos siempre usan arrays. Exportación individual
crea subcarpeta de familia de juego en destino elegido; no sobreescribe archivos
existentes. Bulk se guarda como entrenadores.json. Teclado nativo en formularios.

Validación visual local 2026-11-16: cliente Flet nativo a 800 × 480 útiles,
columnas completas, búsqueda RED, navegación desde/hacia Ajustes y cancelar
eliminación individual. Fixtures temporales. Selector de archivos Linux e
importación entre dos dispositivos pendientes de comprobación física.
