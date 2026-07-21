## ADDED Requirements

### Requirement: Crear una tarea
El sistema SHALL permitir crear una nueva tarea con un titulo y una descripcion opcional. La tarea se almacenara con estado "pendiente" y una fecha de creacion automatica.

#### Scenario: Crear tarea con titulo y descripcion
- **WHEN** el usuario proporciona un titulo "Comprar leche" y una descripcion "En el supermercado de la esquina"
- **THEN** el sistema crea una tarea con esos datos, estado "pendiente" y fecha actual

#### Scenario: Crear tarea sin descripcion
- **WHEN** el usuario proporciona solo un titulo "Llamar al medico" sin descripcion
- **THEN** el sistema crea una tarea con descripcion vacia, estado "pendiente" y fecha actual

### Requirement: Listar tareas
El sistema SHALL mostrar todas las tareas existentes en la base de datos, incluyendo su id, titulo, descripcion, estado y fecha de creacion.

#### Scenario: Listar tareas existentes
- **WHEN** existen multiples tareas en la base de datos
- **THEN** el sistema retorna una lista con todas las tareas y sus campos completos

#### Scenario: Listar sin tareas
- **WHEN** no hay tareas en la base de datos
- **THEN** el sistema retorna una lista vacia

### Requirement: Actualizar una tarea
El sistema SHALL permitir modificar el titulo, descripcion y/o estado de una tarea existente identificada por su id.

#### Scenario: Marcar tarea como completada
- **WHEN** el usuario cambia el estado de una tarea a "completada"
- **THEN** el sistema actualiza el campo estado de la tarea correspondiente

#### Scenario: Editar titulo y descripcion
- **WHEN** el usuario modifica el titulo y la descripcion de una tarea existente
- **THEN** el sistema actualiza ambos campos manteniendo el id, estado y fecha originales

### Requirement: Eliminar una tarea
El sistema SHALL permitir eliminar una tarea existente identificada por su id.

#### Scenario: Eliminar tarea existente
- **WHEN** el usuario solicita eliminar una tarea con un id valido
- **THEN** el sistema elimina la tarea de la base de datos

#### Scenario: Eliminar tarea inexistente
- **WHEN** el usuario intenta eliminar una tarea con un id que no existe
- **THEN** el sistema no produce errores y la operacion es idempotente
