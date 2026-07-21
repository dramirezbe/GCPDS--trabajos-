# Estado del Arte: Agentes de Código y Desarrollo Guiado por Especificaciones (SDD)

**Público Objetivo:** Ingenieros de Software, Líderes Técnicos, Estudiantes de Ingeniería
**Prerrequisitos:** Familiaridad básica con CLI, una cuenta de GitHub, un editor de código
**Ejemplo Guía:** Construcción de una caja de herramientas de Procesamiento Digital de Señales (DSP) — usaremos un **Diseñador de Filtros FIR** como hilo conductor que une cada fase.

---

## 1. Estado del Arte: Desarrollo Guiado por Especificaciones (SDD)

### 1.1 El Problema que Resuelve

En 2024, Princeton y Stanford publicaron [SWE-bench](https://swebench.com) — un benchmark de issues reales de GitHub. Los mejores agentes de IA resolvieron aproximadamente el 20% de ellos. A mediados de 2025, [mini-swe-agent](https://mini-swe-agent.com) — un **script de Python de 100 líneas** — resolvió el **74%** en el mismo benchmark.

La diferencia no fue un modelo más inteligente. Fue un mejor *contrato* entre el humano y la máquina.

| Era | Flujo de Trabajo | Resultado |
|---|---|---|
| "Vibe coding" (2023–2024) | El humano escribe un prompt vago → la IA genera código → el humano lo prueba manualmente, descubre requisitos faltantes, vuelve a hacer prompt | Inconsistente, ciclo de retroalimentación lento, sin barreras de protección |
| **Desarrollo Guiado por Especificaciones (2025–presente)** | El humano escribe un `spec.md` explícito → la IA lo lee, propone un `plan.md` → el humano aprueba el plan → la IA genera `tasks.md` y los ejecuta uno por uno, validando cada uno contra la especificación | Determinista, auditable, el humano mantiene el control |

### 1.2 Principios Fundamentales

*   **La Especificación es la Verdad.** En lugar de que el código sea la fuente última de verdad, la especificación se convierte en un contrato ejecutable. Si el código y la especificación discrepan, la especificación prevalece.
*   **Rol del Humano — Qué y Por Qué.** El desarrollador dicta la intención a través de reglas de negocio explícitas, invariantes, criterios de aceptación y límites arquitectónicos. El humano no escribe detalles de implementación.
*   **Rol de la IA — Cómo.** El código se convierte en un artefacto secundario, generado. El agente materializa el código y lo valida contra la especificación explícita.
*   **Progresión de Madurez.** Los equipos evolucionan de *"Spec-first"* (escribir especificación, generar código una vez) a *"Spec-anchored"* (especificación y código evolucionan simbióticamente, impuestos por testing continuo y validación en cada cambio).

### 1.3 El SOTA en Una Frase

> **La simplicidad gana.** Los agentes con mejor rendimiento (mini-swe-agent, Claude Code) no son los que tienen más andamiaje — son los que tienen el ciclo de retroalimentación más cerrado entre especificación, código y verificación.

---

## 2. La Pila de Extensiones del Agente

Los agentes de código modernos son modulares. Piensa en ellos como una **cadena de señal**: cada componente procesa una parte específica del problema sin acoplarse a los demás — tal como una etapa de amplificador, un filtro y un ADC en un pipeline de instrumentación.

```
┌──────────────────────────────────────────────────┐
│                    HOST                          │
│  (OpenCode, Claude Code, Cursor, Codex CLI)      │
│  El motor de razonamiento — el "cerebro"         │
├──────────────────────────────────────────────────┤
│  SKILLS  │  MCP Servers  │  PLUGINS  │ SUBAGENTS │
│  Instruc-│  Conectores   │  Paquetes │ Contextos │
│  ciones  │  a sistemas   │  empaque- │ aislados  │
│  bajo    │  externos     │  tados    │ para      │
│  demanda │  y APIs       │  para     │ tareas    │
│          │               │  equipos  │ pesadas   │
└──────────────────────────────────────────────────┘
```

### 2.1 El Host

El **host** es el motor de razonamiento central — el LLM ejecutándose dentro de un CLI o IDE. Ejemplos: OpenCode, Claude Code, Cursor, GitHub Copilot, Codex CLI. El host orquesta todo: lee tu especificación, carga skills, llama herramientas MCP, genera subagentes y ejecuta comandos. No necesitas entender sus componentes internos. Tú lo diriges.

### 2.2 Skills — `SKILL.md`

> **Qué es:** Un archivo markdown con control de versiones que enseña al agente convenciones, flujos de trabajo y conocimiento de dominio para tu proyecto. Las skills se cargan **bajo demanda**, no en cada conversación — mantienen el contexto ligero.

#### Anatomía de un SKILL.md

Una skill es un directorio que contiene un archivo `SKILL.md` con frontmatter YAML:

```
tu-proyecto/
├── .agents/
│   └── skills/
│       └── dsp-conventions/
│           └── SKILL.md
```

```markdown
---
name: dsp-conventions
description: DSP coding conventions — fixed-point arithmetic, 
             filter coefficient formats, and test patterns
---

# DSP Conventions for This Repo

- All filter coefficients stored as Q15 fixed-point (int16_t).
- Frequency-domain tests use known-input/known-output golden files.
- FIR implementation must match the direct-form structure from 
  Oppenheim & Schafer, Chapter 6.
- Test commands: `pytest tests/ --cov=src/ --cov-report=term`
```

#### Cuándo usar una Skill vs. un System Prompt

| Mecanismo | Alcance | Vive en |
|---|---|---|
| **Skill** | Específica del proyecto, cargada solo cuando es relevante | `.agents/skills/<nombre>/SKILL.md` |
| **System Prompt / AGENTS.md** | Siempre cargado al inicio de la sesión | `AGENTS.md` en la raíz del proyecto |

Las skills son para conocimiento de dominio. Los system prompts son para reglas universales ("nunca commits de secretos", "usar sintaxis de módulos ES").

#### Descubrimiento de Skills

El agente puede listar las skills disponibles en cualquier momento. Un registro de skills (`.atl/skill-registry.md`) las indexa por frase disparadora y ruta para que el agente sepa cuál skill cargar.

### 2.3 MCP — Model Context Protocol

> **Qué es:** Un estándar de código abierto (como USB-C para IA). Los servidores MCP proporcionan a los agentes una forma estandarizada y segura de conectarse a sistemas externos — bases de datos, APIs, sistemas de archivos, gestores de issues. El agente descubre las herramientas MCP disponibles y las invoca.

**Sitio oficial:** [modelcontextprotocol.io](https://modelcontextprotocol.io)

#### Arquitectura MCP

```
┌──────────┐     JSON-RPC      ┌──────────────┐
│  HOST    │ ◄──────────────► │  MCP Server  │ ◄──► Sistema Externo
│ (Agente) │   (stdio/HTTP)    │  (tu código) │     (DB, API, HW)
└──────────┘                   └──────────────┘
```

- El **host** es el agente de IA (OpenCode, Claude Code, etc.)
- El **MCP server** es un programa que escribes/instalas que expone **tools**, **resources** y **prompts**
- El **sistema externo** es aquello a lo que necesitas conectarte — una base de datos, un generador de señales, Jira, GitHub

#### Ejemplo: Construyendo un MCP Server para Análisis de Señales

Imagina un MCP server que se conecta a un **generador de señales** o lee **archivos WAV**. El servidor expone:

```
Tools:
  - read_wav(path)        → retorna {sample_rate, samples, duration}
  - compute_fft(samples)  → retorna {frequencies, magnitudes}
  - apply_filter(samples, coeffs) → retorna muestras filtradas

Resources:
  - signal://<id>/metadata → metadatos estáticos sobre una captura

Prompts:
  - analyze_noisefloor    → plantilla de prompt para análisis de ruido
```

El servidor es un programa normal (Python, Node, Go) que habla JSON-RPC sobre stdio. El agente de IA lo descubre al inicio y puede llamar `read_wav("/data/capture.wav")` como si fuera una función incorporada.

#### Conceptos Clave de MCP

| Concepto | Significado | Ejemplo |
|---|---|---|
| **Tool** | Una acción que el agente puede invocar | `query_database(sql)`, `create_issue(title, body)` |
| **Resource** | Datos de solo lectura expuestos al agente | `file://docs/architecture.md`, `postgres://schema/users` |
| **Prompt** | Una plantilla de prompt reutilizable | "Analyze this signal for harmonic distortion" |

### 2.4 Plugins

> **Qué es:** Un paquete empaquetado de Skills + MCP servers + Hooks, distribuido como una sola unidad instalable. Los plugins aseguran que todo un equipo de ingeniería use el conjunto idéntico de comportamientos de IA, herramientas y convenciones.

**Cómo funcionan:** Alguien en tu organización empaqueta una skill ("nuestras convenciones de testing DSP"), un MCP server ("conectar a nuestra base de datos de señales") y un hook ("ejecutar lint antes de cada commit") en un plugin. Todos lo instalan una vez. Las actualizaciones se propagan a todo el equipo.

| Componente | Empaquetado en Plugin | Propósito |
|---|---|---|
| Skills | ✅ | Convenciones de dominio, flujos de trabajo |
| MCP Servers | ✅ | Conexiones de herramientas a sistemas de la organización |
| Hooks | ✅ | Scripts deterministas pre/post-acción |
| Subagentes | ✅ | Agentes de revisión especializados |

### 2.5 Subagentes — Aislamiento de Contexto

> **Este es el patrón más importante que aprenderás hoy.** Los subagentes son la respuesta a la restricción fundamental de la programación con IA: **la ventana de contexto se llena rápido, y la calidad se degrada a medida que se llena.**

#### El Problema

Cada archivo que el agente lee, cada salida de comando, cada turno de conversación — todo vive en una sola ventana de contexto (típicamente 200K tokens). Una sola sesión de debugging puede consumir decenas de miles de tokens. A medida que el contexto se llena:

- El agente "olvida" instrucciones anteriores
- Comete más errores
- Pierde el rastro de la especificación

#### La Solución: Subagentes

Un **subagente** es una sesión de agente fresca y aislada que recibe una tarea específica, hace el trabajo y retorna un **resumen** al agente principal. La lectura pesada y la iteración ocurren en el contexto del subagente, no en el tuyo.

```
┌─────────────────────┐
│   AGENTE PRINCIPAL  │
│   (contexto ligero) │
│                     │
│  "Lee la spec"      │
│  "Planifica el      │──────► ┌───────────────────┐
│   cambio"           │        │   SUBAGENTE A      │
│  "Genera subagente  │        │   (ctx aislado)    │
│   para implementar  │        │                    │
│   Tarea 3"          │        │ Lee 47 archivos    │
│                     │◄───────│ Implementa feature  │
│  Recibe resumen:    │        │ Ejecuta 200 tests  │
│  "Hecho. 3 archivos │        │ Retorna resumen    │
│   modificados, tests│        └───────────────────┘
│   pasan. Caso borde │
│   X necesita        │──────► ┌───────────────────┐
│   atención"         │        │   SUBAGENTE B      │
│                     │        │   (ctx fresco)     │
│  "Genera subagente  │        │                    │
│   revisor para      │        │ Lee solo el        │
│   revisar el diff"  │        │ diff + spec        │
│                     │◄───────│ Reporta: "Falta    │
│  Recibe feedback    │        │ caso borde Y"      │
│  directamente en    │        └───────────────────┘
│  sesión             │
└─────────────────────┘
```

#### Cuándo Usar Subagentes

| Escenario | Sin Subagente | Con Subagente |
|---|---|---|
| **Explorar un codebase nuevo** | El agente lee 60 archivos, el contexto está al 40% antes de empezar | El subagente lee 60 archivos, retorna un resumen de 500 palabras. El contexto se mantiene ligero. |
| **Implementar una tarea grande** | Toda la salida de debugging, fallos de tests e iteraciones se acumulan en una sesión | Cada tarea tiene su propio subagente. Los fallos no contaminan el contexto principal. |
| **Revisión de código** | El agente que escribió el código revisa su propio trabajo — puntos ciegos garantizados | Un subagente fresco ve solo el diff + spec. Detecta lo que el escritor pasó por alto. |

#### El Patrón de Agente Dual (Revisión Adversarial)

La práctica de calidad SOTA:

1. **Agente escritor** implementa la feature contra la especificación.
2. **Subagente revisor** recibe un contexto fresco, ve solo el diff + spec, y reporta: "¿Cada criterio de aceptación tiene un test? ¿Hay casos borde sin cobertura? ¿Se modificó algo fuera del alcance?"
3. El escritor corrige las brechas y vuelve a enviar.

Esto es el equivalente en programación del *señalización diferencial* — dos caminos independientes validan el resultado. El ruido (alucinaciones) que afecta a un camino es improbable que afecte a ambos de forma idéntica.

---

## 3. Gestión de Contexto — La Restricción Fundamental

### 3.1 Por Qué el Contexto lo Es Todo

Cada archivo leído, cada salida de comando, cada turno de conversación consume tokens de una ventana finita. Cuando la ventana se llena:

```
Calidad
  │  ████████████████░░░░░░░░░░  ← zona de degradación
  │  ████████████████████████░░
  │  ██████████████████████████
  │
  └──────────────────────────────► % de llenado de contexto
```

El documento de mejores prácticas de Claude Code es fundamentalmente un manual de gestión de contexto. Las estrategias principales:

### 3.2 Estrategias

| Estrategia | Cómo | Cuándo |
|---|---|---|
| **`/clear`** | Reiniciar contexto completamente entre tareas no relacionadas | Después de terminar una feature, antes de comenzar otra |
| **Subagentes** | Delegar lectura pesada a sesiones aisladas | Exploración de codebase, implementaciones grandes, revisión adversarial |
| **Compactación** | El agente resume mensajes antiguos, conserva decisiones clave | Sesiones largas que no se pueden dividir |
| **Modo plan** | El agente lee y planifica sin editar archivos | Cuando necesitas entender antes de actuar |
| **Nombrado de sesiones** | Nombrar sesiones como ramas de git (`fir-filter`, `fft-optimize`) | Flujos de trabajo de múltiples sesiones |

### 3.3 La Regla de Dos Correcciones

Si has corregido al agente más de **dos veces** sobre el mismo problema en una sesión:
1. El contexto está contaminado con enfoques fallidos.
2. Haz `/clear` y comienza fresco con un mejor prompt que incorpore lo que aprendiste.
3. Una sesión limpia con un prompt preciso supera a una sesión larga con correcciones acumuladas — siempre.

### 3.4 Modo Plan: Explorar Primero, Luego Programar

Para cualquier cosa más grande que una corrección de una línea:

```
1. EXPLORAR (modo plan)
   El agente lee archivos, responde preguntas, propone enfoque.
   No ocurren ediciones. Seguro para iterar.

2. PLANIFICAR (modo plan)
   El agente escribe spec.md → plan.md → tasks.md.
   El humano revisa y aprueba el plan.

3. IMPLEMENTAR (modo por defecto)
   El agente ejecuta tareas una por una.
   Los subagentes mantienen el contexto limpio.

4. REVISAR (subagente)
   Un agente fresco revisa el diff contra la spec.
   Las brechas se corrigen antes del merge.
```

---

## 4. El Ciclo de Verificación — El Motor que Hace Funcionar SDD

### 4.1 Los Tests No Son Opcionales

El predictor individual más grande de éxito en SDD: **¿el repositorio ya tiene tests?**

Sin tests, el agente no tiene ciclo de retroalimentación. Produce código, dice "parece listo" y espera a que tú encuentres los bugs. Tú te conviertes en el ciclo de verificación — lo cual derrota el propósito.

| Escenario | Comportamiento del Agente |
|---|---|
| ✅ Tests existen + CI pasa | El agente ejecuta tests después de cada cambio. Ciclo: código → test → falla → corrige → test → pasa. Autónomo. |
| ❌ Sin tests | El agente escribe código, dice "hecho." El humano prueba manualmente. El humano encuentra bugs. El humano vuelve a hacer prompt. Solo vibe coding rápido. |

### 4.2 Niveles de Verificación (del más débil al más fuerte)

| Nivel | Mecanismo | Ejemplo |
|---|---|---|
| **1. A nivel de prompt** | "Ejecuta los tests y corrige cualquier fallo" | Funciona para una tarea, no persiste entre tareas |
| **2. Condiciones objetivo** | `/goal "todos los tests pasan y lint está limpio"` | El agente vuelve a verificar después de cada turno automáticamente |
| **3. Hooks** | Un script que se ejecuta en cada guardado de archivo | `pre-save: pytest --lf` — determinista, no se puede omitir |
| **4. Revisión adversarial** | Un subagente separado revisa el diff | Detecta errores lógicos que el escritor no puede ver |

### 4.3 Qué Hace una Buena Verificación

Una buena verificación es:

- **Binaria** (pasa/falla, sin zona gris)
- **Rápida** (idealmente menos de 30 segundos)
- **Legible por el agente** (salida de tests, código de salida de build, salida de lint — no una GUI)
- **Cubre los criterios de aceptación de la especificación**

Para trabajo DSP, los tests de golden file son ideales: "Dada la señal de entrada X, después de aplicar el filtro con coeficientes Y, la salida debe coincidir con el golden file Z dentro de la tolerancia epsilon."

### 4.4 Evidencia, No Afirmaciones

Cuando el agente dice "los tests pasan," exige ver la salida. Nunca aceptes "se ve bien" como verificación. Quieres:

```
$ pytest tests/test_fir_filter.py -v
tests/test_fir_filter.py::test_lowpass_cutoff PASSED
tests/test_fir_filter.py::test_linear_phase PASSED
tests/test_fir_filter.py::test_coefficient_symmetry PASSED
=================== 3 passed in 0.42s ===================
```

La evidencia es más rápida de revisar que volver a ejecutar los tests tú mismo, y funciona para sesiones que no estabas monitoreando activamente.

---

## 5. Memoria y Persistencia — Engram + OpenSpec

Los agentes de IA son sin estado por defecto. Cada sesión comienza en blanco. Dos sistemas complementarios resuelven esto:

### 5.1 Engram — Memoria Persistente entre Sesiones

> **Qué es:** Un sistema de memoria que sobrevive entre sesiones. El agente guarda decisiones, bugs, convenciones y descubrimientos — y los recupera en sesiones futuras automáticamente.

```
Sesión 1                      Sesión 2 (días después)
────────                      ──────────────────────
"El filtro FIR usa formato    El agente carga auto-
 Q15 fixed-point"             máticamente: "El filtro
         │                    FIR usa formato Q15
         ▼                    fixed-point"
    mem_save()                         │
    ┌──────────────┐                   ▼
    │ Engram Store │            El agente genera código
    │ (SQLite FTS) │            usando Q15 — sin que
    └──────────────┘            tengas que re-explicarlo
```

#### Qué se Guarda (proactivamente, no manualmente)

| Disparador | Ejemplo |
|---|---|
| Decisión de arquitectura tomada | "Se eligió Q15 fixed-point sobre float32 para coeficientes de filtro" |
| Corrección de bug completada | "Corregido overflow en buffer FFT: causa raíz fue saturación de int16 a >32767 muestras" |
| Convención establecida | "Archivos golden test van en tests/fixtures/, nombrados <test>_input.wav y <test>_expected.wav" |
| Gotcha descubierto | "El driver ADC del STM32 retorna valores de 12 bits alineados a la izquierda en palabras de 16 bits — se debe desplazar a la derecha 4 bits" |
| Herramienta/librería elegida | "Usando `scipy.signal.firwin` para generación de coeficientes; `numpy` para vectores de test" |

#### Engram vs. Archivos

| | Archivos (spec.md, plan.md) | Engram |
|---|---|---|
| **Alcance** | Un proyecto, un cambio | Multi-proyecto, multi-sesión |
| **Contenido** | Requisitos formales, planes, tareas | Decisiones, bugs, gotchas, convenciones |
| **Tiempo de vida** | Archivado después de completar el cambio | Persiste indefinidamente |
| **Búsqueda** | grep | Búsqueda de texto completo en todas las sesiones |

### 5.2 OpenSpec — Contexto de Carpeta de Proyecto

> **Qué es:** Una convención de carpeta (`openspec/` o `sdd/`) dentro de cada proyecto que almacena la especificación, el plan y las tareas para el cambio actual. Este es el complemento con *alcance de proyecto* a la memoria *multi-sesión* de Engram.

```
tu-proyecto-dsp/
├── openspec/
│   ├── config.yaml          # Convenciones del proyecto (test runner, lint, TDD estricto)
│   ├── testing-capabilities.yaml  # Qué capas de test existen, objetivos de cobertura
│   └── changes/
│       └── fir-filter-designer/
│           ├── proposal.md   # Por qué este cambio, qué problema resuelve
│           ├── spec.md       # Requisitos, criterios de aceptación, límites de alcance
│           ├── design.md     # Decisiones de arquitectura, disposición de componentes
│           └── tasks.md      # Lista de tareas atómicas e independientemente entregables
├── src/
├── tests/
└── AGENTS.md                 # System prompt (siempre cargado)
```

#### Cómo se Complementan Engram y OpenSpec

```
┌─────────────────────────────────────────────────────────┐
│                   ENGRAM (persistente)                    │
│  "Convención Q15 fixed-point"                            │
│  "ADC STM32 retorna 12 bits alineados a la izq en 16"   │
│  "Golden files en tests/fixtures/"                       │
│  "Overflow a >32767 muestras en buffer FFT — corregido"  │
└─────────────────────────────────────────────────────────┘
                          │
                          │ alimenta
                          ▼
┌─────────────────────────────────────────────────────────┐
│              OPENSPEC (por proyecto/cambio)              │
│  spec.md: "Diseñador FIR para STM32 — formato Q15"     │
│  plan.md: "Usar DMA double-buffering + CMSIS-DSP lib"  │
│  tasks.md: "1. Struct FIR, 2. Cargador coeficientes..." │
└─────────────────────────────────────────────────────────┘
                          │
                          │ impulsa
                          ▼
┌─────────────────────────────────────────────────────────┐
│              EJECUCIÓN DEL AGENTE (sesión)               │
│  Implementa tareas contra spec, valida con tests,       │
│  guarda descubrimientos de vuelta en Engram              │
└─────────────────────────────────────────────────────────┘
```

El ciclo: Engram provee el contexto de "por qué hacemos las cosas así" → OpenSpec provee el "qué estamos construyendo ahora" → El agente ejecuta → Los descubrimientos fluyen de vuelta a Engram.

### 5.3 Cómo Inicializar SDD en un Proyecto

```
# Desde la raíz de tu proyecto:
> /sdd-init

El agente hará:
1. Detectar tu stack (Python, C, Go, etc.)
2. Encontrar tu test runner, linter, formateador
3. Crear carpeta openspec/ con config.yaml
4. Guardar capacidades en Engram
5. Reportar: "Listo. Siguiente: /sdd-explore para definir un cambio."
```

---

## 6. Metodología de Escritura de Especificaciones

Escribir una buena especificación es una habilidad. Una mala especificación produce mal código, sin importar qué tan bueno sea el agente.

### 6.1 Anatomía de un Buen `spec.md`

```markdown
# Change: FIR Filter Designer

## Intent
Provide a Python module that generates FIR filter coefficients
given user-specified parameters (cutoff frequency, filter order,
window type) and exports them as a C header file for embedded use.

## Acceptance Criteria
- [ ] Accepts: sample_rate (Hz), cutoff_freq (Hz), order (odd int),
      window_type (rectangular | hamming | hann | blackman)
- [ ] Rejects: order > 512 (memory constraint on STM32F4),
      cutoff_freq >= sample_rate/2 (Nyquist violation)
- [ ] Outputs coefficients in Q15 fixed-point format (int16_t array)
- [ ] Writes a valid C header: `const int16_t fir_coeffs[ORDER] = {...};`
- [ ] Provides frequency-response plot (matplotlib) for verification
- [ ] All functions have type hints and docstrings
- [ ] Unit tests cover: valid input, invalid input, Nyquist edge,
      each window type produces correct known-output

## Scope Boundaries
### In scope
- FIR coefficient generation via window method
- C header export
- Frequency response visualization

### Out of scope
- IIR filters (separate change)
- Real-time filtering on device (separate change)
- GUI for coefficient design (separate change)
- Adaptive filter algorithms (separate change)

## Verification
- `pytest tests/test_fir_designer.py -v` must pass
- `mypy src/` must be clean
- Golden test: hamming(128, cutoff=1000, fs=8000) must match
  `tests/fixtures/fir_hamming_128_1000hz.json` within 1e-6
```

### 6.2 Reglas de Escritura de Especificaciones

1. **Cada criterio de aceptación debe ser testeable.** "El filtro debe sonar bien" no es testeable. "La magnitud de salida a 2 kHz debe ser < -40 dB relativo a la banda de paso" es testeable.
2. **Los límites de alcance son tan importantes como los requisitos.** Decir qué está FUERA del alcance previene el scope creep y mantiene al agente enfocado.
3. **Incluye casos borde explícitamente.** "¿Qué pasa cuando el orden es par?" (rechazarlo). "¿Qué pasa exactamente en Nyquist?" (rechazarlo). El agente no puede adivinar esto.
4. **La verificación es parte de la especificación, no una idea tardía.** El comando exacto de test y la ruta del golden file van en la especificación.
5. **Usa ejemplos concretos.** Estilo "Dado X, cuando Y, entonces Z".

### 6.3 El Patrón "Given-When-Then" (Estilo Gherkin)

```
Scenario: Low-pass filter with Hamming window
  Given a sample rate of 8000 Hz
  And a cutoff frequency of 1000 Hz
  And a filter order of 128
  And window type "hamming"
  When the FIR designer generates coefficients
  Then the coefficient array must be symmetric
  And the passband ripple must be < 0.1 dB
  And the stopband attenuation must be > 50 dB
  And the output must match golden file fir_hamming_128_1000hz.json
```

---

## 7. Seguridad y Sandboxing

### 7.1 La Realidad de la Cadena de Suministro

Cada MCP server, cada skill, cada plugin es código que se ejecuta en tu máquina. Un agente con permisos de escritura de archivos y ejecución de comandos tiene el poder de modificar tu sistema. La pregunta no es "¿deberíamos confiar en él?" sino "¿cómo limitamos el radio de explosión?"

### 7.2 Enfoques de Sandboxing

| Enfoque | Qué Hace | Cuándo Usarlo |
|---|---|---|
| **Listas blancas de permisos** | Solo permitir comandos específicos (`git commit`, `npm test`, nunca `rm -rf`) | Desarrollo cotidiano |
| **Sandbox Docker** | El agente se ejecuta dentro de un contenedor con acceso limitado al sistema de archivos | Generación de código no confiable |
| **Modo plan** | El agente lee y planifica pero no puede editar archivos | Fase de exploración |
| **Aprobación manual** | El agente solicita permiso para cada acción | Operaciones de alto riesgo |
| **Aislamiento de subprocesos** | Cada acción es un `subprocess.run` independiente — sin shell persistente con estado acumulado | Diseño central de mini-swe-agent |

### 7.3 Principio de Mínimo Privilegio

Un agente que implementa un diseñador de filtros FIR necesita:
- ✅ Acceso de lectura a `src/`, `tests/`
- ✅ Acceso de escritura a `src/fir_designer.py`, `tests/test_fir_designer.py`
- ✅ Ejecutar: `python`, `pytest`, `mypy`, `git`
- ❌ Acceso de red (no necesario)
- ❌ Acceso de escritura a `setup.py`, `requirements.txt` (fuera del alcance)
- ❌ `rm`, `sudo`, `chmod`

### 7.4 Contexto Empresarial

En un entorno empresarial, los MCP servers y skills son **dependencias de cadena de suministro** — deben estar versionados, escaneados, firmados y auditados tal como los paquetes `npm` o las dependencias `pip`. Una skill que enseña a tu agente convenciones de migración de base de datos es tan crítica como el framework de migración mismo.

---

## 8. Diseño del Taller

**Duración:** 2.5 Horas (30 min agregados para verificación de prerrequisitos)
**Formato:** Práctico, con un repositorio inicial limpio proporcionado
**Ejemplo Guía (todas las fases):** Diseñador de Filtros FIR para DSP Embebido

### Pre-Taller: Configuración del Estudiante (hacer esto antes de llegar)

- [ ] Instalar el agente de código con IA (OpenCode, Claude Code o equivalente)
- [ ] Clonar el repositorio inicial del taller (un proyecto Python mínimo con `pytest`, `mypy` y `AGENTS.md` ya configurados)
- [ ] Verificar: `pytest` pasa, `mypy` está limpio
- [ ] Leer el `AGENTS.md` — describe las convenciones del proyecto

### Fase 0 — README → Verificación (5 min, incluido en la Fase 1)

Punto de enseñanza: **Si los tests no se ejecutan, SDD no puede funcionar. El ciclo de verificación es el motor.** Haz que cada estudiante ejecute `pytest` y confirme que pasa antes de comenzar. Esto no es negociable.

### Agenda y Cronograma

```
0:00 ─────────────────────────────────────────────── 2:30
│                                                        │
│  INTRO    │ FASE 1  │ FASE 2  │   FASE 3    │ FASE 4 │
│  (20 min) │(30 min) │(25 min) │  (60 min)   │(15 min)│
│           │         │         │             │        │
│  SDD +    │Escribir │Generar  │ Implementar │ Retro  │
│  Stack +  │ spec.md │plan.md  │ con sub-    │ +      │
│  Contexto │         │tasks.md │ agentes +   │ Seg    │
│  Mgmt     │         │         │ revisión    │        │
│           │         │         │ adversarial │        │
```

#### 0:00–0:20 — Introducción: SDD, La Pila y Gestión de Contexto

**Contenido:**

1. **La Filosofía SDD (5 min)**
   - Vibe coding → Desarrollo Guiado por Especificaciones
   - Prueba SWE-bench: agente de 100 líneas resuelve el 74% de issues reales de GitHub
   - La especificación es la verdad; el código es derivado

2. **La Pila del Agente (5 min)**
   - Host, Skills, MCP, Plugins, Subagentes
   - Analogía: cadena de señal — cada etapa procesa independientemente
   - MCP como USB-C para IA

3. **Gestión de Contexto (10 min)**
   - La ventana de contexto es la restricción fundamental
   - Los subagentes mantienen el contexto limpio
   - La regla de dos correcciones
   - Modo plan: explorar → planificar → implementar → revisar
   - Engram (memoria persistente) + OpenSpec (contexto de proyecto)

#### 0:20–0:50 — Fase 1: Escribir la Especificación

**Tarea:** Los estudiantes escriben `spec.md` para el Diseñador de Filtros FIR.

**Entregado a los estudiantes:**
- Esqueleto de proyecto con `pytest`, `mypy` y `AGENTS.md` ya configurados
- Una plantilla de prompt:
  ```
  I want to build an FIR filter coefficient designer.
  It should generate coefficients via the window method,
  export them as a C header for STM32, and visualize
  the frequency response. Help me write a spec.md.
  Interview me to clarify requirements I might miss.
  ```

**Puntos de enseñanza durante la Fase 1:**
- Deja que el agente te ENTREVISTE — detectará casos borde que no pensaste (Nyquist, rechazo de orden par, overflow en órdenes altos)
- Cada criterio de aceptación debe ser testeable
- Los límites de alcance importan: ¿qué está explícitamente fuera del alcance?
- Los tests de golden-file son el mejor amigo del desarrollador DSP

**Entregable:** Una especificación con intención, criterios de aceptación, límites de alcance, casos borde y comandos de verificación explícitos.

#### 0:50–1:15 — Fase 2: Generar Plan y Tareas

**Tarea:** Los estudiantes hacen prompt al agente para que lea `spec.md` y produzca `plan.md` + `tasks.md`.

**Puntos de enseñanza:**
- El humano revisa el PLAN, no solo el código final
- Las tareas deben ser atómicas e independientemente entregables — cada una debe tener su propio test
- Si una tarea es "implementar todo," es demasiado grande. Descomponla.
- El agente debe proponer: 1) Generador de coeficientes FIR, 2) Funciones de ventana, 3) Exportador de header C, 4) Graficador de respuesta en frecuencia, 5) Validación de entrada

