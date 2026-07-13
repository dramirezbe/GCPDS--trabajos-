# Skills: Contexto preciso bajo demanda

> Vas a ver cómo los skills cargan instrucciones específicas solo cuando se necesitan, en vez de un archivo monolítico que contamina cada sesión.

## Prerequisitos

- La carpeta `~/.claude/skills/` con al menos los skills de `react-19` y `typescript`
- Claude Code abierto en un proyecto

## Contexto

El enfoque ingenuo es meter TODAS las instrucciones del agente en un solo archivo: convenciones de React, reglas de TypeScript, patrones de testing, configuración de Tailwind... todo junto, todo el tiempo. Eso son fácilmente 2400 líneas cargadas en el contexto ANTES de que escribas un solo prompt. Cada token de instrucciones es un token menos para tu código. Los skills resuelven esto: son módulos independientes que se cargan solo cuando el contexto lo requiere.

## Ejercicio

### Paso 1: Ver la estructura de skills

```bash
eza --tree ~/.claude/skills/ --level 1
```

Vas a ver que cada skill es una carpeta con un `SKILL.md`. React, TypeScript, Tailwind, Zustand, Next.js — cada uno con sus reglas específicas. No se cargan todos a la vez.

### Paso 2: Disparar un skill automáticamente

```prompt
Creá un componente React para mostrar una lista de usuarios con nombre y email. Usá TypeScript.
```

Fijate en el output: Claude lee `~/.claude/skills/react-19/SKILL.md` y `~/.claude/skills/typescript/SKILL.md` ANTES de escribir código. Detectó React y TypeScript en el pedido, cargó los dos skills automáticamente, y el código sigue las convenciones definidas ahí — no es código genérico.

### Paso 3: Inspeccionar las reglas de un skill

```bash
bat ~/.claude/skills/react-19/SKILL.md --line-range 10:50
```

Vas a ver reglas concretas: no usar `useMemo`/`useCallback` porque React Compiler lo maneja, usar function declarations, naming conventions. Son las reglas de TU equipo, no las defaults de Claude.

### Paso 4: Dimensionar la diferencia

Pensá en los números:
- Un `SKILL.md` típico tiene ~80 líneas
- Un `AGENTS.md` monolítico puede tener 2400+ líneas cargadas TODO EL TIEMPO
- Con skills, solo se carga lo relevante al contexto actual
- Menos tokens de instrucciones = más espacio para tu código = menos compactación

Es como la diferencia entre cargar toda la enciclopedia vs abrir el capítulo que necesitás.

## ¿Qué pasó?

Los skills son contexto modular y bajo demanda. En vez de contaminar cada sesión con miles de líneas de instrucciones, se cargan solo las reglas relevantes al trabajo actual. El agente detecta el contexto (React, TypeScript, Tailwind) y carga los skills correspondientes antes de escribir una sola línea de código. Esto mantiene el contexto limpio y las instrucciones precisas.

## Para pensar

- ¿Qué pasaría si tuvieras skills con las convenciones específicas de tu empresa? ¿Cómo cambiaría el onboarding de un dev nuevo que usa agentes?
- Si un skill tiene una regla incorrecta, ¿cuánto código incorrecto puede generar el agente antes de que alguien se dé cuenta?
