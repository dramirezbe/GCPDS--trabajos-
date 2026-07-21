# State of the Art: Agents to Code & Spec-Driven Development (SDD)

**Target Audience:** Software Engineers, Tech Leads, Engineering Students  
**Prerequisites:** Basic CLI familiarity, a GitHub account, a code editor  
**Running Example:** Building a Digital Signal Processing (DSP) toolbox — we will use a **FIR Filter Designer** as the thread that ties every phase together.

---

## 1. State of the Art: Spec-Driven Development (SDD)

### 1.1 The Problem It Solves

In 2024, Princeton and Stanford released [SWE-bench](https://swebench.com) — a benchmark of real GitHub issues. The best AI agents solved roughly 20% of them. By mid-2025, [mini-swe-agent](https://mini-swe-agent.com) — a **100-line Python script** — solved **74%** on the same benchmark.

The difference was not a smarter model. It was a better *contract* between human and machine.

| Era | Workflow | Outcome |
|---|---|---|
| "Vibe coding" (2023–2024) | Human types a vague prompt → AI generates code → human tests it manually, discovers missing requirements, re-prompts | Inconsistent, slow feedback loop, no guardrails |
| **Spec-Driven Development (2025–present)** | Human writes an explicit `spec.md` → AI reads it, proposes a `plan.md` → human approves the plan → AI generates `tasks.md` and executes them one by one, validating each against the spec | Deterministic, auditable, the human stays in control |

### 1.2 Core Principles

*   **The Spec is the Truth.** Instead of code being the ultimate source of truth, the specification becomes an executable contract. If the code and spec disagree, the spec wins.
*   **Human Role — What and Why.** The developer dictates intent through explicit business rules, invariants, acceptance criteria, and architectural boundaries. The human does not write implementation details.
*   **AI Role — How.** Code becomes a secondary, generated artifact. The agent materializes the code and validates it against the explicit specification.
*   **Maturity Progression.** Teams evolve from *"Spec-first"* (write spec, generate code once) to *"Spec-anchored"* (spec and code evolve symbiotically, enforced by continuous testing and validation at every change).

### 1.3 The SOTA in One Sentence

> **Simplicity wins.** The best-performing agents (mini-swe-agent, Claude Code) are not the ones with the most scaffolding — they are the ones with the tightest feedback loop between spec, code, and verification.

---

## 2. The Agent Extension Stack

Modern coding agents are modular. Think of them as a **signal chain**: each component processes a specific part of the problem without coupling to the others — just like an amplifier stage, a filter, and an ADC in an instrumentation pipeline.

```
┌──────────────────────────────────────────────────┐
│                    HOST                          │
│  (OpenCode, Claude Code, Cursor, Codex CLI)      │
│  The reasoning engine — the "brain"              │
├──────────────────────────────────────────────────┤
│  SKILLS  │  MCP Servers  │  PLUGINS  │ SUBAGENTS │
│  On-de-  │  Connectors   │  Bundled  │ Isolated  │
│  mand    │  to external  │  packages │ contexts  │
│  instru- │  systems      │  for teams│ for heavy │
│  ctions  │  & APIs       │           │ tasks     │
└──────────────────────────────────────────────────┘
```

### 2.1 The Host

The **host** is the core reasoning engine — the LLM running inside a CLI or IDE. Examples: OpenCode, Claude Code, Cursor, GitHub Copilot, Codex CLI. The host orchestrates everything: it reads your spec, loads skills, calls MCP tools, spawns subagents, and executes commands. You do not need to understand its internals. You direct it.

### 2.2 Skills — `SKILL.md`

> **What it is:** A version-controlled markdown file that teaches the agent conventions, workflows, and domain knowledge for your project. Skills are loaded **on demand**, not into every conversation — they keep context lean.

#### Anatomy of a SKILL.md

A skill is a directory containing a `SKILL.md` file with YAML frontmatter:

```
your-project/
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

#### When to use a Skill vs. a System Prompt

| Mechanism | Scope | Lives in |
|---|---|---|
| **Skill** | Project-specific, loaded only when relevant | `.agents/skills/<name>/SKILL.md` |
| **System Prompt / AGENTS.md** | Always loaded at session start | Project root `AGENTS.md` |

Skills are for domain knowledge. System prompts are for universal rules ("never commit secrets", "use ES module syntax").

#### Skill Discovery

The agent can list available skills at any time. A skill registry (`.atl/skill-registry.md`) indexes them by trigger phrase and path so the agent knows which skill to load.

### 2.3 MCP — Model Context Protocol

> **What it is:** An open-source standard (like USB-C for AI). MCP servers provide agents with a standardized, secure way to connect to external systems — databases, APIs, file systems, issue trackers. The agent discovers available MCP tools and calls them.

**Official site:** [modelcontextprotocol.io](https://modelcontextprotocol.io)

#### MCP Architecture

```
┌──────────┐     JSON-RPC      ┌──────────────┐
│  HOST    │ ◄──────────────► │  MCP Server  │ ◄──► External System
│ (Agent)  │   (stdio/HTTP)    │  (your code) │     (DB, API, HW)
└──────────┘                   └──────────────┘
```

- The **host** is the AI agent (OpenCode, Claude Code, etc.)
- The **MCP server** is a program you write/install that exposes **tools**, **resources**, and **prompts**
- The **external system** is whatever you need to connect to — a database, a signal generator, Jira, GitHub

#### Example: Building an MCP Server for Signal Analysis

Imagine an MCP server that connects to a **signal generator** or reads **WAV files**. The server exposes:

```
Tools:
  - read_wav(path)        → returns {sample_rate, samples, duration}
  - compute_fft(samples)  → returns {frequencies, magnitudes}
  - apply_filter(samples, coeffs) → returns filtered samples

Resources:
  - signal://<id>/metadata → static metadata about a capture

Prompts:
  - analyze_noisefloor    → template prompt for noise analysis
```

The server is a normal program (Python, Node, Go) that speaks JSON-RPC over stdio. The AI agent discovers it at startup and can call `read_wav("/data/capture.wav")` as if it were a built-in function.

#### Key MCP Concepts

| Concept | Meaning | Example |
|---|---|---|
| **Tool** | An action the agent can invoke | `query_database(sql)`, `create_issue(title, body)` |
| **Resource** | Read-only data exposed to the agent | `file://docs/architecture.md`, `postgres://schema/users` |
| **Prompt** | A reusable prompt template | "Analyze this signal for harmonic distortion" |

### 2.4 Plugins

> **What it is:** A bundled package of Skills + MCP servers + Hooks, distributed as a single installable unit. Plugins ensure an entire engineering team uses the identical set of AI behaviors, tools, and conventions.

**How they work:** Someone in your org packages a skill ("our DSP testing conventions"), an MCP server ("connect to our signal database"), and a hook ("run lint before every commit") into a plugin. Everyone installs it once. Updates propagate to the whole team.

| Component | Packaged in Plugin | Purpose |
|---|---|---|
| Skills | ✅ | Domain conventions, workflows |
| MCP Servers | ✅ | Tool connections to org systems |
| Hooks | ✅ | Deterministic pre/post-action scripts |
| Subagents | ✅ | Specialized review agents |

### 2.5 Subagents — Context Isolation

> **This is the single most important pattern you will learn today.** Subagents are the answer to the fundamental constraint of AI coding: **the context window fills up fast, and quality degrades as it fills.**

#### The Problem

Every file the agent reads, every command output, every conversation turn — it all lives in one context window (typically 200K tokens). A single debugging session can consume tens of thousands of tokens. As context fills:

- The agent "forgets" earlier instructions
- It makes more mistakes
- It loses track of the spec

#### The Solution: Subagents

A **subagent** is a fresh, isolated agent session that receives a specific task, does the work, and returns a **summary** back to the main agent. The heavy reading and iteration happens in the subagent's context, not yours.

```
┌─────────────────────┐
│   MAIN AGENT        │
│   (light context)   │
│                     │
│  "Read the spec"    │
│  "Plan the change"  │──────► ┌───────────────────┐
│  "Spawn subagent    │        │   SUBAGENT A       │
│   to implement      │        │   (isolated ctx)   │
│   Task 3"           │        │                    │
│                     │◄───────│ Reads 47 files     │
│  Receives summary:  │        │ Implements feature │
│  "Done. 3 files     │        │ Runs 200 tests     │
│   changed, tests    │        │ Returns summary    │
│   pass. Edge case   │        └───────────────────┘
│   X needs attention"│
│                     │──────► ┌───────────────────┐
│  "Spawn reviewer    │        │   SUBAGENT B       │
│   subagent to check │        │   (fresh ctx)      │
│   the diff"         │        │                    │
│                     │◄───────│ Reads only the     │
│  Receives feedback  │        │ diff + spec        │
│  directly in session│        │ Reports: "Missing  │
└─────────────────────┘        │ edge case Y"       │
                               └───────────────────┘
```

#### When to Use Subagents

| Scenario | Without Subagent | With Subagent |
|---|---|---|
| **Exploring a new codebase** | Agent reads 60 files, context is 40% full before you start | Subagent reads 60 files, returns a 500-word summary. Context stays lean. |
| **Implementing a large task** | All debugging output, test failures, and iterations pile up in one session | Each task gets its own subagent. Failures don't pollute the main context. |
| **Code review** | The agent that wrote the code reviews its own work — blind spots guaranteed | A fresh subagent sees only the diff + spec. It catches what the writer missed. |

#### The Dual-Agent (Adversarial Review) Pattern

The SOTA quality practice:

1. **Writer agent** implements the feature against the spec.
2. **Reviewer subagent** gets a fresh context, sees only the diff + spec, and reports: "Does every acceptance criterion have a test? Are there edge cases with no coverage? Was anything outside scope changed?"
3. The writer fixes gaps and re-submits.

This is the coding equivalent of *differential signaling* — two independent paths validate the result. Noise (hallucinations) that affects one path is unlikely to affect both identically.

---

## 3. Context Management — The Fundamental Constraint

### 3.1 Why Context Is Everything

Every file read, every command output, every conversation turn consumes tokens from a finite window. When the window fills:

```
Quality
  │  ████████████████░░░░░░░░░░  ← degradation zone
  │  ████████████████████████░░
  │  ██████████████████████████
  │
  └──────────────────────────────► Context fill %
```

Claude Code's best practices document is fundamentally a context-management manual. The main strategies:

### 3.2 Strategies

| Strategy | How | When |
|---|---|---|
| **`/clear`** | Reset context entirely between unrelated tasks | After finishing one feature, before starting another |
| **Subagents** | Delegate heavy reading to isolated sessions | Codebase exploration, large implementations, adversarial review |
| **Compaction** | Agent summarizes old messages, keeps key decisions | Long sessions that can't be split |
| **Plan mode** | Agent reads and plans without editing files | When you need to understand before acting |
| **Session naming** | Name sessions like git branches (`fir-filter`, `fft-optimize`) | Multi-sitting workstreams |

### 3.3 The Rule of Two Corrections

If you have corrected the agent more than **twice** on the same issue in one session:
1. The context is polluted with failed approaches.
2. `/clear` and start fresh with a better prompt that incorporates what you learned.
3. A clean session with a precise prompt beats a long session with accumulated corrections — every time.

### 3.4 Plan Mode: Explore First, Then Code

For anything larger than a one-line fix:

```
1. EXPLORE (plan mode)
   Agent reads files, answers questions, proposes approach.
   No edits happen. Safe to iterate.

2. PLAN (plan mode)
   Agent writes spec.md → plan.md → tasks.md.
   Human reviews and approves the plan.

3. IMPLEMENT (default mode)
   Agent executes tasks one by one.
   Subagents keep context clean.

4. REVIEW (subagent)
   Fresh agent reviews diff against spec.
   Gaps are fixed before merge.
```

---

## 4. The Verification Loop — The Engine That Makes SDD Work

### 4.1 Tests Are Not Optional

The single biggest predictor of SDD success: **does the repo already have tests?**

Without tests, the agent has no feedback loop. It produces code, says "looks done," and waits for you to find the bugs. You become the verification loop — which defeats the purpose.

| Scenario | Agent Behavior |
|---|---|
| ✅ Tests exist + CI passes | Agent runs tests after every change. Loop: code → test → fail → fix → test → pass. Autonomous. |
| ❌ No tests | Agent writes code, says "done." Human tests manually. Human finds bugs. Human re-prompts. Just slow vibe coding. |

### 4.2 Verification Tiers (from weakest to strongest)

| Tier | Mechanism | Example |
|---|---|---|
| **1. Prompt-level** | "Run the tests and fix any failures" | Works for one task, does not persist across tasks |
| **2. Goal conditions** | `/goal "all tests pass and lint is clean"` | Agent re-checks after every turn automatically |
| **3. Hooks** | A script that runs on every file save | `pre-save: pytest --lf` — deterministic, cannot be skipped |
| **4. Adversarial review** | A separate subagent reviews the diff | Catches logical errors the writer can't see |

### 4.3 What Makes a Good Verification Check

A good check is:

- **Binary** (pass/fail, no gray area)
- **Fast** (under 30 seconds ideally)
- **Readable by the agent** (test output, build exit code, lint output — not a GUI)
- **Covers the spec's acceptance criteria**

For DSP work, golden-file tests are ideal: "Given input signal X, after applying filter with coefficients Y, output must match golden file Z within tolerance epsilon."

### 4.4 Evidence, Not Assertions

When the agent says "tests pass," demand to see the output. Never accept "looks good" as verification. You want:

```
$ pytest tests/test_fir_filter.py -v
tests/test_fir_filter.py::test_lowpass_cutoff PASSED
tests/test_fir_filter.py::test_linear_phase PASSED
tests/test_fir_filter.py::test_coefficient_symmetry PASSED
=================== 3 passed in 0.42s ===================
```

Evidence is faster to review than re-running the tests yourself, and it works for sessions you were not actively watching.

---

## 5. Memory & Persistence — Engram + OpenSpec

AI agents are stateless by default. Every session starts blank. Two complementary systems solve this:

### 5.1 Engram — Persistent Cross-Session Memory

> **What it is:** A memory system that survives across sessions. The agent saves decisions, bugs, conventions, and discoveries — and recalls them in future sessions automatically.

```
Session 1                     Session 2 (days later)
────────                      ──────────────────────
"FIR filter uses Q15          Agent auto-loads:
 fixed-point format"           "FIR filter uses Q15
         │                     fixed-point format"
         ▼                              │
    mem_save()                          ▼
    ┌──────────────┐            Agent generates code
    │ Engram Store │            using Q15 — without
    │ (SQLite FTS) │            you re-explaining it
    └──────────────┘
```

#### What Gets Saved (proactively, not manually)

| Trigger | Example |
|---|---|
| Architecture decision made | "Chose Q15 fixed-point over float32 for filter coeffs" |
| Bug fix completed | "Fixed overflow in FFT buffer: root cause was int16 saturation at >32767 samples" |
| Convention established | "Golden test files go in tests/fixtures/, named <test>_input.wav and <test>_expected.wav" |
| Gotcha discovered | "STM32 ADC driver returns 12-bit values left-aligned in 16-bit words — must shift right by 4" |
| Tool/library chosen | "Using `scipy.signal.firwin` for coefficient generation; `numpy` for test vectors" |

#### Engram vs. Files

| | Files (spec.md, plan.md) | Engram |
|---|---|---|
| **Scope** | One project, one change | Cross-project, cross-session |
| **Content** | Formal requirements, plans, tasks | Decisions, bugs, gotchas, conventions |
| **Lifetime** | Archived after change completes | Persists indefinitely |
| **Search** | grep | Full-text search across all sessions |

### 5.2 OpenSpec — Project-Folder Context

> **What it is:** A folder convention (`openspec/` or `sdd/`) inside each project that stores the spec, plan, and tasks for the current change. This is the *project-scoped* complement to Engram's *cross-session* memory.

```
your-dsp-project/
├── openspec/
│   ├── config.yaml          # Project conventions (test runner, lint, strict TDD)
│   ├── testing-capabilities.yaml  # What test layers exist, coverage targets
│   └── changes/
│       └── fir-filter-designer/
│           ├── proposal.md   # Why this change, what problem it solves
│           ├── spec.md       # Requirements, acceptance criteria, scope boundaries
│           ├── design.md     # Architecture decisions, component layout
│           └── tasks.md      # Atomic, independently shippable task list
├── src/
├── tests/
└── AGENTS.md                 # System prompt (always loaded)
```

#### How Engram and OpenSpec Complement Each Other

```
┌─────────────────────────────────────────────────────────┐
│                   ENGRAM (persistent)                    │
│  "Q15 fixed-point convention"                           │
│  "STM32 ADC returns left-aligned 12-bit in 16-bit word" │
│  "Golden files in tests/fixtures/"                      │
│  "Overflow at >32767 samples in FFT buffer — fixed"     │
└─────────────────────────────────────────────────────────┘
                          │
                          │ feeds
                          ▼
┌─────────────────────────────────────────────────────────┐
│              OPENSPEC (per project/change)               │
│  spec.md: "FIR Filter Designer for STM32 — Q15 format"  │
│  plan.md: "Use DMA double-buffering + CMSIS-DSP lib"    │
│  tasks.md: "1. FIR struct, 2. Coefficient loader, ..."  │
└─────────────────────────────────────────────────────────┘
                          │
                          │ drives
                          ▼
┌─────────────────────────────────────────────────────────┐
│              AGENT EXECUTION (session)                   │
│  Implements tasks against spec, validates with tests,   │
│  saves discoveries back to Engram                       │
└─────────────────────────────────────────────────────────┘
```

The cycle: Engram provides the "why we do things this way" context → OpenSpec provides the "what we're building right now" → Agent executes → Discoveries flow back to Engram.

### 5.3 How to Initialize SDD in a Project

```
# From your project root:
> /sdd-init

The agent will:
1. Detect your stack (Python, C, Go, etc.)
2. Find your test runner, linter, formatter
3. Create openspec/ folder with config.yaml
4. Save capabilities to Engram
5. Report: "Ready. Next: /sdd-explore to define a change."
```

---

## 6. Spec-Writing Methodology

Writing a good spec is a skill. A bad spec produces bad code, no matter how good the agent is.

### 6.1 Anatomy of a Good `spec.md`

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

### 6.2 Spec Writing Rules

1. **Every acceptance criterion must be testable.** "The filter should sound good" is not testable. "Output magnitude at 2 kHz must be < -40 dB relative to passband" is testable.
2. **Scope boundaries are as important as requirements.** Saying what is OUT of scope prevents scope creep and keeps the agent focused.
3. **Include edge cases explicitly.** "What happens when order is even?" (reject it). "What happens at exactly Nyquist?" (reject it). The agent cannot guess these.
4. **Verification is part of the spec, not an afterthought.** The exact test command and golden file path go in the spec.
5. **Use concrete examples.** "Given X, when Y, then Z" style.

### 6.3 The "Given-When-Then" Pattern (Gherkin-style)

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

## 7. Security & Sandboxing

### 7.1 The Supply-Chain Reality

Every MCP server, every skill, every plugin is code that runs on your machine. An agent with file-write and command-execute permissions has the power to modify your system. The question is not "should we trust it?" but "how do we constrain the blast radius?"

### 7.2 Sandboxing Approaches

| Approach | What It Does | When to Use |
|---|---|---|
| **Permission allowlists** | Only allow specific commands (`git commit`, `npm test`, never `rm -rf`) | Everyday development |
| **Docker sandbox** | Agent runs inside a container with limited filesystem access | Untrusted code generation |
| **Plan mode** | Agent reads and plans but cannot edit files | Exploration phase |
| **Manual approval** | Agent requests permission for each action | High-risk operations |
| **Subprocess isolation** | Every action is an independent `subprocess.run` — no persistent shell with accumulated state | Core design of mini-swe-agent |

### 7.3 Principle of Least Privilege

An agent implementing an FIR filter designer needs:
- ✅ Read access to `src/`, `tests/`
- ✅ Write access to `src/fir_designer.py`, `tests/test_fir_designer.py`
- ✅ Execute: `python`, `pytest`, `mypy`, `git`
- ❌ Network access (not needed)
- ❌ Write access to `setup.py`, `requirements.txt` (not in scope)
- ❌ `rm`, `sudo`, `chmod`

### 7.4 Enterprise Context

In an enterprise setting, MCP servers and skills are **supply-chain dependencies** — they should be versioned, scanned, signed, and audited just like `npm` packages or `pip` dependencies. A skill that teaches your agent database migration conventions is as critical as the migration framework itself.

---

## 8. Workshop Design

**Duration:** 2.5 Hours (30 min added for pre-requisite verification)  
**Format:** Hands-on, with a clean starter repo provided  
**Running Example (all phases):** FIR Filter Designer for Embedded DSP

### Pre-Workshop: Student Setup (do this before arriving)

- [ ] Install the AI coding agent (OpenCode, Claude Code, or equivalent)
- [ ] Clone the workshop starter repo (a minimal Python project with `pytest`, `mypy`, and `AGENTS.md` already configured)
- [ ] Verify: `pytest` passes, `mypy` is clean
- [ ] Read the `AGENTS.md` — it describes the project conventions

### Phase 0 — README → Verification (5 min, included in Phase 1)

Teaching point: **If tests don't run, SDD cannot work. The verification loop is the engine.** Have every student run `pytest` and confirm it passes before we begin. This is non-negotiable.

### Agenda & Timeline

```
0:00 ─────────────────────────────────────────────── 2:30
│                                                        │
│  INTRO    │ PHASE 1  │ PHASE 2  │   PHASE 3    │ PH 4 │
│  (20 min) │ (30 min) │ (25 min) │   (60 min)   │(15m) │
│           │          │          │              │      │
│  SDD +    │ Write    │ Generate │ Implement    │ Retro│
│  Stack +  │ spec.md  │ plan.md │ with sub-    │ +    │
│  Context  │          │ tasks.md│ agents +     │ Sec  │
│  Mgmt     │          │          │ adversarial  │      │
│           │          │          │ review       │      │
```

#### 0:00–0:20 — Introduction: SDD, The Stack, and Context Management

**Content:**

1. **The SDD Philosophy (5 min)**
   - Vibe coding → Spec-Driven Development
   - SWE-bench proof: 100-line agent solves 74% of real GitHub issues
   - The spec is truth; code is derived

2. **The Agent Stack (5 min)**
   - Host, Skills, MCP, Plugins, Subagents
   - Analogy: signal chain — each stage processes independently
   - MCP as USB-C for AI

3. **Context Management (10 min)**
   - The context window is the fundamental constraint
   - Subagents keep context clean
   - The rule of two corrections
   - Plan mode: explore → plan → implement → review
   - Engram (persistent memory) + OpenSpec (project context)

#### 0:20–0:50 — Phase 1: Write the Specification

**Task:** Students write `spec.md` for the FIR Filter Designer.

**Given to students:**
- Project skeleton with `pytest`, `mypy`, and `AGENTS.md` already set up
- A prompt template:
  ```
  I want to build an FIR filter coefficient designer.
  It should generate coefficients via the window method,
  export them as a C header for STM32, and visualize
  the frequency response. Help me write a spec.md.
  Interview me to clarify requirements I might miss.
  ```

**Teaching points during Phase 1:**
- Let the agent interview YOU — it will catch edge cases you did not think of (Nyquist, even-order rejection, overflow at high orders)
- Every acceptance criterion must be testable
- Scope boundaries matter: what is explicitly out of scope?
- Golden-file tests are the DSP developer's best friend

**Deliverable:** A spec with intent, acceptance criteria, scope boundaries, edge cases, and explicit verification commands.

#### 0:50–1:15 — Phase 2: Generate Plan and Tasks

**Task:** Students prompt the agent to read `spec.md` and produce `plan.md` + `tasks.md`.

**Teaching points:**
- The human reviews the PLAN, not just the final code
- Tasks must be atomic and independently shippable — each one should have its own test
- If a task is "implement the whole thing," it is too big. Break it down.
- The agent should propose: 1) FIR coefficient generator, 2) Window functions, 3) C header exporter, 4) Frequency response plotter, 5) Input validation

