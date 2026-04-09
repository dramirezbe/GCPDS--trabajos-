### USER PROMPT

Role
You are a senior RF/DSP engineer and SDR systems architect with experience in educational laboratory design. Your task is to produce a Requirements and Feasibility Analysis for an FM broadcast spectrum sensing and monitoring system intended for university laboratory use.
System Context
The system uses the following hardware and software:

Receiver: RTL-SDR dongle (R820T2 or equivalent COTS device)
Antenna: Passive FM broadcast dipole or telescopic whip
Host platform: Standard personal computer (Windows, Linux, or macOS)
Software tools: GNU Radio, Python (NumPy, SciPy, Matplotlib), and FFT/PSD analysis libraries
This is a receive-only system. No transmission is involved at any point. The system monitors the FM broadcast band (88–108 MHz) for educational and research purposes only.
Your Task
Produce a structured Requirements and Feasibility Analysis document. This is Phase 1 of a broader SDR system design lifecycle. You are not designing the full system. You are not writing code. You are not producing a lab manual. You are scoping and validating whether the system is technically viable and what constraints govern the design.
Required Output Structure
A. Stakeholder Requirements
Identify and state the needs of each stakeholder group:

Students (primary users)
Lab instructor or course designer
Institution (cost, safety, reproducibility)
For each stakeholder, list requirements in plain language. Distinguish between must-have and nice-to-have requirements.
B. Functional Requirements
State what the system must do. Each requirement must be:

Specific and testable
Referenced to a measurable parameter where possible
Tagged as FR-01, FR-02, etc.
Cover at minimum:

Signal detection range (88–108 MHz band)
Frequency resolution achievable with RTL-SDR and FFT
Spectrum occupancy estimation
Signal visualization (spectrum, waterfall, PSD)
Channel identification within the FM band
Data capture and storage (IQ samples, CSV, or similar)
Support for offline (recorded IQ) and live (hardware) operation modes
C. Non-Functional Requirements
State constraints on system quality, usability, and context. Tag as NFR-01, NFR-02, etc.
Cover at minimum:

Cost ceiling (total BOM must remain below a defined threshold — propose a realistic value)
PC hardware baseline (RAM, CPU, OS)
Reproducibility (must run on a standard student laptop)
Regulatory compliance (passive monitoring only, no transmission, applicable spectrum regulations)
Software licensing (open-source preferred)
Ease of setup (target: student with no prior SDR experience can operate within one lab session)
Maintainability and extensibility
D. RTL-SDR Hardware Constraints and Feasibility
This section is mandatory and must be technically rigorous. Address each of the following limitations explicitly. For each one, state the limitation, its engineering consequence for this application, and whether it makes the requirement feasible, conditionally feasible, or infeasible.
ConstraintDescriptionEngineering consequenceFeasibility verdictADC resolution8-bit ADC, ~48 dB theoretical dynamic range......Sample rateStable range approximately 0.5–2.4 MSPS (up to 3.2 MSPS with drop risk)......Tuning range~24 MHz to ~1.766 GHz (R820T2)......DC spikeLO leakage causes a spurious spike at center frequency......IQ imbalanceAmplitude and phase mismatch between I and Q channels......Gain controlManual or AGC; no calibrated absolute power level......Frequency accuracyTCXO variants improve accuracy; standard crystals may drift tens of ppm......Aliasing riskSignals near band edges of the IF filter may alias......USB throughputBandwidth limited by USB 2.0; sample drops possible under load......Noise figureTypically 8–15 dB NF depending on gain settings and LNA presence......After completing the table, write a short paragraph summarizing the overall feasibility verdict for FM band monitoring given these constraints.
E. Regulatory and Ethical Constraints
State the applicable regulatory framework for passive spectrum monitoring in an educational context (reference ITU Radio Regulations, or national framework such as FCC Part 15 or local equivalent as appropriate — acknowledge that regulations vary by country and that the design team must verify locally).
Confirm that no transmission is involved and explain why this removes the primary regulatory burden.
Note any institutional or ethical obligations around data storage of intercepted broadcast content.
State that the system must never be used to interfere with, decode in an unauthorized manner, or retransmit broadcast content.
F. Feasibility Summary
Produce a structured feasibility assessment across four dimensions:
Technical feasibility: Can the RTL-SDR hardware meet the functional requirements within its known limitations? Be specific about which requirements are fully met, which require mitigation, and which are borderline.
Economic feasibility: Provide a realistic Bill of Materials estimate with approximate costs. Include RTL-SDR dongle, antenna, any optional components (LNA, bias tee, bandpass filter), and software (should be zero-cost if open-source). Confirm the system fits within a university lab budget.
Operational feasibility: Can a student with introductory RF/DSP knowledge operate this system after a one-session orientation? What prerequisite knowledge is assumed?
Schedule feasibility: Estimate realistic time allocations for each subsequent design phase (architecture, prototyping, DSP development, integration, validation) so that stakeholders understand what follows this phase. These are rough estimates, not commitments.
G. Assumptions and Open Questions
List all assumptions made during this analysis. Use a numbered list. For each assumption, state what would change if the assumption is wrong.
List any open questions that must be resolved before moving to the next design phase. These may include site-specific RF environment questions, institutional software licensing questions, or unresolved hardware variant choices.
Mandatory Style and Quality Rules
Be technically precise. Use engineering units throughout (MHz, MSPS, dB, dBm, bits, ms, etc.).
Do not hand-wave. If a tradeoff exists, name both sides and explain which is preferred and why.
If something is uncertain, say so explicitly rather than asserting false confidence.
Do not include implementation details, code, GNU Radio flowgraphs, or lab exercises. Those belong to later phases.
Do not recommend unnecessary expensive hardware. If an optional component is mentioned, justify its inclusion with a concrete engineering reason.
Every functional requirement must be traceable to a stakeholder need.
The feasibility verdict must be honest. If a requirement is borderline or conditionally feasible, say so clearly and state what condition must be met.
Flag any requirement that the RTL-SDR cannot meet without qualification.
Penalization Rules for Self-Review
Before finalizing your output, verify the following. If any item is violated, revise before outputting:

