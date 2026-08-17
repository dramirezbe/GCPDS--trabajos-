# PLAN_CHECKPOINTS.md — Per-Section Change Log (HITL Audit Trail)

Purpose: record, per section of `report/RAG-informed-SpectrumSensing.tex`, **what changed and why**, with the source documents used, at each human review gate. This file is filled by the builder agent as it works; it is the audit trail that makes every edit traceable.

**Format of every gate report:** the builder fills the section block below, then STOPS for human approval. Approval = checking the box. No approval → no next section.

Legend:
- **Change**: exact text-level edit made (with pre-refactor line number)
- **Why**: the defect (wrong number, broken citation, inconsistency, unverifiable attribution)
- **Source**: RAG corpus file + chunk index (`file@chunk`), or `EXTERNAL` (no corpus support), or `INTERNAL` (consistency fix, no external source)
- **Unchanged deliberately**: things reviewed and left alone, with reason
- **Compile**: `latexmk -g` result

---

## Gate 0 — Baseline (before any edit)

| Metric | Value |
|--------|-------|
| File | `report/RAG-informed-SpectrumSensing.tex` |
| Length | 1260 lines |
| RAG index | 8 documents, 7083 chunks (`/home/javastral/RAG-documents/`) |
| Baseline compile | ✅ PASS — `latexmk -g` produced 32-page PDF, zero errors (2026-08-16) |

Baseline issues inventory (from PLAN_RAG_latex.md §5; builder checks these off as fixed or consciously declined):

- [ ] L233 carrier-tolerance formula unsourceable → replace with FCC §73.1545 tiers (Section 3 gate)
- [ ] L326 "Three capability classes" but four listed (bug)
- [ ] L345 parenthetical omits Conditional Compliance-Grade
- [ ] L518 ">80 dB" mask claim vs stepped FCC/ANE masks
- [ ] L518 DR arithmetic (6.02×8+1.76 = 49.92 dB ≠ ≈48 dB) vs Table 3 (48.2 dB)
- [ ] L599 ">70 dB" mask claim in Table 2
- [ ] L660 "2 kHz tolerance" without FCC power tiers
- [ ] L670/L695 "200 kHz" without ANE 100 kHz raster
- [ ] L702 400 kHz IF bandwidth attributed to BS.412 — unverified
- [ ] L703 MPX 0 dBr definition vs BS.412 §2.5.1
- [ ] L478 dangling appendix pointer
- [ ] L141 87.5–108 vs regulated 88–108 band wording
- [ ] Optional anchors: SM.2152 (SDR def), BS.450-4, ISO 17025 §7.7, JCGM 106:2012

---

## Introduction (unnumbered; lines 76–103)

**Changes**
| # | Change | Why | Source |
|---|--------|-----|--------|
| 1 | L98: "(applicable jurisdiction)" → "(Colombia)" | State plainly that Resolución 105 is the Colombian national plan; generic phrasing obscured jurisdiction | ANE_0105_2020 (corpus title: Colombian national spectrum plan) |
| 2 | L99–100: added ITU-R BS.450-4 list item (signal model, max deviation, stereophonic multiplex) | Human-approved gate decision (plan §5, Introduction gate); standard is used in Sections 3 and 7 but was absent from the context list | BS.450-4@4 |
| 3 | L101: added ITU-R SM.2152 list item (SDR definition) | Human-approved gate decision; anchors the SDR terminology used throughout, esp. Section 1 reconfigurability | SM.2152@21–23 |

**Deliberately unchanged**
- L87 "Regulatory bodies evaluating technical adequacy" — accurate; no change (plan §5, Introduction gate, issue 1)
- L103 RFC 2119 footnote — kept unchanged (plan §5, Introduction gate, issue 4)
- Note: +2 lines on a 28-line section ≈ +7% vs the ±5% R3 budget — authorized by the human at the gate (plan explicitly permits "adding = expansion" as a gate decision)

**Compile status**: ✅ PASS — `latexmk -g` 32-page PDF, zero errors; aux cleaned (2nd compile after list additions also PASS)

**Sources consulted**
- SM.2152@21–23 (SDR definition, E23) — verified
- BS.450-4@4 (±75 kHz deviation standard, E16) — verified
- 47_CFR_Part_73@703 (FM band 88–108 MHz, 200 kHz raster, E4) — verified