**Concepto clave de SDD:** No necesitas saber CÓMO implementar una ventana Hamming. La especificación define el contrato; el agente descifra las matemáticas de procesamiento de señales.

**Entregable:** `plan.md` (arquitectura) + `tasks.md` (5–7 tareas atómicas con comandos de test).

#### 1:15–2:15 — Fase 3: Ejecución del Agente con Subagentes y Revisión Adversarial

**Este es el núcleo del taller.** Los estudiantes implementan el Diseñador de Filtros FIR usando subagentes para mantener el contexto y un revisor adversarial para detectar brechas.

**Paso 3.1 — Ejecución de Tareas con Subagentes (35 min):**

```
> For each task in tasks.md, spawn a subagent to implement it.
  After each task, verify: do tests pass? Is mypy clean?

El agente:
1. Genera subagente para Tarea 1 (Generador de coeficientes FIR)
   → El subagente lee spec, implementa, ejecuta tests, retorna resumen
2. Genera subagente para Tarea 2 (Funciones de ventana)
   → El subagente lee spec, implementa, ejecuta tests, retorna resumen
3. ... continúa por todas las tareas
```

**Puntos de enseñanza:**
- Observa el uso de contexto del agente. Después de 3–4 tareas, ¿todavía recuerda la especificación?
- Si la calidad se degrada, `/clear` no es fracaso — es buena práctica
- El agente principal se mantiene como orquestador; los subagentes hacen el trabajo pesado

