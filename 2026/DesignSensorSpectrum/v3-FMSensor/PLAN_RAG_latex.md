# PLAN — RAG-Informed Refactor of `report/RAG-informed-SpectrumSensing.tex`

Status: PLANNING COMPLETE — RAG queries executed, evidence base compiled. Awaiting builder-agent execution with per-section human review (HITL).

---

## 1. Purpose and Scope

Refactor the LaTeX document **`report/RAG-informed-SpectrumSensing.tex`** (the file — 1260 lines, 11 sections) so that every regulatory, metrological, and standards claim is verified and, where wrong or unverifiable, corrected **in place** using the RAG corpus at `/home/javastral/RAG-documents/`.

The refactor improves the document's **evidence anchoring**, not its volume. This is not a rewrite, not an expansion, and not a redesign.

### Target file inventory (line numbers refer to the pre-refactor file)

| # | Section | Lines | Key content |
|---|---------|-------|-------------|
| — | Introduction (unnumbered) | 76–103 | Purpose, audience, regulatory context (FCC, ANE 105, BS.412, ISO 17025) |
| 1 | System-Level Requirements | 105–133 | 6 requirements + 3 calibration tiers (Tier 1/2/3) |
| 2 | Functional Decomposition | 135–222 | 4 components + Figure 1 (architecture TikZ) |
| 3 | FM Compliance Measurands | 224–359 | Primary measurands, secondary observables, metadata, Table 1, classification framework |
| 4 | Node-Level DSP Pipeline | 361–478 | 6-stage pipeline overview + Figure 2 |
| 5 | Array-Level Coordination | 480–510 | 8 coordination items (inter-node calibration → degraded mode) |
| 6 | Baseline HackRF One Platform Assessment | 512–649 | Limitations, DC artifact, I/Q imbalance, upgrade paths, Tables 2–3 |
| 7 | Reference Requirements (Compliance-Grade) | 651–713 | Per-measurand requirements |
| 8 | Estimation Pipeline of Measurands | 715–1070 | Stage 1–6 detailed math (notebook-derived) |
| 9 | Uncertainty Budget and Reporting | 1072–1144 | GUM Type A/B, combined/expanded uncertainty, decision rules intro |
| 10 | Compliance Decision Logic | 1146–1260 | 3 decision frameworks, Table 4, escalation |

---

## 2. Builder Agent Ground Rules (MANDATORY — this is the contract)

These rules are normative for whoever executes this plan. Any deviation requires human authorization.

### R1 — Section-by-section, never whole-document
Work on exactly **one section per iteration**, in document order (Introduction, then 1 → 10). Do not batch edits across sections. Each section's work ends at its HITL gate.

### R2 — HITL gate after every section (hard stop)
After finishing one section's changes, **STOP**. Do not start the next section. Report to the human:
- what changed (inline list with line refs),
- what was deliberately left unchanged and why,
- the RAG sources used (file + chunk index),
- compile status.

Wait for explicit human approval before moving on. Approval is recorded in `PLAN_CHECKPOINTS.md` (checkbox + date + approver initials). No approval → no next section.

### R3 — Improve content WITHOUT expanding it
- **No new sections, subsections, paragraphs, tables, or figures.** The document's structure, length, and section count must stay effectively constant.
- Edits are replacements and refinements of existing sentences: correct a wrong number, fix a citation, tighten a claim, align wording with a standard.
- Net length change per section: ≤ ±5% of that section's line count. If a correction genuinely needs more words, they must come from trimming elsewhere in the same section.
- Numbered equations, table labels (`tab:*`, `fig:*`), and `\ref` keys are preserved unless the reference itself is broken.

### R4 — Design/structure changes only where necessary
Structural LaTeX changes (geometry, colors, titleformat, table column widths, TikZ) are permitted **only** to fix an actual defect (e.g., a broken cross-reference, an overfull table) and never for cosmetic restyling. The document's visual identity is not in scope.

### R5 — Every claim must be traceable
Each corrected claim must be grounded in a corpus chunk (recorded in `PLAN_CHECKPOINTS.md` as `file@chunk`), or explicitly marked **EXTERNAL** when the claim is internal engineering design with no corpus support (see §6 register). Never invent a citation. Never attribute a claim to a standard that the corpus does not contain (see §6).

### R6 — No code, LaTeX only
This is a document project. Do not create scripts, notebooks, or build tooling. Verification is only: `latexmk -g report/RAG-informed-SpectrumSensing.tex && latexmk -c` (run from project root; see AGENTS.md build instructions — the `-g` force rebuild always produces a PDF, then aux files are cleaned).

