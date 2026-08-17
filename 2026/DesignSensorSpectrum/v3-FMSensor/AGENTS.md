# AGENTS.md — v3-FMSensor

## Project Overview

LaTeX-based technical specification for an **SDR-agnostic** FM broadcast compliance monitoring system (VHF-II, 87.5–108 MHz). This is a **document project**, not a software codebase.

The specification is hardware-agnostic by design: every reference is to a generic "SDR device" / "baseline SDR platform", never to a specific product. Baseline numeric characterizations (8-bit ADC, ~7 ENOB, ~42 dB dynamic range, ±20 ppm crystal, 20 MS/s class) are kept as the *baseline platform* values that the capability classification depends on.

- **Primary document**: `report/RAG-informed-SpectrumSensing.tex` (~1280 lines, unnumbered Introduction + 10 numbered LaTeX sections) — the current, RAG-verified, hardware-agnostic specification. Compiled PDF `report/RAG-informed-SpectrumSensing.pdf` is tracked.
- **Legacy copy**: `template/03SpectrumSensingFM0-copy.tex` (~1260 lines) — pre-refactor version, still vendor-specific (HackRF One). **Do not edit** unless explicitly asked; it exists as a historical/derivation reference only.

## Build Instructions

```bash
# Compile the primary document (force rebuild, always produces PDF)
latexmk -g -outdir=report report/RAG-informed-SpectrumSensing.tex

# Clean auxiliary files (always clean after compilation)
latexmk -c -outdir=report report/RAG-informed-SpectrumSensing.tex
```

**CRITICAL**: always pass `-outdir=report`. Without it, latexmk writes the PDF and aux files to the **current working directory** (project root), leaving a stale PDF next to the source and untracked junk in the root. The tracked PDF is `report/RAG-informed-SpectrumSensing.pdf`.

### latexmk Reference

| Flag | Purpose |
|------|---------|
| `-g` | Force rebuild — ignores timestamps, recompiles from scratch |
| `-c` | Clean auxiliary files (.aux, .log, .out, .toc, etc.) but keep PDF |
| `-C` | Clean everything including PDF — use when you need a full reset |
| `-gg` | Super go mode: clean (`-CA`) then rebuild regardless of state |
| `-outdir=DIR` | Write output files (PDF, aux) to `DIR` instead of the current directory — **REQUIRED for this project** |
| `-pdf` | Explicitly generate PDF via pdflatex (default for most configs) |
| `-lualatex` | Use LuaLaTeX instead of pdflatex |
| `-pvc` | Preview continuously — recompiles on file save (useful for live editing) |
| `-pvc-` | Stop continuous preview mode |
| `-quiet` / `-silent` | Suppress progress messages from called programs |
| `-verbose` | Show all progress messages (debugging) |
| `-jobname=NAME` | Set output filename basename (e.g., `-jobname=final` produces `final.pdf`) |
| `-view=pdf` | Open PDF viewer after compilation |
| `-view=none` | Do not open viewer |
| `-f` | Force continued processing past errors |
| `-commands` | List all commands latexmk uses (diagnostic) |

### latexmk Recipes

```bash
# Standard compile + clean cycle
latexmk -g -outdir=report report/RAG-informed-SpectrumSensing.tex && latexmk -c -outdir=report report/RAG-informed-SpectrumSensing.tex

# Full reset and rebuild
latexmk -gg -outdir=report report/RAG-informed-SpectrumSensing.tex

# Compile with verbose output for debugging
latexmk -g -verbose -outdir=report report/RAG-informed-SpectrumSensing.tex

# Compile and open PDF viewer
latexmk -g -view=pdf -outdir=report report/RAG-informed-SpectrumSensing.tex

# Live preview (recompiles on save — requires viewer support)
latexmk -pvc -view=pdf -outdir=report report/RAG-informed-SpectrumSensing.tex

# Compile to a differently-named PDF
latexmk -g -outdir=report -jobname=spec-v3 report/RAG-informed-SpectrumSensing.tex
# → produces report/spec-v3.pdf
```

## local-rag (Document Search)

Eight reference PDFs are ingested into a vector database for hybrid keyword + semantic search. The RAG index lives at `/home/javastral/RAG-documents/` (outside this repo) and holds **7083 chunks / 8 documents** (verified live 2026-08-16). The `docs-RAG/` folder in this project is **not** part of the RAG index — it is a local reading copy for humans only; never ingest from it or treat it as the index.

