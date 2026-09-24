Especificación técnica — Backlog de Videojuegos ("Nunca acabo los juegos")
1. Resumen del proyecto
Aplicación de escritorio local (Windows) para gestionar el backlog de videojuegos pendientes/abandonados/en curso, como apoyo a la serie de YouTube "Nunca acabo los juegos".

Objetivo: consultar y mantener actualizado, en un único sitio, qué juegos hay pendientes, en qué punto se dejaron y cuántas horas se han invertido.

No pretende:

Ser un catálogo completo de biblioteca (no sustituye a Steam ni a ningún launcher).
Importar datos automáticamente de fuentes externas (se refiere a servicios externos como Steam: la exportación/importación LOCAL del JSON con los datos propios de la app SÍ está en alcance desde v1.1.0, misma aclaración que el README).
Ser multiusuario ni sincronizarse online.
Exportar datos (pospuesta en el alcance original de este documento; ENTREGADA en v1.1.0 como exportación e importación a JSON local, ver §6, §7 y §14).

2. Decisiones de diseño
DECISIÓN-001
Problema: ¿Qué tipo de interfaz usar?
Opciones:
A) CLI
B) GUI de escritorio
Decisión: B) GUI de escritorio
Motivo: uso esporádico, no durante grabación; se prioriza comodidad visual sobre rapidez de terminal.

DECISIÓN-002
Problema: ¿Qué librería usar para la GUI?
Opciones:
A) Tkinter (stdlib, sin dependencias, aspecto básico)
B) CustomTkinter (dependencia extra, aspecto moderno)
Decisión: B) CustomTkinter
Motivo: prioridad al aspecto visual, aceptando la dependencia extra.

DECISIÓN-003
Problema: ¿Cómo persistir los datos?
Opciones:
A) JSON/CSV
B) SQLite
Decisión: B) SQLite
Motivo: acceso concurrente seguro, consultas con filtros más sencillas, escalable si crece el número de juegos.

DECISIÓN-004
Problema: ¿Se permiten títulos duplicados en el backlog (mismo juego en dos plataformas, o rejugado)?
Opciones:
A) Permitir duplicados de título
B) Título único
Decisión (propuesta, pendiente de tu confirmación): A) Permitir duplicados
Motivo: es habitual tener el mismo juego en varias plataformas o querer registrar una segunda vuelta; no se valida unicidad de título, solo que no esté vacío.

DECISIÓN-005
Problema: ¿Dónde se guarda el archivo de base de datos?
Opciones:
A) Junto al ejecutable
B) Carpeta de datos de usuario de Windows (%APPDATA%)
Decisión: B) %APPDATA%\NuncaAcaboLosJuegos\backlog.db
Motivo: es el estándar en Windows para datos de aplicación; evita perder datos si se reemplaza el .exe, y evita problemas de permisos de escritura junto al ejecutable.
Si alguna de estas decisiones (especialmente la 004) no es la que quieres, dímelo y actualizo la especificación antes de pasar a OpenCode.

DECISIÓN-006
Problema: ¿Cómo se exporta e importa el backlog (respaldo y migración local de los datos propios)?
Opciones:
A) JSON local con fusión por (título, plataforma)
B) Exportación a CSV (sin importación)
C) Exportación sin importación (solo lectura)
Decisión: A) JSON local, con envoltorio versionado {"app", "version": 1, "exported_at", "games": [...]}, fusión por (título, plataforma) y validación todo-o-nada.
Motivo: JSON se parsea con la librería estándar (sin dependencias nuevas, §8); la clave (título, plataforma) evita depender de ids locales autoincrementales; la validación todo-o-nada garantiza que un archivo inválido nunca dañe la base de datos. (La opción B, CSV, era el plan original "después del MVP"; se entregó como JSON en v1.1.0.)

DECISIÓN-007
Problema: ¿Dónde vive la lógica de exportación/importación? (implica enmendar §4)
Opciones:
A) En db.py (añadir manejo de ficheros al lado del SQL)
B) En la GUI (app.py)
C) Módulo nuevo src/export_import.py entre GUI y db.py
Decisión: C) src/export_import.py — único fichero nuevo, añadido a la estructura §4.
Motivo: cero SQL (usa solo los contratos §6 de db.py y las validaciones de models.Game), db.py permanece SQLite-only, y el módulo es testeable sin GUI; la GUI solo abre diálogos y muestra avisos.

3. Arquitectura
Arquitectura simple en 3 capas, sin frameworks adicionales:

Usuario
  ↓
GUI (CustomTkinter)
  ↓
