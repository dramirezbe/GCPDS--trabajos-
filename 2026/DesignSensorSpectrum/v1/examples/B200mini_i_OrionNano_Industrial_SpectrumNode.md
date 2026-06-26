# Industrial Spectrum-Sensing Node: B200mini-i + Jetson Orin Nano 8GB
## Architecture Summary & Context Document

> **Purpose:** Single-channel, FM-to-C-band (70 MHz – 6 GHz) industrial spectrum-monitoring node.  
> **Design philosophy:** Minimum-cost industrial-ready RF chain, single-board SDR, edge-AI capable backend.  
> **Target budget:** ~$3,200 – $4,500 (prototype) / ~$5,000 – $6,500 (field-deployable with enclosure & calibration).

---

## 1. Executive Summary

This document replaces the legacy dual-channel USRP N210 + Jetson Nano 4GB architecture with a **single-channel industrial build** using:

| Subsystem | Selected Hardware | Key Spec | Rationale |
|-----------|-------------------|----------|-----------|
| **SDR** | USRP B200mini-i (industrial enclosure) | 70 MHz – 6 GHz, 1×1 RX, 56 MHz BW, USB 3.0, **−40 °C to +75 °C** | Cheapest Ettus industrial-rated unit. AD9361 RFIC eliminates daughterboard cost. |
| **Processing** | NVIDIA Jetson Orin Nano 8GB | 1020 TOPS INT8, 8 GB LPDDR5, 15–25 W | Replaces discontinued Jetson Nano 4GB. Massive AI headroom for future signal classification. |
| **Host Interface** | USB 3.0 (co-located) | 5 Gbps, <3 m cable | B200mini-i is USB-only. Orin Nano must reside in same enclosure. |
| **Network Backhaul** | Gigabit Ethernet (Orin Nano) | 100 m reach | Orin Nano streams processed PSD/metadata to central server. |

**Key trade-off:** Single RX channel vs. original dual-channel N210. Diversity/MIMO is sacrificed for cost and industrial temperature grade. Full FM-to-6 GHz coverage is preserved via a **switched RF front-end**.

---

## 2. System Block Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INDUSTURAL ENCLOSURE (IP65)                         │
│  ┌──────────────────────┐         ┌─────────────────────────────────────┐   │
│  │   ANTENNA SWITCH     │         │         DIGITAL BACKEND             │   │
│  │      (SPDT)          │         │                                     │   │
│  │  ┌─────┐  ┌─────┐   │         │   ┌─────────────────────────────┐   │   │
│  │  │ ANT1│  │ ANT2│   │         │   │   Jetson Orin Nano 8GB      │   │   │
│  │  │Bico │  │Hyper│   │         │   │   • ARM A78AE               │   │   │
│  │  │LOG  │  │LOG  │   │         │   │   • 8 GB LPDDR5             │   │   │
│  │  │70-700│  │0.7-6│   │         │   │   • USB 3.0 ↔ B200mini-i    │   │   │
│  │  │ MHz │  │ GHz │   │         │   │   • GigE → WAN/Server       │   │   │
│  │  └──┬──┘  └──┬──┘   │         │   │   • GPIO → RF switches      │   │   │
│  │     └────┬───┘      │         │   │   • 15-25 W (MAXN)          │   │   │
│  │          │          │         │   └─────────────────────────────┘   │   │
│  └──────────┼──────────┘         └─────────────────────────────────────┘   │
│             │                                                               │
│  ┌──────────┴──────────┐                                                   │
│  │   LIMITER / ESD     │  ← Transient protection (first element outdoors)   │
│  │   (Gas discharge    │                                                   │
│  │    + TVS + DC block)│                                                   │
│  └──────────┬──────────┘                                                   │
│             │                                                               │
│  ┌──────────┴──────────┐                                                   │
│  │  PRESELECTOR BANK   │  ← Modular bandpass filters (Table 3 below)       │
│  │   (SP6T switched)   │     Switched path selection per target band       │
│  └──────────┬──────────┘                                                   │
│             │                                                               │
│  ┌──────────┴──────────┐                                                   │
│  │    LNA / BYPASS     │  ← ZX60-33LN-S+ (50 MHz–3 GHz) or bypass         │
│  │   (band-selected)   │    AGLNA035082 (4–8 GHz) for C-band path          │
│  └──────────┬──────────┘                                                   │
│             │                                                               │
│  ┌──────────┴──────────┐                                                   │
│  │  PROG. ATTENUATOR   │  ← ZX76-31R75PP-S+ (0–31.5 dB, 0.5 dB steps)     │
│  │   (single unit)     │     Industrial: remote gain control mandatory     │
│  └──────────┬──────────┘                                                   │
│             │                                                               │
│  ┌──────────┴──────────┐                                                   │
│  │   USRP B200mini-i   │  ← 70 MHz – 6 GHz, 1 RX, 56 MHz BW, USB 3.0      │
│  │  (Industrial case)  │     −40 °C to +75 °C rated                        │
│  └─────────────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────────────┘

