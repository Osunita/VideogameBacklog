Especificación técnica — Backlog de Videojuegos ("Nunca acabo los juegos")
1. Resumen del proyecto
Aplicación de escritorio local (Windows) para gestionar el backlog de videojuegos pendientes/abandonados/en curso, como apoyo a la serie de YouTube "Nunca acabo los juegos".

Objetivo: consultar y mantener actualizado, en un único sitio, qué juegos hay pendientes, en qué punto se dejaron y cuántas horas se han invertido.

No pretende:

Ser un catálogo completo de biblioteca (no sustituye a Steam ni a ningún launcher).
Importar datos automáticamente de fuentes externas.
Ser multiusuario ni sincronizarse online.
Exportar datos (se añadirá en una fase posterior, fuera de este documento).

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
src/gui/app.py

Responsabilidad: ventana principal, orquesta game_list.py y game_form.py, gestiona los filtros.
Importa: customtkinter, db, models, gui.game_list, gui.game_form.
No debe encargarse de: SQL directo (siempre a través de db.py).
src/gui/game_list.py

Responsabilidad: tabla/listado de juegos y controles de filtro (estado, plataforma, búsqueda por título).
Importa: customtkinter, models.
No debe encargarse de: acceso a datos directo (recibe los datos ya filtrados desde app.py).
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

7. Flujo de funcionamiento principal
Usuario abre la app
  ↓
main.py llama a init_db()
  ↓
gui.app.py carga la ventana con list_games() sin filtros
  ↓
Usuario aplica filtro (estado/plataforma/búsqueda)
  ↓
gui.app.py llama a list_games(status, platform, search) y refresca la tabla
  ↓
Usuario pulsa "Añadir" / "Editar" / "Eliminar"
  ↓
game_form.py valida datos en el formulario → db.py ejecuta create_game/update_game/delete_game
  ↓
gui.app.py refresca la lista tras la operación
Caso de error (ejemplo — título vacío al guardar): game_form.py valida antes de llamar a db.py; si falla, muestra un mensaje de error en el propio formulario y no cierra la ventana.

Caso "base de datos no existe" (primer arranque): init_db() la crea automáticamente; no requiere ninguna acción del usuario.

Caso "eliminar juego inexistente" (condición de carrera improbable en single-user, pero se contempla): db.py lanza GameNotFoundError; la GUI muestra un aviso y refresca la lista.

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
Filtro sin resultados	La tabla se muestra vacía con un mensaje tipo "Sin resultados", no es un error
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
13. MVP
MVP (esta especificación completa):

Alta, edición, borrado y listado de juegos.
Filtros por estado, plataforma y búsqueda por título.
Persistencia en SQLite.
Empaquetado como .exe.
Después del MVP:

Exportación de datos (a CSV, mencionado explícitamente por el usuario para una fase posterior).
Fuera de alcance (no se implementará en esta versión):

Importación desde Steam u otras fuentes.
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