**Key SDD concept:** You do not need to know HOW to implement a Hamming window. The spec defines the contract; the agent figures out the signal processing math.

**Deliverable:** `plan.md` (architecture) + `tasks.md` (5–7 atomic tasks with test commands).

#### 1:15–2:15 — Phase 3: Agent Execution with Subagents and Adversarial Review

**This is the core of the workshop.** Students implement the FIR Filter Designer using subagents to maintain context and an adversarial reviewer to catch gaps.

**Step 3.1 — Task Execution with Subagents (35 min):**

```
> For each task in tasks.md, spawn a subagent to implement it.
  After each task, verify: do tests pass? Is mypy clean?

The agent:
1. Spawns subagent for Task 1 (FIR coefficient generator)
   → Subagent reads spec, implements, runs tests, returns summary
2. Spawns subagent for Task 2 (Window functions)
   → Subagent reads spec, implements, runs tests, returns summary
3. ... continues through all tasks
```

**Teaching points:**
- Watch the agent's context usage. After 3–4 tasks, does it still remember the spec?
- If quality degrades, `/clear` is not failure — it is good practice
- The main agent stays as the orchestrator; subagents do the heavy lifting

**Step 3.2 — Adversarial Review (15 min):**

```
> Now spawn a REVIEWER subagent with a fresh context.
  Give it only the spec.md and the git diff of all changes.
  Ask it: "Does every acceptance criterion have a test?
  Are there edge cases with no coverage? Was anything
  outside scope changed? Report gaps only — skip style."

The reviewer returns findings. The writer fixes them and re-tests.
```

