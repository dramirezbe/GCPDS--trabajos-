# Hardware Bill of Materials — Portable RF Monitoring System

> **Purpose of this document:** This file serves as structured context for an AI assistant working on this RF system. It describes every hardware component: its role in the system, key technical specifications, procurement source, and cost. Refer to this document when answering questions about hardware capabilities, integration constraints, or budgeting.

---

## System Overview

This is a portable, self-contained Software Defined Radio (SDR) monitoring platform. It is designed to capture, process, and display RF signals across the 698 MHz – 6 GHz spectrum. The system pairs an Ettus USRP B210 SDR front-end with an NVIDIA Jetson Orin Nano Super for real-time AI-assisted signal processing and analysis. Bandpass filters provide RF preselectivity, a wideband omnidirectional antenna handles signal collection, and a 7-inch touchscreen provides the user interface — all housed inside a custom enclosure.

---

## Cost Summary

| Item | Unit Price (USD) | Landed / Import Price (USD) |
|------|------------------|-----------------------------|
| USRP B210 | $2,200 | $2,860 |
| Antenna 698–2700 MHz | $200 | $260 |
| Preselection Filters (×2) | $200 | $260 |
| Jetson Orin Nano Super | $300 | $390 |
| 7-inch Touchscreen Display | $60 | $78 |
| Enclosure (Carcaza) | $100 | $130 |
| **TOTAL** | **$3,060** | **$3,978** |

---

## Component Specifications

---

### 1. Software Defined Radio — Ettus Research USRP B210

**Role in system:** Primary RF front-end. Handles wideband spectrum capture and transmission over USB 3.0 to the Jetson for processing.

**Part number / model:** USRP B210 (Kit, UB210-KIT)  
**Supplier:** Ettus Research (a National Instruments brand)  
**Purchase URL:** https://www.ettus.com/all-products/ub210-kit/

**Key specifications:**

| Parameter | Value |
|-----------|-------|
| Frequency range | 70 MHz – 6 GHz (continuous) |
| RF bandwidth | Up to 56 MHz instantaneous |
| Architecture | 2×2 MIMO (2 TX, 2 RX) |
| ADC/DAC resolution | 12-bit |
| Host interface | USB 3.0 |
| FPGA | Xilinx Spartan-6 XC6SLX150 |
| Form factor | Single-board (no enclosure) |
| Software support | GNU Radio, UHD driver, MATLAB, LabVIEW |
| Typical TX power | Up to 10 dBm |
| Noise figure | ~8 dB (dependent on frequency) |
| Impedance | 50 Ω |

**Integration notes:**
- Connects to the Jetson Orin via USB 3.0.
- Requires UHD (USRP Hardware Driver) installed on the Jetson host.
- Two SMA RF ports (RX/TX) per channel; total 4 SMA connectors.
- The preselection bandpass filters are placed inline between the antenna and the B210 RX inputs.
- Power is drawn entirely from USB; no external supply required.

---

### 2. Computing Module — NVIDIA Jetson Orin Nano Super Developer Kit

**Role in system:** Central processing unit for AI inference, signal processing, system control, and display output.

**Part number / model:** Jetson Orin Nano Super Developer Kit (945-13766-0005-000)  
**Supplier:** Amazon / NVIDIA authorized resellers  
**Purchase URL:** https://www.amazon.com/-/es/NVIDIA-Jetson-Orin-Super-Desarrollo/dp/B0BZJTQ5YP/

**Key specifications:**

| Parameter | Value |
|-----------|-------|
| AI performance | Up to 67 TOPS |
| GPU | NVIDIA Ampere architecture, 1024 CUDA cores |
| CPU | 6-core ARM Cortex-A78AE |
| RAM | 8 GB LPDDR5, 102 GB/s bandwidth |
| Storage interface | 2× M.2 Key M (NVMe SSD) |
| Display output | DisplayPort 1.2 (HDMI via adapter) |
| USB | 4× USB 3.2 Gen 2 Type-A, 1× USB-C |
| Connectivity | Wi-Fi (pre-installed M.2 Key E module), Gigabit Ethernet |
| GPIO | 40-pin expansion header |
| Power | 5V DC, ~7–15 W depending on power mode |
| OS | JetPack (Ubuntu-based Linux) |
| Framework support | ROS 2, PyTorch, TensorRT, GNU Radio, Ollama, llama.cpp |

**Integration notes:**
- The USRP B210 connects to one of the USB 3.2 Gen 2 Type-A ports.
- The 7-inch display connects via HDMI (using a DisplayPort-to-HDMI cable or adapter).
- The display's USB touch interface connects to a second USB Type-A port.
- GNU Radio and the UHD driver must be installed under JetPack for SDR operation.
- TensorRT or PyTorch can be used for real-time AI signal classification pipelines.

---

### 3. RF Preselection Filters (×2)

**Role in system:** Bandpass preselectivity filtering placed between the antenna and the USRP B210 RX inputs. Suppress out-of-band interference before the ADC, improving sensitivity and reducing intermodulation.

**Supplier:** Mini-Circuits

---

#### Filter 1 — Mini-Circuits VBFZ-925-S+

**Description:** Connectorized bandpass filter targeting the cellular 800/900 MHz band.  
**Purchase URL:** https://www.minicircuits.com/WebStore/dashboard.html?model=VBFZ-925-S%2B

| Parameter | Value |
|-----------|-------|
| Type | Connectorized bandpass filter |
| Passband | 800 – 1050 MHz |
| Connector | SMA |
| Impedance | 50 Ω |
| Form factor | Connectorized metal housing |

**Coverage:** GSM 850, GSM 900, LTE Band 5, LTE Band 8, LTE Band 20.

---

#### Filter 2 — Mini-Circuits BPF-A1340+

