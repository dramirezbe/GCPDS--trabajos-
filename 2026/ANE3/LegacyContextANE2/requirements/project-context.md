# Project Context

## Project Title

Monitoreo SDR a exposicion de IoT con alta densidad de dispositivos.

## Problem And Justification

The project addresses monitoring of electric-field exposure in indoor labor environments with high concentration of IoT devices. The source proposal frames this as a health, safety, regulatory, and operational problem:

- IoT proliferation in offices and factories increases concern about exposure to electric fields.
- Traditional spectrum analyzers are expensive, bulky, and hard to use for dense or mobile studies.
- SDR is proposed as a practical lower-cost alternative, but it brings limits around dynamic range, ADC/DAC behavior, and usable frequency range.
- The system must support monitoring across relevant IoT/telecom bands, especially the proposed range from 700 MHz to 3.5 GHz.
- Indoor spaces require many fast measurements to identify high-radiation areas and compare them against exposure norms.
- Static thresholds are not enough in noisy, dynamic IoT environments; the proposal calls for adaptive thresholding, machine learning, and cooperative sensing.
- Heat maps of electric field exposure are needed to correlate device density, frequency usage, and exposure levels.

Referenced regulatory/scientific context includes UIT-T K.52, ICNIRP exposure criteria, spectrum regulation in Colombia by ANE, and literature on SDR, spectrum sensing, Kriging interpolation, and RF exposure mapping.

## Research Question

How does IoT-device density influence electric-field exposure levels in closed environments, and what impact can that exposure have on worker health, using an SDR-based monitoring system and advanced machine-learning techniques for detection and analysis?

## General Objective

Develop a system for evaluating human exposure levels to electric fields, based on SDR and machine-learning techniques, allowing measurement of radiation density in indoor environments with high IoT-device occupancy.

## Specific Objectives

1. Design and build an SDR measurement module for spectral monitoring of high-density IoT networks in indoor spaces using spectrum-sensing techniques.
2. Develop thresholding algorithms and cooperative processes based on machine-learning methods to handle measurement variability in high-interference indoor environments.
3. Generate spatial maps of electric fields using advanced measurement and data-analysis techniques to evaluate compliance with human-exposure regulations and produce detailed reports/presentations for regulators and interested organizations.

## Methodology Summary

The proposal organizes the work around the three specific objectives.

### Objective 1: SDR Module

Activities:

- analyze technical and functional SDR requirements;
- evaluate SDR hardware and software;
- design the SDR module architecture;
- design circuits/diagrams and select components;
- build and configure the SDR module;
- install/configure SDR software;
- validate module operation.

Expected outputs:

- requirements document;
- SDR module design diagrams;
- functional SDR module.

### Objective 2: AI Thresholding And Cooperative Processes

Activities:

- research and select machine-learning algorithms for thresholding and cooperative detection;
- develop advanced thresholding algorithms to improve radiation measurement precision and reduce false alarms;
- implement two-level/cooperative thresholding inspired by communication systems such as 5G;
- integrate cooperative AI processes with the SDR environment.

Expected outputs:

- selected AI algorithms;
- functional thresholding algorithms;
- integrated cooperative processes;
- scientific/technical validation reports.

### Objective 3: Field Maps And Evaluation

Activities:

- develop spatial sensing and field-map generation techniques;
- process data efficiently, including edge/embedded processing with Jetson Nano;
- collect SDR data;
- generate field maps from collected data;
- evaluate maps against exposure standards;
- explore Kriging interpolation and selective sampling to reduce measurement points while preserving map quality.

Expected outputs:

- sensing and mapping techniques;
- generated/evaluated electric-field maps;
- evaluation reports against exposure standards.

## Expected Results

Expected scientific and technical outputs include:

- a system for monitoring electric-field exposure levels, validated in real environments;
- a functional monitoring-system prototype at TRL 7;
- indexed scientific publication(s);
- one Minciencias-categorized journal article or evidence of submission/acceptance;
- use of AI technologies in real environments with electric-emission sources;
- software registration before the national copyright authority;
- a repository containing installers, source code, manuals, and support documentation;
- technical reports and student thesis/progress documents.

## Participants And Roles

Captured roles from the proposal:

| Role | Responsible / group | Main responsibility |
| --- | --- | --- |
| Research group | GCPDS, UNAL Manizales | Project coordination, schedule management, integration of activities |
| Principal investigator | Julio Cesar Garcia Alvarez | Scientific/technical leadership, mentoring, supervision |
| Coinvestigator | Marcelo Herrera Gonzalez | Information-analysis supervision and student advising |
| Undergraduate student | Alejandro Patino Bedoya | Field-data collection and preliminary analysis |
| Undergraduate student | Luis Felipe Giraldo Diaz | Technical reports and article contributions |
| Master's student | Julian Andres Salazar Parias | AI algorithm design and optimization |

Additional organizations and support mentioned include Universidad Nacional de Colombia, Universidad de Caldas, OPEN BUSINESS CONSULTING S.A.S, Inference SAS, and Dunderlab SAS.

## Budget Context

The proposal includes:

- financed amount around COP 100,000,000;
- in-kind contribution around COP 177,984,960;
- total project cost around COP 277,984,960.

Budget categories include research services, specialized technical services, SDR/radio equipment, signal-processing devices, training, cloud/AI/deployment support, and faculty dedication.

## Notes For Product Scope

- The software platform is not just a dashboard; it is expected to support scientific traceability, validation, reporting, and software registration.
- The data model must preserve raw captures, processed outputs, algorithm settings, campaign definitions, hardware configuration, and report artifacts.
- Regulations and exposure thresholds should be modeled as configurable or versioned domain data, not hard-coded UI constants.
