# System Architecture Context

> This document describes the architecture of an SDR-based RF signal processing system. It is intended as context for an AI assistant (`software_arch`) to reason about design decisions, integrations, and potential evolutions of this system.

---

## Overview

The system captures raw RF signals from a Software Defined Radio (SDR), processes them in real time through a C layer, applies DSP-RF analysis and AI-based spectrum evaluation in a Python layer, persists results to a database, and exposes a reactive frontend via Vite/React.

---

## Components

### 1. SDR — Software Defined Radio
- **Role**: External RF hardware input/output device.
- **Interface**: Bidirectional connection to the C layer's Buffers.
- **Responsibility**: Captures raw radio-frequency signal samples and passes them to the system for processing.

---

### 2. C Layer — Low-Level Real-Time Engine
- **Language**: C
- **Role**: High-performance, real-time signal capture and pre-processing.
- **Sub-components**:

  #### 2a. Buffers
  - Acts as the bridge between the SDR hardware and internal processing.
  - Receives raw samples from SDR (bidirectional: read/write).
  - Feeds data to the Event Engine.

  #### 2b. Event Engine (No Polling)
  - Event-driven architecture; explicitly avoids polling for efficiency.
  - Reacts to incoming data events from the Buffers.
  - Communicates bidirectionally with the Python layer via ZMQ over IPC.
  - Sends data/events to Python: labeled **"ZMQ in IPC"**.
  - Receives control commands back from Python: labeled **"programmed measure"**.

  #### 2c. PSD (AI Model)
  - Power Spectral Density analysis module embedded in the C layer.
  - Incorporates an AI model for spectrum analysis or anomaly detection.
  - Operates on buffered signal data.

- **Outbound to frontend**: Streams binary data directly to Vite/React via **Libwebsocket**.
- **Inbound from frontend**: Receives streaming control messages from Vite/React: **trigger** and **change params**.

---

### 3. Python Layer — DSP and Business Logic
- **Language**: Python
- **Role**: Higher-level signal processing, RF-specific logic, and data orchestration.
- **Sub-components**:

  #### 3a. DSP-RF
  - Digital Signal Processing module focused on RF signals.
  - Receives events and data from the C layer via **ZMQ IPC**.
  - Sends programmed measurement commands back to the C layer.
  - Communicates bidirectionally with the Vite/React frontend: **query** and **program** operations.

  #### 3b. Queries
  - Data access layer within the Python service.
  - Interfaces bidirectionally with the **Database** for read/write operations.
  - Handles persistence of measurements, results, and configuration.

---

### 4. Database
- **Role**: Persistent storage for signal data, query results, configurations, and historical records.
- **Interface**: Bidirectional connection with the Python **Queries** sub-component.

---

### 5. Vite/React — Frontend UI
- **Stack**: Vite + React (web-based SPA)
- **Role**: User-facing interface for monitoring, controlling, and querying the system.
- **Connections**:
  - Receives **Libwebsocket binary** stream from the C layer (real-time signal data).
  - Sends **Streaming (trigger, change params)** messages back to the C layer for control.
  - Exchanges **query / program** messages bidirectionally with the Python DSP-RF module.

---

## Communication Channels

| From | To | Protocol / Label | Direction |
|------|-----|-----------------|-----------|
| SDR | C / Buffers | Raw RF samples | Bidirectional |
| C / Buffers | C / Event Engine | Internal data flow | Internal |
| C / Event Engine | Python / DSP-RF | ZMQ over IPC | Bidirectional |
| Python / DSP-RF | C / Event Engine | Programmed measure | Python → C |
| C Layer | Vite/React | Libwebsocket binary | C → Frontend |
| Vite/React | C Layer | Streaming (trigger, change params) | Frontend → C |
| Python / DSP-RF | Vite/React | Query, program | Bidirectional |
| Python / Queries | Database | SQL / queries | Bidirectional |

---

## Architecture Diagram (Text Representation)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│   ┌───────┐        ┌────────────────────────────────┐                           │
│   │  SDR  │◄──────►│             C Layer             │                           │
│   └───────┘        │  ┌─────────┐ ┌──────────────┐  │  Libwebsocket binary      │
│                    │  │ Buffers │ │ Event Engine  │  │──────────────────────────►│
│                    │  │         │ │  (No polling) │  │                           │
│                    │  └─────────┘ └──────┬────────┘  │◄──────────────────────── │
│                    │  ┌───────────────┐  │            │  Streaming(trigger,      │
│                    │  │  PSD (AI mdl) │  │            │  change params)          │
│                    │  └───────────────┘  │            │                          │
│                    └─────────────────────┼────────────┘         ┌─────────────┐ │
│                                          │ ZMQ / IPC            │  Vite/React │ │
│                                          ▼                       └──────┬──────┘ │
│                               ┌──────────────────────┐                  │        │
│                               │      Python Layer     │◄─────────────────┘        │
│                               │  ┌────────┐           │  query, program           │
│                               │  │ DSP-RF │           │                           │
│                               │  └────────┘           │                           │
│                               │  ┌─────────┐          │                           │
│                               │  │ Queries │          │                           │
│                               │  └────┬────┘          │                           │
│                               └───────┼───────────────┘                           │
│                                       │                                           │
│                                  ┌────▼─────┐                                    │
│                                  │ Database  │                                    │
│                                  └──────────┘                                    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

- **Event-driven C engine**: Avoids polling to minimize CPU usage and latency in real-time signal processing.
- **ZMQ over IPC**: Uses ZeroMQ with inter-process communication for fast, low-overhead messaging between C and Python processes on the same host.
- **Libwebsocket for binary streaming**: Pushes raw or processed binary signal data directly from the C layer to the browser, bypassing Python for latency-sensitive streams.
- **Python for DSP-RF logic**: Leverages Python's ecosystem (NumPy, SciPy, etc.) for higher-level RF digital signal processing while keeping performance-critical code in C.
- **AI model in C (PSD)**: The Power Spectral Density AI model is embedded directly in the C layer for low-latency inference close to the data source.
- **Decoupled frontend**: Vite/React is fully decoupled and communicates via WebSocket (binary) and HTTP/query APIs, making the UI replaceable independently of the backend.
