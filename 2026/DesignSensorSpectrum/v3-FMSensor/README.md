# SDR-Based FM Broadcast Compliance Monitoring System

Technical specification for an SDR-based FM broadcast compliance monitoring system covering architecture, measurement framework, and processing algorithms. This is a **LaTeX document project** — no executable software code is produced.

The specification is **hardware-agnostic**: the design references a generic "SDR device" / "baseline SDR platform" with no vendor product context (8-bit ADC class baseline characterization: ~7 ENOB, ~42 dB dynamic range, ±20 ppm crystal, 20 MS/s).

## Quick path

1. Compile: `latexmk -g -outdir=report report/RAG-informed-SpectrumSensing.tex`
2. Clean: `latexmk -c -outdir=report report/RAG-informed-SpectrumSensing.tex`
3. Output: `report/RAG-informed-SpectrumSensing.pdf`

> Always pass `-outdir=report`: without it latexmk writes the PDF and aux files to the project root instead of next to the source, leaving a stale PDF and untracked junk.

## Building the document

### Essential commands

```bash
# Standard compile + clean cycle
latexmk -g -outdir=report report/RAG-informed-SpectrumSensing.tex && latexmk -c -outdir=report report/RAG-informed-SpectrumSensing.tex

# Full reset (clean everything, rebuild from scratch)
latexmk -gg -outdir=report report/RAG-informed-SpectrumSensing.tex

# Debug compile with full log output
latexmk -g -verbose -outdir=report report/RAG-informed-SpectrumSensing.tex
```

### latexmk cheat sheet

| Command | What it does |
|---------|--------------|
| `latexmk -g file.tex` | Force rebuild, produce PDF |
| `latexmk -c` | Clean aux files (.aux, .log, .out, .toc) |
| `latexmk -C` | Clean everything including PDF |
| `latexmk -gg file.tex` | Clean + rebuild regardless of timestamps |
| `latexmk -outdir=report file.tex` | Write PDF + aux to `report/` — **required** for this project |
| `latexmk -pvc -view=pdf file.tex` | Live preview — recompiles on save |
| `latexmk -g -jobname=final file.tex` | Compile to `final.pdf` instead of default name |
| `latexmk -g -verbose file.tex` | Full log output for debugging |

Full flag reference: `latexmk --help | head -80`

## What this document specifies

| Area | Coverage |
|------|----------|
| Regulatory basis | FCC Part 73, ANE Resolución 105, ITU-R BS.412, BS.450-4, SM.2152, ISO/IEC 17025 |
| Target platform | Vendor-agnostic SDR device (8-bit ADC baseline, 87.5–108 MHz VHF-II observation; 88–108 MHz regulated FM band) |
| DSP pipeline | 6 stages: Acquisition → Preprocessing → Spectral Estimation → Channel Detection → Carrier Estimation → Confidence Scoring |
| Compliance measurands | Frequency error, received power, field strength, occupied bandwidth, ACLR, peak deviation, channel occupancy |
| Capability classes | Compliance-Grade, Screening-Grade, Conditional Compliance-Grade, Unsupported |
| Decision frameworks | Simple threshold, Guard-band (ISO 14253-1), Shared-risk |
| Uncertainty | GUM-compliant Type A/B evaluation, combined/expanded uncertainty, periodic re-evaluation |
| Array coordination | Inter-node calibration, timing alignment, fusion rules, degraded-mode operation |

## Project structure

```
v3-FMSensor/
├── report/                            # PRIMARY document
│   ├── RAG-informed-SpectrumSensing.tex   # LaTeX source (~1280 lines, SDR-agnostic)
│   └── RAG-informed-SpectrumSensing.pdf   # Compiled output (tracked)
├── template/                          # LEGACY pre-refactor copy — do not edit
│   ├── 03SpectrumSensingFM0-copy.tex  # Old primary (~1260 lines, HackRF-specific)
│   ├── 03SpectrumSensingFM0-copy.pdf  # Old output
│   ├── 03SpectrumSensingFM0.pdf       # Reference PDF
│   └── sdr_diagram.tex                # Figure 1 architecture diagram (standalone TikZ)
├── context/                           # Agent workflow context
│   ├── SCOPE-RAG.md                   # RAG document-to-section mapping
│   └── prompts/                       # Agent prompt artifacts (find-docs, lap1, lap2)
├── PLAN_RAG_latex.md                  # LAP1 refactor plan (DONE)
├── PLAN_CHECKPOINTS.md                # LAP1 HITL audit trail (11 gates approved)
├── PLAN_FEEDBACK.md                   # LAP2 feedback-review plan (PENDING)
├── docs-RAG/                          # 8 PDFs — local reading copies only, NOT the RAG index
├── models/                            # ML model files (Xenova/)
├── lancedb/                           # Vector database for RAG queries
├── AGENTS.md                          # Agent context and build instructions
└── README.md                          # This file
```

## Refactor history and future work

The document is maintained through evidence-anchored, human-in-the-loop (HITL) refactor passes using the RAG corpus:

