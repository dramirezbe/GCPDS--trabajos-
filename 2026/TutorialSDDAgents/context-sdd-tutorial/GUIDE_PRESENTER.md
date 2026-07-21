# Presenter Guide — SDD Workshop (1 Hour)

**Tool:** [OpenSpec](https://github.com/Fission-AI/OpenSpec) by Fission AI  
**Visual support:** `dist/sdd-workshop.html` — open in browser alongside terminal  
**Running example:** FIR Filter Designer for Embedded DSP  
**Prerequisites for students:** Node.js ≥ 20.19, a code editor, a GitHub account

### Alternative Project Ideas

If the FIR DSP example doesn't resonate with your audience, swap it for any of these.
Each is small enough to complete in one session and exercises the full OpenSpec pipeline:

| # | Project Idea | Stack | What SDD Teaches |
|---|-------------|-------|-----------------|
| 1 | **Dev Jokes API** — `GET /api/jokes/random` returning a random programming joke with consistent `{ ok, data, error }` envelope | Node.js, Express, Vitest | Greenfield: proposal → specs → tasks → apply → archive. Three requirements (random endpoint, response envelope, data model) with Given-When-Then. Tight scope teaches boundaries. |
| 2 | **URL Shortener** — `POST /shorten` and `GET /:slug` with in-memory store | Node.js, Express, Vitest | Input validation, collision handling, redirect logic. Teaches edge cases explicitly in the spec. |
| 3 | **Task CLI** — A `task` command that adds, lists, and completes tasks stored in a JSON file | Node.js, commander, Vitest | CLI testing patterns. Teaches spec-driven CLI design and golden-file tests for known output. |
| 4 | **Markdown Parser** — Convert a subset of Markdown (headings, bold, links) to HTML | Python, pytest | Teaches spec-as-contract: given Markdown input X, expect HTML output Y. Perfect for golden-file tests. |
| 5 | **Password Validator** — Validate passwords against configurable rules (length, special chars, common passwords blocklist) | Python, pytest | Combinatorial edge cases. Teaches acceptance criteria like "must reject" + "must accept." |
| 6 | **Rate Limiter Middleware** — Express middleware that rate-limits by IP with configurable window and max requests | Node.js, Express, Vitest | Time-dependent tests, middleware pattern. Teaches scope boundaries (in scope: IP-based; out of scope: auth-based). |
| 7 | **Image Thumbnail Service** — `POST /thumbnail` that resizes an uploaded image to given dimensions | Python, Flask, Pillow, pytest | File I/O, image processing. Teaches golden-file tests (known input image → known output thumbnail). |

Pick one that matches your audience's stack. The OpenSpec workflow is identical for all of them.

---

## Before the Workshop Starts

- [ ] Open `dist/sdd-workshop.html` in a browser, press `F` for focus mode (hides sidebar)
- [ ] Have a terminal ready with a clean project directory
- [ ] Verify your own OpenSpec install: `openspec --version`
- [ ] Pre-clone a starter repo if you're providing one, or use a blank project

---

## Cheat Sheet — Slide to Concept Mapping

| Slide | Topic | Use it for… |
|-------|-------|-------------|
| 01 | SDD — The Problem | Explain why specs beat vibe coding. Quote SWE-bench numbers. |
| 02 | SDD — Core Principles | Spec is truth. Human says what/why, AI says how. |
| 03 | SDD — Feedback Loop | spec → plan → tasks → verify. This IS the OpenSpec flow. |
| 04 | Agent Stack — Host | The LLM is the reasoning engine. You direct it. |
| 05 | Agent Stack — Skills | SKILL.md = on-demand domain knowledge. Lean context. |
| 06 | Agent Stack — MCP | USB-C for AI. Tools, resources, prompts. |
| 07 | Agent Stack — Subagents | *Most important pattern.* Isolated context per task. |
| 08 | Context — The Constraint | The window fills up. Quality degrades. This is physics. |
| 09 | Context — Strategies | /clear, subagents, compaction, plan mode, session naming |
| 10 | Context — Rule of Two | Two corrections → /clear. Clean slate beats noisy history. |
| 11 | Verification — Tests | No tests = no feedback loop = fast vibe coding. |
| 12 | Verification — Tiers | Prompt level → Goal conditions → Hooks → Adversarial review |
| 13 | Verification — Stack | spec → plan → tasks, all aligned, all verified |
| 14 | Memory — Engram | Persistent cross-session memory. Saves WHY. |
| 15 | Memory — OpenSpec | Project-folder context. Saves WHAT. |
| 16 | Memory — The Cycle | Engram feeds OpenSpec feeds Agent → discoveries flow back |
| 17 | Spec-Writing — Anatomy | Intent, acceptance criteria, scope, edge cases, verification |
| 18 | Spec-Writing — Gherkin | Given-When-Then. Binary, testable, concrete. |
| 19 | Security — Sandboxing | Permission allowlists, Docker, plan mode, manual approval |
| 20 | Security — Enterprise | Supply-chain: version, scan, sign, audit |
| 21 | FAQ — When to use SDD | 3+ files, uncertain approach, unmapped edges → SDD. Typo → skip. |
| 22 | FAQ — DSP/Hardware | Golden-file tests, fixed-point conventions, platform-agnostic specs |

---

## Timeline (60 minutes)

```
0:00 ─────────────────────────────────────────────────────── 1:00
│                                                               │
│ SETUP    │ CONCEPTS   │ EXPLORE+PROPOSE │ APPLY+VERIFY │ WRAP │
│ (10 min) │ (12 min)   │ (15 min)        │ (13 min)     │(10m) │
│          │            │                 │              │      │
│ Install  │ Slides     │ openspec init   │ Review       │ Sec  │
│ tools    │ 01–10      │ /opsx:explore   │ artifacts    │ FAQ  │
│          │            │ /opsx:propose   │ /opsx:apply  │ Q&A  │
│          │            │ (AI thinks!)    │ (subagents!) │ Next │
```

---

## Phase 0 — Setup (0:00–0:10)

### 0:00–0:05 — Install OpenSpec

**What you say:**

> "OpenSpec is an npm package. It's the tool that implements everything on these slides. First, let's install it."

**What everyone types in terminal:**

```bash
npm install -g @fission-ai/openspec@latest
```

**Verify:**

```bash
openspec --version   # should print ≥ 1.6.0
```

**Troubleshooting queue (walk the room):**
- "Node.js not found?" → `node --version` must be ≥ 20.19. If not, install via nvm or from nodejs.org.
- "Permission denied?" → Use a Node version manager (nvm, fnm, volta). Never `sudo npm`.

### 0:05–0:10 — Project Setup

**What you say:**

> "OpenSpec works in any existing project. Today we'll use a Python project — a DSP signal toolbox. Let's initialize it."

**What everyone types (presenter shows on screen):**

```bash
mkdir fir-designer && cd fir-designer
git init
# Create a minimal Python project skeleton:
mkdir src tests
echo 'pytest>=7.0' > requirements.txt
echo 'def test_placeholder(): assert True' > tests/test_placeholder.py
git add . && git commit -m "initial skeleton"
```

**Then:**

```bash
openspec init
```

**What happens:** OpenSpec creates an `openspec/` folder with `specs/`, a `config.yaml` (optional), and registers slash commands for the AI agent.

**Teaching point:**

> "`openspec init` detected your tech stack — Python in this case. It knows pytest is your test runner. This detection is what makes SDD work: the agent knows HOW to verify, so you only need to specify WHAT to build."

---

## Phase 1 — Concepts (0:10–0:22)

**Open `dist/sdd-workshop.html` now. Navigate slide by slide.**

### 0:10–0:14 — Slides 01–03: Why SDD Exists

**Slide 01:** Read the slide aloud. Emphasize:

> "74% of real GitHub issues solved by a 100-line script. Not because the model got smarter — because the human wrote a spec. The contract is everything."

**Slide 02:** Explain:

> "In SDD, the spec is the truth. If code and spec disagree, the spec wins. You say WHAT and WHY. The agent figures out HOW."

**Slide 03:** Point at the diagram:

> "This loop — spec → plan → tasks → verify — is literally what OpenSpec automates. Every `/opsx:` command maps to one of these boxes."

### 0:14–0:18 — Slides 04–07: The Agent Stack

**Slide 04:** Quick overview of host/skills/MCP/plugins/subagents.

> "Think of this as a signal chain. Each component does one thing, no coupling. The host orchestrates — you direct."

**Slide 05:**

> "Skills are markdown files that teach the agent YOUR conventions. Loaded on demand — context stays lean. OpenSpec itself ships skills that teach the agent how to do SDD."

**Slide 06:**

> "MCP is USB-C for AI. Standard protocol. Your agent discovers MCP servers and calls tools like `read_wav()` or `query_db()` as if they were built-in."

**Slide 07 — Critical teaching moment:**

> "This is the single most important pattern you will learn. Subagents. A subagent gets a clean, isolated context. It reads 47 files, implements a feature, runs 200 tests — and returns a 200-word summary. The heavy lifting never pollutes YOUR context. OpenSpec does this automatically under `/opsx:apply`."

### 0:18–0:22 — Slides 08–10: Context Management

**Slide 08:**

> "The context window is a fixed-size pizarra. ~200K tokens. Every file read, every command output, every message consumes tokens. When it fills up, the agent forgets. This is not a bug — it's a physical limit."

**Slide 09:**

> "Five strategies. /clear between tasks. Subagents for heavy work. Compaction to summarize. Plan mode to explore without editing. Session naming like git branches."

**Slide 10:**

> "The rule of two corrections. If you've told the agent the same thing twice, /clear. A clean session with a precise prompt ALWAYS beats a long session full of corrections. Empirically true across every LLM."

**Bridge to OpenSpec:**

> "Now. All of this — specs, plans, tasks, subagents, verification, context management — OpenSpec packages it into four slash commands. Let's see it in action."

---

## Phase 2 — Explore & Propose (0:22–0:37)

### 0:22–0:23 — Start Explore (AI Chat)

**What you type in the AI chat (presenter shares screen):**

```
/opsx:explore
```

**What the AI will ask:** "What would you like to explore?"

**What you answer:**

```
I want to build an FIR filter coefficient designer.
It should generate coefficients using the window method,
export them as a C header for STM32, and visualize
the frequency response.
```

### 0:23–0:28 — WHILE AI EXPLORES (5 min): Keep Teaching

**The AI is reading the project, analyzing the codebase. Use this time!**

**Switch to Slide 11:**

> "The single biggest predictor of SDD success: does the repo have tests? Without tests, the agent has no feedback loop. You become the verification loop — which defeats the purpose."

**Slide 12:**

> "Four verification tiers. Weakest to strongest. Prompt-level works once. Goal conditions re-check every turn. Hooks are deterministic — run on every save. Adversarial review: a separate subagent reviews the diff. Catches what the writer cannot see. OpenSpec uses tier 4 by default."

**Slide 13:**

> "Evidence, not assertions. Never accept 'tests pass' — demand to see the output. Test results are faster to review than re-running the tests yourself."

**Check on the AI:** By now (0:28), the explore should be done. The AI will have analyzed the project and suggested an approach.

### 0:28–0:31 — Review Explore Results

**Read aloud what the AI proposed.** Highlight:

> "Look at this: the AI understood we have a Python project, detected pytest, and proposed a scoped plan. It did NOT start writing code. Explore is safe — no files are edited."

### 0:31–0:33 — Start Propose (AI Chat)

**What you type:**

```
/opsx:propose fir-filter-designer
```

**What the AI creates:**
```
openspec/changes/fir-filter-designer/
├── proposal.md   # Why this change exists
├── design.md     # Architecture and technical decisions
├── tasks.md      # Implementation checklist
└── specs/        # Delta specs (what's changing)
    └── fir/
        └── spec.md
```

### 0:33–0:37 — WHILE AI PROPOSES (2–3 min): Keep Teaching

**Switch to Slide 14:**

> "AI agents are stateless by default. Every session starts blank. Engram fixes this — it's persistent cross-session memory. The agent saves decisions, bugs, conventions, discoveries — and recalls them in future sessions automatically."

**Slide 15:**

> "OpenSpec — the project-folder context we just saw. This is the project-scoped complement to Engram's cross-session memory. OpenSpec stores WHAT we are building. Engram stores WHY we made certain decisions."

**Slide 16:**

> "The cycle: Engram provides tribal knowledge → OpenSpec provides formal artifacts → Agent executes → Discoveries flow back to Engram. This eliminates the 're-explain everything' problem forever."

**Check on the AI:** By 0:37, the proposal should be generated.

---

## Phase 3 — Apply & Verify (0:37–0:50)

### 0:37–0:40 — Review Generated Artifacts

**Open each file and narrate:**

**`proposal.md`:**
> "The proposal captures intent and scope. Notice it specifies what's IN scope (FIR coefficients, C header export) and OUT of scope (IIR filters, real-time filtering). Boundaries prevent scope creep."

**`specs/fir/spec.md`:**
> "Delta specs. ADDED, MODIFIED, REMOVED sections. The AI writes requirements in Given-When-Then format. Sample rate, cutoff frequency, filter order, window type — all specified as acceptance criteria. Each one testable. Each one binary."

**`design.md`:**
> "Architecture decisions. The AI chose scipy.signal.firwin for coefficient generation. It knows about Q15 fixed-point format because the spec told it. The human approved the approach."

**`tasks.md`:**
> "Notice: 5–7 atomic tasks. Each has its own test. 'Implement the whole thing' is NOT a task — that's too big. The AI broke it down: coefficient generator, window functions, C header exporter, frequency response plotter, input validation."

### 0:40–0:45 — Start Apply (AI Chat)

**What you type:**

```
/opsx:apply
```

**What happens:** The AI spawns subagents — one per task. Each subagent gets a fresh context, reads the spec, implements its task, runs tests, and returns a summary.

**WHILE AI APPLIES — Slides 17–18:**

**Slide 17:**
> "Five rules for writing specs. Every criterion must be testable. Scope boundaries matter. Include edge cases explicitly — the agent cannot guess them. Verification is part of the spec. Use concrete examples."

**Slide 18:**
> "Given-When-Then. Gherkin-style. Given preconditions. When the action happens. Then the expected outcome. Binary, testable, no gray area. The agent CAN implement it because the spec leaves no ambiguity."

**Check on the AI:** By 0:45, implementation should be complete. Subagents have returned summaries.

### 0:45–0:50 — Verify Results

> "The agent says it's done. Do we trust it?"

**Run the tests yourself:**

```bash
pytest tests/ -v
```

**Show the output:**

> "Three tests passed. This is evidence, not an assertion. I can see exactly what passed and how long it took. This output works for sessions I wasn't watching."

**Teaching point:**

> "The adversarial review pattern: the agent that wrote the code should NOT be the one reviewing it. OpenSpec can spawn a fresh subagent that sees ONLY the diff and the spec. It asks: does every acceptance criterion have a test? Are there edge cases with no coverage? Was anything outside scope changed?"

---

## Phase 4 — Wrap-Up (0:50–1:00)

### 0:50–0:53 — Archive & Review

**What you type:**

```
/opsx:archive
```

> "Archive merges the delta specs into the main specs. The change folder moves to archive/ for audit history. Your specs are now the documentation of what the system DOES — and they're always up to date because the agent enforces them."

### 0:53–0:56 — Security & Enterprise (Slides 19–20)

**Slide 19:**

> "Every MCP server, every skill, every plugin is code that runs on your machine. Sandbox with permission allowlists, Docker, plan mode, manual approval. Principle of least privilege: an FIR filter designer doesn't need network access or sudo."

**Slide 20:**

> "In enterprise, MCP servers and skills are supply-chain dependencies. Versioned, scanned, signed, audited — just like npm packages. A skill that teaches your agent migration conventions is as critical as the migration framework itself."

### 0:56–0:58 — FAQ (Slides 21–22)

**Slide 21:**

> "When is SDD overkill? One-sentence diff: skip it. Three or more files: use it. Uncertain approach: use it. Unmapped edge cases: use it. Also: if the agent keeps making the same mistake, /clear and write a better prompt."

**Slide 22:**

> "SDD works for embedded and hardware. Golden-file tests. Fixed-point conventions. The agent doesn't need to know your microcontroller — the spec encodes the constraints."

### 0:58–1:00 — Closing

**Three things to remember:**

1. **The spec is the truth.** Code is derived. The human stays in control.
2. **Context is the fundamental constraint.** Subagents keep it clean. `/clear` is not failure — it's hygiene.
3. **Verification is the engine.** No tests = no SDD. Evidence, not assertions.

**Where to go next:**

- OpenSpec docs: https://openspec.dev/
- Workshop source guide: `sdd_workshop_guide.md`
- HTML slides: `dist/sdd-workshop.html`
- OpenSpec Discord: https://discord.gg/YctCnvvshC

---

## Presenter Tips

### Managing the Room

- **Install issues dominate setup.** Have a Node.js version manager ready (nvm, fnm). Walk the room during 0:00–0:05.
- **AI think time is teaching time.** Never stare at a loading spinner. Always switch to the next slide and keep talking.
- **One terminal, one screen.** Students follow your shared screen. They type the same commands in their terminals.
- **Recover from AI failures.** If `/opsx:explore` produces nonsense, say "this is expected — the model sometimes hallucinates. Let me show you what `/opsx:propose` does with a more precise prompt." Don't hide failures — they're teaching moments.

### What If There's No Time?

| Cut this | If running behind |
|----------|-------------------|
| Slides 04–06 (agent stack) | Skip to slide 07 (subagents — most important) |
| Slides 14–16 (memory) | Mention in one sentence: "Engram persists decisions; OpenSpec stores artifacts" |
| Slides 11–13 (verification) | Keep slide 11. Skip 12–13. |
| Slides 19–20 (security) | Combine into one 30-second mention |
| FAQ slides 21–22 | Skip entirely — mention in closing |

### Key Phrases to Repeat

- "The spec is the truth."
- "Context is the fundamental constraint."
- "Evidence, not assertions."
- "Simplicity wins."

### Demo Checklist

- [ ] Terminal: `npm install -g @fission-ai/openspec@latest`
- [ ] Terminal: `openspec init` in a demo project
- [ ] AI Chat: `/opsx:explore` (start this early, talk while it thinks)
- [ ] AI Chat: `/opsx:propose fir-filter-designer`
- [ ] Show artifacts: proposal.md, spec.md, design.md, tasks.md
- [ ] AI Chat: `/opsx:apply`
- [ ] Terminal: `pytest tests/ -v` (show evidence)
- [ ] AI Chat: `/opsx:archive`