### R7 — Never delete, only correct
No content may be silently removed. Wrong content is replaced by correct content in the same location, and the replacement is logged in `PLAN_CHECKPOINTS.md`.

### R8 — Unresolvable claims escalate to the human
If the corpus cannot settle a claim (e.g., the ANE FM plan's carrier-tolerance value is not in the index), do NOT guess. Either leave the text unchanged with a flag, or present the options at the HITL gate and let the human decide. One question at a time.

---

## 3. RAG Tooling Reference

- Index: 8 documents, 7083 chunks, hybrid keyword+semantic search (`local-rag_query_documents`).
- Scope a query to one document with the `scope` parameter, e.g. `scope: "/home/javastral/RAG-documents/47_CFR_Part_73.pdf"`.
- Get context around a hit with `local-rag_read_chunk_neighbors` (`filePath` + `chunkIndex`, default ±2 chunks).
- `docs-RAG/` in this repo is a **human reading copy only** — never treat it as the index; use it only to verify what the index cannot extract (e.g., table rows dropped by PDF parsing).
- `context/SCOPE-RAG.md` maps each document to the spec sections it supports. Follow that mapping; do not query BS.1698-1 / M.2225 / M.2242 / CRC-162 (dropped).

### Queries already executed (this planning phase)

| Theme | Queries run | Key hits (file@chunk) |
|-------|-------------|------------------------|
| Carrier tolerance | `carrier frequency tolerance FM broadcast FCC ±2000 Hz station` | `47_CFR_Part_73@1670` (§73.1545), `47_CFR_Part_73@1668` (§73.1540) |
| Occupied BW / mask | `occupied bandwidth 99 percent of total mean emission power FM` + neighbors of `47_CFR_Part_73@817` | `47_CFR_Part_73@818` (§73.317(b)–(e)) |
| ANE mask | `emisiones no esenciales 25 dB entre 120 kHz 240 kHz…` + neighbors of `ANE_0105_2020@1158` | `ANE_0105_2020@1155–1162` |
| ANE channel plan | `separación entre canales portadoras FM 100 kHz 200 kHz banda 88 108` | `ANE_0105_2020@1501, 1801, 1051` |
| ANE protection ratios | neighbors of `ANE_0105_2020@1859` | `ANE_0105_2020@1857–1862` |
| ANE deviation/pilot | `frequency deviation maximum FM broadcast 75 kHz …` (scope ANE_0463) | `ANE_0463_2020@284` |
| ANE tolerance (STL) | `tolerancia de frecuencia portadora estación FM clase…` + neighbors of `ANE_0105_2020@1176` | `ANE_0105_2020@1170–1178` (20 ppm is STL, NOT FM) |
| Field strength | `minimum usable field strength FM broadcasting rural urban large cities dBµV/m BS.412` | `BS.412-9@5` (Table 1), `47_CFR_Part_73@789` (§73.315), `47_CFR_Part_73@914` (§73.515) |
| Protection ratios | `radio frequency protection ratio co-channel adjacent channel FM broadcasting dB BS.412` | `BS.412-9@10, 18, 21` |
| MPX / deviation | `0 dBr reference level complete multiplex signal power pilot 19 kHz…` (scope BS.412), `multiplex signal power reference…` (scope BS.450) | `BS.412-9@26, 29, 90–96`; `BS.450-4@4, 7, 9, 11, 12, 13` |
| 400 kHz IF claim | `measurement receiver IF bandwidth 400 kHz peak deviation FM demodulation` (BS.412), `bandwidth receiver measurement 400 kHz…` (BS.450) | **No supporting chunk found** (see §6) |
| Decision rules | `decision rule guard band conformity assessment ISO 14253 acceptance rejection zone` | `ISO_IEC_17025_2017@35` (3.7), `@123` (7.8.6), `@75` (Guide 98-4 note) |
| Uncertainty | `Welch-Satterthwaite effective degrees of freedom…`, `Type B evaluation rectangular triangular…`, `7.6 evaluation of measurement uncertainty…` | `ISO_IEC_17025_2017@105` (7.6), `@183` (bibliography: Guide 98-3, 98-4, JCGM 106) |
| Traceability | `metrological traceability calibration chain SI ISO 17025` (implicit in 7.6 query) | `ISO_IEC_17025_2017@65` (6.5), `@58` (6.4.5/6.4.6) |
| Validity of results | `interlaboratory comparison proficiency testing…` | `ISO_IEC_17025_2017@107–110` (7.7), `@33` (3.3–3.5) |
| SDR definition | `software defined radio definition SDR ITU-R SM.2152 reconfigurable` | `SM.2152@21–23` |
| FCC definitions | `73.310 FM technical definitions authorized bandwidth…` + neighbors of `47_CFR_Part_73@703` | `47_CFR_Part_73@701–706` |
| FCC stereo | `carrier frequency tolerance…` (bonus hit) | `47_CFR_Part_73@829` (§73.322 pilot 8–10%) |
| Negative findings | `tolerancia 2000 Hz tres mil variación frecuencia portadora…` (ANE, all docs) | No FM-specific tolerance formula in corpus |

---

## 4. RAG Evidence Base — canonical facts for the builder

These facts were verified against the index during planning. The builder re-verifies with `read_chunk_neighbors` before each edit and records the chunk in `PLAN_CHECKPOINTS.md`.

| # | Fact | Source (file@chunk) |
|---|------|---------------------|
| E1 | FCC §73.1545(b): FM carrier tolerance ±2000 Hz (>10 W), ±3000 Hz (≤10 W) | `47_CFR_Part_73@1670` |
| E2 | FCC §73.1540(c): primary frequency standard = NBS (NIST) / WWV, WWVB, WWVH | `47_CFR_Part_73@1668` |
| E3 | FCC §73.317(b)–(e): emission mask — ≥25 dB at 120–240 kHz, ≥35 dB at 240–600 kHz, ≥ max(43+10log₁₀P, 80 dB) beyond 600 kHz; compliance with (b) deems occupied BW ≤ 240 kHz; pre-emphasis ≤ 75 µs | `47_CFR_Part_73@818` |
| E4 | FCC §73.310: FM band 88–108 MHz; channel 200 kHz wide, 88.1→107.9 in 200 kHz steps | `47_CFR_Part_73@703` |
| E5 | FCC §73.315: ≥70 dBu (3.16 mV/m) over principal community; §73.515: NCE-FM 60 dBu over ≥50% of community | `47_CFR_Part_73@789, 914` |
| E6 | FCC §73.322: 19 kHz pilot FM-modulates carrier 8–10%; 38 kHz subcarrier = 2nd harmonic | `47_CFR_Part_73@829` |
| E7 | ANE 105 FM plan: 100 kHz channel raster; 199 channels 88.1–107.9 | `ANE_0105_2020@1501, 1801, 1051` |
| E8 | ANE 105 FM plan: non-essential emissions mask — 35 dB at 240–600 kHz; beyond 600 kHz, protect 32 [µV/m] field criterion in 108–137 MHz aeronautical bands (25 dB row for 120–240 kHz exists in the PDF but was dropped by chunk extraction — verify in `docs-RAG/ANE_0105_2020.pdf` before citing) | `ANE_0105_2020@1155–1162` |
| E9 | ANE 105 FM plan: RF protection ratios, classes A/B/C at ±100/±200/±300 kHz = 37 dB / 25 dB / (third value truncated in index — verify in PDF); class D = 6 / 3 / 0 / −7 dB | `ANE_0105_2020@1857–1862` |
| E10 | ANE 463: Colombian FM must be "stereophonic quality" with 19 kHz pilot and maximum frequency excursion ±75 kHz | `ANE_0463_2020@284` |
| E11 | ANE 105: 20 ppm carrier tolerance text belongs to the studio-transmitter link, NOT the FM broadcast service | `ANE_0105_2020@1170–1172` |
| E12 | BS.412-9 Table 1: minimum usable field strength (10 m AGL) mono/stereo — rural 48/54, urban 60/66, large cities 70/74 dB(µV/m) | `BS.412-9@5` |
| E13 | BS.412-9 §2.1.1: RF protection ratio definition; curves (Figs 1–2) assume ±75 kHz / ±50 kHz max deviation; tabulated values in Table 3 | `BS.412-9@10, 18, 21` |
| E14 | BS.412-9 §2.5.1: MPX power limit — power of complete multiplex signal (pilot + additional signals) integrated over any 60 s ≤ power of single tone causing ±19 kHz peak deviation (equivalent: coloured noise ±32 kHz quasi-peak per BS.641) | `BS.412-9@26, 29` |
| E15 | BS.412-9 Annex 4: peak deviation measured peak-hold per minute; MPX power in floating 60 s window shifted 1 s; measurement devices use very short response time | `BS.412-9@90–94` |
| E16 | BS.450-4: max deviation ±75 kHz or ±50 kHz (75 in W. Europe + US); pilot-tone MPX amplitudes: M 90%, S 90%, pilot 8–10%, residual 38 kHz subcarrier ≤1%; pilot phase tolerance ±3° | `BS.450-4@4, 11, 12` |
| E17 | BS.450-4: supplementary signals constrained to subcarriers 15–23 kHz or 53–76 kHz; total deviation never > ±75 kHz | `BS.450-4@13` |
| E18 | ISO 17025 §3.7: decision rule definition; §7.8.6: statements of conformity must document the decision rule and risk | `ISO_IEC_17025_2017@35, 123` |
| E19 | ISO 17025 §6.4.5/6.4.6: equipment capability + calibration triggers; §6.5: metrological traceability (unbroken chain to SI) | `ISO_IEC_17025_2017@58, 65` |
| E20 | ISO 17025 §7.6.1–7.6.3: evaluate measurement uncertainty, all significant contributions | `ISO_IEC_17025_2017@105` |
| E21 | ISO 17025 §7.7 + 7.7.2: monitor validity of results; monitor performance by comparison with other laboratories (proficiency testing, interlaboratory comparisons) | `ISO_IEC_17025_2017@107–110` |
| E22 | ISO 17025 bibliography: ISO/IEC Guide 98-3 (GUM:1995), Guide 98-4, JCGM 106:2012 (uncertainty in conformity assessment), ISO 21748 | `ISO_IEC_17025_2017@183` |
| E23 | SM.2152: SDR definition — radio employing technology allowing RF operating parameters (frequency range, modulation type, output power) to be set or altered by software | `SM.2152@21–23` |

---

## 5. Per-Section Refactor Directives

For each section: **Issues** (with pre-refactor line numbers), **Evidence to apply** (E# references from §4), **Allowed changes**, **Forbidden changes**, and the **HITL gate question**.

---

### Introduction (unnumbered; lines 76–103)

**Issues**
- L87: "Regulatory bodies evaluating technical adequacy" — fine; no change.
- L94–101 Regulatory Context list cites FCC Part 73, ANE Resolución 105, ITU-R BS.412, ISO/IEC 17025 — all present in corpus ✓, but the list omits BS.450-4 (signal model source, E16/E17) and SM.2152 (SDR definition, E23), both actively used later. **Decision for human at gate: add 1–2 list items or leave as-is (adding = expansion; alternative is to leave list and let Sections 3 and 7 carry the citations).**
- L98: "ANE Resolución 105 (applicable jurisdiction)" — the document should state plainly that 105 is Colombian (ANR→ANE) or keep the generic phrasing; corpus title confirms it is the Colombian national plan (MINTIC compilation). Minor wording fix, no length change.
- L103 footnote (RFC 2119) — keep unchanged.

**Evidence to apply**: E23 (SDR def), E16 (BS.450 signal model), E4 (FCC band).

**Allowed**: wording corrections only; no new sentences beyond a possible one-line citation.

**Forbidden**: expanding the regulatory context into a table or adding a "standards overview" subsection.

**HITL gate**: approve the regulatory-context wording fixes and decide whether SM.2152/BS.450-4 get cited in the list.

---

### Section 1 — System-Level Requirements (lines 105–133)

**Issues**
- L109 Reconfigurability item — aligns with SM.2152's "parameters set or altered by software" (E23). Optional: one clause to anchor the definition ("as defined by ITU-R SM.2152"). No expansion otherwise.
- L119 Measurement Integrity item — matches ISO 17025 §6.5 traceability + §6.4.6 calibration triggers (E19). Anchoring optional, same rule.
- L115 Cybersecurity item — **no corpus support** (index has no security standard). Leave text unchanged; record as EXTERNAL in `PLAN_CHECKPOINTS.md`.
- Tier 1/2/3 descriptions (L127–131) — consistent with ISO 17025 §6.5 (E19) and §7.8.4 calibration certificates. No change required.

**Evidence to apply**: E23, E19.

**Allowed**: at most two in-place anchoring clauses if human approves; otherwise no changes.

**Forbidden**: new requirements, new tiers, rewording that changes normative meaning.

**HITL gate**: confirm whether definition anchoring is wanted here or skipped (zero-change section is an acceptable outcome).

---

### Section 2 — Functional Decomposition (lines 135–222)

**Issues**
- L141: "VHF-II broadcast band (87.5–108 MHz)" — the *regulated FM broadcast* band is 88–108 MHz in both FCC (§73.310, E4) and the ANE plan (E7); 87.5–108 MHz is the wider ITU Region 2 planning band. **Fix in place**: distinguish the front-end observation band (87.5–108 MHz) from the regulated FM service band (88–108 MHz) in the same sentence. No length growth.
- L143: "multiple contiguous FM broadcast channels within a single acquisition window" — channel raster differs by jurisdiction (FCC 200 kHz vs ANE 100 kHz, E4/E7). **Fix in place**: make the sentence jurisdiction-aware ("contiguous channels on the applicable 100 kHz or 200 kHz raster").
- Figure 1 (L151–222): content is fine; no RAG issues. Leave TikZ untouched.

**Evidence to apply**: E4, E7.

**Allowed**: the two sentence-level precision fixes above.

**Forbidden**: touching the TikZ figure, adding component descriptions.

**HITL gate**: approve the band/raster wording.

---

### Section 3 — FM Compliance Measurands and Traceability Requirements (lines 224–359)

**Issues** (this is the section with the most findings)
- **L233 — HIGH SEVERITY**: "carrier frequency error: ±(0.5 + 2 × f × 10⁻⁵) kHz" — this formula has **no source in the corpus** (queries across all 8 documents found nothing; the only ANE tolerance text, 20 ppm, belongs to the STL, E11). **Correct in place** to the jurisdiction-cited values: FCC §73.1545 ±2000 Hz (>10 W) / ±3000 Hz (≤10 W) (E1), with a clause that the ANE FM plan sets no explicit FM carrier tolerance in the indexed text (verify once in `docs-RAG/ANE_0105_2020.pdf` Anexo 2 before finalizing). Present the replacement sentence at the HITL gate.
- L234: "±2.5 dB" power and L235: "±3.5 dB" field-strength — internal design targets, no corpus conflict. Keep; mark EXTERNAL.
- L236: "occupied bandwidth and related spectral-containment indicators" — anchor to FCC §73.317(b) (deemed ≤240 kHz when mask met, E3) as the compliance reference in Table 1 row (L293–297).
- L239: "channel occupancy" — no corpus source; keep generic (policy-defined detection rule). Already correct.
- L326 — **BUG**: "Three capability classes are defined:" but four classes follow (L330–336). **Fix**: "The following capability classes are defined:" (or "Four").
- L345: parenthetical "(compliance-grade, screening-grade, unsupported)" omits Conditional Compliance-Grade. **Fix**: add it to the parenthetical.
- Table 1 (L259–317): compliance-reference column is generic; anchor each row: carrier freq → FCC §73.1545 (E1); occupied BW → FCC §73.317(b) (E3); field strength → BS.412-9 Table 1 + FCC §73.315 (E5, E12); ACLR → FCC §73.317(c)/(d) + ANE mask (E3, E8); peak deviation/MPX → BS.450-4 ±75 kHz + BS.412 §2.5.1 (E14–E16). Keep the cell text short; these are section-number insertions, not new prose.
- L357: "Guide to the Expression of Uncertainty in Measurement (GUM)" — correct citation is JCGM 100:2008; add "(JCGM 100:2008)" if not already there in Section 9 (check L1076 — already cited there; harmonize here).

**Evidence to apply**: E1, E3, E5, E8, E12, E14, E16, E11 (negative).

**Allowed**: all fixes above; table-cell compliance references.

**Forbidden**: adding measurands, changing units, reformatting Table 1 columns.

**HITL gate**: approve the carrier-tolerance replacement sentence and the Table 1 reference anchoring.

---

### Section 4 — Node-Level DSP Pipeline (lines 361–478)

**Issues**
- Content is an internal design specification; no corpus source needed or available (index has no spectrum-monitoring methodology document). Zero RAG changes expected.
- **Internal-consistency check only** (no edits unless broken): L463 "Three supported decision frameworks" ↔ Section 10 has exactly three ✓; stage names in Figure 2 ↔ subsection titles ✓; L478 appendix pointer — the document has no appendix (pre-existing inconsistency; **flag at gate, do not fix silently** — human decides whether to delete the pointer, which is allowed under R7 as a defect fix, or leave it).

**Evidence to apply**: none (internal section).

**Allowed**: only the appendix-pointer fix if human approves.

**Forbidden**: any content changes.

**HITL gate**: decide on the dangling appendix pointer (L478).

---

### Section 5 — Array-Level Coordination (lines 480–510)

**Issues**
- L486 Inter-node calibration and L494–495 cross-node consistency checks align directly with ISO 17025 §7.7.2 "monitor performance by comparison with results of other laboratories" and §3.3–3.5 interlaboratory comparison definitions (E21). **Optional one-clause anchor** ("consistent with the validity-of-results monitoring concept of ISO/IEC 17025:2017 §7.7") — human decides.
- L504: "two eligible nodes independently report the same exceedance" — internal fusion policy, no corpus conflict. Keep.

**Evidence to apply**: E21.

**Allowed**: at most one anchoring clause per item where human approves; otherwise zero changes.

**Forbidden**: changing fusion rules, adding coordination items.

**HITL gate**: approve/reject the ISO 17025 §7.7 anchoring.

---

### Section 6 — Baseline HackRF One Platform Assessment (lines 512–649)

**Issues**
- **L518 — HIGH SEVERITY (arithmetic + citation)**: "8-bit ADC offers a theoretical dynamic range of only ≈48 dB (6.02 × 8 + 1.76 dB)". The parenthetical evaluates to 49.92 dB ≈ 50 dB, not ≈48 dB. Table 3 (L629) states 48.2 dB theoretical. **Fix in place**: make the two consistent — either quote the datasheet figure (48.2 dB) with the formula removed, or quote 6.02·8+1.76 = 49.92 dB. Human picks at the gate; corpus has no HackRF datasheet (record as EXTERNAL).
- **L518 — HIGH SEVERITY (citation)**: "Regulatory standards (e.g., FCC Part 73, ANE Resolución 105) often mandate out-of-band emission attenuation exceeding 80 dB" — imprecise vs E3 (stepped mask: 25/35 dB steps, 80 dB only beyond 600 kHz and only as the lesser of 43+10logP and 80 dB) and vs E8 (ANE: 35 dB at 240–600 kHz; aeronautical-band protection beyond). **Fix in place**: replace "exceeding 80 dB" with a correct one-clause summary of the stepped masks, or cite the specific sections (§73.317(b)–(d); ANE Anexo 2 "Emisiones no esenciales") without listing all numbers.
- L528 (I/Q imbalance): −40 dBc residual threshold is internal design; consistent across Sections 6 and 7 and Table 2 ✓. No change.
- L530: Δ_det = 8 dB default ↔ Stage 4 (L830) ✓ consistent. No change.
- L534: ±20 ppm XO claim and GPSDO requirement — EXTERNAL (datasheet not in index). Keep; mark EXTERNAL.
- L536: harmonic-rejection placeholder — internal. Keep.
- **L590 (Table 2)**: "Absolute power accuracy limited by gain quantisation (±2–8 dB steps)" — fine; consistent with L736 (IF gain 8 dB steps, baseband 2 dB steps) ✓. No change.
- **L593 (Table 2, Field Strength row)**: "dynamic range of 35–45 dB is insufficient for weak-signal monitoring" — internally consistent with Table 3 (L630). No change.
- **L599 (Table 2, ACLR row)**: "regulatory emission masks requiring >70 dB attenuation" — same stepped-mask imprecision as L518. Align with the chosen L518 formulation (E3/E8).
- L633 (Table 3, SFDR note): the dBFS/dBc explanatory note is technically sound. Keep.
- L645 (Table 3): "±20 ppm → ±2 kHz absolute error at 100 MHz" ✓ arithmetic correct (20×10⁻⁶ × 100 MHz = 2 kHz) and meaningfully tied to E1. Keep.

**Evidence to apply**: E3, E8, E1.

**Allowed**: L518 (both parts), L599 fixes; nothing else.

**Forbidden**: changing HackRF figures that are EXTERNAL but internally consistent.

**HITL gate**: approve the emission-mask summary wording and pick the DR arithmetic resolution (48.2 dB vs 49.92 dB).

---

### Section 7 — Reference Requirements for Compliance-Grade Deployments (lines 651–713)

**Issues**
- **L660**: "2 kHz carrier-frequency tolerance specified by FCC Part 73" — incomplete per E1 (power-dependent tiers). **Fix in place**: "+2000 Hz (>10 W) / ±3000 Hz (≤10 W) per §73.1545(b), or the applicable jurisdictional limit".
- **L659**: GPSDO "±1 × 10⁻⁹ or better" — EXTERNAL (no corpus support). Keep; mark.
- **L670 — HIGH SEVERITY**: "nominally 200 kHz for FM broadcast" — jurisdiction-dependent (FCC 200 kHz, ANE 100 kHz raster, E4/E7). **Fix in place**: "nominally 200 kHz under FCC channelization; 100 kHz under the ANE plan" style clause.
- **L695**: ACLR integration window "200 kHz centred on the adjacent or alternate channel carrier, consistent with the FM channel plan" — same jurisdiction issue (ANE adjacent channels at ±100 kHz). Align with the L670 fix; also ANE protection ratios (E9: 37 dB @ ±100 kHz, 25 dB @ ±200 kHz) are the applicable adjacent-channel thresholds for Colombia and may be cited in one clause.
- **L702 — HIGH SEVERITY (unverifiable attribution)**: "minimum IF bandwidth of 400 kHz … consistent with the measurement method defined in ITU-R BS.412". Planning queries found **no 400 kHz receiver bandwidth in BS.412-9** (Annex 4 describes response time and 60 s integration, E15; the only bandwidths indexed are filter bandwidths in Annex 2). **Fix in place**: either (a) de-attribute — drop the "consistent with … BS.412" clause and keep 400 kHz as an internal engineering requirement, or (b) verify manually in `docs-RAG/BS.412-9.pdf` §2.5 and restore the citation if actually present. Human decides at the gate.
- **L703 — HIGH SEVERITY (definition mismatch)**: MPX 0 dBr reference described as "75 kHz peak deviation of a 1 kHz sine tone, with the 19 kHz stereo pilot present at its nominal level". BS.412 §2.5.1 (E14) defines the reference differently: the 60 s-integrated complete-multiplex power must not exceed the power of a single tone causing ±19 kHz peak deviation (BS.641 equivalence). **Fix in place**: align the definition with BS.412 §2.5.1, or explicitly label the current text as "an adopted procedure definition, distinct from the BS.412 §2.5.1 criterion" — human decides.
- L704: "19 kHz pilot and 57 kHz RDS sub-carrier independently verified in magnitude" — supported by E6 (pilot 8–10%) and E16 (BS.450 MPX amplitudes). Optional anchor only.
- L710–712 (occupancy): site-calibrated threshold etc. — internal; consistent with Table 2. No change.

**Evidence to apply**: E1, E4, E7, E9, E14, E15, E16, E6.

**Allowed**: the four flagged fixes (L660, L670, L695, L702, L703).

**Forbidden**: adding requirement bullets.

**HITL gate**: approve the four fixes; decide 400 kHz attribution and MPX reference wording.

---

### Section 8 — Estimation Pipeline of Measurands (lines 715–1070)

**Issues**
- Internal notebook-derived spec. No RAG changes expected.
- **Internal-consistency checks only**: Stage 1 offset-tuning equation ↔ Section 6 L526 ✓; Stage 2 mirror threshold −40 dBc ↔ Table 2 precondition (5) ✓; Stage 4 Δ_det = 8 dB ↔ Section 6 L530 ✓; Stage 4 DC guard (30 kHz parameter, 60 kHz effective test) is faithfully described as an implementation quirk — leave.
- Stage 6 flag word (L1042–1050) includes `UNCALIBRATED_REFERENCE` ↔ Section 6 L534 ✓.

**Evidence to apply**: none (internal).

**Allowed**: nothing, unless a broken cross-reference is found during compile checks.

**Forbidden**: any changes.

**HITL gate**: zero-change confirmation (human may still request specific checks).

---

### Section 9 — Uncertainty Budget and Reporting (lines 1072–1144)

**Issues**
- L1076: "GUM, JCGM 100:2008" — correct citation ✓ (corpus corroborates via ISO 17025 bibliography Guide 98-3 = GUM:1995, E22). No change.
- L1085: "minimum of n = 10 independent estimates" — internal recommendation; EXTERNAL. Keep.
- L1092: Type B distribution factors (a/√3, a/√6, a/2) — standard GUM arithmetic; GUM full text is NOT in the index. Values are correct GUM practice; keep, mark EXTERNAL (formula itself unverifiable in corpus).
- L1119: Welch–Satterthwaite + k from t-distribution at 95.45% — standard GUM §G.4 practice; **Welch–Satterthwaite text is not in the corpus** (query confirmed). Keep; mark EXTERNAL. Do not remove.
- L1136–1142 (uncertainty-aware decisions): consistent with Section 10 equations and ISO 17025 §3.7/7.8.6 (E18). No change.
- Optional (human decides): add "JCGM 106:2012" as a corpus-backed reference next to ISO 14253-1 in Section 10 (E22) — see Section 10.

**Evidence to apply**: E18, E22.

**Allowed**: nothing mandatory; the optional JCGM 106 addition belongs to Section 10.

**Forbidden**: rewriting GUM math.

**HITL gate**: zero-change confirmation + decision on the JCGM 106/Guide 98-4 citation option for Section 10.

---

### Section 10 — Compliance Decision Logic and Uncertainty Handling (lines 1146–1260)

**Issues**
- L1148/L1168: "ISO 14253-1" guard-band attribution — ISO 14253-1 is **not in the index**. The corpus-backed references for uncertainty-in-conformity-assessment are ISO 17025 §3.7/§7.8.6 (E18) and, via its bibliography, ISO/IEC Guide 98-4 and JCGM 106:2012 (E22). **Fix in place**: keep ISO 14253-1 if the human wants it (it is a legitimate real-world standard; it is simply outside the corpus), and/or add the corpus-verifiable JCGM 106:2012 reference. Decision at gate; a one-clause addition is the maximum expansion permitted.
- Equations (eq:simple, eq:guardband, eq:sharedrisk) — mathematically consistent with the Section 9 summary (L1139–1141) ✓. No change.
- L1201: shared-risk boundary convention (|x−x_ref| = T+U → NON-COMPLIANT) — consistent with the R-set definition ✓. No change.
- Table 4 (L1207–1244): measurand↔rule mapping consistent with Section 7 defaults ✓. No change.
- L1253: "default: 72 hours" escalation bound — internal policy. Keep.

**Evidence to apply**: E18, E22.

**Allowed**: the citation decision above; nothing else.

**Forbidden**: changing decision equations or the Table 4 mapping.

**HITL gate**: final approval of the citation handling; then end-of-document review.

---

## 6. Out-of-Corpus Claims Register (do NOT alter without human decision)

These claims appear in the document but are **not verifiable in the RAG index**. The builder must not silently rewrite them; they are either left as-is with an EXTERNAL marker in `PLAN_CHECKPOINTS.md`, or changed only after an explicit human decision.

| Line (pre-refactor) | Claim | Status |
|---------------------|-------|--------|
| L115 | Cybersecurity requirements | Internal requirement — leave |
| L233 | Carrier error formula ±(0.5 + 2×f×10⁻⁵) kHz | **Replace with E1 tiers (decision already taken in §5, Section 3 gate)** |
| L234–235 | ±2.5 dB / ±3.5 dB targets | Internal design targets — leave |
| L518, L629 | HackRF DR/SFDR numbers (MAX2837) | Datasheet not in index — leave numbers, fix only the arithmetic/citation issue |
| L534, L645 | ±20 ppm XO; GPSDO requirement | Platform datasheet — leave |
| L659 | ±1×10⁻⁹ GPSDO accuracy | Internal requirement — leave |
| L702 | 400 kHz IF bandwidth "per BS.412" | **Gate decision: de-attribute or verify in docs-RAG PDF** |
| L1085 | n ≥ 10 recommendations | Internal — leave |
| L1092, L1119 | GUM Type B factors, Welch–Satterthwaite | GUM not in index; math is standard — leave, mark EXTERNAL |
| L1168 | ISO 14253-1 | Standard not in index; legitimate — keep and/or add JCGM 106:2012 (gate decision) |
| L478 | Dangling appendix pointer | Defect; gate decision whether to remove |

---

## 7. Execution Order and Checkpoint Protocol

1. Builder reads this plan + `PLAN_CHECKPOINTS.md` + `context/SCOPE-RAG.md`.
2. For each section (Introduction unnumbered, then 1 → 10):
   a. Re-verify each evidence chunk with `local-rag_read_chunk_neighbors` before editing.
   b. Apply only the **Allowed** changes from the section directive.
   c. Compile: `latexmk -g report/RAG-informed-SpectrumSensing.tex && latexmk -c` from the project root. Zero errors required (warnings tolerated only if pre-existing).
   d. Fill the section's row in `PLAN_CHECKPOINTS.md` (changes, why, sources, deliberately unchanged, compile status).
   e. **HITL gate**: present the summary, STOP, wait for approval (recorded by checkbox in `PLAN_CHECKPOINTS.md`).
3. After Section 11 approval: final full compile + clean, update `PLAN_CHECKPOINTS.md` roll-up, done.

Definition of done for the whole refactor:
- All 11 gates approved;
- Document compiles clean with `latexmk -g` and aux files cleaned;
- Net document length within ±5% of 1260 lines;
- Every regulatory figure in the document traces to a corpus chunk or is on the EXTERNAL register;
- `PLAN_CHECKPOINTS.md` fully populated.
