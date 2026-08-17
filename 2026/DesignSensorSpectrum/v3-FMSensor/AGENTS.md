# AGENTS.md — v3-FMSensor

## Project Overview

LaTeX-based technical specification document for an SDR-based FM broadcast compliance monitoring system. This is a **document project**, not a software codebase.

## Build Instructions

```bash
# Compile the document (force rebuild, always produces PDF)
latexmk -g template/03SpectrumSensingFM0-copy.tex

# Clean auxiliary files (always clean after compilation)
latexmk -c
```

### latexmk Reference

| Flag | Purpose |
|------|---------|
| `-g` | Force rebuild — ignores timestamps, recompiles from scratch |
| `-c` | Clean auxiliary files (.aux, .log, .out, .toc, etc.) but keep PDF |
| `-C` | Clean everything including PDF — use when you need a full reset |
| `-gg` | Super go mode: clean (`-CA`) then rebuild regardless of state |
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
| `-g` | Run at least one pass of all rules |
| `-commands` | List all commands latexmk uses (diagnostic) |

### latexmk Recipes

```bash
# Standard compile + clean cycle
latexmk -g template/03SpectrumSensingFM0-copy.tex && latexmk -c

# Full reset and rebuild
latexmk -gg template/03SpectrumSensingFM0-copy.tex

# Compile with verbose output for debugging
latexmk -g -verbose template/03SpectrumSensingFM0-copy.tex

# Compile and open PDF viewer
latexmk -g -view=pdf template/03SpectrumSensingFM0-copy.tex

# Live preview (recompiles on save — requires viewer support)
latexmk -pvc -view=pdf template/03SpectrumSensingFM0-copy.tex

# Compile to a differently-named PDF
latexmk -g -jobname=spec-v3 template/03SpectrumSensingFM0-copy.tex
# → produces spec-v3.pdf
```

## local-rag (Document Search)

Eight reference PDFs are ingested into a vector database for hybrid keyword + semantic search. The RAG index lives at `/home/javastral/RAG-documents/` (outside this repo) and holds 7083 chunks. The `docs-RAG/` folder in this project is **not** part of the RAG index — it is a local reading copy for humans only; never ingest from it or treat it as the index.

### Querying Documents

Use `local-rag_query_documents` to search across all ingested reference PDFs. The tool returns results sorted by relevance with source file, chunk index, and text snippet.

**Example queries:**

| Query topic | What it finds |
|-------------|---------------|
| `carrier frequency tolerance FM broadcast` | FCC Part 73 §73.1545 — ±2000 Hz for FM >10W |
| `HackRF One ADC dynamic range` | BS.412, 47 CFR references to signal quality |
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
- `memoryUsage`: ~66 MB
- `searchMode`: hybrid (keyword + semantic)
- `ftsIndexEnabled`: true

## Project Structure

- `template/` — Main LaTeX source and compiled PDF
  - `03SpectrumSensingFM0-copy.tex` — Primary document (~1205 lines)
  - `03SpectrumSensingFM0-copy.pdf` — Compiled output
  - `03SpectrumSensingFM0.pdf` — Reference/template PDF
  - `sdr_diagram.tex` — Figure 1 architecture diagram (standalone TikZ, inlined into the main document)
- `docs-RAG/` — Reference PDFs for local reading only (8 documents) — NOT the RAG index
  - FCC Part 73, ANE Resoluciones, ITU-R BS standards, ISO 17025
  - The real RAG index lives at `/home/javastral/RAG-documents/` (outside this repo)
- `models/` — ML model files (Xenova/)
- `lancedb/` — Vector database for RAG queries
- `.atl/` — Agent tooling cache (skill registry)
- `.gitignore` — Excludes `.atl/`, `models/`, `lancedb/`

## Document Sections

The specification covers (Introduction is an unnumbered `\section*` in the compiled PDF; numbered sections run 1–10):
1. **Introduction** (unnumbered) — Purpose, scope, regulatory context (FCC, ANE, ITU-R, ISO)
2. **System-Level Requirements** — Reconfigurability, cost, remote monitoring, cybersecurity, multi-channel capacity, measurement integrity
3. **Functional Decomposition** — RF front-end, signal acquisition, software processing engine, data management
4. **FM Compliance Measurands** — Primary (frequency error, power, field strength, BW, ACLR, deviation, occupancy) and secondary observables; capability classification framework
5. **Node-Level DSP Pipeline** — 6-stage acquisition-to-reporting pipeline with estimation algorithms
6. **Array-Level Coordination** — Inter-node calibration, timing, fusion rules, degraded-mode operation
7. **Baseline HackRF One Platform Assessment** — Hardware limitations, DC artifact, I/Q imbalance, upgrade paths
8. **Reference Requirements** — Per-measurand compliance-grade requirements, jurisdiction-aware limits
9. **Estimation Pipeline of Measurands** — Stage 1–6 estimator detail, notebook-derived math
10. **Uncertainty Budget and Reporting** — GUM-compliant Type A/B uncertainty, combined/expanded uncertainty, decision rules
11. **Compliance Decision Logic and Uncertainty Handling** — Simple threshold, guard-band (ISO 14253-1), shared-risk rules

## Key Technical Details

- **Platform**: HackRF One SDR (8-bit ADC, ~7 effective bits, ~42 dB dynamic range)
- **Frequency range**: VHF-II broadcast band (87.5–108 MHz)
- **Pipeline stages**: Acquisition → Preprocessing → Spectral Estimation → Channel Detection → Carrier Estimation → Confidence Scoring
- **Decision frameworks**: Simple threshold, Guard-band (ISO 14253-1), Shared-risk
- **Calibration tiers**: Primary (lab), Secondary (field), Relative (channel)

## Skills to Load

- `cognitive-doc-design` — For documentation/guide writing tasks
- `judgment-day` — For adversarial review of document content
