# Ejercicio: SDD — De idea a dashboard en minutos

> Vas a usar Spec-Driven Development para generar un dashboard de ciberseguridad completo desde cero. Sin escribir una línea de código manualmente.

## Prerequisitos

- Claude Code instalado y configurado
- Agent Teams Lite activo (CLAUDE.md con reglas de orquestación)
- Engram funcionando (para persistencia entre fases)
- Una carpeta vacía para el proyecto (ej: `mkdir ~/cyber-dashboard && cd ~/cyber-dashboard`)

## Contexto

"Vibe coding" es tirarle un prompt al agente y rezar para que salga algo potable. A veces funciona, a veces te genera un Frankenstein de código que no podés mantener ni explicar. SDD es lo opuesto: en vez de "haceme un dashboard", pasás por un pipeline de ingeniería — explorar, proponer, especificar, diseñar, descomponer en tareas, implementar, verificar. Cada fase la ejecuta un sub-agente con contexto limpio que produce un artefacto revisable. El resultado no es "lo que al LLM se le cantó generar", sino código que cumple especificaciones concretas que vos definiste.

## Ejercicio

### Paso 1: Iniciar el cambio

```prompt
/sdd-new cyber-dashboard
```

Cuando te pregunte de qué se trata, explicale:

```prompt
Quiero crear un dashboard de ciberseguridad en un solo archivo HTML con CSS y JS inline. Tema visual Kanagawa Blur (fondo #1A1B26, cards #24283B con glassmorphism). Debe tener: header con título "Security Dashboard" y badge de status verde, 4 cards de severidad (Critical rojo #F7768E, High naranja #FF9E64, Medium amarillo #DFBD76, Low azul #7AA2F7) con contadores animados, un gráfico de barras horizontal mostrando vulnerabilidades por provider (AWS, GCP, Azure), animaciones de entrada staggered, hover con glow, y la barra de status con pulse breathing. Data hardcodeada pero realista.
```

Vas a ver que SDD lanza un Explorer que analiza los requerimientos y después un Proposer que genera una propuesta formal con scope, approach y rollback plan. Fijate que son dos sub-agentes distintos, cada uno con contexto fresco.

### Paso 2: Generar especificaciones y diseño

```prompt
/sdd-continue
```

Esto genera specs en formato Given/When/Then — lo que el dashboard DEBE cumplir. No es código, son criterios de aceptación verificables.

```prompt
/sdd-continue
```

Ahora se genera el design: decisiones técnicas, estructura del archivo, patrones a usar. Specs y design pueden salir en cualquier orden porque son paralelas en el DAG de dependencias — eso es normal.

### Paso 3: Generar tareas

```prompt
/sdd-continue
```

El Task Planner lee las specs + design y genera un plan de ejecución concreto: tareas numeradas, ordenadas, con criterios de aceptación individuales. Fijate que cada tarea es chica y enfocada — no es "hacé todo el dashboard".

### Paso 4: Implementar

```prompt
/sdd-apply
```

Recién ACÁ se escribe código. El Implementer arranca con contexto limpio, lee las tareas + specs + design, y genera el HTML/CSS/JS contra esos artefactos. No improvisa: implementa lo que se especificó.

### Paso 5: Verificar

```prompt
/sdd-verify
```

El Verificador chequea la implementación CONTRA las specs del paso 2. No es "me parece que está bien" — es verificación sistemática spec por spec. Vas a ver un reporte con qué pasó y qué falló.

### Paso 6: Ver el resultado

```bash
open index.html
```

Abrí el archivo en el browser. Vas a ver las cards con glassmorphism apareciendo con fade staggered, los números de severidad contando desde cero, las barras del chart creciendo de izquierda a derecha, y el badge verde respirando con un pulse suave. Todo en una paleta Kanagawa Blur sobre fondo oscuro.

## ¿Qué pasó?

Generaste un dashboard completo con 6 sub-agentes, cada uno con contexto limpio, cada uno produciendo un artefacto revisable. La idea pasó por exploración, propuesta, especificación, diseño, descomposición en tareas, implementación y verificación. Eso NO es vibe coding — es ingeniería con agentes.

La diferencia clave: cada línea de código tiene una spec detrás. Si algo no funciona, sabés exactamente qué spec se rompió, en qué fase se definió, y dónde corregirlo. Cuando le tirás un prompt suelto a un chat y rezás, no tenés nada de eso.

```
idea → explore → proposal → specs + design → tasks → apply → verify
                                                        ↑
                                             cada fase es un agente
                                             con contexto limpio
```

## Para pensar

- ¿Qué fase atraparía la mayoría de los bugs ANTES de que lleguen a producción? ¿Por qué esa y no otra?
- Si le pidieras este mismo dashboard a un chat sin SDD, ¿qué cosas podrían salir diferentes? ¿Qué se perdería?