Capa de acceso a datos (db.py)
  ↓
SQLite (backlog.db)
No hay capa de "servicios" ni "lógica de negocio" separada porque las reglas son mínimas (validar título no vacío, horas ≥ 0) y se resuelven directamente en la capa de datos. Añadir una capa extra sería overengineering para este alcance.

4. Estructura del proyecto
backlog-videojuegos/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── export_import.py
│   └── gui/
│       ├── app.py
│       ├── game_list.py
│       └── game_form.py
├── tests/
│   ├── test_db.py
│   └── test_models.py
├── build.spec
├── README.md
└── requirements.txt
src/main.py

Responsabilidad: punto de entrada. Inicializa la base de datos (crea el archivo/tabla si no existe) y lanza la ventana principal.
Importa: config, db, gui.app.
No debe encargarse de: lógica de UI ni de acceso a datos directamente.
src/config.py

Responsabilidad: definir rutas y constantes (ruta del .db, nombre de la app, estados válidos).
Importa: solo librería estándar (os, pathlib).
No debe encargarse de: acceso a datos ni UI.
src/db.py

Responsabilidad: toda la interacción con SQLite (crear tabla, CRUD, filtros). Es la única capa que ejecuta SQL.
Importa: sqlite3 (stdlib), models, config.
No debe encargarse de: nada de UI ni de formateo visual.
src/models.py

Responsabilidad: definir la entidad Game (dataclass) y las validaciones de datos (título no vacío, horas ≥ 0, estado válido).
Importa: solo librería estándar.
No debe encargarse de: acceso a datos ni UI.
src/export_import.py

Responsabilidad: exportar el backlog completo a un archivo JSON versionado (UTF-8) y leer, validar y fusionar los archivos JSON importados (validación todo-o-nada; fusión por (title, platform)). CERO SQL: usa solo los contratos de db.py (list_games, create_game, update_game) y las validaciones de models.Game.
Importa: json y librería estándar, db, config, models. Nunca importa GUI.
No debe encargarse de: SQL directo ni diálogos de interfaz (los filedialog y avisos viven en gui/app.py).
src/gui/app.py

Responsabilidad: ventana principal. En la cabecera conviven los controles de filtro (estado, plataforma, búsqueda por título), los botones secundarios "Exportar" e "Importar" y el botón "Añadir juego" con color de acento (arriba a la derecha, único botón acento). Orquesta game_list.py (listado en tarjetas) y game_form.py, y gestiona CRUD, refresco, errores y los diálogos de exportación/importación (filedialog + avisos + refresh tras importar). No hay barra inferior de botones ni selección global: editar/eliminar llegan desde cada tarjeta vía los callbacks on_edit/on_delete que inyecta en GameList.
Importa: customtkinter, db, export_import, models, gui.game_list, gui.game_form.
No debe encargarse de: SQL directo (siempre a través de db.py) ni la lógica JSON de exportar/importar (vive en export_import.py).
src/gui/game_list.py

Responsabilidad: listado de juegos en tarjetas (CTkScrollableFrame con un CTkFrame por juego: indicador de color del estado, título, línea secundaria "plataforma · horas", píldora de estado y botones ✎/✕ siempre visibles), placeholder "Sin resultados" y tooltip hover con progress_note/episode_url. Los controles de filtro NO viven en este archivo: están en app.py.
Importa: customtkinter, models.
No debe encargarse de: acceso a datos directo (recibe los datos ya filtrados desde app.py y delega las acciones en los callbacks on_edit/on_delete inyectados por app.py).
src/gui/game_form.py

Responsabilidad: formulario modal de alta/edición de un juego, con validación de campos antes de enviar a db.py.
Importa: customtkinter, models.
No debe encargarse de: acceso a datos directo.
5. Modelo de datos
Game
- id: int              (autogenerado, PK)
- title: str            (obligatorio, no vacío)
- platform: str          (obligatorio, no vacío)
- status: str            (obligatorio; uno de: "pendiente", "en_curso", "abandonado", "completado")
- hours_played: float    (opcional, por defecto 0, debe ser >= 0)
- progress_note: str     (opcional, texto libre; "punto donde lo dejaste")
- episode_url: str       (opcional; enlace al vídeo del episodio relacionado)
No hay relaciones entre entidades: es una única tabla games.

6. Interfaces y contratos (capa db.py)
init_db() -> None
Crea el archivo de base de datos y la tabla games si no existen. Se llama una vez al arranque.

