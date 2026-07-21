# System Architecture Diagrams

---

## 1. Skills System — How It Works

```mermaid
flowchart TD
    subgraph SKILL_DEF["Skill Definition (SKILL.md)"]
        FM["Frontmatter\n- name\n- description (triggers)\n- license\n- metadata"]
        AC["Activation Contract\n- When to trigger"]
        HR["Hard Rules\n- Constraints"]
        DG["Decision Gates\n- Branching logic"]
        ES["Execution Steps\n- Step-by-step workflow"]
        OC["Output Contract\n- Expected result format"]
        RF["References\n- assets/ files\n- references/ docs"]
    end

    subgraph DISCOVERY["Skill Discovery"]
        USER["User / Agent Prompt"] -->|"matches description triggers"| RESOLVE
        RESOLVE["Skill Resolver"] -->|"paths-injected (preferred)"| SUB
        RESOLVE -->|"fallback: registry scan"| SUB
        RESOLVE -->|"fallback: explicit SKILL:Load"| SUB
        REGISTRY["atl/skill-registry.md\n(index of all available skills)"] -.->|"populated by"| REGEN["skill-registry skill\nscans skill dirs, deduplicates"]
    end

    subgraph LOADING["Skill Loading"]
        SUB["Sub-agent/Ochestrator"] -->|"skill(name) tool"| INJECT["Injects SKILL.md\ninstructions into context"]
        INJECT --> EXEC["Agent follows skill\nas runtime contract"]
    end

    subgraph CREATION["Skill Creation (skill-creator)"]
        NEED["Reusable pattern detected"] --> CHECK{"Check repo\nstyle guide"}
        CHECK -->|"docs/skill-style-guide.md"| STYLE["Apply repo rules"]
        CHECK -->|"none available"| FALL["Apply inline fallback rules"]
        STYLE --> STRUCT["Create structure:\nskills/{name}/\n├── SKILL.md\n├── assets/\n└── references/"]
        FALL --> STRUCT
        STRUCT --> REGEN
    end

    subgraph HIERARCHY["Skills Folder Hierarchy"]
        DIR["~/.config/opencode/skills/"] --> SHARED["_shared/\n├── SKILL.md (not invokable)\n├── sdd-phase-common.md\n├── persistence-contract.md\n├── engram-convention.md\n├── openspec-convention.md\n├── skill-resolver.md\n└── sdd-status-contract.md"]
        DIR --> SDD["sdd-{phase}/\n├── SKILL.md\n├── references/\n└── assets/"]
        DIR --> TOOLS["{tool-name}/\n├── SKILL.md\n├── references/\n└── assets/"]
        SDD --- SDD_LIST["sdd-init  sdd-explore  sdd-propose\nsdd-spec  sdd-design   sdd-tasks\nsdd-apply sdd-verify   sdd-archive\nsdd-onboard"]
        TOOLS --- TOOL_LIST["skill-creator  skill-improver\nskill-registry  branch-pr\nchained-pr  work-unit-commits\nissue-creation  comment-writer\njudgment-day  go-testing\ncognitive-doc-design"]
    end

    EXEC -.->|"report resolution"| REPORT["skill_resolution:\npaths-injected | fallback-registry\nfallback-path | none"]
```

### Key concepts

| Concept | Description |
|---------|-------------|
| **SKILL.md** | Runtime instruction contract for an LLM — not human documentation |
| **description** | One-line YAML field with trigger words; the matching mechanism |
| **skill()** tool | Injects the skill's full instructions into the conversation context |
| **Skill Resolver** | Protocol for delegators to pass exact SKILL.md paths to sub-agents |
| **Skill Registry** | Index (`.atl/skill-registry.md` + Engram) of all available skills by trigger |
| **`_shared/`** | Support package with shared conventions — not invokable as a skill |
| **skill-creator** | Meta-skill that governs how new skills are authored and structured |

---

## 2. OpenSpec — Spec-Driven Development Pipeline

