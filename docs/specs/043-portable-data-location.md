# Carpeta de datos portátil consistente

## Contexto
Terminal con POKELDN_DATA, launcher con .local-preview/portable y paquete con
carpeta de usuario podían abrir perfiles distintos y pedir claves de nuevo.
## Objetivo
Una elección persistente compartida por terminal, acceso y nuevas versiones.
## Alcance
Resolución temprana antes de paths/settings, launcher, runtime portátil y selector
inicial sólo cuando existen varias carpetas con datos. Perfil desktop intacto.
## Fuera de alcance
Mover/mezclar/borrar datos, corregir archivos .desktop remotos, SSH y push.
## Comportamiento esperado
POKELDN_DATA explícito prevalece y no modifica elección persistente (fixtures y
usos aislados). Sin variable, usar elección guardada. Sin elección, detectar carpeta
estándar de usuario y legacy <instalación>/.local-preview/portable: si sólo una
contiene datos conservarla; si ninguna, usar estándar. Si ambas tienen datos,
pedir elección en ventana independiente antes de cargar settings/radio. Persistir
la elección absoluta, no los datos. Cancelar no inicia app ni crea perfil vacío.
## Decisiones técnicas
Módulo stdlib sin importar paths; configuración por usuario fuera del checkout,
portable-data.json bajo directorio de configuración pokeldn-portable.
Picker independiente Flet, invocado por bootstrap de gui/main.py también frozen.
Resolver usa POKELDN_INSTALL_ROOT estable para legacy después de self-update.
No persistir overrides explícitos. Detectar alias/symlinks como misma carpeta.
## Componentes afectados
portable_data, picker, gui/main.py temprano, launcher/runtime, tests/docs.
## Backend
Persistencia JSON atómica. Carpeta guardada desaparecida o ilegible: error explícito,
no sustituir silenciosamente. Selección crea carpeta sólo si instalación nueva.
## Frontend
Ventana 800 × 480 con rutas candidatas, elegir/continuar y cancelar. No leer ni
mostrar claves, Pokémon ni entrenadores para decidir. Respeta teclado/táctil.
## Persistencia
Ruta guardada, sin migración de contenido. Elegir no copia ni fusiona carpetas.
## API
Resolver root/entorno devuelve ruta absoluta o elección requerida/error.
## Validaciones
Paths válidos; binding JSON íntegro; candidatos accesibles; overrides no persistidos.
## Permisos y seguridad
Datos locales; no exposición de contenido sensible. No buscar todo el disco.
## Casos límite
Dos carpetas, ninguna, sólo legacy, alias, override temporal, config corrupta,
ruta guardada desaparecida, instalación versionada y cancelación.
## Estrategia de pruebas
Fixtures temporales para cada resolución, persistencia/override sin contaminación,
launcher/paquete y aislamiento de datos, picker sin import de settings, regresión update.
## Estrategia de validación
pytest warnings-as-errors, bash -n, py_compile, Computer Use 800 × 480 con rutas fake.
## Estrategia de commits
Un commit local independiente después de pruebas, sin publicación.
## Archivos estimados a modificar
Módulo nuevo, picker nuevo, main/bootstrap, runtime, scripts y docs/ai.
## Riesgos
Una carpeta incorrecta elegida sigue mostrando otro perfil; no adivinar entre dos
ubicaciones pobladas. No reparar automáticamente rutas internas de settings antiguos.
## Preguntas abiertas
Ninguna bloqueante: selección del usuario sólo si la detección es ambigua.
## Plan de implementación
1. Resolver común con compatibilidad legacy y tests.
2. Bootstrap previo a imports y picker de conflicto.
3. Unificar scripts/runtime, validar UI/regresiones, documentar y commit.

## Resultado y evidencia
Implementado resolver stdlib, bootstrap previo a paths/settings y picker independiente.
Launcher/runtime dejan de inventar una variable de datos; actualizador conserva la
ruta efectiva explícita al reiniciar. Workers --run/--module sin ruta heredada usan
resolución no interactiva y fallan ante conflicto, sin fallback a perfil desktop.

21 pruebas del resolver + 8 del picker y pruebas de bootstrap/launcher. Suite amplia
`tests/test_portable*.py tests/test_app_update.py -q -W error`: 504 aprobadas.
Tras añadir cobertura de workers no interactivos, 8 pruebas de startup aprobadas.
Bash -n, py_compile y diff-check limpios. Revisión independiente sin bloqueantes.
Computer Use nativo a 800 × 480: dos rutas largas, scroll al Tab, elección de segunda
carpeta por Enter y salida0. Verificado JSON temporal con ruta elegida; ninguna
preferencia real ni dato del usuario modificado. No probado en hardware Pi.

Compatibilidad: el launcher estable042 exportaba default indistinguible de override
real. Requiere actualización manual única del checkout original (ambos scripts),
además de código activo043. No borrar pointer ni migrar datos. Esta limitación está
explicada en guía; no sobrescribir variables explícitas por heurística.
