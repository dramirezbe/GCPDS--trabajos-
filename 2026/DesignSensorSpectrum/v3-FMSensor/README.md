# SDR-Based FM Broadcast Compliance Monitoring System

Technical specification for an SDR-based FM broadcast compliance monitoring system covering architecture, measurement framework, and processing algorithms. This is a **LaTeX document project** — no executable software code is produced.

## Quick path

1. Compile: `latexmk -g template/03SpectrumSensingFM0-copy.tex`
2. Clean: `latexmk -c`
3. Output: `template/03SpectrumSensingFM0-copy.pdf`

## Building the document

### Essential commands

```bash
# Standard compile + clean cycle
latexmk -g template/03SpectrumSensingFM0-copy.tex && latexmk -c

# Full reset (clean everything, rebuild from scratch)
latexmk -gg template/03SpectrumSensingFM0-copy.tex

# Debug compile with full log output
latexmk -g -verbose template/03SpectrumSensingFM0-copy.tex
```

### latexmk cheat sheet

| Command | What it does |
|---------|--------------|
| `latexmk -g file.tex` | Force rebuild, produce PDF |
| `latexmk -c` | Clean aux files (.aux, .log, .out, .toc) |
| `latexmk -C` | Clean everything including PDF |
| `latexmk -gg file.tex` | Clean + rebuild regardless of timestamps |
| `latexmk -pvc -view=pdf file.tex` | Live preview — recompiles on save |
| `latexmk -g -jobname=final file.tex` | Compile to `final.pdf` instead of default name |
| `latexmk -g -verbose file.tex` | Full log output for debugging |

Full flag reference: `latexmk --help | head -80`

## What this document specifies

| Area | Coverage |
|------|----------|
| Regulatory basis | FCC Part 73, ANE Resolución 105, ITU-R BS.412, ISO/IEC 17025 |
| Target platform | HackRF One SDR (8-bit ADC, 87.5–108 MHz VHF-II) |
| DSP pipeline | 6 stages: Acquisition → Preprocessing → Spectral Estimation → Channel Detection → Carrier Estimation → Confidence Scoring |
| Compliance measurands | Frequency error, received power, field strength, occupied bandwidth, ACLR, peak deviation, channel occupancy |
| Capability classes | Compliance-Grade, Screening-Grade, Conditional Compliance-Grade, Unsupported |
| Decision frameworks | Simple threshold, Guard-band (ISO 14253-1), Shared-risk |
| Uncertainty | GUM-compliant Type A/B evaluation, combined/expanded uncertainty, periodic re-evaluation |
| Array coordination | Inter-node calibration, timing alignment, fusion rules, degraded-mode operation |

## Project structure

```
v3-FMSensor/
├── template/
│   ├── 03SpectrumSensingFM0-copy.tex   # Primary LaTeX source (~1159 lines)
│   ├── 03SpectrumSensingFM0-copy.pdf   # Compiled output
│   └── 03SpectrumSensingFM0.pdf        # Reference PDF
├── docs-RAG/                            # 8 PDFs — local reading copies only, NOT the RAG index
├── models/                              # ML model files (Xenova/)
├── lancedb/                             # Vector database for RAG queries
├── AGENTS.md                            # Agent context and build instructions
└── README.md                            # This file
```

## Searching reference documents (local-rag)

Eight reference PDFs are ingested into a vector database for hybrid keyword + semantic search. The RAG index lives at `/home/javastral/RAG-documents/` (outside this repo) and holds 7083 chunks. `docs-RAG/` in this project is a human-readable copy only and is not part of the index.

### Query the reference corpus

Use `local-rag_query_documents` with natural language or specific terms:

| Search example | Relevant standard |
|----------------|-------------------|
| `carrier frequency tolerance FM broadcast` | 47 CFR §73.1545 — ±2000 Hz for FM >10W |
| `occupied bandwidth 99 percent FM` | 47 CFR §73.317 — transmission system requirements |
| `GUM uncertainty measurement Type A Type B` | ISO 17025 §6.4.5 — equipment capability |
| `decision rule conformity ISO 14253` | ISO 17025 §3.7 — decision rule definitions |
| `field strength dBuV/m antenna factor` | Field measurement methodology |
| `HackRF One ADC dynamic range` | Platform capability assessment |

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

- **HackRF One** selected for cost and reconfigurability, but 8-bit ADC limits dynamic range to ~42 dB effective
- **GPSDO required** for carrier-frequency compliance (stock ±20 ppm XO insufficient)
- **6-stage pipeline** designed for auditability — intermediate quantities retained for regulatory review
- **Calibration hierarchy**: Tier 1 (lab), Tier 2 (field verification), Tier 3 (relative/channel)
- **I/Q imbalance correction** required within ±5 MHz of calibration tone; residual > −40 dBc invalidates occupied bandwidth results

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

- [ ] Document compiles without errors with `latexmk -g`
- [ ] Auxiliary files cleaned after compilation (`latexmk -c`)
- [ ] All regulatory references traceable to cited standards
- [ ] Measurand definitions consistent across tables and text
