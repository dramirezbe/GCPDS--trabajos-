# PLAN_FEEDBACK.md — LAP2: RAG-Informed Feedback Review of the Refactored Document

Status: PLANNING COMPLETE — awaiting builder execution with per-section human review (HITL).

---

## 0. Relation to LAP1 (read these first, mandatory)

- LAP1 = `PLAN_RAG_latex.md`, executed via `PLAN_CHECKPOINTS.md`. All 11 gates approved (2026-08-16, JS). Final roll-up: 1265 lines (current file is 1260 lines; the +5/−5 difference is whitespace drift — re-baseline in Gate 0).
- LAP2 reviews the **post-LAP1 text**. All line numbers below are **current** (2026-08-16) and refer to `report/RAG-informed-SpectrumSensing.tex` (the primary document; `template/03SpectrumSensingFM0-copy.tex` is the legacy pre-refactor copy and is NOT a LAP2 target).
- **LAP2 differs from LAP1 in intent**: LAP1 fixed wrong/unverifiable claims. LAP2 hunts **gaps, redundancies, contradictions, and weak or unsupported arguments** — including defects introduced by LAP1's own edits (every LAP1 change must be re-verified in context).
- Numbering continuity: LAP1 numbered the sections 1–11; the LaTeX document numbers them 1–10 with an unnumbered Introduction. **Keep LAP1's numbering** in all logs (both checkpoint files cross-reference it) and note the document section number in each gate report.

| LAP1 # | Document section | Current lines | LaTeX section |
|--------|------------------|---------------|----------------|
| 1 | Introduction (unnumbered) | 76–103 | `\section*{Introduction}` |
| 2 | System-Level Requirements | 105–133 | §1 |
| 3 | Functional Decomposition | 135–222 | §2 |
| 4 | FM Compliance Measurands | 224–359 | §3 |
| 5 | Node-Level DSP Pipeline | 361–478 | §4 |
| 6 | Array-Level Coordination | 480–510 | §5 |
| 7 | Baseline SDR Platform Assessment | 512–649 | §6 |
| 8 | Reference Requirements | 651–713 | §7 |
| 9 | Estimation Pipeline | 715–1070 | §8 |
| 10 | Uncertainty Budget | 1072–1144 | §9 |
| 11 | Compliance Decision Logic | 1146–1260 | §10 |

---

## 1. Purpose and Scope

Perform a **second, RAG-informed feedback pass** on the refactored document. For each section, in document order:

1. Read the section **in full**.
2. Run RAG queries against the sources mapped to that section in `context/SCOPE-RAG.md`.
3. Identify **gaps** (content a governing standard requires but the document omits), **redundancies** (claims duplicated across sections), **contradictions** (conflicting numbers, definitions, or references), and **weak or unsupported arguments** (claims without corpus support, or with a citation that does not say what the text claims).
4. Present findings at the HITL gate and **STOP** until human approval.

LAP2 may propose **trims** (LAP1 forbade deletion; LAP2 permits it **only** for verified redundancies and **only** with explicit human approval per instance — never silently).

Scope boundaries, identical to LAP1:
- No new sections, subsections, paragraphs, tables, or figures (R3 of LAP1 still applies).
- The document's visual identity, TikZ figures, and equation structure are out of scope unless defective.
- `docs-RAG/` remains a human reading copy only — never treat it as the index; use it solely to verify what the index cannot extract (table rows, PDF-only sections).

---

## 2. Builder Agent Ground Rules (MANDATORY — this is the contract)

### R1 — Section-by-section, never whole-document
Work on exactly **one section per iteration**, in LAP1 numbering order (1 → 11). Do not batch edits across sections. Each section's work ends at its HITL gate.

### R2 — HITL gate after every section (hard stop)
After presenting one section's findings, **STOP**. Do not start the next section. Report to the human:
- the findings (taxonomy + severity + proposed verdict per R5),
- what changed (inline list with current line refs),
- what was deliberately left unchanged and why,
- the RAG queries run and their hits (file + chunk index),
- compile status.

Wait for explicit human approval before moving on. Approval is recorded in `PLAN_CHECKPOINTS_lap2.md` (checkbox + date + approver initials). No approval → no next section. One question at a time at the gate.

### R3 — Read the section in full before anything else
The **first** action on each section is a full read of its current line range. Queries and edits follow the read. Findings must cite the current line number they refer to.

