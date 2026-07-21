## ADDED Requirements

### Requirement: Ventana principal con lista de tareas
La aplicacion SHALL mostrar una ventana principal que contenga una tabla con todas las tareas almacenadas, mostrando las columnas: titulo, descripcion, estado y fecha de creacion.

#### Scenario: Apertura de la aplicacion
- **WHEN** el usuario inicia la aplicacion
- **THEN** se muestra una ventana con la tabla de tareas cargada desde la base de datos

#### Scenario: Refresco automatico tras operaciones
- **WHEN** el usuario crea, edita o elimina una tarea
- **THEN** la tabla se actualiza automaticamente para reflejar los cambios

### Requirement: Botones de accion CRUD
La aplicacion SHALL proporcionar botones claramente visibles para cada operacion: Crear, Editar y Eliminar.

#### Scenario: Botones visibles
- **WHEN** la ventana principal esta abierta
- **THEN** los botones "Nueva Tarea", "Editar" y "Eliminar" estan visibles y habilitados

### Requirement: Formulario de creacion/edicion de tarea
La aplicacion SHALL mostrar un dialogo o formulario modal para crear una nueva tarea o editar una existente, con campos para titulo, descripcion y un checkbox de completada.

#### Scenario: Abrir formulario para nueva tarea
- **WHEN** el usuario presiona "Nueva Tarea"
- **THEN** se abre un dialogo con campos vacios de titulo, descripcion y checkbox de completada desmarcado

#### Scenario: Abrir formulario para editar tarea
- **WHEN** el usuario selecciona una tarea y presiona "Editar"
- **THEN** se abre un dialogo con los datos actuales de la tarea precargados

#### Scenario: Validacion de titulo requerido
- **WHEN** el usuario intenta guardar una tarea sin titulo
- **THEN** el sistema muestra un mensaje de error indicando que el titulo es obligatorio

### Requirement: Confirmacion al eliminar
La aplicacion SHALL solicitar confirmacion antes de eliminar una tarea.

#### Scenario: Confirmar eliminacion
- **WHEN** el usuario selecciona una tarea y presiona "Eliminar"
- **THEN** se muestra un dialogo de confirmacion con "Aceptar" y "Cancelar"

#### Scenario: Cancelar eliminacion
- **WHEN** el usuario presiona "Cancelar" en el dialogo de confirmacion
- **THEN** la tarea no se elimina y la tabla permanece sin cambios
