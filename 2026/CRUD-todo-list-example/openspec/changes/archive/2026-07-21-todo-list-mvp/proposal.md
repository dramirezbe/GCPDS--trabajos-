## Why

Se necesita una aplicacion de escritorio tipo todo-list que demuestre operaciones CRUD basicas como herramienta educativa y de referencia. La combinacion Python + SQLite + PyQt permite una solucion autocontenida, portatil y sin dependencias externas de servidor.

## What Changes

- Nueva aplicacion de escritorio con interfaz grafica PyQt
- Persistencia local mediante base de datos SQLite
- Operaciones CRUD completas: crear, leer, actualizar y eliminar tareas
- Cada tarea incluye: titulo, descripcion, estado (pendiente/completada) y fecha de creacion

## Capabilities

### New Capabilities
- `task-crud`: Crear, listar, editar y eliminar tareas en una base de datos SQLite local
- `gui-todo-list`: Interfaz grafica con PyQt que muestra la lista de tareas y permite interactuar con ellas mediante botones y formularios

### Modified Capabilities
<!-- None - this is a new project -->

## Impact

- Nuevo proyecto autocontenido en `2026/CRUD-todo-list-example/`
- Dependencias: Python >= 3.9, PyQt5 o PyQt6, modulo sqlite3 (stdlib)
- Sin impacto en otros proyectos del monorepo
- Sin dependencias de red ni servicios externos