### R4 — Per-section RAG queries, recorded
Run at least **two queries per section**, scoped per `context/SCOPE-RAG.md` mapping. Reuse the query strings from `PLAN_RAG_latex.md` §3 where they exist (they are known-good), plus the LAP2 probe queries listed in §5. Record each query string, its hits (`file@chunk`), and its verdict (confirm / contradict / negative) in the checkpoint log. Re-verify every evidence chunk with `local-rag_read_chunk_neighbors` before using it.

### R5 — Findings taxonomy (every finding gets all three)
- **Type**: GAP / REDUNDANCY / CONTRADICTION / WEAK-UNSUPPORTED
- **Severity**: HIGH (changes a number or a normative claim) / MED (wording, citation precision) / LOW (style, duplicate mention)
- **Verdict** (proposed at the gate, decided by the human): FIX / KEEP+NOTE / TRIM (TRIM requires explicit human approval)

### R6 — No silent edits
Every edit is logged in `PLAN_CHECKPOINTS_lap2.md` with: current line, exact change, why, and **Source** = `file@chunk` (corpus), `EXTERNAL` (no corpus support, consciously kept), or `INTERNAL` (consistency fix). Never invent a citation; never attribute a claim to a standard the corpus does not contain.

### R7 — Compile after every gate
`latexmk -g -outdir=report report/RAG-informed-SpectrumSensing.tex && latexmk -c -outdir=report report/RAG-informed-SpectrumSensing.tex` from the project root. Zero errors required; warnings tolerated only if pre-existing (compare against Gate 0 baseline). `-outdir=report` is mandatory — without it latexmk writes the PDF to the project root.

### R8 — Unresolvable claims escalate
If the corpus cannot settle a finding, do NOT guess. Leave the text unchanged with the finding flagged, present the options at the gate, and let the human decide. One question at a time.

### R9 — Trims only with approval
Deletion is forbidden except: (a) a redundancy verified by at least two corpus sources or two internal cross-references, AND (b) explicit human approval recorded at that section's gate. Net length change per section: ≤ ±5% of that section's line count.

### R10 — Re-verify LAP1's out-of-corpus register against the grown index
The index has **not** changed since LAP1: `local-rag_status` verified live (2026-08-16) reports **8 documents / 7,083 chunks**. The "12 documents / 7,836 chunks" figure in `context/SCOPE-RAG.md` is the **full catalog** of all documents considered during planning (8 ingested + 4 dropped: BS.1698-1 EMF, M.2225/M.2242 cognitive radio, CRC-162-2025 corrupted) — it is NOT the live index. At Gate 0, run `local-rag_status` and record the numbers; if they changed since this reconciliation, re-run the negative findings of LAP1 (400 kHz BS.412, ANE tolerance formula) and re-check every EXTERNAL row of LAP1 §6 against the current index. If unchanged, record that and proceed.

---

## 3. RAG Tooling Reference

Same as LAP1 (`PLAN_RAG_latex.md` §3): hybrid keyword+semantic search, `scope` parameter for single-document queries, `read_chunk_neighbors` (default ±2) for context. Query strings marked (LAP1) below are reproduced from LAP1's executed table and are known-good; strings marked (LAP2) are new probes for this pass.

---

## 4. The "§" Symbol Work-Stream (Gate 0)

### 4.1 Verified facts (byte-level inspection, 2026-08-16 — do not re-litigate)

| Fact | Evidence |
|------|----------|
| `§` in all `.md` files is **valid UTF-8** U+00A7 SECTION SIGN | bytes `C2 A7` (octal `302 247`) in `README.md`, `AGENTS.md`, `PLAN_RAG_latex.md`, `PLAN_CHECKPOINTS.md`, `context/SCOPE-RAG.md` |
| **No mojibake exists** | zero occurrences of `Â§` (`C3 82 C2 A7`, the classic double-encoded artifact) in any file |
| `.tex` files contain **zero** `§` | `report/RAG-informed-SpectrumSensing.tex`, `template/03SpectrumSensingFM0-copy.tex` and `template/sdr_diagram.tex` are pure ASCII; the only `\S` hits are `\node`/`\font` commands |
| 119 occurrences total, all in `.md` | PLAN_RAG_latex.md 46 · PLAN_CHECKPOINTS.md 47 · SCOPE-RAG.md 19 · README.md 4 · AGENTS.md 3 |