create_game(title, platform, status, hours_played=0, progress_note="", episode_url="") -> Game
Entrada: title y platform obligatorios (str no vacío); status debe ser uno de los 4 valores válidos; hours_played ≥ 0. Resultado: Game creado, con id asignado. Errores: ValueError si título/plataforma vacíos, status inválido, u horas negativas.

update_game(game_id, **fields) -> Game
Entrada: id existente + campos a actualizar. Resultado: Game actualizado. Errores: GameNotFoundError si el id no existe; ValueError si algún campo actualizado es inválido.

delete_game(game_id) -> None
Errores: GameNotFoundError si el id no existe.

get_game(game_id) -> Game | None
Devuelve None si no existe (no lanza error; se usa para comprobaciones).

list_games(status=None, platform=None, search=None) -> list[Game]
Devuelve la lista filtrada. search filtra por coincidencia parcial (case-insensitive) en title. Sin filtros, devuelve todos los juegos.

Contratos de src/export_import.py (módulo añadido a §4 en v1.1.0; ver DECISIÓN-007):

export_games(path) -> int
Exporta el backlog COMPLETO (list_games() sin filtros; los filtros activos de la GUI se ignoran) a un archivo JSON UTF-8 con envoltorio versionado {"app", "version": 1, "exported_at", "games": [...]}. Devuelve el número de juegos exportados (0 si el backlog está vacío). Errores: ExportImportError si el archivo no se puede escribir (la GUI muestra entonces un diálogo de error y NO muestra aviso de éxito).

import_games(path) -> ImportResult
Lee y valida TODOS los registros del archivo ANTES de aplicar ninguno (todo-o-nada) y después aplica la fusión por (title, platform): coincidencia exacta → update_game SOBRESCRIBE status, hours_played, progress_note y episode_url (el id del archivo se ignora; si la clave está duplicada en la BD se actualiza el registro de menor id); sin coincidencia → create_game; duplicado (title, platform) DENTRO del archivo → gana la primera aparición. ImportResult es un dataclass inmutable con los conteos created y updated. Errores: ExportImportError ante archivo ilegible, JSON malformado, forma incorrecta (sin lista "games"), versión ≠ 1 o registros inválidos; el mensaje acumula todos los motivos ("registro i: ...") y la base de datos NO se modifica.

ExportImportError
Excepción única del módulo (mensaje en español); es el único tipo de error que la GUI necesita capturar para exportar/importar. La envoltura con versión distinta de 1 se rechaza (formatos futuros incompatibles); los campos extra desconocidos del archivo se ignoran (compatibilidad futura).

7. Flujo de funcionamiento principal
Usuario abre la app
  ↓
main.py llama a init_db()
  ↓
gui.app.py carga la ventana con list_games() sin filtros
  ↓
Usuario aplica filtro (estado/plataforma/búsqueda)
  ↓
gui.app.py llama a list_games(status, platform, search) y repinta el listado en tarjetas
  ↓
Usuario pulsa "Añadir juego" (cabecera, arriba a la derecha) o ✎/✕ en una tarjeta concreta
  ↓
game_form.py valida datos en el formulario → db.py ejecuta create_game/update_game/delete_game
  ↓
gui.app.py refresca la lista tras la operación
No hay barra inferior de botones ni selección global: alta desde la cabecera, edición (✎) y borrado (✕, con confirmación) desde cada tarjeta. Al pasar el ratón sobre una tarjeta aparece un tooltip con progress_note y/o episode_url (fallback "No hay info"), solo presentación.

Caso de error (ejemplo — título vacío al guardar): game_form.py valida antes de llamar a db.py; si falla, muestra un mensaje de error en el propio formulario y no cierra la ventana.

Caso "base de datos no existe" (primer arranque): init_db() la crea automáticamente; no requiere ninguna acción del usuario.

Caso "eliminar juego inexistente" (condición de carrera improbable en single-user, pero se contempla): db.py lanza GameNotFoundError; la GUI muestra un aviso y refresca la lista.

Exportación / importación (añadido en v1.1.0, cambio export-import):
Usuario pulsa "Exportar" (cabecera) → filedialog de guardado .json (cancelar = sin acción, sin error) → export_import.export_games(ruta) escribe el backlog COMPLETO → aviso "N juegos exportados" (si la ruta no es escribible: diálogo de error y NO aviso de éxito).
  ↓
Usuario pulsa "Importar" (cabecera) → filedialog de selección (cancelar = sin acción) → export_import.import_games(ruta): lee, parsea y valida TODOS los registros; cualquier error → UN ÚNICO diálogo con todos los motivos ("registro i: ...") y la base de datos queda intacta (todo-o-nada).
  ↓
