# Identidad compacta del entrenador portátil

## Contexto
El selector de la cabecera muestra OT y un fragmento del hash interno. El usuario
requiere OT, ID, SID e idioma en todas las modalidades, sin aumentar el layout.

## Objetivo
Mostrar identidad útil y completa, conservando búsqueda, selección y bloqueo.

## Alcance
Cabecera compartida de TeamView/ReceivedView y un formateador reutilizable.

## Fuera de alcance
Persistencia, importación/exportación, protocolos y despliegue remoto.

## Comportamiento esperado
Opciones identificadas por OT completo, ID/SID del juego e idioma abreviado.
El encabezado del selector muestra ID/SID/idioma del perfil confirmado incluso
cuando la consulta de búsqueda está vacía. Base de pokeLDN sigue siendo la opción
base y limpiar no cambia ese contrato. Se elimina el hash de presentación.

## Decisiones técnicas
Reutilizar console_trainer.shown y la cabecera compartida. Etiquetas de idioma
estables EN/ES/JA/etc.; código numérico de respaldo si desconocido. Mantener la
altura de 60 y el menú acotado 280 × 160.

## Componentes afectados
TeamView._init_trainer/_trade_header/_refresh_trainer y formateador compartido.

## Backend
Sin cambios.

## Frontend
Reemplazar información opaca por identidad; mantener acciones y búsqueda.

## Persistencia
Sin cambios.

## API
Sin cambios.

## Validaciones
Mostrar formato de ID por juego; no reemplazar consulta activa durante refresh.

## Permisos y seguridad
No acceso SSH ni escritura de perfiles; controles bloqueados durante sesiones.

## Casos límite
Base, nombre Unicode, idiomas desconocidos, perfil seleccionado y búsqueda activa.

## Estrategia de pruebas
Formatter Gen III/Switch, etiquetas completas, base, consulta activa y Received.

## Estrategia de validación
pytest focalizado -W error y diff --check. Verificación real Flet 800 × 480 pendiente.

## Estrategia de commits
Un commit local para formato compacto y pruebas, realizado por agente principal.

## Archivos estimados a modificar
portable_team_view.py, portable_trainer_labels.py, test_portable_trainer_label.py.

## Riesgos
Nombres extensos en selector; conservar nombre completo en opción y tooltip.

## Preguntas abiertas
Comprobación visual en cliente Flet real antes de afirmar ajuste físico.

## Plan de implementación
1. Añadir formateador sin modificar IDs almacenados.
2. Conectar opciones/encabezado compartido sin alterar tamaño ni selección.
3. Ejecutar regresiones y documentar resultado.

## Resultado
59 pruebas aprobadas de etiquetas, TeamView y ReceivedView con -W error;
git diff --check sin errores. La cabecera conserva 60 px de alto, IDs/idioma
reemplazan la etiqueta anterior, OT completo se conserva en opción/tooltip.
Pendiente inspección del cliente Flet real a 800 × 480; no se afirma validación
visual a partir de pruebas de propiedades. Sin SSH ni commits de este subtask.