**Conclusion**: the premise "encoding error present across all .md and .tex files" is **falsified for .tex** (no occurrences to fix) and **unsupported for .md** (valid UTF-8, correctly rendered by any UTF-8-aware editor). The character is a legitimate legal-citation convention (`§73.1545`, `§5.1.1`). If the user sees a rendering error, it is a viewer/font/encoding-setting issue in their tool, not a file defect.

### 4.2 What the builder still does (the task's flag-every-occurrence requirement)

1. **Full inventory**: list **all 119 occurrences** as `file:line — context` in the Gate 0 block of `PLAN_CHECKPOINTS_lap2.md`. Do not skip any.
2. **Classify** each occurrence: `REG-CITE` (regulatory citation, e.g. `§73.1545`, `§5.1.1`), `DOC-REF` (cross-reference to a section of the document or a plan, e.g. `§4`, `§8`), `PROSE` (paragraph text).
3. **Record the verification evidence** (the facts table above) verbatim in the log — the plan does not require fixing a non-defect, it requires documenting why there is nothing to fix in `.tex` and letting the human rule on `.md`.

### 4.3 Correction options presented to the human at Gate 0

| Option | Action | Effect on files |
|--------|--------|-----------------|
| **A (recommended)** | Keep as-is; log the verification | No file changes |
| **B** | Normalize only `DOC-REF` occurrences to "Section N" wording; keep `REG-CITE` (`§73.x`, `§5.x`) as legal-citation convention | `.md` only |
| **C** | Replace all 119 with "Sec. N" / "sect. N" consistently | `.md` only |
| — | `.tex` | **untouched in all options** — it contains no `§` |

If the human picks B or C, the corrections are logged per-file (one log entry per `.md` file, listing every changed line) as entries G0-1…G0-5 in `PLAN_CHECKPOINTS_lap2.md`. The human's decision and initials are recorded at Gate 0.

---

## 5. Per-Section Review Directives

For each section: **Read** (current lines), **Queries** (record query strings + hits in the log), **Hunt** (what to look for — every LAP1 edit listed here must be re-verified in context), and the **HITL gate question**.

---

### Section 1 — Introduction (lines 76–103)

**Read**: 76–103 in full.

**Queries**
- (LAP1) `software defined radio definition SDR ITU-R SM.2152 reconfigurable` — re-verify the SM.2152 list item added at L99–100.
- (LAP1) `0 dBr reference level complete multiplex signal power pilot 19 kHz` (scope BS.450) — re-verify the BS.450-4 list item (E16).
- (LAP2) `ANE resolución 105 plan nacional de frecuencias FM Colombia` (scope ANE_0105_2020) — re-verify the "(Colombia)" edit at L98.

**Hunt**
- GAP: ANE Resolución 0463 was used as a source in LAP1 Sections 3 and 7 (see LAP1 roll-up: `ANE_0463_2020@284`) but was **not** added to the regulatory-context list in LAP1 (only BS.450-4 and SM.2152 were). Verify whether the list still omits a standard the document actively cites later.
- WEAK-UNSUPPORTED: any regulatory claim in the intro without a citation anchor.

**LAP1 edits to re-verify**: L98 "(Colombia)"; L99–100 BS.450-4 item; L101 SM.2152 item.

**HITL gate**: approve findings; decide ANE 0463 list treatment if the gap is confirmed.

---

### Section 2 — System-Level Requirements (lines 105–133)

**Read**: 105–133 in full.

**Queries**
- (LAP1) `metrological traceability calibration chain SI ISO 17025` — re-verify the §6.5 anchor at L119.
- (LAP2) `equipment capability calibration triggers ISO 17025 6.4` — re-verify the §6.4.6 anchor at L119.
- (LAP2) `software defined radio definition reconfigurable parameters SM.2152` — re-verify the L109 anchor.

