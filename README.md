# Nunca acabo los juegos

Aplicación de escritorio (Windows) para gestionar el backlog de videojuegos pendientes, abandonados y en curso. Sirve de apoyo a la serie de YouTube **"Nunca acabo los juegos"**: consultar y mantener actualizado en un único sitio qué juegos hay pendientes, en qué punto se dejaron y cuántas horas se han invertido.

No es un catálogo de biblioteca (no sustituye a Steam ni a ningún launcher), no importa datos de fuentes externas ni se sincroniza online.

## Requisitos

- Windows (único sistema soportado)
- Python 3.13 o superior

Dependencias (ver `requirements.txt`):

| Paquete | Tipo | Uso |
|---------|------|-----|
| `customtkinter` | runtime | GUI con aspecto moderno |
| `pyinstaller` | desarrollo | Empaquetar el `.exe` |
| `pytest` | desarrollo | Tests unitarios |

`sqlite3` viene incluido en Python (biblioteca estándar). No se usa ningún ORM.

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecutar desde código

```bash
python src/main.py
```

## Tests

```bash
python -m pytest
```

Ejecuta la suite completa de `tests/` (modelos y capa de datos con base de datos temporal). Debe terminar en verde: **29 passed**. No hay tests automatizados de la capa GUI (se prueba manualmente).

## Construir el .exe

```bash
python -m PyInstaller build.spec
```

Genera `dist\NuncaAcaboLosJuegos.exe` (onefile, sin ventana de consola). El spec empaqueta también los archivos de tema/JSON de CustomTkinter (`collect_data_files("customtkinter")`), necesarios para que la interfaz arranque correctamente.

## Dónde se guardan los datos

```
%APPDATA%\NuncaAcaboLosJuegos\backlog.db
```

Es decir: `C:\Users\<usuario>\AppData\Roaming\NuncaAcaboLosJuegos\backlog.db`.

- La carpeta y el archivo se crean automáticamente en el primer arranque.
- Los datos viven fuera de la carpeta del programa: reemplazar o borrar el `.exe` no borra el backlog.
- La aplicación no usa variables de entorno ni secretos.

## Prueba manual (criterios de aceptación)

Checklist correspondiente a AC-001..AC-007 de la especificación:

- [ ] **AC-001** — Borrar (si existe) `%APPDATA%\NuncaAcaboLosJuegos` y lanzar `dist\NuncaAcaboLosJuegos.exe` por primera vez: arranca sin errores y crea la base de datos sola.
- [ ] **AC-002** — Dar de alta un juego con título, plataforma y estado: aparece en el listado.
- [ ] **AC-003** — Editar un juego existente, cerrar y reabrir la aplicación: los cambios persisten.
- [ ] **AC-004** — Eliminar un juego: deja de aparecer en el listado.
- [ ] **AC-005** — Filtrar por estado, por plataforma y por texto de título: los resultados se actualizan correctamente (sin coincidencias → "Sin resultados", no es error).
- [ ] **AC-006** — Intentar guardar sin título u horas negativas: la aplicación muestra el error en el formulario, marca el campo y no guarda.
- [ ] **AC-007** — Tras cerrar y volver a abrir, los datos siguen en `%APPDATA%\NuncaAcaboLosJuegos\backlog.db`.

## Estructura del proyecto

```
backlog-videojuegos/
├── src/
│   ├── main.py          # Punto de entrada: init_db() + ventana principal
│   ├── config.py        # Rutas y constantes (ruta de la BD, estados)
│   ├── db.py            # Única capa que ejecuta SQL (CRUD + filtros)
│   ├── models.py        # Dataclass Game + validaciones
│   └── gui/
│       ├── app.py       # Ventana principal, filtros, orquestación
│       ├── game_list.py # Tabla de juegos + controles de filtro
│       └── game_form.py # Formulario modal de alta/edición
├── tests/
│   ├── test_db.py       # Tests de la capa de datos (BD temporal)
│   └── test_models.py   # Tests de validación del modelo
├── build.spec           # Spec de PyInstaller
├── README.md
└── requirements.txt
```