`context/SCOPE-RAG.md` catalogs **12 documents (7,836 chunks total)** — the full inventory considered during planning — of which **8 are ingested** and 4 were dropped as out of scope or unusable (BS.1698-1 EMF, M.2225/M.2242 cognitive radio, CRC-162-2025 corrupted). The 12/7,836 figure is the catalog, not the live index; reconcile with `local-rag_status` before assuming growth.

### Querying Documents

Use `local-rag_query_documents` to search across all ingested reference PDFs. The tool returns results sorted by relevance with source file, chunk index, and text snippet.

**Example queries:**

| Query topic | What it finds |
|-------------|---------------|
| `carrier frequency tolerance FM broadcast` | FCC Part 73 §73.1545 — ±2000 Hz for FM >10W |
| `SDR ADC dynamic range` | BS.412, 47 CFR references to signal quality |
| `GUM uncertainty measurement Type A Type B` | ISO 17025 — uncertainty evaluation and metrological traceability |
| `occupied bandwidth 99 percent FM` | 47 CFR §73.317 — FM transmission system requirements |
| `field strength dBuV/m antenna factor` | Field measurement methodology references |
| `decision rule conformity ISO 14253` | ISO 17025 §3.7 — decision rule definitions |

### Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `query` | (required) | Search string — preserve specific terms, add context for vague queries |
| `limit` | 10 | Max results (range 1–20). Lower = higher precision, higher = more recall |
| `scope` | (none) | Absolute path prefix to restrict results (e.g., `/home/javastral/RAG-documents/47_CFR_Part_73.pdf`) |

### Reading Neighboring Chunks

After `query_documents` returns a result, use `read_chunk_neighbors` with the `chunkIndex` and `filePath` to get surrounding context (default: 2 chunks before, 2 after).

### Syncing New Files

To ingest new PDFs into the RAG index:

```bash
# Place PDFs in /home/javastral/RAG-documents/ then sync
# Use local-rag_sync_start with path to the specific file or directory
```

### Index Status

Check current index state with `local-rag_status`:
- `documentCount`: 8
- `chunkCount`: 7083
- `memoryUsage`: ~62 MB
- `searchMode`: hybrid (keyword + semantic)
- `ftsIndexEnabled`: true

## Project Structure

- `report/` — **PRIMARY document** (LaTeX source + compiled PDF)
  - `RAG-informed-SpectrumSensing.tex` — Primary document (~1280 lines, SDR-agnostic)
  - `RAG-informed-SpectrumSensing.pdf` — Compiled output (tracked)
- `template/` — **LEGACY pre-refactor copy** (vendor-specific, do not edit)
  - `03SpectrumSensingFM0-copy.tex` — Old primary (~1260 lines, HackRF One references)
  - `03SpectrumSensingFM0-copy.pdf`, `03SpectrumSensingFM0.pdf` — Old outputs
  - `sdr_diagram.tex` — Figure 1 architecture diagram (standalone TikZ, inlined into the main document)
- `context/` — Agent workflow context
  - `SCOPE-RAG.md` — RAG document-to-section mapping (12 catalogued, 8 ingested)
  - `prompts/` — Agent prompt artifacts (find-documents, lap1-refactor, lap2-refactor)
- `PLAN_RAG_latex.md` — LAP1 refactor plan (DONE)
- `PLAN_CHECKPOINTS.md` — LAP1 per-section HITL audit trail (all 11 gates approved, 2026-08-16)
- `PLAN_FEEDBACK.md` — LAP2 feedback-review plan (PENDING execution)
- `docs-RAG/` — Reference PDFs for local reading only (8 documents) — NOT the RAG index
- `models/` — ML model files (Xenova/)
- `lancedb/` — Vector database for RAG queries
- `.atl/` — Agent tooling cache (skill registry)
- `.gitignore` — Excludes `.atl/`, `models/`, `lancedb/`

## Document Sections

**Numbering note**: LAP1 (`PLAN_RAG_latex.md`) numbers the sections 1–11 with an unnumbered Introduction; LaTeX numbers them 1–10. Both checkpoint files (`PLAN_CHECKPOINTS.md`, and the future `PLAN_CHECKPOINTS_lap2.md`) use **LAP1 numbering**.