**Teaching points:**
- The agent that wrote the code cannot reliably review its own code
- A fresh context sees what the writer missed
- This is the SDD equivalent of a pull request review — but automated

**Step 3.3 — Save Discoveries to Engram (10 min):**

```
> Save to memory: the Q15 fixed-point convention, the golden-file
  test pattern we established, and the Nyquist edge case behavior.
  These will be available in all future sessions.
```

**Teaching points:**
- Engram persists across sessions. Tomorrow's session starts with this knowledge.
- OpenSpec stores the formal artifacts; Engram stores the tribal knowledge.
- Together they eliminate the "re-explain everything" problem.

#### 2:15–2:30 — Phase 4: Retrospective & Enterprise Context

**Discussion questions:**

1. Where did the agent succeed without correction? Where did it hallucinate?
2. Did the adversarial reviewer catch anything the writer missed?
3. How much context was consumed? What would have happened without subagents?
4. If you came back tomorrow, would Engram remember what we established today?

**Enterprise context:**
- MCP servers as supply-chain dependencies — versioned, scanned, signed
- Sandboxing and permission models for production use
- SDD in CI: non-interactive agents running specs as pre-merge gates
- The evolution path: spec-first → spec-anchored → self-validating codebase

---

## 9. FAQ & Common Failure Patterns

