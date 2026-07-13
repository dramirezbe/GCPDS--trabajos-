# Engram: Memoria persistente para agentes

> Vas a experimentar cómo un agente de IA puede recordar decisiones entre sesiones usando Engram.

## Prerequisitos

- Claude Code instalado y funcionando
- Engram configurado (el protocolo en tu `CLAUDE.md`)
- Un proyecto abierto en el que puedas tomar decisiones de arquitectura

## Contexto

Los agentes de IA son **stateless por defecto**. Cada vez que abrís una sesión nueva, el agente arranca de cero: no sabe qué decidiste ayer, qué convenciones definiste, ni qué bugs resolviste. Es como trabajar con un dev que tiene amnesia todos los días. Engram resuelve esto agregando una capa de memoria persistente que sobrevive entre sesiones, sin que tengas que repetirte.

## Ejercicio

### Paso 1: Tomar una decisión arquitectónica

Abrí Claude Code en tu proyecto y mandá este prompt:

```prompt
Quiero usar Clean Architecture con inyección de dependencias en este proyecto. Las capas van a ser: domain, application, infrastructure, presentation. Usemos un patrón de repositorio para el acceso a datos.
```

Fijate en el output que Claude hace un `mem_save` automáticamente. Nadie se lo pidió: el protocolo de Engram lo dispara solo cuando detecta una decisión de arquitectura.

### Paso 2: Verificar que se guardó

```prompt
Qué decisiones de arquitectura tenemos registradas?
```

Vas a ver que Claude hace un `mem_search` y recupera la decisión. Observá el `topic_key` que le asignó, algo como `architecture/clean-architecture`.

### Paso 3: Cerrar la sesión correctamente

```prompt
Listo, cerramos sesión
```

Esperá a que Claude ejecute el `mem_session_summary` antes de salir. Recién cuando termine, usá `/exit`. Si hacés Ctrl+C directo, matás el proceso sin darle chance de guardar el resumen.

### Paso 4: Abrir una nueva sesión

Abrí Claude Code de nuevo en el mismo proyecto:

```bash
claude
```

```prompt
Qué arquitectura decidimos usar para este proyecto?
```

Vas a ver que Claude hace `mem_context` + `mem_search` y recupera la decisión de Clean Architecture con las capas exactas. Sin Engram, esto se habría perdido al cerrar la terminal.

### Paso 5: Verificar desde el CLI

En otra terminal, probá la búsqueda directa:

```bash
engram search "arquitectura" --project stream-web
```

Fijate que Engram tiene CLI propia. Podés buscar memorias sin abrir Claude Code. Por debajo es una base de datos SQLite con FTS5 (full-text search nativo).

## ¿Qué pasó?

Engram convierte a un agente sin estado en un sistema con memoria persistente. Las decisiones, convenciones y descubrimientos se guardan automáticamente y se recuperan en sesiones futuras. No es magia: es un protocolo que dispara `mem_save` ante ciertos triggers (decisiones, bugfixes, descubrimientos) y `mem_context` al inicio de cada sesión.

## Para pensar

- ¿Qué pasa en un proyecto donde 3 devs usan el mismo agente pero no comparten memoria? ¿Cuántas decisiones de arquitectura se repiten o se contradicen?
- Si el agente "recuerda" una decisión incorrecta, ¿cómo impacta eso en todo el código que genera después?