**Paso 3.2 — Revisión Adversarial (15 min):**

```
> Now spawn a REVIEWER subagent with a fresh context.
  Give it only the spec.md and the git diff of all changes.
  Ask it: "Does every acceptance criterion have a test?
  Are there edge cases with no coverage? Was anything
  outside scope changed? Report gaps only — skip style."

El revisor retorna hallazgos. El escritor corrige las brechas y vuelve a testear.
```

**Puntos de enseñanza:**
- El agente que escribió el código no puede revisar confiablemente su propio código
- Un contexto fresco ve lo que el escritor pasó por alto
- Este es el equivalente SDD de una revisión de pull request — pero automatizado

**Paso 3.3 — Guardar Descubrimientos en Engram (10 min):**

```
> Save to memory: the Q15 fixed-point convention, the golden-file
  test pattern we established, and the Nyquist edge case behavior.
  These will be available in all future sessions.
```

**Puntos de enseñanza:**
- Engram persiste entre sesiones. La sesión de mañana comienza con este conocimiento.
- OpenSpec almacena los artefactos formales; Engram almacena el conocimiento tribal.
- Juntos eliminan el problema de "re-explicar todo."

#### 2:15–2:30 — Fase 4: Retrospectiva y Contexto Empresarial

**Preguntas de discusión:**