[ ] No transmission is assumed or implied anywhere
[ ] All RTL-SDR limitations are addressed individually and with engineering consequence
[ ] No expensive hardware is proposed without justification
[ ] All functional requirements are tagged and testable
[ ] Regulatory context is addressed
[ ] Feasibility verdict is honest and specific, not generic
[ ] Assumptions are listed explicitly
[ ] Open questions are identified
[ ] No code, flowgraphs, or lab instructions appear in this document (those are later phases)


---

### AI RESPONSE

# Phase 1: Requirements and Feasibility Analysis
**Project:** FM Broadcast Spectrum Sensing System
**Context:** Educational Laboratory / SDR Systems Architecture
**Date:** April 7, 2026

---

## A. Stakeholder Requirements

**1. Students (Primary Users)**
* **Must-Have:** * System must provide immediate, clear visual feedback of the RF spectrum to correlate abstract DSP concepts with real-world signals.
    * System must support offline data processing so assignments can be completed outside of laboratory hours.
    * Setup must be intuitive and not require advanced hardware debugging skills.
* **Nice-to-Have:** * Cross-platform compatibility (Windows, macOS, Linux) to accommodate personal devices.

**2. Lab Instructor / Course Designer**
* **Must-Have:**
    * Hardware and software stack must produce deterministic, reproducible results across multiple workstations.
    * System limitations (e.g., dynamic range, noise) must be well-documented so they can be incorporated into learning objectives rather than acting as silent errors.
* **Nice-to-Have:**
    * Standardized data export formats to facilitate automated grading or standardized analysis scripts.

**3. Institution (Administration / Facilities)**
* **Must-Have:**
    * Total per-station cost must remain strictly within undergraduate lab budget constraints.
    * System must be purely passive (receive-only) to avoid regulatory liabilities and safety hazards associated with RF transmission.
    * Zero ongoing software licensing costs.
* **Nice-to-Have:**
    * Hardware components should be durable or cheap enough to treat as consumable items if damaged.

---

## B. Functional Requirements

* **FR-01: Signal Detection Range.** The system must tune to and capture RF signals within the standard FM broadcast band (88.0 MHz to 108.0 MHz).
* **FR-02: Instantaneous Bandwidth.** The system must capture contiguous frequency spans of at least 2.0 MHz without dropping samples.
* **FR-03: Frequency Resolution.** The system must support an effective FFT frequency resolution of $\leq$ 1 kHz to distinguish narrow sub-carriers or adjacent channel leakage.
* **FR-04: Spectrum Visualization.** The system must generate real-time Power Spectral Density (PSD) plots and waterfall (spectrogram) displays of the live RF environment.
* **FR-05: Channel Identification.** The system must reliably estimate the center frequency and occupied bandwidth of FM broadcast signals possessing an SNR $\geq$ 10 dB above the measured noise floor.
* **FR-06: Data Capture.** The system must record raw baseband IQ samples to local storage in standard binary or CSV formats at a sample rate of $\geq$ 2.0 MSPS for a minimum duration of 10 seconds.
* **FR-07: Offline Operation.** The software architecture must allow users to inject pre-recorded IQ files into the DSP pipeline seamlessly, yielding identical analytical results to live hardware capture.

