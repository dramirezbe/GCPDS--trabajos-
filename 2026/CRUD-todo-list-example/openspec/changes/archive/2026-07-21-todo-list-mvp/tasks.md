## 1. Estructura del proyecto y dependencias

- [x] 1.1 Crear archivo `requirements.txt` con PyQt5
- [x] 1.2 Crear archivo `main.py` como punto de entrada vacio
- [x] 1.3 Verificar que `sqlite3` y `PyQt5` estan disponibles en el entorno

## 2. Capa de datos (models.py)

- [x] 2.1 Implementar funcion `init_db()` que crea la tabla `tasks` si no existe
- [x] 2.2 Implementar funcion `create_task(title, description)` que inserta una tarea
- [x] 2.3 Implementar funcion `get_all_tasks()` que retorna todas las tareas
- [x] 2.4 Implementar funcion `update_task(task_id, title, description, completed)` que actualiza una tarea
- [x] 2.5 Implementar funcion `delete_task(task_id)` que elimina una tarea por id

## 3. Ventana principal (views.py)

- [x] 3.1 Crear clase `MainWindow(QMainWindow)` con layout vertical
- [x] 3.2 Agregar `QTableWidget` con columnas: Titulo, Descripcion, Estado, Creado
- [x] 3.3 Agregar `QHBoxLayout` inferior con botones: Nueva Tarea, Editar, Eliminar
- [x] 3.4 Agregar barra de estado con contador de tareas
- [x] 3.5 Implementar metodo `refresh_table()` que carga datos a la tabla desde la BD
- [x] 3.6 Obtener la tarea seleccionada en la tabla (helper `selected_task_id()`)

## 4. Dialogo de formulario (views.py)

- [x] 4.1 Crear clase `TaskDialog(QDialog)` con campos: titulo, descripcion, completada
- [x] 4.2 Soportar modo "crear" (campos vacios) y modo "editar" (datos precargados)
- [x] 4.3 Validar que el titulo no este vacio al aceptar (mostrar QMessageBox si falta)
- [x] 4.4 Botones Aceptar/Cancelar via `QDialogButtonBox`

## 5. Logica de control (controllers.py)

- [x] 5.1 Implementar funcion `on_new_task(main_window)` que abre TaskDialog en modo crear y guarda la tarea
- [x] 5.2 Implementar funcion `on_edit_task(main_window)` que abre TaskDialog en modo editar con datos actuales y actualiza la tarea
- [x] 5.3 Implementar funcion `on_delete_task(main_window)` que pide confirmacion y elimina la tarea seleccionada

## 6. Integracion y punto de entrada (main.py)

- [x] 6.1 Conectar botones de `MainWindow` con funciones de `controllers.py`
- [x] 6.2 Conectar `refresh_table()` despues de cada operacion CRUD exitosa
- [x] 6.3 Implementar `main()` que inicia QApplication, inicializa BD y muestra MainWindow
