# RAG Document Scope Reference

Purpose: map each ingested document to the sections of the specification it supports, so future queries can target only relevant sources and skip unnecessary ones.

## Index Stats

- Documents: 12
- Chunks: 7,836
- Search mode: hybrid (keyword + semantic)

---

## Document Scope and Section Mapping

### Regulatory — US (FCC)

| Document | Chunks | Scope |
|----------|--------|-------|
| `47_CFR_Part_73.pdf` | 2,611 | FCC Part 73 — US radio broadcast technical standards. Covers FM technical definitions (§73.310), frequency deviation/tolerance (§73.1545), occupied bandwidth (§73.317), stereophonic sound (§73.297), blanketing interference (§73.318), emission masks, station classes, power limits. |

**Relevant to:**
- §4 FM Compliance Measurands — frequency tolerance (±2 kHz), occupied bandwidth (99%), emission mask thresholds
- §6 HackRF Assessment — regulatory standards requiring >80 dB out-of-band attenuation
- §8 Reference Requirements — carrier-frequency tolerance (2 kHz per FCC Part 73), guard-band decision logic
- §10 Uncertainty Budget — compliance thresholds for decision rules
- §11 Compliance Decision Logic — measurand-specific threshold values

### Regulatory — Colombia (ANE)

| Document | Chunks | Scope |
|----------|--------|-------|
| `ANE_0105_2020.pdf` | 3,066 | ANE Resolución 105 (2020) — Colombian national spectrum plan. FM/AM national technical plans (Anexos 2 y 3), station classes (A/B/C), frequency assignments, power limits, antenna requirements, broadcasting allocation table. |
| `ANE_0463_2020.pdf` | 924 | ANE Resolución 463 (2020) — Adds Chapter 2 to Resolución 105, modifies Anexo 2 (FM national technical plan). Updated frequency assignments and technical parameters. |
| `ANE_0406_2026.pdf` | 157 | ANE Resolución 0406 (2026) — Latest modification to Anexo 2 of Resolución 105. Updated FM frequency allocations. |

**Relevant to:**
- §4 FM Compliance Measurands — Colombian-specific technical parameters and thresholds
- §6 HackRF Assessment — Colombian regulatory requirements context
- §8 Reference Requirements — jurisdictional limits for carrier frequency tolerance

### ITU-R Standards — Broadcasting

| Document | Chunks | Scope |
|----------|--------|-------|
| `BS.450-4.pdf` | 14 | ITU-R BS.450-4 — FM transmission standards at VHF. Carrier deviation (±75 kHz / ±50 kHz), pre-emphasis (50/75 µs), stereophonic multiplex signal structure, pilot-tone system (19 kHz pilot, 57 kHz RDS). |
| `BS.412-9.pdf` | 97 | ITU-R BS.412-9 — Planning standards for terrestrial FM at VHF. Minimum usable field strength (rural/urban/large cities), RF protection ratios, frequency deviation as function of measurement time. |
| `BS.1698-1.pdf` | 453 | ITU-R BS.1698-1 — Evaluating EMF from terrestrial broadcasting for human exposure to non-ionizing radiation. Reference curves, VHF/UHF measurement methods. |

**BS.450-4 relevant to:**
- §4 FM Compliance Measurands — peak deviation, multiplex power definitions
- §8 Reference Requirements — MPX power reference (75 kHz deviation, 1 kHz tone, 19 kHz pilot), demodulation bandwidth (400 kHz)
- §9 Estimation Pipeline — FM demodulation, composite baseband recovery, pilot/RDS verification

**BS.412-9 relevant to:**
- §4 FM Compliance Measurands — field strength thresholds, protection ratios
- §8 Reference Requirements — demodulation bandwidth reference (400 kHz per BS.412)

**BS.1698-1 relevant to:** NONE — human exposure assessment, outside scope of broadcast compliance monitoring

### ITU-R Standards — Cognitive Radio / SDR

| Document | Chunks | Scope |
|----------|--------|-------|
| `SM.2152.pdf` | 29 | ITU-R SM.2152 — Definitions of Software-Defined Radio (SDR) and Cognitive Radio System (CRS). Terminology reference. |
| `M.2225.pdf` | 136 | ITU-R M.2225 — Introduction to cognitive radio systems in land mobile service. CRS benefits, spectrum sensing techniques, dynamic frequency selection. |
| `M.2242.pdf` | 163 | ITU-R M.2242 — Cognitive radio systems specific for IMT systems. CRS architecture for mobile networks, spectrum balancing, cognitive pilot channel. |

**SM.2152 relevant to:**
- §2 System-Level Requirements — SDR terminology and definitions

**M.2225 relevant to:** NONE — land mobile service, not broadcasting
**M.2242 relevant to:** NONE — IMT-specific, not relevant to FM broadcast monitoring

### Metrology / Laboratory

| Document | Chunks | Scope |
|----------|--------|-------|
| `ISO_IEC_17025_2017.pdf` | 185 | ISO/IEC 17025:2017 — Laboratory competence requirements. Metrological traceability, measurement uncertainty (Type A/B), calibration chains, proficiency testing, decision rules for conformity assessment. |

**Relevant to:**
- §4 FM Compliance Measurands — measurement traceability, uncertainty framework
- §8 Reference Requirements — calibration tier requirements, traceability to SI
- §10 Uncertainty Budget — GUM-compliant Type A/B evaluation, combined/expanded uncertainty, Welch-Satterthwaite, periodic re-evaluation triggers
- §11 Compliance Decision Logic — decision rules (guard-band per ISO 14253-1), conformity assessment framework

### Other

| Document | Chunks | Scope |
|----------|--------|-------|
| `CRC-162-2025.pdf` | 1 | CRC Report 162 (2025) — 1 chunk, corrupted/encoded text (Cyrillic mojibake). Cullen International report on spectrum monitoring. Unreadable. |

**Relevant to:** NONE — corrupted ingestion, no usable content

---

## Summary: Recommendation by Document

| Document | Verdict | Reason |
|----------|---------|--------|
| `47_CFR_Part_73.pdf` | **KEEP** | Primary US regulatory source — measurand thresholds, emission masks, frequency tolerance |
| `ANE_0105_2020.pdf` | **KEEP** | Primary Colombian regulatory source — national FM technical plan |
| `ANE_0463_2020.pdf` | **KEEP** | Amendment to Colombian FM plan — frequency assignments |
| `ANE_0406_2026.pdf` | **KEEP** | Latest amendment — updated Colombian FM allocations |
| `BS.450-4.pdf` | **KEEP** | FM transmission standards — signal model, deviation, MPX structure |
| `BS.412-9.pdf` | **KEEP** | FM planning standards — field strength thresholds, protection ratios |
| `ISO_IEC_17025_2017.pdf` | **KEEP** | Uncertainty budget and decision rules — GUM framework foundation |
| `SM.2152.pdf` | **KEEP** | SDR/CRS definitions — small but useful terminology reference |
| `BS.1698-1.pdf` | **DROP** | EMF human exposure — outside scope of broadcast compliance |
| `M.2225.pdf` | **DROP** | Cognitive radio in land mobile — not broadcasting |
| `M.2242.pdf` | **DROP** | Cognitive radio for IMT — not broadcasting |
| `CRC-162-2025.pdf` | **DROP** | Corrupted ingestion — no usable content |