---

## C. Non-Functional Requirements

* **NFR-01: Cost Ceiling.** The total Bill of Materials (BOM) per laboratory station must not exceed $50 USD.
* **NFR-02: PC Hardware Baseline.** The processing software must run in real-time without buffer underruns on a standard baseline laptop (x86_64 or ARM64 architecture, 8 GB RAM, multi-core CPU released within the last 5 years).
* **NFR-03: Reproducibility.** The hardware must interface via standard USB 2.0/3.0 Type-A or Type-C ports natively available on student machines.
* **NFR-04: Regulatory Compliance.** The system must strictly operate in a passive monitoring capacity, ensuring zero RF emissions. 
* **NFR-05: Software Licensing.** The software stack must rely entirely on free and open-source software (FOSS), specifically GNU Radio and Python (NumPy, SciPy, Matplotlib).
* **NFR-06: Ease of Setup.** A student with no prior SDR experience must be able to connect the hardware, launch the environment, and view a spectrum plot within 15 minutes during the first lab session.
* **NFR-07: Maintainability.** The system relies entirely on standard hardware variants (R820T2 tuner) and mainstream DSP libraries to prevent "bit rot" over a 5-year curriculum lifecycle.

---

## D. RTL-SDR Hardware Constraints and Feasibility

| Constraint | Description | Engineering Consequence | Feasibility Verdict |
| :--- | :--- | :--- | :--- |
| **ADC resolution** | 8-bit ADC, ~48 dB theoretical dynamic range | Strong local FM stations will easily mask distant, weak stations or saturate the ADC (causing clipping and harmonics). Manual RF gain tuning is required. | **Conditionally feasible** (System must rely on manual gain control; strictly limits weak-signal analysis). |
| **Sample rate** | Stable range approx 0.5–2.4 MSPS (up to 3.2 MSPS with drop risk) | Cannot capture the entire 20 MHz FM band simultaneously. Maximum instantaneous bandwidth is limited to ~2.4 MHz. | **Feasible** for single-station or adjacent-station analysis. Infeasible for instantaneous full-band monitoring (requires swept tuning). |
| **Tuning range** | ~24 MHz to ~1.766 GHz (R820T2) | The entire 88–108 MHz FM band falls comfortably within the primary tuning range. | **Fully feasible**. |
| **DC spike** | LO leakage causes a spurious spike at center frequency | A false high-power signal will appear at the tuned center frequency, corrupting PSD estimates directly at the LO. | **Conditionally feasible** (Requires DSP mitigation: either offset tuning or a digital DC blocking filter). |
| **IQ imbalance** | Amplitude and phase mismatch between I and Q channels | Generates image frequencies (ghost signals) symmetric to the center frequency, confounding spectrum occupancy analysis. | **Conditionally feasible** (Requires digital IQ correction/calibration in the DSP pipeline). |
| **Gain control** | Manual or AGC; no calibrated absolute power level | Impossible to measure absolute power (dBm or Watts) at the antenna without expensive external signal generators for calibration. | **Conditionally feasible** (Analysis must be restricted to relative power measurements, e.g., SNR or dBFS). |
| **Frequency accuracy** | TCXO variants improve accuracy; standard crystals may drift tens of ppm | Center frequencies will drift, especially as the dongle heats up, skewing spectrum plots by several kHz. | **Conditionally feasible** (Wideband FM signals are robust to slight offsets, but utilizing an RTL-SDR v3 with a 1 ppm TCXO is strongly recommended). |
| **Aliasing risk** | Signals near band edges of the IF filter may alias | Out-of-band signals will wrap into the digital passband if the sample rate is not carefully matched to the decimation filters. | **Conditionally feasible** (Mitigated by operating at 2.0-2.4 MSPS and applying digital anti-aliasing low-pass filters). |
| **USB throughput** | Bandwidth limited by USB 2.0; sample drops possible under load | Pushing data > 2.4 MSPS causes packet loss, destroying phase continuity and generating severe broadband spectral noise. | **Feasible** (Enforce a strict software upper bound of 2.4 MSPS in the lab parameters). |
| **Noise figure** | Typically 8–15 dB NF depending on gain settings and LNA presence | Decreased sensitivity for distant stations. However, local FM broadcast signals are typically high-power (+60 dBm ERP). | **Feasible** (External LNA is unnecessary and would likely degrade dynamic range by saturating the ADC). |