- [x] **Human approval** (2026-08-16, JS): approved fixes + "Add both" for SM.2152/BS.450-4

---

## Section 1 — System-Level Requirements (lines 105–133)

**Changes**
| # | Change | Why | Source |
|---|--------|-----|--------|
| 1 | L109 Reconfigurability: anchored to ITU-R SM.2152 SDR definition (RF operating parameters set/altered by software) | Human-approved anchoring; terminology now consistent with the Intro list addition (Introduction gate) | SM.2152@21–23 |
| 2 | L119 Measurement Integrity: anchored to ISO/IEC 17025:2017 clauses 6.5 (metrological traceability) and 6.4.6 (equipment calibration triggers) | Human-approved anchoring; makes the traceability/calibration requirement traceable to the governing standard | ISO_IEC_17025_2017@65, @58 |

**Deliberately unchanged**
- L115 Cybersecurity — no corpus support; left as internal requirement (EXTERNAL register, plan §6)
- L127–131 calibration tiers — consistent with ISO 17025 §6.5 traceability chain and §7.8.4 certificates; no change

**Compile status**: ✅ PASS — `latexmk -g` zero errors; aux cleaned

**Sources consulted**
- SM.2152@21–23 (SDR definition, E23)
- ISO_IEC_17025_2017@65 (6.5 traceability), @58 (6.4.5/6.4.6)

- [x] **Human approval** (2026-08-16, JS): "Anchor both"

---

## Section 2 — Functional Decomposition (lines 135–222)

**Changes**
| # | Change | Why | Source |
|---|--------|-----|--------|
| 1 | L141: band sentence now distinguishes observation span 87.5–108 MHz (ITU Region 2 planning band) from regulated FM service band 88–108 MHz | Previous wording implied the regulated service spans 87.5–108 MHz; FCC defines 88–108 MHz | 47_CFR_Part_73@703; ANE_0105_2020@1801 |
| 2 | L143: channel-raster clause now jurisdiction-aware ("100 kHz (ANE channel plan) or 200 kHz (FCC channelization)") | Raster differs by jurisdiction; single-raster wording was misleading | ANE_0105_2020@1501, @1801; 47_CFR_Part_73@703 |

**Deliberately unchanged**
- Figure 1 TikZ (L151–222) — content correct, no RAG issues (R4: no cosmetic changes)

**Compile status**: ✅ PASS — `latexmk -g` zero errors; aux cleaned

**Sources consulted**
- 47_CFR_Part_73@703 (88–108 MHz, 200 kHz raster, E4)
- ANE_0105_2020@1501 (100 kHz separation), @1801 (199 channels, 88–108 MHz) — E7

- [x] **Human approval** (2026-08-16, JS): "Approve both"

---

## Section 3 — FM Compliance Measurands (lines 224–359)

**Changes**
| # | Change | Why | Source |
|---|--------|-----|--------|
| 1 | L233: unsourceable formula $\pm(0.5 + 2 \times f \times 10^{-5})$ kHz → $\pm 2$ kHz (ANE FM plan + FCC §73.1545(b) >10 W) / $\pm 3$ kHz (FCC ≤10 W) | Formula had NO corpus source. **PLAN DEVIATION**: the plan expected "ANE sets no FM tolerance" — PDF verification (mandated by the plan itself) found ANE Anexo 2 §5.1.1: "máxima variación… será de + 2 kHz" (FM service). Index misses it; local PDF has it | 47_CFR_Part_73@1670; ANE_0105_2020 PDF line 2363 (Anexo 2, §5.1.1) |
| 2 | L326: "Three capability classes" → "The following capability classes" | Four classes listed after an intro saying "three" (bug) | INTERNAL |
| 3 | L345: parenthetical now includes conditional compliance-grade | List omitted the 4th class | INTERNAL |
| 4 | L359: GUM → (GUM, JCGM 100:2008) | Harmonized with Section 9 L1078 citation | ISO_IEC_17025_2017@183 (bibliography, Guide 98-3) |
| 5 | Table 1 carrier row: compliance reference → ANE ±2 kHz + FCC §73.1545(b) tiers | Generic reference anchored | 47_CFR_Part_73@1670; ANE PDF §5.1.1 |
| 6 | Table 1 field-strength row: anchored to 47 CFR §73.315 (≥70 dBu) + BS.412-9 Table 1 | Generic reference anchored | 47_CFR_Part_73@789; BS.412-9@5 |
| 7 | Table 1 occupied-BW row: anchored to §73.317(b) (deemed ≤240 kHz) + ANE 256 kHz stereo limit | Generic reference anchored; ANE 256 kHz is a PDF-only finding (5.1.5) | 47_CFR_Part_73@818; ANE PDF §5.1.5 |
| 8 | Table 1 ACLR row: anchored to §73.317(c)–(d) + ANE non-essential mask | Generic reference anchored | 47_CFR_Part_73@818; ANE_0105_2020@1156–1161 |
| 9 | Table 1 deviation/MPX row: anchored to BS.450-4 ±75 kHz + BS.412-9 §2.5.1 60 s criterion | Generic reference anchored | BS.450-4@4; BS.412-9@26 |