1. **Introduction** (unnumbered) — Purpose, scope, regulatory context (FCC, ANE 105, ITU-R BS.412, BS.450-4, SM.2152, ISO 17025)
2. **System-Level Requirements** — Reconfigurability (anchored to ITU-R SM.2152), cost, remote monitoring, cybersecurity, multi-channel capacity, measurement integrity (anchored to ISO 17025 §6.5/§6.4.6); calibration tiers
3. **Functional Decomposition** — RF front-end, signal acquisition, software processing engine, data management; jurisdiction-aware band (87.5–108 vs 88–108 MHz) and raster (100 kHz ANE / 200 kHz FCC) wording
4. **FM Compliance Measurands** — Primary and secondary observables; Table 1 anchored to FCC/ANE/BS.412/BS.450 rows; capability classification framework (4 classes)
5. **Node-Level DSP Pipeline** — 6-stage acquisition-to-reporting pipeline; cross-ref to Section 8 for estimation detail
6. **Array-Level Coordination** — Inter-node calibration, timing, fusion rules, degraded-mode operation; anchored to ISO 17025 §7.7
7. **Baseline SDR Platform Assessment** — Hardware-agnostic platform limitations (stepped emission masks, DC artifact, I/Q imbalance, frequency-dependent noise floor), upgrade paths, capability matrix, theoretical-vs-practical table (was "Baseline HackRF One Platform Assessment")
8. **Reference Requirements** — Per-measurand compliance-grade requirements; jurisdiction-aware tolerances; 400 kHz IF bandwidth de-attributed from BS.412; MPX 0 dBr labelled as adopted procedure definition
9. **Estimation Pipeline of Measurands** — Stage 1–6 estimator detail (notebook-derived); Stage 1 includes SDR raw sample formats (SoapySDR/GNU Radio nomenclature: CF32/CS16/CS12/CS8/CU8/CS4) and the normalization equation `eq:iq-normalization`
10. **Uncertainty Budget and Reporting** — GUM (JCGM 100:2008) Type A/B uncertainty, combined/expanded uncertainty, periodic re-evaluation
11. **Compliance Decision Logic and Uncertainty Handling** — Simple threshold, guard-band (ISO 14253-1 + JCGM 106:2012 + Guide 98-4 + ISO 17025 §7.8.6), shared-risk rules

## Key Technical Details

- **Platform**: SDR device — vendor-agnostic by design; baseline characterization: 8-bit ADC (~7 effective bits, ~42 dB dynamic range), ±20 ppm crystal reference, 20 MS/s class
- **Frequency range**: VHF-II broadcast band — 87.5–108 MHz observation span; 88–108 MHz regulated FM service band
- **Pipeline stages**: Acquisition → Preprocessing → Spectral Estimation → Channel Detection → Carrier Estimation → Confidence Scoring
- **Decision frameworks**: Simple threshold, Guard-band (ISO 14253-1), Shared-risk
- **Calibration tiers**: Primary (lab), Secondary (field), Relative (channel)
- **Sample formats**: SoapySDR/GNU Radio nomenclature (CF32, CS16, CS12, CS8, CU8, CS4) — Stage 1; format/byte-order/justification/scale are version-controlled acquisition metadata
- **Datasheet sources**: Table 4 footnote cites representative front-end/ADC datasheets — MAX2837, MAX5865, RTL2832U, R820T2, MSI001, AD9361/AD9363, LMS7002M (8-bit-class values empirical, 12–16-bit-class values indicative)

## RAG-Informed Refactor Workflow (LAP1 → LAP2)

The document is maintained through evidence-anchored, human-in-the-loop refactor passes:

- **LAP1 (DONE, 2026-08-16)** — Evidence-anchored refactor: every regulatory/metrological claim verified against the RAG corpus, corrected in place. Plan: `PLAN_RAG_latex.md`; per-section audit trail: `PLAN_CHECKPOINTS.md` (all 11 HITL gates approved, JS). Net: 1260 → 1265 lines (+0.4%).
- **LAP2 (PENDING)** — Feedback pass hunting gaps, redundancies, contradictions, and weak/unsupported arguments (including re-verification of every LAP1 edit). Plan: `PLAN_FEEDBACK.md`; log to `PLAN_CHECKPOINTS_lap2.md` (to be created at Gate 0).

**Corrections for future LAP2 execution** (plan predates recent discoveries):
- `PLAN_FEEDBACK.md` R7 and §0 reference `template/03SpectrumSensingFM0-copy.tex` — **wrong target**. LAP1/LAP2 work on `report/RAG-informed-SpectrumSensing.tex`; compile with `-outdir=report` (see Build Instructions).
- R10's "index may have grown to 12/7,836" — **reconciled**: live index is still 8 documents / 7083 chunks; the 12/7,836 figure is `context/SCOPE-RAG.md`'s full catalog (8 ingested + 4 dropped). No index growth to re-check.

## Skills to Load

- `cognitive-doc-design` — For documentation/guide writing tasks
- `judgment-day` — For adversarial review of document content