**Constraint Summary:**
The RTL-SDR is technically viable for FM broadcast monitoring, provided its limitations are aggressively managed through DSP architecture and curriculum design. The most severe limitation is the 2.4 MSPS maximum sample rate, which absolutely precludes instantaneous wideband capture of the entire 88–108 MHz band. To survey the entire band, the system must employ sequential tuning (sweeping). Furthermore, the lack of hardware calibration restricts the system to relative signal analysis (SNR, PSD shape) rather than absolute power radiometry (dBm).

---

## E. Regulatory and Ethical Constraints

* **Regulatory Framework:** Passive reception of public broadcast signals is generally permissible under international frameworks (ITU Radio Regulations) and national bodies (e.g., FCC Part 15 in the US). 
* **Transmission Exemption:** Because this system is explicitly scoped as receive-only, it removes the primary regulatory burden of experimental broadcast licensing, intentional radiator limits, and harmonic suppression requirements.
* **Ethical Obligations:** While capturing the RF envelope and baseband IQ data of public FM broadcasts is standard practice, institutions must not redistribute decoded, copyrighted audio content intercepted from these broadcasts. The system's data storage requirements (FR-06) must be utilized strictly to store spectral data for DSP analysis, not for media piracy.
* **Operational Boundary:** The system must never be modified to transmit, interfere with, jam, or decode protected/encrypted communications.

---

## F. Feasibility Summary

* **Technical Feasibility:** *Conditionally Feasible.* The RTL-SDR meets all functional requirements if specific DSP mitigations are applied. Offset tuning must be used to bypass the DC spike, and students must be taught that spectrum analysis is limited to 2.4 MHz contiguous windows.
* **Economic Feasibility:** *Highly Feasible.* The estimated BOM per station is ~$35–$45 USD (RTL-SDR v3 dongle with TCXO + basic telescopic dipole antenna). No external LNA, bias tee, or hardware filters are required due to the high transmit power of local FM stations. Software costs are $0.
* **Operational Feasibility:** *Feasible.* A student with introductory knowledge of sampling theory and frequency domains can operate the software within a single lab session, provided the hardware interface scripts abstract away the low-level USB drivers.
* **Schedule Feasibility:** * Phase 2: Architecture & DSP Flowgraph Design (~1 week)
    * Phase 3: Software Prototyping (GNU Radio/Python) (~2 weeks)
    * Phase 4: Hardware Integration & Lab Testing (~1 week)
    * Phase 5: Validation and Lab Manual Authoring (~2 weeks)

---

## G. Assumptions and Open Questions

**Assumptions**
1.  **RF Environment:** We assume the university laboratory space has sufficient RF transparency (e.g., standard windows) to receive local FM stations. *If wrong: We must provision outdoor antennas with coaxial feedlines to the lab, dramatically increasing costs and complexity.*
2.  **Student Hardware:** We assume students possess laptops with physical USB Type-A ports or appropriate adapters, and that they have administrator privileges to install SDR drivers (e.g., Zadig for Windows, udev rules for Linux). *If wrong: The institution must provide dedicated lab PCs, violating NFR-03.*
3.  **Signal Power:** We assume no overwhelming localized RF emitters (e.g., an on-campus multi-kilowatt broadcast transmitter on the roof) are close enough to fundamentally overload the SDR front-end. *If wrong: We must add an external, tunable band-reject filter to the BOM, exceeding the $50 cost ceiling.*

**Open Questions (For Phase 2 Resolution)**
* Which specific variant of the RTL-SDR will be standardized? (The v3 utilizes direct sampling for HF and has a TCXO; the newer v4 uses an upconverter architecture. The v3 is recommended for maximum legacy driver compatibility, but supply chain availability must be verified).
* Will the software rely primarily on GNU Radio Companion (visual flowgraphs) or pure Python scripts utilizing `rtlsdr` wrappers for the DSP processing? This impacts the required software baseline (NFR-05).