### Q: When is SDD overkill?

If you can describe the diff in one sentence (fix a typo, rename a variable, add a log line), skip SDD and just do it. SDD pays off when:
- The change touches 3+ files
- You are unsure about the approach
- The change has edge cases you have not fully mapped

### Q: What if my repo has no tests?

Add tests first (as a separate SDD change). Without tests, you are doing fast vibe coding, not SDD. The first change to any legacy codebase should be: "Add test infrastructure and 80% coverage on module X."

### Q: The agent keeps making the same mistake.

After two corrections, `/clear` and write a better prompt. Long sessions with accumulated corrections perform worse than a clean session with a precise prompt. This is empirically true across all LLMs.

### Q: How do Engram and OpenSpec work together?

OpenSpec stores WHAT we are building (formal specs, plans, tasks). Engram stores WHY we made certain decisions and WHAT we learned (gotchas, conventions, root causes). OpenSpec is project-scoped and change-specific. Engram is cross-project and persistent.

### Q: Can SDD work for hardware/embedded projects?

Yes — and that is exactly why this workshop uses DSP as the running example. Golden-file tests (known input → known output), fixed-point arithmetic conventions, and hardware constraints (memory limits, sample rates) are all spec-able. The agent does not need to know your specific microcontroller — the spec encodes the constraints.

---

## References

- [mini-swe-agent](https://mini-swe-agent.com) — 100-line agent, 74% SWE-bench verified. Proves simplicity wins.
- [SWE-bench](https://swebench.com) — The canonical benchmark for AI coding agents.
- [Model Context Protocol](https://modelcontextprotocol.io) — MCP specification and server SDKs.
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices) — Context management, verification loops, adversarial review.
- [OpenCode](https://opencode.ai) — The open-source AI coding agent used in this workshop.