- **LAP1 — DONE (2026-08-16)**: RAG-informed refactor. Every regulatory/metrological claim verified against the corpus and corrected in place; all 11 per-section HITL gates approved. Plan: `PLAN_RAG_latex.md`; audit trail: `PLAN_CHECKPOINTS.md`. Net: 1260 → 1265 lines. Follow-up edits (SDR-agnostic pass, sample formats, datasheet sources) brought the file to ~1280 lines.
- **LAP2 — PENDING**: Feedback pass hunting gaps, redundancies, contradictions, and weak/unsupported arguments. Plan: `PLAN_FEEDBACK.md`; checkpoint log `PLAN_CHECKPOINTS_lap2.md` will be created at Gate 0.

## Searching reference documents (local-rag)

Eight reference PDFs are ingested into a vector database for hybrid keyword + semantic search. The RAG index lives at `/home/javastral/RAG-documents/` (outside this repo) and holds **7083 chunks / 8 documents** (verified live). `docs-RAG/` in this project is a human-readable copy only and is not part of the index. `context/SCOPE-RAG.md` catalogs the full 12-document inventory (8 ingested + 4 dropped: BS.1698-1, M.2225, M.2242, CRC-162-2025).

### Query the reference corpus

Use `local-rag_query_documents` with natural language or specific terms:

| Search example | Relevant standard |
|----------------|-------------------|
| `carrier frequency tolerance FM broadcast` | 47 CFR §73.1545 — ±2000 Hz for FM >10W |
| `occupied bandwidth 99 percent FM` | 47 CFR §73.317 — transmission system requirements |
| `GUM uncertainty measurement Type A Type B` | ISO 17025 §6.4.5 — equipment capability |
| `decision rule conformity ISO 14253` | ISO 17025 §3.7 — decision rule definitions |
| `field strength dBuV/m antenna factor` | Field measurement methodology |
| `SDR ADC dynamic range` | Platform capability assessment |

### Query parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `query` | (required) | — | Search string. Preserve specific terms, add context for vague queries |
| `limit` | 10 | 1–20 | Max results. Lower = higher precision, higher = more recall |
| `scope` | (none) | — | Path prefix to restrict results (e.g., limit to one PDF) |

### Read surrounding context

After a query result, use `local-rag_read_chunk_neighbors` with the returned `chunkIndex` and `filePath` to get context before/after the match.

### Sync new PDFs

Place new PDFs in `/home/javastral/RAG-documents/` then run `local-rag_sync_start` with the file or directory path. Check status with `local-rag_sync_status`.

### Check index health

`local-rag_status` returns: document count, chunk count, memory usage, search mode, FTS index state.

## Key technical decisions

- **Vendor-agnostic SDR design** — no product references; the 8-bit ADC baseline limits dynamic range to ~42 dB effective (7 ENOB)
- **GPSDO required** for carrier-frequency compliance (stock ±20 ppm crystal insufficient)
- **6-stage pipeline** designed for auditability — intermediate quantities retained for regulatory review
- **Calibration hierarchy**: Tier 1 (lab), Tier 2 (field verification), Tier 3 (relative/channel)
- **I/Q imbalance correction** required within ±5 MHz of calibration tone; residual > −40 dBc invalidates occupied bandwidth results
- **Sample formats** (Stage 1): SoapySDR/GNU Radio nomenclature — CF32, CS16, CS12, CS8, CU8, CS4; format/byte-order/justification are version-controlled acquisition metadata

## Reference documents (docs-RAG/)

Local reading copies only — the searchable RAG index lives at `/home/javastral/RAG-documents/`.

| File | Chunks | Description |
|------|--------|-------------|
| `47_CFR_Part_73.pdf` | 2611 | FCC Part 73 technical standards |
| `ANE_0105_2020.pdf` | 3066 | ANE Resolución 105 (2020) |
| `ANE_0406_2026.pdf` | 157 | ANE Resolución 0406 (2026) |
| `ANE_0463_2020.pdf` | 924 | ANE Resolución 463 (2020) |
| `BS.412-9.pdf` | 97 | ITU-R BS.412 FM broadcasting |
| `BS.450-4.pdf` | 14 | ITU-R BS.450 transmission standards |
| `ISO_IEC_17025_2017.pdf` | 185 | ISO/IEC 17025 laboratory competence |
| `SM.2152.pdf` | 29 | ITU-R SM.2152 |

Four documents were dropped as out of scope or unusable (see `context/SCOPE-RAG.md`): BS.1698-1 (EMF exposure), M.2225/M.2242 (land-mobile/IMT cognitive radio), CRC-162-2025 (corrupted ingestion). They are neither in `docs-RAG/` nor in the RAG index.

## Checklist

- [ ] Document compiles without errors (`latexmk -g -outdir=report report/RAG-informed-SpectrumSensing.tex`)
- [ ] Auxiliary files cleaned after compilation (`latexmk -c -outdir=report`)
- [ ] All regulatory references traceable to cited standards
- [ ] Measurand definitions consistent across tables and text