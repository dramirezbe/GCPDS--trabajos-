# Technical Requirements Context

## System Purpose

Build a platform that receives data from SDR-based sensors, processes or exposes that data for AI/signal algorithms, and visualizes human electric-field exposure in indoor IoT-dense environments.

## Hardware And Edge Context

Mentioned hardware and components:

| Component | Context |
| --- | --- |
| SDR | Core measurement technology for spectrum monitoring |
| USRP B210 | Proposed SDR module for spectral monitoring |
| 800-2400MHz antenna | Mentioned as part of SDR module design |
| Jetson Nano | Edge processing platform for efficient or real-time data processing |

Hardware-related requirements:

- configure SDR hardware and validate initial link;
- calibrate sensors and SDR acquisition;
- validate transfer rate from sensors to the database;
- maintain operational stability of the SDR module at TRL 7;
- support sensor/antenna physical placement and port assignment.

## Measurement Scope

The technical proposal refers to:

- indoor high-density IoT environments;
- spectrum monitoring from 700 MHz to 3.5 GHz as the target design range;
- SDR signal acquisition;
- spectral density and signal metrics;
- electric-field exposure evaluation;
- map generation for exposure assessment;
- comparison with exposure standards such as ICNIRP and UIT-T K.52.

## Data Acquisition Requirements

The platform should support:

- sensor registration and MAC identity;
- sensor status/health telemetry;
- antenna inventory and antenna assignment per sensor port;
- SDR acquisition configuration, including frequency range, resolution, windowing, sample rate, gains, filters, demodulation options, active/monitoring flags;
- captured measurement records with timestamp, frequency range, spectral payload, location, campaign context, and derived metrics.

Relevant legacy tables:

- `sensors`
- `antennas`
- `sensor_antennas`
- `sensor_configurations`
- `sensor_data`
- `sensor_gps`
- `sensor_status`

## Processing And AI Requirements

The proposal calls for:

- adaptive thresholding;
- cooperative spectrum sensing;
- machine-learning models for noisy/high-interference environments;
- Autoencoder-based feature extraction or interference-pattern identification;
- false-alarm reduction;
- model validation and performance metrics;
- integration of signal-processing algorithms into the visual platform.

Database/platform implications:

- store algorithm configurations and versions;
- store threshold parameters and calibration context;
- track model training/evaluation runs;
- persist alerts or detections with enough context to reproduce decisions;
- relate processed outputs back to raw measurement data and campaigns.

Legacy schema coverage:

- `sensor_history_alert` captures alerts, but no model-version or algorithm-version table exists in the old schema.
- `sensor_data` stores measurements and derived metrics but stores `pxx` as text.
- `sensor_configurations` stores acquisition/demod/filter settings.

## Heat Map And Visualization Requirements

The schedule and proposal require:

- dashboard consuming data through an API or direct connection;
- first visualization of isolated data points;
- heat-map UI for office maps;
- Kriging interpolation for heat-map mesh generation;
- map rendering in real-time or near-real-time;
- map validation against control/manual measurements;
- exportable reports.

Database/platform implications:

- store campaign spatial bounds or map context;
- store sampled points and their source sensor/campaign;
- store generated map artifacts or cache;
- track interpolation method and parameters;
- track compliance thresholds used to render/evaluate a map.

Legacy schema coverage:

- `sensor_data` includes `lat` and `lng`.
- `sensors` includes nominal `lat`, `lng`, `alt`.
- `compliance_reports_cache` stores one JSON report per campaign.
- No explicit map, interpolation, floor-plan, or report-export tables exist in the old schema.

## Campaign And Reporting Requirements

The project needs planned measurement campaigns and report outputs:

- campaign schedule;
- assigned sensors;
- frequency range, bandwidth, resolution, interval, and preset/config fields;
- automated exportable reports;
- compliance report caching;
- report/manual documentation for users and technical operators.

Legacy schema coverage:

- `campaigns`
- `campaign_sensors`
- `compliance_reports_cache`

Known old-schema issue:

- `sensor_data.campaign_id` exists but is not enforced as a foreign key to `campaigns(id)`.

## Security And Audit Requirements

The schedule explicitly mentions security/access cleanup before delivery. The old schema includes:

- `users`;
- `audit_logs`;
- `system_configurations`.

Potential new-system requirements:

- password hashing strategy must be confirmed;
- user roles should probably be normalized or constrained;
- audit logs should capture actor, action, entity, entity ID, payload, and timestamp;
- system configurations should support typed values or JSON values where needed.

## Non-Functional Requirements

The source documents imply these non-functional needs:

- traceability of algorithms and measurements;
- reproducibility for scientific reports;
- near-real-time or quasi-real-time dashboard rendering;
- robust ingestion from physical sensors;
- maintainable API for dashboard consumption;
- data cleaning for historical datasets;
- reliable operation in TRL 7 prototype context;
- exportable deliverables for scientific and regulatory stakeholders.