**Description:** Lumped LC bandpass filter covering the 1000–1800 MHz range (GPS L1, LTE mid-bands, 1.3 GHz radar).  
**Purchase URL:** https://www.minicircuits.com/WebStore/dashboard.html?model=BPF-A1340%2B

| Parameter | Value |
|-----------|-------|
| Type | Lumped LC bandpass filter |
| Passband | 1000 – 1800 MHz |
| Impedance | 50 Ω |
| Form factor | Connectorized |

**Coverage:** GPS L1 (1575 MHz), DCS 1800, LTE Band 1/3/4/10, 1.3 GHz radar.

---

**Filter topology note:** The two filters together provide preselectivity across 800 MHz – 1800 MHz. They are used on the two independent RX channels of the USRP B210 (one filter per RX channel), allowing simultaneous dual-band monitoring.

---

### 4. Antenna — L-com LCANOM1075

**Role in system:** Primary signal collection element. Receives RF across the broad 698–2700 MHz cellular/WiFi spectrum.

**Part number / model:** LCANOM1075  
**Supplier:** L-com  
**Purchase URL:** https://www.l-com.com/698-to-2700-mhz-omni-antenna-6.5-dbi-gain-5.5-mm-spring-sma-male-connector-black-fiberglass-radome-lcanom1075

**Key specifications:**

| Parameter | Value |
|-----------|-------|
| Frequency range | 698 – 2700 MHz |
| Gain | 6.5 dBi |
| Radiation pattern | Omnidirectional |
| Polarization | Vertical |
| Connector | SMA Male (spring-loaded, 5.5 mm) |
| Radome | Black fiberglass |
| Impedance | 50 Ω |
| VSWR | ≤ 2.0 (typical) |

**Integration notes:**
- The SMA Male connector mates directly to the RF preselection filter inputs or to the USRP B210 RX SMA ports.
- The antenna covers cellular bands (LTE 700–2600 MHz), WiFi 2.4 GHz, and GPS L1 — ideal for broad-spectrum passive monitoring.
- Mount externally on the enclosure for unobstructed reception.

---

### 5. Display — Waveshare 7inch HDMI LCD (C)

**Role in system:** Operator-facing touchscreen UI. Displays GNU Radio visualizations (spectrum waterfall, FFT), application dashboards, and system status.

**Part number / model:** Waveshare 7inch HDMI LCD (C) — Rev 4.1  
**Supplier:** Amazon (Hosyond/Waveshare)  
**Purchase URL:** https://www.amazon.com/-/es/Hosyond-pantalla-pulgadas-capacitiva-Raspberry/dp/B09XKC53NH/

**Key specifications:**

| Parameter | Value |
|-----------|-------|
| Screen size | 7 inches |
| Panel type | IPS |
| Resolution | 1024 × 600 |
| Touch | 5-point capacitive touch |
| Display interface | HDMI |
| Touch interface | USB Micro-B (HID, driver-free) |
| Power input | USB Micro-B (5V) |
| Backlight | Adjustable (PWM solder pads) |
| OS support | Ubuntu, Raspbian, Windows 10/8/7, Kali, Retropie |
| Included accessories | HDMI cable, USB-A to Micro-USB cable, HDMI-to-Micro-HDMI adapter |

**Integration notes:**
- Connect HDMI to the Jetson's DisplayPort output via a DisplayPort-to-HDMI cable.
- Connect USB Micro-B (touch) to a Jetson USB Type-A port — touch recognized natively under JetPack/Ubuntu, no drivers needed.
- The display requires a separate 5V USB power feed (can be sourced from the Jetson USB port or the enclosure's power rail).
- Compatible with JetPack (Ubuntu 20.04/22.04) — set display resolution to 1024×600 in system settings.

---

### 6. Enclosure — Custom Carcaza

**Role in system:** Mechanical housing for all components. Provides physical protection, cable management, and mounting points for the antenna and display.

**Status:** Custom / to be specified  
**Estimated cost:** $100 (unit) / $130 (landed)

**Design requirements (for AI context):**
- Must accommodate the USRP B210 PCB, Jetson Orin Nano Developer Kit, and 7-inch display panel.
- Requires external antenna mount port (SMA bulkhead passthrough).
- USB 3.0 port access for USRP B210 connection.
- Power input and cooling vents (Jetson draws up to 15 W).
- Display window cut-out for 7-inch panel (≈ 165 × 100 mm visible area).
- Portable form factor: ideally similar to a rugged handheld instrument or pelican-case-style box.

---

## Signal Chain Summary

```
[ANTENNA: LCANOM1075]
        │  SMA
        ▼
[PRESELECTION FILTER 1: VBFZ-925-S+ — 800–1050 MHz]  ──→ USRP B210 RX-A
[PRESELECTION FILTER 2: BPF-A1340+  — 1000–1800 MHz] ──→ USRP B210 RX-B
        │
        │  USB 3.0
        ▼
[JETSON ORIN NANO SUPER — Signal processing, AI inference, GNU Radio]
        │
        │  HDMI + USB (touch)
        ▼
[WAVESHARE 7" DISPLAY — Visualization & UI]
```

All components are housed inside the **Custom Enclosure (Carcaza)**.

---

## Software Stack Context

| Layer | Tool / Framework |
|-------|-----------------|
| SDR driver | Ettus UHD (USRP Hardware Driver) |
| SDR framework | GNU Radio |
| AI inference | NVIDIA TensorRT, PyTorch (JetPack) |
| Signal processing | GNU Radio blocks, SciPy, NumPy |
| OS | NVIDIA JetPack (Ubuntu 20.04 / 22.04 base) |
| Display server | X11 or Wayland |

---

*Last updated: June 2026*