```mermaid
flowchart TD
    subgraph PIPELINE["SDD Pipeline (8 Phases)"]
        INIT["1. sdd-init\nDetect stack, bootstrap\nopenspec/config.yaml"] --> EXPLORE
        EXPLORE["2. sdd-explore\nInvestigate, think, clarify\n→ exploration.md"] --> PROPOSE
        PROPOSE["3. sdd-propose\nIntent, scope, approach\n→ proposal.md"] --> SPEC
        SPEC["4. sdd-spec\nDelta specs: ADDED/MODIFIED\nREMOVED/RENAMED\n→ specs/{domain}/spec.md"] --> DESIGN
        DESIGN["5. sdd-design\nTechnical design, diagrams\n→ design.md"] --> TASKS
        TASKS["6. sdd-tasks\nBreak into work units\nreview budget guard\n→ tasks.md"] --> APPLY
        APPLY["7. sdd-apply\nImplement tasks, mark [x]\n→ updates tasks.md"] --> VERIFY
        VERIFY["8. sdd-verify\nRun tests, prove compliance\n→ verify-report.md"] --> ARCHIVE
        ARCHIVE["9. sdd-archive\nMerge deltas into main specs\nmove to archive/"] -.->|"cycle complete"| INIT
    end

    subgraph PERSISTENCE["Persistence Modes"]
        ENGRAM_M["engram\nWorking memory only\nCross-session recovery\nUpserts (no history)"]
        OPENSPEC_M["openspec\nFiles in repo\nGit history + audit trail\nTeam-shareable"]
        HYBRID_M["hybrid\nBoth Engram + files\nFull capabilities\nHigher token cost"]
        NONE_M["none\nEphemeral\nLost on session end"]
    end

    subgraph OPS_STRUCT["openspec/ Folder Hierarchy"]
        ROOT["openspec/"] --> CONFIG["config.yaml\nschema, context, rules"]
        ROOT --> SPECS["specs/\n{domain}/spec.md\nSOURCE OF TRUTH"]
        ROOT --> CHANGES["changes/"]

        CHANGES --> ACTIVE["{change-name}/\nActive change folder"]
        CHANGES --> ARCHIVE_DIR["archive/\nYYYY-MM-DD-{change-name}/\nCompleted changes"]

        ACTIVE --> STATE["state.yaml\nDAG state (survives compaction)"]
        ACTIVE --> EXPLO["exploration.md (optional)"]
        ACTIVE --> PROP["proposal.md\nIntent + approach"]
        ACTIVE --> DELTA["specs/{domain}/spec.md\nDelta specs"]
        ACTIVE --> DES["design.md\nArchitecture + diagrams"]
        ACTIVE --> TASK["tasks.md\nWork breakdown"]
        ACTIVE --> VREPORT["verify-report.md\nTest results"]

        DELTA -.->|"sections"| DELTA_SEC["## ADDED\n## MODIFIED\n## REMOVED (Reason:)\n## RENAMED (old → new)"]
    end

    subgraph EXECUTION["Execution Model"]
        ORCH["Orchestrator\nManages DAG state\nResolves skills\nChooses persistence mode"] -->|"delegates phase"| EXECUTOR["Phase Executor\n(sub-agent)\nReads artifacts, does work,\npersists result"]
        EXECUTOR -->|"return envelope"| ORCH
        ORCH -.->|"persists"| STATE
    end

    PIPELINE -.->|"stores artifacts in"| PERSISTENCE
    PERSISTENCE -.->|"openspec/hybrid modes"| OPS_STRUCT
    PIPELINE --> EXECUTION
```

### Delta Spec Operations

| Operation | Section | Behavior |
|-----------|---------|----------|
| **ADDED** | New requirement | Appends to main spec |
| **MODIFIED** | Full updated requirement | Replaces matching block in main spec |
| **REMOVED** | Requirement + Reason | Deletes from main spec |
| **RENAMED** | Old → New name | Changes heading, preserves behavior |

### Review Budget Guard

Each change has a default 400-line PR review budget. `sdd-tasks` forecasts risk (Low/Medium/High) and may recommend chained PRs. `sdd-apply` must not start oversized work without explicit resolution.

---

## 3. Engram — Persistent Memory System

