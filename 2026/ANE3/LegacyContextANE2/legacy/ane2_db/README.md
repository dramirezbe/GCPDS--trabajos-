# ANE2 DB Design Context

This folder is the working context for rebuilding and documenting the old `ane_db` database model step by step.

Current source snapshot:

- Database prompt: `ane_db=#`
- Schema shown: `public`
- Owner shown: `ane_user`
- Source commands captured so far: `\d`, `\dt`, `\d antennas`, `\d audit_logs`, `\d campaign_sensors`, `\d+ public.sensors`, `\d+ public.campaigns`, `\d+ public.sensor_status`, `\d+ public.sensor_data`, `\d+ public.sensor_gps`, `\d+ public.sensor_antennas`, `\d+ public.sensor_configurations`, `\d+ public.users`, `\d+ public.compliance_reports_cache`, `\d+ public.sensor_history_alert`, `\d+ public.system_configurations`, `\d+ public.sensor_status_backup_20241215`, full `pg_constraint` query, `timescaledb_information.dimensions`
- Capture date: 2026-05-02

The current snapshots include the table inventory, table definitions, full visible constraints, and TimescaleDB dimension discovery. Triggers, policies, sample data, and full hypertable settings still need to be captured separately if required.

## Files

- [inventory.md](inventory.md): object inventory copied from the old database `\d` output.
- [tables.md](tables.md): captured table definitions and indexes.
- [constraints.md](constraints.md): captured primary keys, unique constraints, and foreign keys.
- [hypertables.md](hypertables.md): TimescaleDB hypertable findings.
- [diagram.md](diagram.md): starter Mermaid diagrams with confirmed relationships.

## Next Metadata Capture Steps

All visible table definitions and constraints have been captured. Run these against the old database and paste the output here if we need deeper TimescaleDB details:

```sql
\pset pager off
SELECT *
FROM timescaledb_information.hypertables
ORDER BY hypertable_schema, hypertable_name;

SELECT *
FROM timescaledb_information.compression_settings
WHERE hypertable_name = 'sensor_status';

SELECT *
FROM timescaledb_information.jobs
WHERE hypertable_name = 'sensor_status';
```

## Modeling Notes

- `sensor_status` is confirmed as a TimescaleDB hypertable.
- `sensor_status.timestamp_ms` is confirmed as the Timescale time dimension with `integer_interval = 86400000000`.
- `sensor_status` has no primary key or foreign key in the captured `pg_constraint` output.
- `sensors`, `campaigns`, and `sensor_status` now have full visible `\d+` captures.
- `sensor_data` stores timestamped measurements but is not listed as a TimescaleDB hypertable in the old database snapshot.
- `sensor_data.campaign_id` exists but is not enforced as a foreign key in the old schema.
- `sensor_gps` stores the latest or sampled GPS position per sensor; no timestamp column other than `created_at` is visible.
- `sensor_configurations` stores SDR, demodulation, and filter settings keyed by sensor MAC.
- `sensor_history_alert` stores timestamped alert events keyed by sensor MAC.
- `compliance_reports_cache` is a one-row-per-campaign JSON cache.
- `system_configurations` is a key-value table.
- `sensor_status_backup_20241215` is a heap backup snapshot with the same visible columns as `sensor_status`, but all columns are nullable and no indexes or constraints are visible.
- `antennas` is confirmed as a real table and resolves the first snapshot's 28-row discrepancy.