**Deliberately unchanged**
- L234–235 ±2.5/±3.5 dB targets — internal design (EXTERNAL register)
- L239 channel occupancy — policy-defined detection rule, correctly generic
- ANE mask row "25 dB @ 120–240 kHz" — was PDF-verified (5.1.4.1) but not inserted: the ACLR row cites the mask section without enumerating rows (kept short per plan)

**Compile status**: ✅ PASS — `latexmk -g` zero errors; aux cleaned

**Sources consulted**
- 47_CFR_Part_73@1670 (E1), @818 (E3), @789 (E5); BS.412-9@5 (E12), @26 (E14); BS.450-4@4, @11 (E16); ANE_0105_2020@1156–1161 (E8), @1170–1172 (E11 STL); docs-RAG/ANE_0105_2020.pdf Anexo 2 §5.1.1/5.1.4/5.1.5 (PDF-verified)

- [x] **Human approval** (2026-08-16, JS): approved Section 3; L233 = "ANE + FCC" (recommended option)

---

## Section 4 — Node-Level DSP Pipeline (lines 361–478)

**Changes**
| # | Change | Why | Source |
|---|--------|-----|--------|
| 1 | L478: "in the Appendix" → "in Section~\ref{sec:estimation}" | Dangling appendix pointer — document has no appendix; Section 8 carries the estimation detail (human-approved defect fix, R7) | INTERNAL |
| 2 | Section 8 header: added \label{sec:estimation} | Required for the new cross-reference to resolve; no `sec:` labels existed in the document (minimal R4 fix) | INTERNAL |

**Deliberately unchanged**
- Entire pipeline content — internal design spec, no corpus source (INTERNAL)
- L463 "Three supported decision frameworks" ↔ Section 10 has exactly three ✓
- Stage names in Figure 2 ↔ subsection titles ✓
- Stage 4 DC guard quirk (30 kHz parameter, 60 kHz effective test) — faithfully documented implementation quirk, left as-is

**Compile status**: ✅ PASS — `latexmk -g` zero errors; aux cleaned

**Sources consulted**
- none — internal section; consistency checks only

- [x] **Human approval** (2026-08-16, JS): approved zero-content changes; appendix pointer → "Point to Section 8"

---

## Section 5 — Array-Level Coordination (lines 480–510)

**Changes**
| # | Change | Why | Source |
|---|--------|-----|--------|
| 1 | L494–495 Cross-node consistency: added closing clause citing ISO/IEC 17025:2017 clause 7.7 | Human-approved anchoring; cross-node comparison is the array analogue of the standard's validity-of-results monitoring | ISO_IEC_17025_2017@107–111 (7.7), @33 (3.3 definition) |

**Deliberately unchanged**
- L486 inter-node calibration — internally consistent with Tier 1/2/3 records
- L504 two-node corroboration rule — internal fusion policy (INTERNAL)

**Compile status**: ✅ PASS — `latexmk -g` zero errors; aux cleaned

**Sources consulted**
- ISO_IEC_17025_2017@107–111 (7.7.1–7.7.3), @33 (3.3)

- [x] **Human approval** (2026-08-16, JS): "Anchor §7.7"

---