1. ¿Dónde tuvo éxito el agente sin corrección? ¿Dónde alucinó?
2. ¿El revisor adversarial detectó algo que el escritor pasó por alto?
3. ¿Cuánto contexto se consumió? ¿Qué habría pasado sin subagentes?
4. Si volvieras mañana, ¿Engram recordaría lo que establecimos hoy?

**Contexto empresarial:**
- MCP servers como dependencias de cadena de suministro — versionados, escaneados, firmados
- Sandboxing y modelos de permisos para uso en producción
- SDD en CI: agentes no interactivos ejecutando especificaciones como barreras pre-merge
- El camino de evolución: spec-first → spec-anchored → codebase auto-validable

---

## 9. Preguntas Frecuentes y Patrones de Falla Comunes

### P: ¿Cuándo es SDD excesivo?

Si puedes describir el diff en una oración (corregir un typo, renombrar una variable, agregar una línea de log), omite SDD y simplemente hazlo. SDD vale la pena cuando:
- El cambio toca 3+ archivos
- No estás seguro del enfoque
- El cambio tiene casos borde que no has mapeado completamente

### P: ¿Qué pasa si mi repositorio no tiene tests?

Agrega tests primero (como un cambio SDD separado). Sin tests, estás haciendo vibe coding rápido, no SDD. El primer cambio en cualquier codebase legacy debe ser: "Agregar infraestructura de test y 80% de cobertura en el módulo X."