External: 24 V DC Industrial PSU → Isolated DC-DC → 5 V (Orin), 6 V (B200mini-i)
```

---

## 3. Hardware Selection Deep-Dive

### 3.1 SDR — USRP B200mini-i (Industrial)
| Parameter | Value |
|-----------|-------|
| RF Coverage | 70 MHz – 6 GHz (AD9361) |
| Channels | 1 TX / 1 RX (half-duplex capable) |
| Inst. Bandwidth | 56 MHz |
| ADC | 12-bit |
| Host Interface | USB 3.0 (Micro-B) |
| FPGA | Xilinx Spartan-6 XC6SLX75 |
| Industrial Temp | **−40 °C to +75 °C** (with Ettus industrial enclosure kit) |
| Clocking | Onboard TCXO; external 10 MHz / 1 PPS via SMA |
| Software | UHD (GPLv3), GNU Radio, SoapySDR, Python/C++ |
| Est. Price | **$1,100 – $1,400** (new, industrial enclosure) |

**Why not N210?**  
The N210 is discontinued/used-only, requires daughterboards (UBX $800–1,200), and lacks industrial temperature certification. The B200mini-i integrates the AD9361 transceiver directly, eliminating daughterboard cost and synchronization complexity while adding industrial-grade ruggedization.

**Why not B205mini-i?**  
The B205mini-i is functionally identical but priced higher (~$1,361) for the same RF performance. The B200mini-i is the cost-optimized variant; both share the AD9361 and industrial enclosure compatibility.

### 3.2 Processing Backend — Jetson Orin Nano 8GB
| Parameter | Value |
|-----------|-------|
| CPU | 6× ARM Cortex-A78AE v8.2 64-bit |
| GPU / AI | 1020 TOPS INT8 (Ampere architecture, 1024 CUDA cores) |
| Memory | 8 GB 128-bit LPDDR5 @ 68 GB/s |
| Storage | microSD / NVMe M.2 Key-M via carrier |
| Network | Gigabit Ethernet, M.2 Key-E Wi-Fi/BT optional |
| USB | 4× USB 3.0 (critical for B200mini-i) |
| GPIO | 40-pin header (3.3 V logic, compatible with RF switches) |
| Power | 7 W (10 W mode) / 15 W (MAXN) / 25 W (super mode) |
| Est. Price | **$499 – $599** (dev kit) |

**Upgrade rationale over Jetson Nano 4GB:**
- Nano 4GB is **end-of-life**; supply chain is unreliable.
- Orin Nano provides **20× AI performance** (1020 TOPS vs. 472 GFLOPS), enabling future real-time signal classification, anomaly detection, and automatic modulation recognition (AMR) at the edge.
- Native USB 3.0 bandwidth is sufficient for B200mini-i streaming (no Ethernet bottleneck).

---

## 4. RF Front-End Design: Cheapest Industrial-Ready Chain

Because the B200mini-i offers only **one RX channel**, the dual-branch architecture of the original N210 design collapses into a **single switched RF path**. This actually *reduces* RF hardware cost by ~40 % for filters, attenuators, and amplifiers.

### 4.1 Antenna Strategy
| Band | Antenna | Coverage | Est. Price |
|------|---------|----------|------------|
| VHF/UHF | Aaronia BicoLOG 5070 (or equivalent biconical) | 70 – 700 MHz | ~$300 |
| UHF–C-band | Aaronia HyperLOG 7060 (log-periodic) | 700 MHz – 6 GHz | ~$320 |
| **Switching** | Mini-Circuits MSW-2-50DR+ (SPDT) | DC – 5 GHz, <2 dB IL | ~$30 |

**Cost-saving note:** A single wideband discone (100 MHz – 3 GHz) plus the HyperLOG could work, but the BicoLOG/HyperLOG pair provides known calibration curves and better gain flatness. For absolute minimum cost, a single discone (~$80) + HyperLOG switchable is viable, but sacrifices 70–100 MHz performance.

### 4.2 Preselector Filter Bank (Single-Channel, SP6T Switched)
The original document’s filter plan (Table 3) is preserved but implemented as **one shared bank** rather than two branches.

| Sensing Region | Filter / Path | Nominal Band | Typ. IL | Est. Price |
|----------------|---------------|--------------|---------|------------|
| FM broadcast | Switchable FM notch OR FM pass | 88 – 108 MHz | <1.5 dB pass | ~$40 (notch) |
| Low-VHF | Custom / broad VHF path | 70 – 88 MHz | ~2 dB | ~$50 |
| VHF/UHF | Mini-Circuits SHP-50+ + SLP-750+ | 108 – 700 MHz | ~2 dB | ~$60 |
| Upper-UHF | Modular BPF / cavity filter | 700 – 960 MHz | <2 dB | ~$80 |
| L-band / Cellular | Custom BPF / VBFZ-2130-S+ path | 1.7 – 2.7 GHz | <2 dB | ~$70 |
| S-band gap | **Mini-Circuits SBP-3800+** (concrete part) | 3.0 – 4.2 GHz | <3 dB | **$45–65** |
| C-band | Marki Microwave C-band BPF (or equiv.) | 4.0 – 6.0 GHz | <3 dB | ~$120 |
| **Switching** | Mini-Circuits MSW-2-50DR+ (SP6T equivalent cascade) | DC – 5 GHz | <2 dB | ~$60 |

**Total filter bank + switching:** ~$525 – $625 (vs. ~$1,000+ for dual-branch).

### 4.3 LNA Strategy (Band-Selected, Single Path)
| Frequency | Amplifier | Gain | NF | Price |
|-----------|-----------|------|----|-------|
| 50 MHz – 3 GHz | Mini-Circuits ZX60-33LN-S+ | 20 dB | 3 dB | ~$159 |
| 3.0 – 4.2 GHz | *Optional gap LNA* | 15–25 dB | TBD | ~$50–150 |
| 4.0 – 8.0 GHz | Amplitech AGLNA035082 | 26 dB | 0.9 dB | ~$35 |
| **Bypass** | Relay or solid-state bypass path | 0 dB | — | ~$15 |

**Implementation:** A small RF relay board or SPDT switch selects between the ZX60-33LN-S+ path (for <3 GHz) and the AGLNA035082 path (for >4 GHz). The 3–4 GHz region can be served by the ZX60-33LN-S+ with reduced gain, or a dedicated gap LNA if budget allows.

### 4.4 Attenuation
| Component | Spec | Price |
|-----------|------|-------|
| Mini-Circuits ZX76-31R75PP-S+ | 0–31.5 dB, 0.5 dB steps, DC–6 GHz | **$300–350** (×1, single channel) |

**Why programmable?** Industrial nodes operate unattended. Remote gain control is mandatory to avoid front-end compression near broadcast transmitters or cellular towers. Fixed pads are unacceptable for field deployment.

---

## 5. Bill of Materials (Industrial-Ready Single-Channel Node)

| Line Item | Component | Est. Price (USD) | Notes |
|-----------|-----------|------------------|-------|
| 1 | USRP B200mini-i (industrial enclosure) | $1,100 – $1,400 | New, −40 °C to +75 °C, AD9361, USB 3.0 |
| 2 | Jetson Orin Nano 8GB Dev Kit | $499 – $599 | 1020 TOPS, 8 GB LPDDR5, USB 3.0 host |
| 3 | BicoLOG 5070 antenna | $280 – $350 | 70–700 MHz, biconical |
| 4 | HyperLOG 7060 antenna | $300 – $380 | 700 MHz–6 GHz, log-periodic |
| 5 | Antenna SPDT switch (MSW-2-50DR+) | $25 – $40 | DC–5 GHz, 3.3 V CMOS control |
| 6 | Limiter / ESD / lightning arrestor | $40 – $80 | Gas discharge + TVS + DC block |
| 7 | Preselector filter bank (SP6T) | $500 – $650 | Includes SBP-3800+, FM notch, C-band BPF |
| 8 | LNA paths (ZX60-33LN-S+, AGLNA035082, bypass) | $220 – $350 | Single-channel set |
| 9 | Programmable attenuator (ZX76-31R75PP-S+) | $300 – $350 | 0–31.5 dB, single unit |
| 10 | GPSDO timing (Leo Bodnar or u-blox module) | $50 – $150 | 10 MHz + 1 PPS to B200mini-i REF IN |
| 11 | RF cables, adapters, terminators (industrial grade) | $100 – $200 | Phase-stable SMA, low-loss |
| 12 | IP65 enclosure, DIN rail, thermal management | $150 – $300 | Die-cast Al, passive + fan |
| 13 | 24 V DC industrial PSU + isolated DC-DC | $60 – $120 | 5 V/6 A, 6 V/3 A rails |
| 14 | Calibration & test allowance | $100 – $250 | Reference loads, verification |
| | **SUBTOTAL (hardware)** | **$3,724 – $5,219** | |
| | Contingency (15 %) | $560 – $780 | |
| | **DEFENSIBLE PROJECT BUDGET** | **$4,300 – $6,000** | |

**Comparison to original N210 design:**
- Original N210 + Jetson Nano 4GB (dual-channel, manual): **$4,500 – $7,000**
- This B200mini-i + Orin Nano 8GB (single-channel, automated): **$4,300 – $6,000**

**Savings driver:** Eliminating the second RF branch (filters, LNA, attenuator) and daughterboard costs offsets the higher price of the Orin Nano and industrial enclosure.

---

## 6. Power Budget

| Subsystem | Supply Rail | Typical Power | Max Power | Notes |
|-----------|-------------|---------------|-----------|-------|
| BicoLOG / HyperLOG antennas | — | 0 W | 0 W | Passive |
| Passive filters & switches | 5 V control | 0.2 – 0.6 W | 1.0 W | Solid-state SP6T/SPDT |
| ZX60-33LN-S+ LNA | 5 V RF rail | 0.3 – 0.5 W | 0.7 W | Switchable/bypassable |
| AGLNA035082 LNA | 5 V RF rail | 0.3 – 0.7 W | 1.0 W | C-band path only |
| Programmable attenuator | 5 V control | <0.1 W | 0.2 W | Low DC power |
| GPSDO / timing module | 5 V rail | 0.5 – 1.0 W | 1.5 W | u-blox or Leo Bodnar |
| USRP B200mini-i | 6 V DC / USB | 2.0 – 4.0 W | 6.0 W | USB 3.0 powered + optional DC jack |
| Jetson Orin Nano 8GB | 5 V system rail | 10 – 20 W | 25 W | 15 W mode typical; 25 W MAXN |
| Storage, USB, GPIO, cooling | 5 V aux | 1.0 – 3.0 W | 5.0 W | NVMe M.2, fan, level shifters |
| **System Total** | | **14.6 – 30.3 W** | **40.4 W** | |
| **Recommended supply capacity** | | **20 – 35 W** | **50 W** | 25 % margin for startup, temp, aging |

**Recommended PSU:** 24 V DC, 3 A (72 W) industrial DIN-rail supply with isolated DC-DC modules:
- Rail 1: 5 V / 6 A (Orin Nano + digital + cooling)
- Rail 2: 6 V / 3 A (B200mini-i + RF front-end)
- Rail 3: 3.3 V / 1 A (GPIO logic, switch control)

---

## 7. Software Stack

| Layer | Technology | License | Purpose |
|-------|------------|---------|---------|
| SDR Driver | UHD (USRP Hardware Driver) | GPLv3 | Device control, streaming, timed commands |
| Abstraction | SoapySDR | BSL-1.0 | Vendor-neutral API, multi-platform |
| Framework | GNU Radio 3.10+ | GPLv3 | Signal processing graphs, FFT sink, file recording |
| AI / ML | NVIDIA JetPack + TensorRT | Proprietary (SDK) | Edge inference, anomaly detection, AMR |
| OS | Ubuntu 22.04 (Jetson) | GPLv2 | Host OS, real-time patches optional |
| Orchestration | Docker + MQTT / ZeroMQ | Apache/BSD | Containerized deployment, telemetry backhaul |

**Key advantage over original design:** The Orin Nano’s 1020 TOPS enables real-time AI classification (e.g., modulation recognition, interference fingerprinting) that was impossible on the Jetson Nano 4GB’s 472 GFLOPS Maxwell GPU.

---

## 8. Deployment Considerations

### 8.1 USB 3.0 Co-Location Requirement
The B200mini-i is **USB 3.0 only** (no Ethernet). Maximum reliable cable length is ~3 m. Therefore:
- The **Orin Nano must be mounted inside the same enclosure** as the B200mini-i.
- The Orin Nano acts as the edge gateway: it streams compressed spectra / metadata over **Gigabit Ethernet** to the WAN.
- This eliminates the N210’s “100 m Ethernet cable” advantage but is acceptable for pole/cabinet-mounted installations.

### 8.2 Single-Channel Limitations
- **No simultaneous dual-band monitoring.** The node must time-share between VHF/UHF and UHF–C-band via antenna/filter switching.
- **No spatial diversity / MIMO.** Phase-coherent measurements (e.g., AoA) are impossible with one channel.
- **Scanning speed trade-off.** If the mission requires rapid full-band sweeps, the SP6T filter bank must switch sequentially. Budget ~10–50 ms per switch settle time.

### 8.3 Environmental & Regulatory
- **Enclosure:** IP65 minimum for outdoor; IP66 preferred for coastal/industrial dust.
- **Lightning:** Gas discharge arrestor on each antenna port; earth bonding to enclosure chassis.
- **EMC:** The B200mini-i industrial enclosure provides shielding; ensure all penetrations use feedthrough capacitors or shielded glands.
- **Calibration:** For regulatory-grade claims, the entire chain (antenna → ADC) requires annual calibration with traceable reference sources. Budget $500/year or internal reference generator (e.g., NanoVNA + comb generator for sanity checks).

---

## 9. Risk Register

| Risk | Mitigation |
|------|------------|
| **B200mini-i USB dropout under thermal load** | Use industrial enclosure with thermal pad; keep internal ambient <60 °C; avoid long USB cables. |
| **AD9361 image rejection / LO leakage** | Enable UHD DC offset / IQ imbalance calibration; use external preselection to suppress image bands. |
| **Jetson Orin Nano supply chain** | Purchase from authorized NVIDIA distributor; consider Orin Nano module + custom carrier for long-term availability. |
| **Single point of failure (1 RX channel)** | If mission-critical, budget for a **second identical node** rather than a dual-channel SDR; spatial separation improves geolocation. |
| **3–4 GHz gain flatness gap** | The ZX60-33LN-S+ rolls off above 3 GHz. Use the SBP-3800+ filter + optional gap LNA if this band is critical. |

---

## 10. Quick-Reference Comparison: Original vs. This Design

| Feature | Original (N210 + Jetson Nano 4GB) | This Design (B200mini-i + Orin Nano 8GB) |
|---------|-----------------------------------|------------------------------------------|
| **RF Coverage** | 10 MHz – 6 GHz (with UBX) | 70 MHz – 6 GHz (AD9361 native) |
| **Channels** | 2× RX (dual-branch) | 1× RX (switched single-branch) |
| **Industrial Temp** | ❌ No (used consumer-grade) | ✅ Yes (−40 °C to +75 °C) |
| **Host Interface** | Gigabit Ethernet (100 m) | USB 3.0 (co-located, <3 m) |
| **Edge AI Performance** | 472 GFLOPS (insufficient) | 1020 TOPS (real-time capable) |
| **Daughterboard Cost** | $800 – $1,200 (UBX) | $0 (integrated AD9361) |
| **RF Automation** | Manual (prototype) / SP4T (Phase 2) | Automated SP6T + prog. attenuator (standard) |
| **Est. Budget** | $4,500 – $7,000 | $4,300 – $6,000 |
| **Availability** | Legacy / used market risk | Current production, supply chain active |

---

*Document generated for AI context ingestion. All prices are 2026 estimates and subject to market fluctuation. Verify FPGA image compatibility (B200mini-i Spartan-6) with target UHD version before procurement.*