## Section 6 — Baseline HackRF One Platform Assessment (lines 512–649)

**Changes**
| # | Change | Why | Source |
|---|--------|-----|--------|
| 1 | L518: "out-of-band attenuation exceeding 80 dB" → stepped-mask summary (25 dB @ 120–240 kHz; 35 dB @ 240–600 kHz; lesser of 43+10log₁₀P or 80 dB beyond 600 kHz FCC; ANE same formula without 80 dB cap) | The 80 dB blanket claim misstated the stepped FCC/ANE masks | 47_CFR_Part_73@818 (E3); ANE_0105_2020@1156–1161 + ANE PDF §5.1.4 (E8) |
| 2 | L518: DR ≈48 dB → ≈50 dB (6.02×8+1.76 = 49.92 dB) | Arithmetic error: formula evaluates to 49.92, not ≈48; human chose "Formula ≈50 dB" | INTERNAL (formula); datasheet EXTERNAL |
| 3 | L599 Table 2 ACLR row: "masks requiring >70 dB" → far-offset mask attenuation (43+10log₁₀P or 80 dB beyond 600 kHz) | Same stepped-mask imprecision as L518 | 47_CFR_Part_73@818 |
| 4 | L631 Table 3: theoretical DR 48.2 dB → 49.9 dB (8-bit, 6.02×8+1.76) | Consistency with L518 after gate decision | INTERNAL |

**Deliberately unchanged**
- L528 −40 dBc I/Q residual threshold — consistent across Sections 6 and 7 and Table 2 (INTERNAL)
- L530 Δ_det = 8 dB default ↔ Stage 4 (L833) ✓
- L534 ±20 ppm XO + GPSDO requirement — EXTERNAL (datasheet), internally consistent
- L536 harmonic-rejection placeholder — internal implementation status
- L634 SFDR note (dBFS vs dBc) — technically sound, kept
- L645 ±20 ppm → ±2 kHz @ 100 MHz — arithmetic verified (20×10⁻⁶ × 100 MHz = 2 kHz), kept

**Compile status**: ✅ PASS — `latexmk -g` zero errors; aux cleaned

**Sources consulted**
- 47_CFR_Part_73@818 (E3), @1670 (E1 cross-check for L645); ANE_0105_2020@1156–1161 (E8), ANE PDF §5.1.4

- [x] **Human approval** (2026-08-16, JS): mask fixes approved; DR = "Formula ≈50 dB"

---

## Section 7 — Reference Requirements (lines 651–713)

**Changes**
| # | Change | Why | Source |
|---|--------|-----|--------|
| 1 | L660: "2 kHz tolerance specified by FCC Part 73" → jurisdiction-complete: ±2000 Hz (>10 W) / ±3000 Hz (≤10 W) per §73.1545(b) or ±2 kHz under the ANE FM plan | Power-tiered FCC tolerance was stated as a single 2 kHz value | 47_CFR_Part_73@1670 (E1); ANE PDF §5.1.1 |
| 2 | L670: "nominally 200 kHz for FM broadcast" → 200 kHz (FCC) / 100 kHz (ANE) | Jurisdiction-dependent raster (high severity per plan) | 47_CFR_Part_73@703 (E4); ANE_0105_2020@1501, 1801 (E7) |
| 3 | L695: ACLR window 200 kHz → 200 kHz (FCC) / 100 kHz (ANE) + ANE protection-ratio clause (25 dB @ ±100 kHz; 7 dB @ ±200 kHz) | Same jurisdiction issue; **plan deviation**: E9's "37 dB @ ±100 kHz" is wrong — PDF shows 37 dB is the CO-CHANNEL ratio; ±100 kHz = 25 dB, ±200 kHz = 7 dB (index truncated the row; verified in PDF lines 4355–4359) | ANE_0105_2020@1857–1862 + ANE PDF §9.1 |
| 4 | L702: 400 kHz IF bandwidth de-attributed from BS.412 — now "internal engineering requirement; ITU-R BS.412 does not prescribe a receiver IF bandwidth" | Human-approved de-attribution; PDF verification found no 400 kHz receiver bandwidth in BS.412-9 (hits are carrier-difference tables) | docs-RAG/BS.412-9.pdf full-text search (negative) |
| 5 | L703: MPX 0 dBr labelled as adopted procedure definition, distinct from BS.412 §2.5.1 criterion (60 s-integrated power vs ±19 kHz single tone), both recorded | Human-approved "Label as adopted def"; original text conflated a reporting reference with the BS.412 criterion | BS.412-9@26, @29 (E14) |