Si todo es válido: fusión por (title, platform) → aviso "N creados, M actualizados" → gui.app.py refresca la lista.

8. Dependencias
Dependencia	Tipo	Motivo
sqlite3	Estándar	Persistencia, incluido en Python
customtkinter	Externa	GUI con aspecto moderno (decisión del usuario)
pyinstaller	Desarrollo	Empaquetar como .exe para Windows
pytest	Desarrollo	Tests unitarios
No se añade ningún ORM (SQLAlchemy, etc.): el volumen y complejidad de datos no lo justifica; sqlite3 + SQL directo en db.py es suficiente y más simple de mantener.

9. Configuración
Ruta de la base de datos: %APPDATA%\NuncaAcaboLosJuegos\backlog.db, definida en config.py. Debe crearse la carpeta si no existe.
Sin variables de entorno ni secrets: la app no se conecta a ningún servicio externo.
Sistema operativo objetivo: Windows (único soportado en esta versión).
10. Errores y casos límite
Caso	Comportamiento esperado
Primer arranque (BD no existe)	Se crea automáticamente, sin intervención del usuario
Título o plataforma vacíos	La GUI bloquea el guardado y muestra el campo con error
Horas jugadas negativas	La GUI bloquea el guardado y muestra error
Estado no válido (no debería ocurrir vía GUI, pero se valida en db.py)	ValueError
Eliminar/editar un id que ya no existe	GameNotFoundError, aviso en GUI, lista se refresca
Base de datos corrupta o bloqueada	La app muestra un mensaje de error al arrancar y no continúa (no intenta reparar automáticamente)
Filtro sin resultados	El listado se muestra vacío con un mensaje tipo "Sin resultados", no es un error
JSON malformado, sin la forma de una exportación o con registros inválidos al importar	UN solo diálogo de error con todos los motivos ("registro i: ..."); no se aplica NINGÚN cambio y la base de datos queda intacta (validación todo-o-nada)
Ruta de exportación no escribible	Se muestra un diálogo de error y NO se muestra el aviso de éxito de la exportación
11. Tests
Unitarios (tests/test_models.py):

Crear Game con datos válidos.
Rechazar título vacío.
Rechazar horas negativas.
Rechazar estado no válido.
Unitarios (tests/test_db.py, usando una BD SQLite temporal):

create_game guarda y devuelve un Game con id.
list_games sin filtros devuelve todos los juegos.
list_games filtra correctamente por estado, por plataforma y por búsqueda de título (parcial, case-insensitive).
update_game modifica los campos indicados.
update_game/delete_game sobre un id inexistente lanzan GameNotFoundError.
delete_game elimina el registro.

Añadidos con el cambio export-import (tests en tests/test_db.py, SOLO al final del fichero — append-only, los 29 originales intactos):
round-trip export→import con tildes/ñ; fusión por (title, platform) (sobrescritura, plataforma distinta → registro nuevo); validación todo-o-nada (JSON malformado o registro inválido → ExportImportError y la BD sin cambios); duplicado (title, platform) dentro del archivo → gana la primera aparición; export de backlog vacío (games: [] → 0 exportados); rechazo de envoltorio (forma incorrecta y versión ≠ 1).

La suite completa suma 40 tests: 29 originales del MVP + 8 de export/import + 3 añadidos durante la verificación (rechazo de envoltorio). Todo en tests/test_db.py y tests/test_models.py; no se crearon ficheros de test nuevos y no se modificaron los tests originales.
TEST-001
Dado: una base de datos vacía
Cuando: se llama a create_game("Hollow Knight", "PC", "pendiente")
Entonces: se devuelve un Game con id asignado y status="pendiente"

TEST-002
Dado: 3 juegos con estados distintos
Cuando: se llama a list_games(status="pendiente")
Entonces: solo se devuelven los juegos con ese estado

TEST-003
Dado: un juego con id=1
Cuando: se llama a delete_game(1) y después a get_game(1)
Entonces: get_game devuelve None
No se especifican tests de la capa GUI: se considera de menor riesgo y más costosa de automatizar; se prueba manualmente.

12. Fases de implementación
Fase 1 — Base del proyecto

Estructura de carpetas, config.py, main.py con ventana vacía.
Fase 2 — Persistencia

models.py, db.py con CRUD completo, tests/test_models.py, tests/test_db.py.
Fase 3 — Listado y filtros

gui/game_list.py conectado a list_games(), controles de filtro funcionales.
Fase 4 — Alta/edición/borrado

