## Main Domain Areas

The project context maps naturally into these data domains:

| Domain | Purpose | Legacy coverage |
| --- | --- | --- |
| Identity and audit | Users, roles, access, activity logs | `users`, `audit_logs` |
| Sensor inventory | Physical sensor/device identity and placement | `sensors` |
| Antenna inventory and assignment | Antenna catalog and port assignment per sensor | `antennas`, `sensor_antennas` |
| Acquisition configuration | SDR frequency, resolution, gain, filter, demodulation, active/monitoring settings | `sensor_configurations` |
| Campaigns | Measurement plans, time windows, sensor assignments, frequency plan | `campaigns`, `campaign_sensors` |
| Measurements | Spectral captures and derived exposure metrics | `sensor_data` |
| Device location | GPS or physical position samples | `sensor_gps`, `sensors.lat/lng/alt` |
| Health/status telemetry | CPU, RAM, disk, temperature, ping, timing, logs | `sensor_status` |
| Alerts | Threshold, status, or exposure alerts | `sensor_history_alert` |
| Reports | Compliance report cache/export data | `compliance_reports_cache` |
| Configuration | Global platform settings | `system_configurations` |

## Requirements Not Fully Covered By Legacy Schema

The old database covers core ingestion and campaign/report basics, but the PDFs imply additional concepts:

- algorithm/model registry;
- model training/evaluation runs;
- threshold profiles and regulatory-limit versions;
- heat-map/floor-plan entities;
- interpolation settings and generated map artifacts;
- report exports and report versions;
- raw-versus-processed data lineage;
- data cleaning jobs and migration/audit metadata;
- device calibration records;
- hardware inventory beyond sensor/antenna names.

## TimescaleDB Considerations

Only `sensor_status` is confirmed as a TimescaleDB hypertable in the old database.

Confirmed from `timescaledb_information.dimensions`:

| Hypertable | Time dimension | Column type | Integer interval |
| --- | --- | --- | ---: |
| sensor_status | timestamp_ms | bigint | 86400000000 |

Important caveat:

- The name `timestamp_ms` suggests epoch milliseconds, but `integer_interval = 86400000000` equals 1,000 days if interpreted as milliseconds and 1 day if interpreted as microseconds. Before recreating the hypertable, confirm the real unit used by inserted status data.

Potential new TimescaleDB candidates:

- `sensor_status`: confirmed old hypertable.
- `sensor_data`: timestamped measurement table; not a hypertable in the old snapshot but likely a candidate for the new system.
- `sensor_history_alert`: timestamped event table; may not require hypertable unless alert volume is high.

## Known Legacy Schema Gaps

Confirmed by the full `pg_constraint` snapshot:

- `sensor_status` has no primary key or foreign key.
- `sensor_data.campaign_id` has no foreign key to `campaigns(id)`.
- `sensor_status.mac` is indexed but has no foreign key to `sensors(mac)`.
- `sensor_configurations.antenna_port` has no foreign key to `sensor_antennas.port`.
- `created_by` / `updated_by` columns are indexed in some tables without foreign keys to `users`.
- several boolean-like flags are stored as integers.
- some epoch defaults use milliseconds, but `sensor_antennas.updated_at` uses epoch seconds.
- `sensor_status_backup_20241215` is a heap backup table with no visible constraints or indexes.

## New Schema Design Signals

When designing the new PostgreSQL/TimescaleDB schema, consider:

1. Use `timestamptz` for application timestamps where possible, and document any epoch integer columns retained for sensor protocol compatibility.
2. Make time-series hypertable choices explicit: `sensor_status` and likely `sensor_data`.
3. Decide whether measurement `campaign_id` should be required and enforced.
4. Normalize or constrain roles, statuses, presets, alert types, and algorithm types.
5. Store acquisition configurations as versioned records so historical measurements can be reproduced.
6. Store algorithm/model versions and threshold profiles alongside alerts and reports.
7. Add report artifact/version tables if exports need traceability beyond the JSON cache.
8. Add calibration and hardware metadata if SDR/antenna validation must be auditable.
9. Treat heat maps as first-class outputs: map context, interpolation method, grid/raster artifact, source measurements, and threshold version.
10. Keep a migration/archive policy for backup tables such as `sensor_status_backup_20241215`.

## Candidate New Tables

These are not final schema decisions, only requirements-derived candidates:

| Candidate table | Why it may be needed |
| --- | --- |
| `algorithm_versions` | Track thresholding, filtering, Autoencoder, and Kriging implementations |
| `threshold_profiles` | Store regulatory/algorithm threshold parameters by version/context |
| `model_runs` | Track model training/evaluation and metrics |
| `calibration_events` | Store sensor/SDR/antenna calibration history |
| `floor_maps` | Store indoor map/floor-plan context |
| `heatmap_runs` | Store interpolation parameters, source campaign, and output artifact references |
| `report_exports` | Track exported reports beyond cached JSON |
| `regulatory_limits` | Store ICNIRP/UIT/ANE-related limits and versions |
| `data_cleaning_runs` | Track historical-data cleaning scripts and outputs |

## Questions To Resolve

- What is the actual unit of `timestamp_ms` in inserted data?
- Should `sensor_data` become a TimescaleDB hypertable?
- Should `sensor_status.mac` be enforced as a foreign key to `sensors(mac)` in the new schema?
- Should `sensor_data.campaign_id` be enforced as a foreign key to `campaigns(id)`?
- Are integer flags legacy compatibility requirements or can they become booleans?
- Should `users.role` become an enum, lookup table, or permission model?
- Should compliance reports be stored only as JSON cache, or as structured report sections plus export artifacts?
