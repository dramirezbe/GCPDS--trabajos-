# Sub-agentes en paralelo

> Vas a ver cómo un orquestador delega tareas a sub-agentes simultáneos para evitar la acumulación de contexto.

## Prerequisitos

- Claude Code con las reglas de delegación configuradas en `CLAUDE.md`
- El proyecto `stream-web` clonado (o cualquier proyecto con archivos JS y CSS diferenciados)

## Contexto

Un agente que hace todo solo acumula tokens con cada archivo que lee y cada análisis que hace. Eventualmente llega al límite de contexto, se dispara la compactación, y pierde estado. El patrón orquestador/sub-agente resuelve esto: el orquestador se mantiene flaco (solo coordina), y cada sub-agente trabaja con contexto fresco y aislado. Cuando termina, devuelve solo el resumen. Los tokens pesados mueren con el sub-agente.

## Ejercicio

### Paso 1: Pedir dos investigaciones independientes

```prompt
Necesito dos investigaciones independientes:
1. Investigá cómo está estructurado el JavaScript de este proyecto — qué hace app.js, cómo maneja la navegación y los eventos
2. Investigá cómo están organizados los estilos CSS — qué sistema de diseño usa, variables, breakpoints, y estructura de clases
```

Fijate que el orquestador no investiga él mismo. Lanza DOS sub-agentes en paralelo porque son dominios completamente distintos: JS por un lado, CSS por otro. No hay dependencia entre los hallazgos.

### Paso 2: Observar la ejecución paralela

Mientras se ejecutan, vas a ver dos bloques de `Task` corriendo al mismo tiempo. Cada uno:
- Tiene contexto fresco (no arrastra tokens del otro)
- Lee solo los archivos que necesita (uno lee `.js`, el otro lee `.css`)
- Devuelve un resumen conciso

El orquestador es flaco: no lee código, no escribe código. Solo coordina.

### Paso 3: Ver la síntesis

Cuando los dos sub-agentes terminan, el orquestador combina los resultados en una respuesta unificada. Fijate que no se perdió contexto del hilo principal, cada agente trabajó con su propio scope, y el resultado final es coherente.

### Paso 4: Repetir con otro par de temas

```prompt
Ahora investigá qué agentes de IA soporta Engram y qué fases tiene el workflow SDD
```

De nuevo, dos temas completamente no relacionados. Vas a ver el mismo patrón: el orquestador lanza dos agentes, cada uno busca su tema, y después sintetiza. Si hiciera todo inline, cada archivo que lee serían tokens acumulándose en el contexto principal.

## ¿Qué pasó?

El patrón orquestador/sub-agente evita la acumulación de contexto que causa compactación y pérdida de estado. Cada agente trabaja en aislamiento y devuelve solo el resumen. El orquestador se mantiene liviano y puede seguir coordinando sin degradarse. Si necesitás 5 análisis, lanza 5 sub-agentes. Escala sin explotar el contexto.

## Para pensar

- ¿En qué casos paralelizar sería PEOR que un solo agente? Pensá en tareas donde el resultado de una depende del resultado de la otra.
- Si el orquestador no lee código, ¿cómo puede saber si un sub-agente le devolvió un resumen incorrecto o incompleto?