### P: El agente sigue cometiendo el mismo error.

Después de dos correcciones, haz `/clear` y escribe un mejor prompt. Las sesiones largas con correcciones acumuladas rinden peor que una sesión limpia con un prompt preciso. Esto es empíricamente cierto en todos los LLMs.

### P: ¿Cómo funcionan juntos Engram y OpenSpec?

OpenSpec almacena QUÉ estamos construyendo (especificaciones formales, planes, tareas). Engram almacena POR QUÉ tomamos ciertas decisiones y QUÉ aprendimos (gotchas, convenciones, causas raíz). OpenSpec tiene alcance de proyecto y es específico del cambio. Engram es multi-proyecto y persistente.

### P: ¿Puede SDD funcionar para proyectos de hardware/embebidos?

Sí — y es exactamente por eso que este taller usa DSP como ejemplo guía. Los tests de golden-file (entrada conocida → salida conocida), las convenciones de aritmética de punto fijo y las restricciones de hardware (límites de memoria, tasas de muestreo) son todos especificables. El agente no necesita conocer tu microcontrolador específico — la especificación codifica las restricciones.

---

## Referencias

- [mini-swe-agent](https://mini-swe-agent.com) — Agente de 100 líneas, 74% SWE-bench verificado. Demuestra que la simplicidad gana.
- [SWE-bench](https://swebench.com) — El benchmark canónico para agentes de código con IA.
- [Model Context Protocol](https://modelcontextprotocol.io) — Especificación MCP y SDKs de servidor.
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices) — Gestión de contexto, ciclos de verificación, revisión adversarial.
- [OpenCode](https://opencode.ai) — El agente de código con IA de código abierto usado en este taller.
