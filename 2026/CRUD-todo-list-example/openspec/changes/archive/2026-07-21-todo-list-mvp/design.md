## Context

Aplicacion de escritorio autocontenida para gestion de tareas. El proyecto es independiente dentro del monorepo (`2026/CRUD-todo-list-example/`). Se busca un MVP funcional con minima complejidad arquitectonica.

## Goals / Non-Goals

**Goals:**
- Aplicacion de escritorio ejecutable con `python main.py`
- Persistencia local en archivo SQLite (`todo.db`)
- Interfaz grafica responsiva con PyQt
- Operaciones CRUD completas sobre tareas

**Non-Goals:**
- Autenticacion o multiusuario
- Sincronizacion remota o API REST
- Filtros avanzados, busqueda o categorias
- Empaquetado como ejecutable (.exe, .app, etc.)
- Pruebas automatizadas en esta fase

## Decisions

### Arquitectura: Modelo-Vista minimalista
Se usara una separacion logica en tres modulos:
- `models.py`: Definicion de la tabla y clase Task, inicializacion de SQLite
- `views.py`: Interfaz PyQt (QMainWindow, QDialog para formularios)
- `controllers.py`: Logica CRUD que conecta views con models

**Alternativa considerada:** Todo en un solo archivo. Se descarto porque separar en modulos facilita mantenimiento y testing futuro, sin anadir complejidad significativa.

### Base de datos: SQLite con sqlite3 (stdlib)
Una tabla `tasks` con columnas:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `title` TEXT NOT NULL
- `description` TEXT DEFAULT ''
- `completed` INTEGER DEFAULT 0 (0=pendiente, 1=completada)
- `created_at` TEXT DEFAULT CURRENT_TIMESTAMP

La base de datos se crea automaticamente en el directorio de ejecucion si no existe.

**Alternativa considerada:** JSON file. Se descarto porque SQLite ofrece integridad, consultas y no requiere dependencias adicionales (viene con Python).

### Libreria UI: PyQt5
Se usara PyQt5 por ser la version mas estable y ampliamente disponible en repositorios Linux. La interfaz es programatica (sin Qt Designer) para mantener un solo stack tecnologico y facilitar la lectura del codigo.

**Alternativa considerada:** PyQt6. Se descarto por menor disponibilidad en algunas distribuciones LTS. La migracion es trivial si se requiere en el futuro.

**Alternativa considerada:** Tkinter (stdlib). Se descarto porque PyQt ofrece widgets mas modernos (QTableWidget, QDialog) y mejor apariencia nativa.

### Layout de ventana principal
Estructura vertical:
1. QTableWidget ocupando la mayor parte del espacio (lista de tareas, solo lectura)
2. QHBoxLayout inferior con tres botones: Nueva Tarea, Editar, Eliminar
3. Barra de estado inferior con contador de tareas

### Formulario de tarea: QDialog modal
Campos:
- QLineEdit para titulo (con validacion de campo requerido)
- QTextEdit para descripcion
- QCheckBox para estado completada/pendiente
- QDialogButtonBox con Aceptar/Cancelar

## Risks / Trade-offs

- [Baja] PyQt5 puede no estar instalado en el sistema del usuario → Se documentara `pip install PyQt5` en el README
- [Baja] SQLite no es concurrente para multiples procesos → No es relevante para una app de escritorio monousuario
- [Media] Separacion MVC puede ser excesiva para un MVP tan simple → Se mantiene por valor educativo y extension futura