**Deliberately unchanged**
- L659 GPSDO ±1×10⁻⁹ — EXTERNAL internal requirement, kept
- L704 pilot/RDS verification — supported by E6/E16; optional anchor declined to keep changes minimal
- L710–712 occupancy items — internal, consistent with Table 2

**Compile status**: ✅ PASS — `latexmk -g` zero errors; aux cleaned

**Sources consulted**
- 47_CFR_Part_73@1670, @703, @829 (E6); ANE_0105_2020@1501, @1801, @1857–1862; ANE PDF §9.1; BS.412-9@26, @29, @90–94 (E15); docs-RAG/BS.412-9.pdf full-text (negative 400 kHz finding); BS.450-4@4, @11 (E16)

- [x] **Human approval** (2026-08-16, JS): approved fixes; L702 = "De-attribute"; L703 = "Label as adopted def"

---

## Section 8 — Estimation Pipeline (lines 715–1070)

**Changes**
| # | Change | Why | Source |
|---|--------|-----|--------|
| — | (none) | Zero-change section — internal notebook-derived spec; no corpus source exists or is needed | INTERNAL |

**Deliberately unchanged**
- Stage 1 offset tuning f_off = f_s/4 ↔ Section 6 L526 ✓ consistent
- Stage 2 mirror threshold −40 dBc ↔ Table 2 (tab:capability) precondition (5) ✓
- Stage 4 Δ_det = 8 dB ↔ Section 6 L530 ✓
- Stage 4 DC guard (30 kHz parameter, 60 kHz effective test) — faithfully described implementation quirk, left
- Stage 6 flag word incl. UNCALIBRATED_REFERENCE ↔ Section 6 L534 GPSDO rule ✓
- Cross-refs "Section~5" (L550, L1239) verified: Array-Level Coordination IS section 5 — consistent with the document's LaTeX numbering, no defect

**Compile status**: ✅ PASS (no edits this section; compile verified at Section 8 gate)

**Sources consulted**
- none — internal section; consistency checks only

- [x] **Human approval** (2026-08-16, JS): zero-change section confirmed

---

## Section 9 — Uncertainty Budget (lines 1072–1144)

**Changes**
| # | Change | Why | Source |
|---|--------|-----|--------|
| — | (none) | Zero-change section — GUM citation verified correct and harmonized with Section 3 (L359/L1079 both "GUM, JCGM 100:2008"); Type A/B factors, Welch-Satterthwaite, k=2 all standard GUM | INTERNAL |

**Deliberately unchanged**
- L1088 n ≥ 10 minimum — internal operational rule (EXTERNAL)
- L1090–1098 Type B a/√3, a/√6, a/2 factors — standard GUM §4.3 (not in corpus)
- L1122 Welch-Satterthwaite + t-distribution k at 95.45% — standard GUM §G.4
- L1137–1147 uncertainty-aware decision summary ↔ Section 10 eq:simple/eq:guardband/eq:sharedrisk — verified consistent (3 rules, same zones, same defaults)
- Cross-refs verified: L480 → \ref{sec:estimation} (§8) ✓; L550/L698/L1239/L1257 "Section~5" = Array-Level Coordination ✓

**Compile status**: ✅ PASS (no edits; compile verified at Section 8 gate)

**Sources consulted**
- none — internal section; consistency checks only

- [x] **Human approval** (2026-08-16, JS): zero-change section confirmed

---

## Section 10 — Compliance Decision Logic (lines 1146–1260)

**Changes**
| # | Change | Why | Source |
|---|--------|-----|--------|
| 1 | Guard-band subsection intro: added clause citing JCGM 106:2012 + ISO/IEC Guide 98-4 as equivalent conformity-assessment frameworks, and requiring decision-rule documentation per ISO/IEC 17025:2017 §7.8.6 | ISO 14253-1 not in corpus (EXTERNAL); JCGM 106:2012 and Guide 98-4 verified in ISO 17025 bibliography; §7.8.6 mandates documenting the decision rule and risk | ISO_IEC_17025_2017@183 ([28] Guide 98-4, [33] JCGM 106:2012), @123 (§7.8.6), @35 (§3.7) |

