# Schedule Context

There are two planning views:

- a 12-week practical execution schedule;
- a broader proposal schedule expressed across project months up to month 18.

## 12-Week Execution Schedule

### Month 1: Structuring And Connectivity

Milestone: sensor data flows to the platform in an organized way.

| Week | Main work |
| --- | --- |
| 1 | Article writing starts; database audit and schema creation; mathematical documentation of acquisition algorithms; SDR hardware setup and initial link test |
| 2 | Historical-data cleaning scripts; threshold parameter definition for IoT signal detection in the office; transfer-rate validation from sensors to database |
| 3 | API or direct dashboard data connection; Autoencoder environment setup for feature extraction; algorithm implementation knowledge transfer; antenna adjustments and physical device placement |
| 4 | First web visualization tests with isolated data points; filtering-algorithm tests on real captured data; SDR operational stability for TRL 7 |

### Month 2: Advanced Processing And Heat Maps

Milestone: first functional heat-map version with interpolation.

| Week | Main work |
| --- | --- |
| 5 | Heat-map UI design for the office; Kriging interpolation implementation; systematic data collection at different times to capture IoT traffic variability |
| 6 | Autoencoder training with cleaned data; integration of algorithm logic into visual platform; sensor calibration support |
| 7 | Dashboard optimization for real-time or near-real-time map rendering; mathematical-model adjustment according to ICNIRP exposure norms; AI refinement to reduce false alarms |
| 8 | Full integrated test: capture, processing/AI, and visualization |

### Month 3: Validation And Final Delivery

Milestone: operational system and final-ready results.

| Week | Main work |
| --- | --- |
| 9 | Validate generated map precision against manual control measurements; implement automatic exportable reports; final documentation of cooperative thresholding logic |
| 10 | Prototype dismantling or final fixation; Autoencoder performance validation; user-facing bug fixes and platform access security |
| 11 | Final system tests and validation in the office; user and technical platform manual delivery |
| 12 | Work-plan closure, milestone review, and preparation for result presentation |

## Proposal-Level Schedule

The proposal also includes a broader activity schedule:

| Months | Activity |
| --- | --- |
| 1-2 | Evaluate technical and operational requirements for monitoring bands of interest |
| 2-6 | Collect spectrum data |
| 2-8 | Program and calibrate SDR sensors |
| 8-10 | Exhaustive SDR sensor operation tests |
| 10-12 | Integrate signal-processing algorithms |
| 12-14 | Optimize and capture data with SDR sensors |
| 13-16 | Develop algorithms for evaluating electromagnetic-field exposure |
| 13-18 | Select network architectures for spectral analysis |
| 14-18 | Develop and optimize deep-learning models |
| 15-18 | Integrate and operate models |
| 17-18 | Scientific and academic dissemination |

## Delivery Implications For The Platform

The software/database work should prioritize:

1. Sensor ingestion and schema stability early.
2. Historical-data cleaning and migration support.
3. API/dashboard access to measurements.
4. Map rendering and interpolation outputs.
5. AI/model result tracking.
6. Exportable reports and cacheable report data.
7. User access and auditability before final delivery.