**Hunt**
- REDUNDANCY: calibration-tier descriptions (L127–131) vs the calibration/GPSDO requirements in Section 7 (L655–671) — two places stating traceability/calibration duties; flag if duplicated.
- CONTRADICTION: any requirement text that conflicts with the LAP1-added anchors (e.g., reconfigurability wording vs SM.2152's "parameters set or altered by software").
- WEAK-UNSUPPORTED: cybersecurity item (L115) — EXTERNAL by design; confirm no new corpus source appeared (R10).

**LAP1 edits to re-verify**: L109 anchor; L119 anchor.

**HITL gate**: approve findings; zero-change is an acceptable outcome.

---

### Section 3 — Functional Decomposition (lines 135–222)

**Read**: 135–222 in full (including Figure 1 caption; do not edit the TikZ).

**Queries**
- (LAP1) `73.310 FM technical definitions authorized bandwidth` + neighbors of `47_CFR_Part_73@703` — re-verify L141 band wording.
- (LAP1) `separación entre canales portadoras FM 100 kHz 200 kHz banda 88 108` — re-verify L143 raster clause.

**Hunt**
- REDUNDANCY: the jurisdiction-aware raster clause (L143, "100 kHz ANE / 200 kHz FCC") is now repeated in Section 7 L670 — flag as a duplication candidate (TRIM only with approval).
- CONTRADICTION: L141 "87.5–108 MHz observation span / 88–108 MHz regulated band" vs any other band statement in the document (check Section 7 and Table 1).

**LAP1 edits to re-verify**: L141 band sentence; L143 raster sentence.

**HITL gate**: approve findings; decide on the Section 2 ↔ Section 7 raster redundancy.

---

### Section 4 — FM Compliance Measurands (lines 224–359)

**Read**: 224–359 in full (including Table 1, L259–317).

**Queries**
- (LAP1) `carrier frequency tolerance FM broadcast FCC ±2000 Hz station` — re-verify L233 tiers (±2 kHz ANE / ±3 kHz FCC ≤10 W).
- (LAP2) `ocupación de banda 256 kHz estéreo plan técnico FM ANE` (scope ANE_0105_2020) — re-verify Table 1 occupied-BW row (ANE 256 kHz, PDF-only finding 5.1.5).
- (LAP2) `relación de protección co-canal 37 dB ±100 kHz 25 dB FM` (scope ANE_0105_2020) — re-verify Table 1 ACLR row vs Section 7 L695 (LAP1 corrected E9: ±100 kHz = 25 dB, not 37 dB).
- (LAP1) `0 dBr reference level complete multiplex signal power pilot 19 kHz` (scope BS.412) — re-verify Table 1 MPX row (60 s criterion).

**Hunt**
- REDUNDANCY: the carrier-tolerance statement now appears **three times** — L233, Table 1 carrier row, Section 7 L660. Flag for consolidation (TRIM only with approval) if the three statements are not verbatim identical.
- CONTRADICTION: Table 1 ANE references (PDF-only findings 5.1.1/5.1.5) vs the indexed ANE chunks — verify the numbers match the PDF verification LAP1 recorded; any mismatch is HIGH.
- GAP: classification framework (L322–339) vs Table 1 rows — every measurand in Table 1 should have a capability class; flag missing ones.

**LAP1 edits to re-verify**: L233 formula replacement; L326/L345 class-count fixes; L359 GUM citation; Table 1 rows 5–9 anchors.

**HITL gate**: approve findings; decide the triple-statement tolerance redundancy.

---

### Section 5 — Node-Level DSP Pipeline (lines 361–478)

**Read**: 361–478 in full (Figure 2 caption; do not edit the TikZ).

**Queries**: none — internal design section (same as LAP1). No RAG source exists.

**Hunt**
- REDUNDANCY: pipeline overview (L361–396) vs the per-stage detail in Section 8 — the overview should reference, not duplicate.
- CONTRADICTION: Figure 2 stage names vs Section 8 subsubsection titles (Stage 1–6 mapping); L463 "Three supported decision frameworks" vs Section 10's three rules.
- INTERNAL: verify the LAP1-added `\ref{sec:estimation}` at L478 resolves (label exists at Section 8 header) — compile check covers this.

**LAP1 edits to re-verify**: L478 appendix-pointer replacement; Section 8 `\label{sec:estimation}`.

**HITL gate**: approve findings; zero-change acceptable.

---

### Section 6 — Array-Level Coordination (lines 480–510)

**Read**: 480–510 in full.

**Queries**
- (LAP1) `interlaboratory comparison proficiency testing monitor validity of results` — re-verify the §7.7 anchor at L494–495.

**Hunt**
- WEAK-UNSUPPORTED: the ISO 17025 §7.7 anchor is an analogy (laboratory-to-laboratory comparison vs node-to-node). Assess whether the sentence overclaims the standard — if it does, propose tightening wording (FIX) or a KEEP+NOTE.
- REDUNDANCY: inter-node calibration (L486) vs Tier 1/2/3 records in Section 1.
- CONTRADICTION: two-node corroboration rule (L504) vs Section 10 shared-risk rule semantics.

**LAP1 edits to re-verify**: L494–495 anchor.

**HITL gate**: approve findings; decide anchor wording if overclaiming.

---

### Section 7 — Baseline HackRF One Platform Assessment (lines 512–649)

**Read**: 512–649 in full (Tables 2–3).

**Queries**
- (LAP1) `occupied bandwidth 99 percent of total mean emission power FM` + neighbors of `47_CFR_Part_73@817` — re-verify L518 stepped-mask summary (25/35 dB steps, 43+10log₁₀P vs 80 dB).
- (LAP2) `emisiones no esenciales 35 dB 240 600 kHz protección aeronáutica` (scope ANE_0105_2020) — re-verify the ANE mask half of L518.
- (LAP1) `carrier frequency tolerance…` bonus hit — re-verify Table 3 ±20 ppm → ±2 kHz note at L645.

**Hunt**
- CONTRADICTION: after LAP1, the dynamic-range figure appears as **≈50 dB** (L518, "6.02×8+1.76 = 49.92") and **49.9 dB** (Table 3, L631) and Table 3's SFDR note — verify the three statements are numerically and stylistically consistent; flag precision mismatch (≈50 vs 49.9) as a candidate FIX.
- REDUNDANCY: the stepped-mask summary at L518 vs L599 (Table 2 ACLR row) — LAP1 rewrote both; check whether they are now identical duplicates.
- WEAK-UNSUPPORTED: all HackRF datasheet claims (±20 ppm XO, gain steps, ADC bits) — EXTERNAL; re-check the register against the grown index (R10) before re-marking.

**LAP1 edits to re-verify**: L518 (both fixes); L599; L631 (48.2 → 49.9 dB).

**HITL gate**: approve findings; decide the DR-precision and mask-duplication findings.

---

### Section 8 — Reference Requirements (lines 651–713)

**Read**: 651–713 in full.

**Queries**
- (LAP1) `carrier frequency tolerance FM broadcast FCC ±2000 Hz station` — re-verify L660 tiers.
- (LAP2, R10) `measurement receiver IF bandwidth 400 kHz peak deviation FM demodulation` (scope BS.412, all docs) — **re-run the LAP1 negative finding** now that the index may have grown; if still negative, confirm the de-attribution at L702 stands.
- (LAP1) `0 dBr reference level complete multiplex signal power pilot 19 kHz…` — re-verify the L703 "adopted procedure definition" label vs BS.412 §2.5.1.
- (LAP2) `relación de protección ±100 kHz 25 dB ±200 kHz 7 dB ANE` — re-verify L695 protection-ratio clause.

**Hunt**
- REDUNDANCY: L660 tolerance vs Section 3 L233 + Table 1 (the triple-statement finding); L670 raster vs Section 2 L143; L695 protection ratios vs Table 1 ACLR row — consolidate only with approval.
- CONTRADICTION: after de-attribution, L702 must contain **no** lingering "per BS.412" attribution; L703's "adopted procedure definition" label must not be contradicted by the surrounding Section 7 text (e.g., a later sentence re-attributing the definition to BS.412).
- GAP: each subsection (L655–712) should map to a Table 1 row and a Table 4 rule — flag unmapped requirements.

**LAP1 edits to re-verify**: L660; L670; L695; L702 de-attribution; L703 label.

**HITL gate**: approve findings; decide each redundancy/contradiction verdict.

---

### Section 9 — Estimation Pipeline (lines 715–1070)

**Read**: 715–1070 in full (Stages 1–6).

**Queries**: none — internal notebook-derived spec (same as LAP1).

**Hunt**
- CONTRADICTION: stage parameters vs Section 6 — f_off = f_s/4 (Stage 1) ↔ Section 6 L526; −40 dBc mirror threshold (Stage 2) ↔ Table 2 precondition; Δ_det = 8 dB (Stage 4) ↔ Section 6 L530; 30 kHz/60 kHz DC guard (Stage 4); flag word incl. UNCALIBRATED_REFERENCE (Stage 6) ↔ Section 6 GPSDO rule.
- INTERNAL: spot-check equations for unit consistency and algebra (at minimum: offset-tuning equation, spectral-estimation normalization, carrier estimator, confidence-score combination). No corpus source exists — findings here are INTERNAL.
- GAP: Stage 6 confidence scoring vs Section 9 uncertainty concepts — if the pipeline emits uncertainties that Section 9 never consumes (or vice versa), flag.

**LAP1 edits to re-verify**: `\label{sec:estimation}` resolves; no content edits were made in LAP1.

**HITL gate**: approve findings; zero-change acceptable.

---

### Section 10 — Uncertainty Budget (lines 1072–1144)

**Read**: 1072–1144 in full.

**Queries**
- (LAP1) `7.6 evaluation of measurement uncertainty` — re-verify the ISO 17025 §7.6 basis.
- (LAP1) `Welch-Satterthwaite effective degrees of freedom` — confirm still not in corpus; keep EXTERNAL.
- (LAP2) `Type B evaluation rectangular triangular distribution standard uncertainty` — probe for GUM content in the index; if absent, EXTERNAL as in LAP1.

**Hunt**
- CONTRADICTION: the uncertainty-aware decision summary (L1137–1147) vs Section 10 equations (eq:simple, eq:guardband, eq:sharedrisk) — zone boundaries and defaults must match exactly; flag any drift.
- REDUNDANCY: GUM citation appears in Section 3 L359 AND Section 9 L1079 — LAP1 harmonized them; verify they are now identical.
- WEAK-UNSUPPORTED: Type B factors (a/√3, a/√6, a/2), Welch-Satterthwaite, k at 95.45% — standard GUM practice, not in corpus; re-check under R10 before re-marking EXTERNAL.

**LAP1 edits to re-verify**: none (zero-change section) — but cross-check L359↔L1079 GUM harmonization.

**HITL gate**: approve findings; zero-change acceptable.

---

### Section 11 — Compliance Decision Logic (lines 1146–1260)

**Read**: 1146–1260 in full (equations, Table 4, escalation).

**Queries**
- (LAP1) `decision rule guard band conformity assessment ISO 14253 acceptance rejection zone` — re-verify the ISO 14253-1 treatment (not in corpus; EXTERNAL by decision).
- (LAP2) `JCGM 106 uncertainty conformity assessment` (scope ISO_IEC_17025_2017) — re-verify the LAP1-added JCGM 106:2012 + Guide 98-4 clause.
- (LAP2) `7.8.6 statement of conformity decision rule documentation` — re-verify the §7.8.6 documentation requirement.

**Hunt**
- WEAK-UNSUPPORTED: after LAP1, ISO 14253-1 is still named in the section title (L1168) without corpus support — verify the LAP1 clause (JCGM 106 + Guide 98-4 + §7.8.6) sufficiently frames it as external; if the text still implies corpus backing, propose a FIX.
- CONTRADICTION: eq:simple/eq:guardband/eq:sharedrisk boundary conventions vs Section 9 summary (L1137–1147); Table 4 measurand→rule mapping vs Section 7 subsection defaults — verify every row.
- GAP: escalation policy (L1246–1260) vs Section 5 degraded-mode operation — cross-reference consistency.

**LAP1 edits to re-verify**: the guard-band intro clause (JCGM 106:2012 + Guide 98-4 + §7.8.6).

**HITL gate**: approve findings; then end-of-document review and final roll-up.

---

## 6. Out-of-Corpus Re-Verification Register (LAP1 §6 carry-over)

Re-check **every** row below against the current index at Gate 0 (R10). Record the new verdict (CONFIRMED-EXTERNAL / NOW-VERIFIABLE / STILL-NEGATIVE) in the Gate 0 block of `PLAN_CHECKPOINTS_lap2.md`.

| LAP1 claim | LAP1 status | LAP2 action |
|------------|-------------|-------------|
| L115 cybersecurity requirements | EXTERNAL — leave | re-check index for any security standard; if none, CONFIRMED-EXTERNAL |
| ±2.5 / ±3.5 dB targets (Section 3) | Internal design | INTERNAL — no re-check needed |
| HackRF DR/SFDR numbers (MAX2837) | Datasheet not in index | re-check for HackRF/MAX2837 chunks; EXTERNAL if absent |
| ±20 ppm XO; GPSDO requirement (Section 6) | Platform datasheet | re-check; EXTERNAL if absent |
| ±1×10⁻⁹ GPSDO accuracy (Section 7) | Internal requirement | INTERNAL |
| 400 kHz IF bandwidth "per BS.412" (Section 7 L702) | De-attributed (LAP1 gate) | **re-run negative query** — if the index now contains a 400 kHz receiver-BW reference, the de-attribution decision must be revisited at the Section 7 gate |
| n ≥ 10 recommendations (Section 9) | Internal | INTERNAL |
| GUM Type B factors, Welch-Satterthwaite (Section 9) | GUM not in index; standard math | re-check for GUM/JCGM 100 content; EXTERNAL if absent |
| ISO 14253-1 (Section 10) | Not in index; JCGM 106 added | re-check; EXTERNAL if absent — the Section 10 framing must make this explicit |

---

## 7. PLAN_CHECKPOINTS_lap2.md — Log Template (mandatory)

The builder creates `PLAN_CHECKPOINTS_lap2.md` at Gate 0, **same template as `PLAN_CHECKPOINTS.md`** with these additions:

- **Legend**: `Change` / `Why` / `Source` (`file@chunk`, `EXTERNAL`, or `INTERNAL`) / `Unchanged deliberately` / `Compile` — plus `Finding` (type + severity) and `Verdict` (FIX / KEEP+NOTE / TRIM).
- **Gate 0 — Baseline**: file, length (re-baseline: 1260 lines), `local-rag_status` result (document count / chunk count vs LAP1's 8/7083), baseline compile ✅/❌, the full **§ inventory table** (all 119 occurrences: `file:line — context — class`), the § verification evidence, the § correction decision (A/B/C + approver), and the out-of-corpus re-verification register (per §6).
- **Gate 1…11**: one block per section, same shape as LAP1's blocks:
  - **Findings** table: # | line | finding (type/severity) | evidence (file@chunk or INTERNAL) | proposed verdict | human verdict
  - **Changes** table: # | change | why | source
  - **Deliberately unchanged**, **Compile status**, **Sources consulted**, approval checkbox with date + initials.
- **Final Roll-Up**: all 11 gates approved; final compile clean; net length ≤ ±5% per section; every finding resolved (FIX/KEEP+NOTE/TRIM); every regulatory figure traced to chunk, EXTERNAL, or INTERNAL; § inventory closed; summary of source documents used (per-file, as in LAP1's roll-up).

---

## 8. Execution Order and Definition of Done

1. Builder reads: this plan, `PLAN_RAG_latex.md`, `PLAN_CHECKPOINTS.md`, `context/SCOPE-RAG.md`.
2. **Gate 0**: baseline compile; `local-rag_status` + index reconciliation (R10); § inventory (all 119, §4.2); § correction decision (HITL); out-of-corpus re-verification register (§6). **STOP for human approval of Gate 0** before any section work — Gate 0 carries the § decision the user requested.
3. For each section 1 → 11 (LAP1 numbering):
   a. Read the section in full (R3).
   b. Run the section's queries; record strings + hits (R4).
   c. Compile the findings (R5); present at the gate with proposed verdicts.
   d. Apply only the changes the human approves at the gate.
   e. Compile: `latexmk -g -outdir=report report/RAG-informed-SpectrumSensing.tex && latexmk -c -outdir=report report/RAG-informed-SpectrumSensing.tex`. Zero errors.
   f. Fill the gate block in `PLAN_CHECKPOINTS_lap2.md`; **STOP** for approval (R2).
4. After Section 11: final full compile + clean; fill the Final Roll-Up; done.

Definition of done for LAP2:
- All 11 gates + Gate 0 approved;
- Document compiles clean and aux files are cleaned;
- Net length within ±5% per section;
- Every finding logged with type, severity, verdict, and source;
- Every regulatory figure traces to a corpus chunk, an EXTERNAL/INTERNAL register entry, or an approved TRIM;
- The § work-stream is closed: 119 occurrences inventoried, verification evidence recorded, correction decision made by the human and applied (if B or C) with per-file logs;
- `PLAN_CHECKPOINTS_lap2.md` fully populated per §7.