**Deliberately unchanged**
- eq:simple / eq:guardband / eq:sharedrisk — mathematically consistent, no change (INTERNAL)
- L1204 shared-risk boundary convention (|x−x_ref| = T+U → NON-COMPLIANT) — explicit, left
- Table 4 rows ↔ Section 7 defaults (Guard-Band: carrier/BW/ACLR/deviation/occupancy; Shared-Risk: power; N/A: field strength) — verified consistent
- L1239/L1257 "Section~5" = Array-Level Coordination ✓

**Compile status**: ✅ PASS — `latexmk -g` zero errors; aux cleaned

**Sources consulted**
- ISO_IEC_17025_2017@35, @123, @183 (Guide 98-4, JCGM 106:2012, §7.8.6 decision-rule documentation)

- [x] **Human approval** (2026-08-16, JS): "Add JCGM 106:2012"

---

## Final Roll-Up (after Section 11 approval)

| Check | Result |
|-------|--------|
| All 11 gates approved | ✅ (2026-08-16, JS) |
| Final compile `latexmk -g` clean | ✅ zero errors |
| Aux files cleaned (`latexmk -c`) | ✅ |
| Net length within ±5% of 1260 lines | ✅ 1265 lines (+5, +0.4%) |
| Every regulatory figure traced to chunk or EXTERNAL register | ✅ (see §2.1/§3.3/§4.4/§6.5/§8.1–8.5 sources; L233/L702 rows resolved by gate decisions) |

## Summary of Source Documents Used (roll-up)

| Document | Sections where it was used | Key chunks |
|----------|---------------------------|------------|
| `47_CFR_Part_73.pdf` | Introduction, 2, 3, 6, 7 | 703–706, 789, 818, 829, 914, 1668, 1670 |
| `ANE_0105_2020.pdf` | 2, 3, 6, 7 | 1051, 1155–1162, 1501, 1801, 1857–1862, 1170–1178 + PDF-only: §5.1.1 (±2 kHz), §5.1.4.1 (25 dB row), §5.1.5 (256/302/200 kHz), §9.1 (protection ratios co-channel 37/25/7/−7, D 6/3/0/−7) |
| `ANE_0463_2020.pdf` | 3, 7 | 284 |
| `BS.412-9.pdf` | 3, 7 | 5, 10, 18, 21, 26, 29, 90–96 + full-text negative: no 400 kHz receiver IF bandwidth |
| `BS.450-4.pdf` | 3, 7 | 4, 7, 9, 11, 12, 13 |
| `ISO_IEC_17025_2017.pdf` | 5, 9, 10 | 33, 35, 58, 65, 105, 107–110, 123, 183 |
| `SM.2152.pdf` | Introduction, 1 | 21–23 |
| `ANE_0406_2026.pdf` | (allocations only — no text claims) | — |

Documents dropped from scope (per `context/SCOPE-RAG.md`): BS.1698-1, M.2225, M.2242, CRC-162-2025.

## PDF-only findings (index gaps discovered during this run)

| Finding | Location | Status |
|---------|----------|--------|
| ANE FM carrier tolerance ±2 kHz (§5.1.1) | ANE PDF line 2363 | Used — falsified plan E11 |
| ANE mask row 25 dB @120–240 kHz (§5.1.4.1) | ANE PDF | Used — Section 6 edit |
| ANE occupied-BW limits 256/302/200 kHz (§5.1.5) | ANE PDF | Used — Sections 3 and 6 edits |
| ANE protection ratios (co-channel 37, ±100: 25, ±200: 7, ±300: −7 dB; D: 6/3/0/−7) | ANE PDF §9.1, lines 4355–4361 | Used — corrected plan E9 misread |
| No 400 kHz receiver IF bandwidth in BS.412-9 | BS.412-9 PDF full-text | Used — L702 de-attribution |
| 20 ppm STL tolerance (heading at ANE@1170) | ANE PDF | Confirmed — not FM carrier tolerance |