gui/game_form.py, integración completa de crear/editar/eliminar desde la GUI.
Fase 5 — Empaquetado

build.spec de PyInstaller, generación del .exe, README.md con instrucciones de uso y de build.

Entrega v1.0.0 y adiciones posteriores a la verificación

Las 5 fases anteriores se entregaron como v1.0.0 (cambio backlog-mvp, 16/16 tareas, verificación PASS). Tras la verificación se aplicaron tres adiciones post-verify, ya incluidas en v1.0.0:
- Etiqueta de estado "en curso" en la GUI (solo presentación: el valor almacenado sigue siendo "en_curso").
- Tooltip al pasar el ratón sobre una fila/tarjeta con progress_note y episode_url.
- Rediseño del listado a tarjetas: se sustituyó la tabla Treeview por un listado en tarjetas (CTkScrollableFrame); desapareció la barra inferior de Añadir/Editar/Eliminar → "Añadir juego" arriba a la derecha con color de acento y botones ✎/✕ por tarjeta.
Fase 6 — Exportación/importación JSON (post-MVP, entregada en v1.1.0, cambio export-import)

src/export_import.py (único fichero nuevo, §4 enmendada — DECISIÓN-007), botones Exportar/Importar en la cabecera de gui/app.py, tests añadidos a tests/test_db.py, sección "Exportar / Importar" del README.
13. MVP
MVP (entregado como v1.0.0, cambio backlog-mvp):

Alta, edición, borrado y listado de juegos.
Filtros por estado, plataforma y búsqueda por título.
Persistencia en SQLite.
Empaquetado como .exe.
Después del MVP:

Nada pendiente en esta versión: la exportación de datos, prevista aquí originalmente (a CSV), se ha entregado como exportación e IMPORTACIÓN a JSON local en v1.1.0 (cambio export-import, ver §6/§7/§14 — AC-008..AC-011). El listado en tarjetas y el tooltip hover son adiciones post-verificación ya incluidas en v1.0.0.
Fuera de alcance (no se implementará en esta versión):

Importación desde Steam u otras fuentes externas (la aclaración "no importa datos de fuentes externas" de §1 se refiere a servicios externos: el JSON local exportado por la propia app SÍ se importa, ver §6).
Historial de notas de progreso con fechas.
Multiusuario o sincronización online.
Soporte para macOS/Linux.

14. Criterios de aceptación
AC-001
La aplicación puede iniciarse mediante el .exe sin errores, incluso si es la primera vez (sin BD previa).

AC-002
El usuario puede dar de alta un juego con título, plataforma y estado, y aparece en el listado.

AC-003
El usuario puede editar un juego existente y los cambios persisten tras cerrar y reabrir la app.

AC-004
El usuario puede eliminar un juego y este deja de aparecer en el listado.

AC-005
El usuario puede filtrar el listado por estado, por plataforma y por texto de título, y los resultados se actualizan correctamente.

AC-006
Si se intenta guardar un juego sin título o con horas negativas, la aplicación muestra un error y no lo guarda.

AC-007
Los datos persisten en %APPDATA%\NuncaAcaboLosJuegos\backlog.db tras cerrar y volver a abrir la aplicación.

AC-008
El usuario puede exportar el backlog COMPLETO a un archivo JSON (los filtros activos se ignoran); con el backlog vacío se escribe `games: []` y el aviso "0 juegos exportados"; cancelar el diálogo no hace nada ni muestra error; si la ruta no es escribible se muestra un diálogo de error y NO se muestra aviso de éxito.

AC-009
Al importar, la fusión es por (title, platform): una coincidencia exacta SOBRESCRIBE status, hours_played, progress_note y episode_url conservando el id local; una plataforma distinta o un título nuevo crea un registro nuevo; el id del archivo se ignora; un duplicado (title, platform) dentro del archivo gana la PRIMERA aparición y las repeticiones se descartan.

AC-010
La importación es todo-o-nada: si el JSON está malformado, no tiene la forma de una exportación, su versión no es la soportada o algún registro es inválido, se muestra un ÚNICO diálogo con todos los motivos ("registro i: ..."), no se aplica ningún cambio y la base de datos queda intacta.

AC-011
Round-trip y compatibilidad: exportar un backlog, vaciar la BD e importar el archivo deja el backlog idéntico (mismos campos; ids asignados por la BD), con tildes/ñ sin cambios; los archivos con "version": 1 (p. ej. exportados por v1.0.0) se importan limpiamente y las versiones > 1 se rechazan con mensaje claro.