```mermaid
flowchart TD
    subgraph CORE["Core Architecture"]
        DB["SQLite Database\n(local, per-device)\nFTS5 full-text search"] <--> OBS["Observations\nImmutable memory entries\nwith type, scope, title,\ncontent, topic_key"]
        DB <--> REL["Relations\nSemantic links between\nobservations (conflict,\ncompatible, supersedes)"]
        DB <--> SESS["Sessions\nTrack activity across\nconversation sessions"]
    end

    subgraph OPS["Core Operations"]
        SAVE["mem_save\nPROACTIVE — do not wait\nTriggers: decisions, bugs,\ndiscoveries, patterns, configs\n\nNaming: sdd/{change}/{artifact}\ntopic_key → upserts\ncapture_prompt: false for SDD"]
        SEARCH["mem_search\nFTS5 full-text search\nReturns 300-char previews\nMust follow with\nmem_get_observation(id)"]
        CONTEXT["mem_context\nRecent session history\nFast, cheap lookup\nCall at session start"]
        GET["mem_get_observation(id)\nFull untruncated content\nREQUIRED after search"]
        SUMMARY["mem_session_summary\nMANDATORY before session end\nStructured format:\nGoal/Instructions/Discoveries/\nAccomplished/Next Steps/Files"]
        JUDGE["mem_judge\nResolve memory conflicts\nVerdicts: related, compatible,\nscoped, conflicts_with,\nsupersedes, not_conflict"]
    end

    subgraph LIFECYCLE["Memory Lifecycle"]
        NEW["Observation created\n(mem_save)"] --> ACTIVE["active\nTrusted, current"]
        ACTIVE -->|"decay policy triggers"| STALE["needs_review\nStale — verify before use"]
        STALE -->|"mem_review mark_reviewed\n(user confirmation only)"| ACTIVE
        ACTIVE -->|"same topic_key upserted"| OVERWRITE["Overwritten\nrevision_count++\nold content lost"]
    end

    subgraph CONFLICT["Conflict Detection"]
        SAVE2["mem_save"] -->|"returns"| JUDGE_CHECK{"judgment_required?"}
        JUDGE_CHECK -->|"true: candidates[]"| EVAL{"confidence ≥ 0.7\nAND not supersedes/conflicts?"}
        EVAL -->|"yes"| SILENT["Resolve silently\nmem_judge()"]
        EVAL -->|"no: ask user"| ASK["Surface to user\nconversationally"]
        ASK -->|"user decides"| JUDGE2["mem_judge(relation, reason)"]
        SILENT --> DONE["Conflict resolved"]
        JUDGE2 --> DONE
    end

    subgraph PATTERNS["Usage Patterns"]
        RECOVERY["Recovery Protocol\n1. mem_search('sdd/{change}/...')\n2. mem_get_observation(id)\n→ full content"]
        ARTIFACT_WRITE["Artifact Write\nmem_save(\n  title: sdd/{change}/{type}\n  topic_key: sdd/{change}/{type}\n  type: architecture\n  capture_prompt: false\n  content: full markdown\n)"]
        BROWSING["Browse all artifacts\nmem_search('sdd/{change}/')\n→ all artifacts for change"]
        STATE_PERSIST["State Persistence\nmem_save(\n  topic_key: sdd/{change}/state\n  content: change, phase,\n  artifacts, tasks_progress\n)"]
    end

    subgraph PROACTIVE["Proactive Save Triggers"]
        TRIGGERS["Architecture/design decision\nBug fix (root cause + solution)\nNon-obvious discovery\nPattern established\nConfiguration change\nUser preference learned\nGotcha/edge case found"]
    end

    OPS --> LIFECYCLE
    OPS --> CONFLICT
    OPS --> PATTERNS
    PROACTIVE -.->|"triggers"| SAVE
```

### Artifact Naming Convention

```
title:     sdd/{change-name}/{artifact-type}
topic_key: sdd/{change-name}/{artifact-type}
type:      architecture
```

| Artifact Type | Produced By | Purpose |
|---------------|-------------|---------|
| `explore` | sdd-explore | Exploration analysis |
| `proposal` | sdd-propose | Change proposal |
| `spec` | sdd-spec | Delta specifications |
| `design` | sdd-design | Technical design |
| `tasks` | sdd-tasks | Task breakdown |
| `apply-progress` | sdd-apply | Implementation progress |
| `verify-report` | sdd-verify | Verification report |
| `archive-report` | sdd-archive | Archive closure with lineage |
| `state` | orchestrator | DAG state for compaction recovery |

### Key Principles

- **Proactive saves**: save immediately after any significant event — do NOT wait to be asked
- **Upsert over insert**: same `topic_key` + `project` + `scope` updates the existing observation
- **No revision history**: Engram is working memory, not an audit trail — old content is overwritten
- **Two-step retrieval**: `mem_search` → truncated preview → `mem_get_observation(id)` → full content
- **Mandatory session summary**: every session must end with `mem_session_summary`
- **Deterministic naming**: the `sdd/{change}/{artifact}` convention enables exact-match recovery
- **capture_prompt: false**: mandatory for automated SDD pipeline artifacts
