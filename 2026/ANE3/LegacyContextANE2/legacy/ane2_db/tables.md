# ANE DB Captured Tables

This file records table-level details pasted from `psql`. Keep it factual: only add columns, indexes, and references that appear in captured output.

## public.antennas

Source:

```text
ane_db=# \d antennas
```

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | integer | not null | `nextval('antennas_id_seq'::regclass)` |
| name | character varying(255) | not null | |
| type | character varying(100) | not null | |
| frequency_min_hz | bigint | nullable | |
| frequency_max_hz | bigint | nullable | |
| gain_db | numeric(5,2) | nullable | |
| description | text | nullable | |
| created_at | bigint | nullable | `EXTRACT(epoch FROM now())::bigint * 1000` |
| updated_at | bigint | nullable | `EXTRACT(epoch FROM now())::bigint * 1000` |
| created_by | integer | nullable | |
| updated_by | integer | nullable | |
| inventory_code | character varying(255) | nullable | |

Indexes:

| Name | Type | Columns |
| --- | --- | --- |
| antennas_pkey | primary key, btree | id |
| idx_antennas_created_by | btree | created_by |
| idx_antennas_updated_by | btree | updated_by |

Referenced by:

| Referencing table | Constraint | Definition |
| --- | --- | --- |
| sensor_antennas | sensor_antennas_antenna_id_fkey | `FOREIGN KEY (antenna_id) REFERENCES antennas(id) ON DELETE CASCADE` |

Notes:

- `created_by` and `updated_by` are indexed, but no foreign key to `users` was shown in the captured `\d antennas` output.
- Timestamps are stored as epoch milliseconds in `bigint`, not PostgreSQL timestamp types.

## public.audit_logs

Source:

```text
ane_db=# \d audit_logs
```

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | integer | not null | `nextval('audit_logs_id_seq'::regclass)` |
| user_id | integer | nullable | |
| action | character varying(100) | not null | |
| details | jsonb | nullable | |
| created_at | timestamp without time zone | nullable | `now()` |

Indexes:

| Name | Type | Columns |
| --- | --- | --- |
| audit_logs_pkey | primary key, btree | id |
| idx_audit_logs_action | btree | action |
| idx_audit_logs_created_at | btree | created_at |
| idx_audit_logs_user_id | btree | user_id |

Foreign keys:

| Constraint | Definition |
| --- | --- |
| audit_logs_user_id_fkey | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` |

## public.campaign_sensors

Source:

```text
ane_db=# \d campaign_sensors
```

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | integer | not null | `nextval('campaign_sensors_id_seq'::regclass)` |
| campaign_id | integer | not null | |
| sensor_mac | character varying(17) | not null | |
| created_at | timestamp without time zone | nullable | `now()` |

Indexes and constraints:

| Name | Type | Columns |
| --- | --- | --- |
| campaign_sensors_pkey | primary key, btree | id |
| campaign_sensors_campaign_id_sensor_mac_key | unique constraint, btree | campaign_id, sensor_mac |

Foreign keys:

| Constraint | Definition |
| --- | --- |
| campaign_sensors_campaign_id_fkey | `FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE` |
| campaign_sensors_sensor_mac_fkey | `FOREIGN KEY (sensor_mac) REFERENCES sensors(mac) ON DELETE CASCADE` |

## public.sensors

Source:

```text
ane_db=# \d+ public.sensors
```

Capture status: complete visible `\d+` output.

Columns:

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | integer | not null | `nextval('sensors_id_seq'::regclass)` |
| mac | character varying(17) | not null | |
| name | character varying(255) | not null | |
| description | text | nullable | |
| lat | numeric(10,7) | nullable | |
| lng | numeric(10,7) | nullable | |
| alt | numeric(10,2) | nullable | |
| status | character varying(50) | nullable | `'inactive'::character varying` |
| created_at | bigint | nullable | `EXTRACT(epoch FROM now())::bigint * 1000` |
| updated_at | bigint | nullable | `EXTRACT(epoch FROM now())::bigint * 1000` |
| created_by | integer | nullable | |
| updated_by | integer | nullable | |
| status_admin | character varying(50) | nullable | `'active'::character varying` |

Indexes and constraints:

| Name | Type | Columns |
| --- | --- | --- |
| sensors_pkey | primary key, btree | id |
| idx_sensors_created_by | btree | created_by |
| idx_sensors_updated_by | btree | updated_by |
| sensors_mac_key | unique constraint, btree | mac |

Referenced by:

| Referencing table | Constraint | Definition |
| --- | --- | --- |
| campaign_sensors | campaign_sensors_sensor_mac_fkey | `FOREIGN KEY (sensor_mac) REFERENCES sensors(mac) ON DELETE CASCADE` |
| sensor_antennas | sensor_antennas_sensor_id_fkey | `FOREIGN KEY (sensor_id) REFERENCES sensors(id) ON DELETE CASCADE` |
| sensor_configurations | sensor_configurations_mac_fkey | `FOREIGN KEY (mac) REFERENCES sensors(mac) ON UPDATE CASCADE ON DELETE CASCADE` |
| sensor_data | sensor_data_mac_fkey | `FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE` |
| sensor_gps | sensor_gps_mac_fkey | `FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE` |
| sensor_history_alert | sensor_history_alert_sensor_mac_fkey | `FOREIGN KEY (sensor_mac) REFERENCES sensors(mac) ON DELETE CASCADE` |

Notes:

- `created_by` and `updated_by` are indexed, but no foreign keys to `users` were visible in this capture.
- Timestamps are stored as epoch milliseconds in `bigint`, matching `antennas`.

## public.campaigns

Source:

```text
ane_db=# \d+ public.campaigns
```

Capture status: complete visible `\d+` output.

Columns:

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | integer | not null | `nextval('campaigns_id_seq'::regclass)` |
| name | character varying(255) | not null | |
| description | text | nullable | |
| status | character varying(50) | nullable | `'scheduled'::character varying` |
| start_date | date | nullable | |
| end_date | date | nullable | |
| start_time | time without time zone | nullable | |
| end_time | time without time zone | nullable | |
| interval_seconds | integer | nullable | |
| start_freq_mhz | numeric(10,3) | nullable | |
| end_freq_mhz | numeric(10,3) | nullable | |
| bandwidth_mhz | numeric(10,3) | nullable | |
| resolution_khz | numeric(10,3) | nullable | |
| preset | character varying(50) | nullable | `'custom'::character varying` |
| config | jsonb | nullable | |
| created_at | timestamp without time zone | nullable | `now()` |
| updated_at | timestamp without time zone | nullable | `now()` |
| updated_by | integer | nullable | |
| created_by | integer | nullable | |

Indexes:

| Name | Type | Columns |
| --- | --- | --- |
| campaigns_pkey | primary key, btree | id |
| idx_campaigns_created_by | btree | created_by |
| idx_campaigns_dates | btree | start_date, end_date |
| idx_campaigns_status | btree | status |
| idx_campaigns_updated_by | btree | updated_by |

Foreign keys:

| Constraint | Definition |
| --- | --- |
| fk_campaigns_created_by | `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL` |

Referenced by:

| Referencing table | Constraint | Definition |
| --- | --- | --- |
| campaign_sensors | campaign_sensors_campaign_id_fkey | `FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE` |
| compliance_reports_cache | compliance_reports_cache_campaign_id_fkey | `FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE` |

Notes:

- `updated_by` is indexed, but no foreign key to `users` was visible in this capture.

## public.sensor_status

Source:

```text
ane_db=# \d+ public.sensor_status
```

Capture status: complete visible `\d+` output. TimescaleDB metadata confirms this table is a hypertable.

Columns:

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | bigint | not null | `nextval('sensor_status_id_seq'::regclass)` |
| mac | character varying(17) | not null | |
| cpu_0 | double precision | nullable | |
| cpu_1 | double precision | nullable | |
| cpu_2 | double precision | nullable | |
| cpu_3 | double precision | nullable | |
| ram_mb | bigint | nullable | |
| swap_mb | bigint | nullable | |
| disk_mb | bigint | nullable | |
| total_ram_mb | bigint | nullable | |
| total_swap_mb | bigint | nullable | |
| total_disk_mb | bigint | nullable | |
| temp_c | double precision | nullable | |
| ping_ms | double precision | nullable | |
| delta_t_ms | bigint | nullable | |
| last_kal_ms | bigint | nullable | |
| last_ntp_ms | bigint | nullable | |
| logs | text | nullable | |
| timestamp_ms | bigint | not null | |
| created_at | timestamp with time zone | not null | `now()` |

Indexes:

| Name | Type | Columns |
| --- | --- | --- |
| idx_sensor_status_mac | btree | mac |
| idx_sensor_status_mac_timestamp | btree | mac, timestamp_ms DESC |
| idx_sensor_status_timestamp | btree | timestamp_ms DESC |
| sensor_status_timestamp_ms_idx | btree | timestamp_ms DESC |

TimescaleDB:

| Property | Value |
| --- | --- |
| Hypertable | yes |
| Visible child table | `_timescaledb_internal._hyper_26_2_chunk` |

Notes:

- No primary key or foreign key was visible in the pasted `sensor_status` output, despite the `id` column using `sensor_status_id_seq`.
- `sensor_status_timestamp_ms_idx` may be a Timescale-created/default time index; confirm with full metadata.

## public.sensor_data

Source:

```text
ane_db=# \d+ public.sensor_data
```

Capture status: complete visible `\d+` output.

Columns:

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | integer | not null | `nextval('sensor_data_id_seq'::regclass)` |
| mac | character varying(17) | not null | |
| campaign_id | integer | nullable | |
| pxx | text | not null | |
| start_freq_hz | bigint | not null | |
| end_freq_hz | bigint | not null | |
| timestamp | bigint | not null | |
| lat | numeric(10,7) | nullable | |
| lng | numeric(10,7) | nullable | |
| excursion_peak_to_peak_hz | numeric(15,3) | nullable | |
| excursion_peak_deviation_hz | numeric(15,3) | nullable | |
| excursion_rms_deviation_hz | numeric(15,3) | nullable | |
| depth_peak_to_peak | numeric(10,6) | nullable | |
| depth_peak_deviation | numeric(10,6) | nullable | |
| depth_rms_deviation | numeric(10,6) | nullable | |
| created_at | bigint | not null | `EXTRACT(epoch FROM now())::bigint * 1000` |

Indexes:

| Name | Type | Columns |
| --- | --- | --- |
| sensor_data_pkey | primary key, btree | id |
| idx_sensor_data_mac | btree | mac |
| idx_sensor_data_timestamp | btree | timestamp |

Foreign keys:

| Constraint | Definition |
| --- | --- |
| sensor_data_mac_fkey | `FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE` |

Notes:

- `campaign_id` is present but no foreign key to `campaigns(id)` was visible in this capture.
- `timestamp` is a `bigint`, likely epoch milliseconds, but the unit should be confirmed from application code or sample data.
- `pxx` likely stores spectral/PSD data as text; confirm format before modeling the new schema.

## public.sensor_gps

Source:

```text
ane_db=# \d+ public.sensor_gps
```

Capture status: complete visible `\d+` output.

Columns:

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | integer | not null | `nextval('sensor_gps_id_seq'::regclass)` |
| mac | character varying(17) | not null | |
| lat | numeric(10,7) | not null | |
| lng | numeric(10,7) | not null | |
| alt | numeric(10,2) | nullable | |
| created_at | bigint | nullable | `EXTRACT(epoch FROM now())::bigint * 1000` |

Indexes:

| Name | Type | Columns |
| --- | --- | --- |
| sensor_gps_pkey | primary key, btree | id |
| idx_sensor_gps_mac | btree | mac |

Foreign keys:

| Constraint | Definition |
| --- | --- |
| sensor_gps_mac_fkey | `FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE` |

## public.sensor_antennas

Source:

```text
ane_db=# \d+ public.sensor_antennas
```

Capture status: complete visible `\d+` output.

Columns:

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | integer | not null | `nextval('sensor_antennas_id_seq'::regclass)` |
| sensor_id | integer | not null | |
| antenna_id | integer | not null | |
| port | integer | not null | |
| is_active | integer | nullable | `1` |
| created_at | bigint | nullable | `EXTRACT(epoch FROM now())::bigint * 1000` |
| created_by | integer | nullable | |
| updated_at | bigint | nullable | `EXTRACT(epoch FROM now())::bigint` |
| updated_by | integer | nullable | |

Indexes and constraints:

| Name | Type | Columns |
| --- | --- | --- |
| sensor_antennas_pkey | primary key, btree | id |
| idx_sensor_antennas_created_by | btree | created_by |
| idx_sensor_antennas_updated_by | btree | updated_by |
| sensor_antennas_sensor_id_port_key | unique constraint, btree | sensor_id, port |

Foreign keys:

| Constraint | Definition |
| --- | --- |
| sensor_antennas_antenna_id_fkey | `FOREIGN KEY (antenna_id) REFERENCES antennas(id) ON DELETE CASCADE` |
| sensor_antennas_sensor_id_fkey | `FOREIGN KEY (sensor_id) REFERENCES sensors(id) ON DELETE CASCADE` |

Notes:

- `is_active` is stored as `integer`, not `boolean`.
- `updated_at` default lacks `* 1000`, unlike most other epoch timestamp defaults. Confirm whether this is intentional or a legacy bug.
- `created_by` and `updated_by` are indexed, but no foreign keys to `users` were visible in this capture.

## public.sensor_configurations

Source:

```text
ane_db=# \d+ public.sensor_configurations
```

Capture status: complete visible `\d+` output.

Columns:

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | integer | not null | `nextval('sensor_configurations_id_seq'::regclass)` |
| mac | character varying(17) | not null | |
| start_freq_hz | bigint | not null | |
| end_freq_hz | bigint | not null | |
| resolution_hz | integer | nullable | |
| antenna_port | integer | nullable | |
| window | character varying(50) | nullable | |
| overlap | numeric(5,2) | nullable | |
| sample_rate_hz | integer | nullable | |
| lna_gain | integer | nullable | |
| vga_gain | integer | nullable | |
| antenna_amp | integer | nullable | `0` |
| demod_type | character varying(50) | nullable | |
| demod_bandwidth_hz | integer | nullable | |
| demod_center_freq_hz | integer | nullable | |
| demod_with_metrics | integer | nullable | `0` |
| demod_port_socket | character varying(100) | nullable | |
| is_active | integer | nullable | `1` |
| created_at | bigint | nullable | `EXTRACT(epoch FROM now())::bigint * 1000` |
| updated_at | bigint | nullable | `EXTRACT(epoch FROM now())::bigint * 1000` |
| filter_type | character varying(50) | nullable | |
| filter_bw_hz | integer | nullable | |
| filter_order | integer | nullable | |
| filter_start_freq_hz | bigint | nullable | |
| filter_end_freq_hz | bigint | nullable | |
| is_monitoring | integer | nullable | `0` |

Indexes:

| Name | Type | Columns |
| --- | --- | --- |
| sensor_configurations_pkey | primary key, btree | id |
| idx_sensor_config_mac | btree | mac |

Foreign keys:

| Constraint | Definition |
| --- | --- |
| sensor_configurations_mac_fkey | `FOREIGN KEY (mac) REFERENCES sensors(mac) ON UPDATE CASCADE ON DELETE CASCADE` |

Notes:

- `antenna_amp`, `demod_with_metrics`, `is_active`, and `is_monitoring` are stored as `integer`, not `boolean`.
- `antenna_port` likely maps to `sensor_antennas.port`, but no foreign key was visible in this capture.

## public.users

Source:

```text
ane_db=# \d+ public.users
```

Capture status: complete visible `\d+` output.

Columns:

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | integer | not null | `nextval('users_id_seq'::regclass)` |
| username | character varying(100) | not null | |
| password | character varying(255) | not null | |
| full_name | character varying(255) | not null | |
| email | character varying(255) | not null | |
| role | character varying(50) | not null | `'tecnico'::character varying` |
| is_active | boolean | nullable | `true` |
| created_at | timestamp without time zone | nullable | `now()` |
| updated_at | timestamp without time zone | nullable | `now()` |

Indexes and constraints:

| Name | Type | Columns |
| --- | --- | --- |
| users_pkey | primary key, btree | id |
| idx_users_email | btree | email |
| idx_users_role | btree | role |
| idx_users_username | btree | username |
| users_email_key | unique constraint, btree | email |
| users_username_key | unique constraint, btree | username |

Referenced by:

| Referencing table | Constraint | Definition |
| --- | --- | --- |
| audit_logs | audit_logs_user_id_fkey | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` |
| campaigns | fk_campaigns_created_by | `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL` |

Notes:

- Password storage format is unknown from schema alone; confirm hashing strategy before migration.
- `role` is free text in the schema, not an enum.

## public.compliance_reports_cache

Source:

```text
ane_db=# \d+ public.compliance_reports_cache
```

Capture status: complete visible `\d+` output.

Columns:

| Column | Type | Nullable | Default | Description |
| --- | --- | --- | --- | --- |
| id | integer | not null | `nextval('compliance_reports_cache_id_seq'::regclass)` | |
| campaign_id | integer | not null | | ID de la campana asociada al reporte |
| report_data | jsonb | not null | | Datos completos del reporte en formato JSON |
| created_at | timestamp with time zone | nullable | `now()` | Fecha de primera generacion del reporte |
| updated_at | timestamp with time zone | nullable | `now()` | Fecha de ultima actualizacion del reporte |

Indexes and constraints:

| Name | Type | Columns |
| --- | --- | --- |
| compliance_reports_cache_pkey | primary key, btree | id |
| compliance_reports_cache_campaign_id_key | unique constraint, btree | campaign_id |
| idx_compliance_reports_campaign | btree | campaign_id |
| idx_compliance_reports_created | btree | created_at DESC |

Foreign keys:

| Constraint | Definition |
| --- | --- |
| compliance_reports_cache_campaign_id_fkey | `FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE` |

Notes:

- Unique `campaign_id` means at most one cached compliance report per campaign.

## public.sensor_history_alert

Source:

```text
ane_db=# \d+ public.sensor_history_alert
```

Capture status: complete visible `\d+` output.

Columns:

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | integer | not null | `nextval('sensor_history_alert_id_seq'::regclass)` |
| sensor_mac | character varying(17) | not null | |
| alert_type | character varying(50) | not null | |
| description | text | nullable | |
| timestamp | bigint | not null | |
| created_at | bigint | nullable | `EXTRACT(epoch FROM now())::bigint * 1000` |

Indexes:

| Name | Type | Columns |
| --- | --- | --- |
| sensor_history_alert_pkey | primary key, btree | id |
| idx_sensor_history_alert_mac_timestamp | btree | sensor_mac, timestamp DESC |
| idx_sensor_history_alert_timestamp | btree | timestamp DESC |

Foreign keys:

| Constraint | Definition |
| --- | --- |
| sensor_history_alert_sensor_mac_fkey | `FOREIGN KEY (sensor_mac) REFERENCES sensors(mac) ON DELETE CASCADE` |

Notes:

- `timestamp` is a `bigint`, likely epoch milliseconds, but the unit should be confirmed.

## public.system_configurations

Source:

```text
ane_db=# \d+ public.system_configurations
```

Capture status: complete visible `\d+` output.

Columns:

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| key | character varying(100) | not null | |
| value | text | nullable | |
| description | text | nullable | |
| updated_at | timestamp without time zone | nullable | `now()` |

Indexes and constraints:

| Name | Type | Columns |
| --- | --- | --- |
| system_configurations_pkey | primary key, btree | key |

Notes:

- This is a simple key-value configuration table with text values.

## public.sensor_status_backup_20241215

Source:

```text
ane_db=# \d+ public.sensor_status_backup_20241215
```

Capture status: complete visible `\d+` output.

Columns:

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | bigint | nullable | |
| mac | character varying(17) | nullable | |
| cpu_0 | double precision | nullable | |
| cpu_1 | double precision | nullable | |
| cpu_2 | double precision | nullable | |
| cpu_3 | double precision | nullable | |
| ram_mb | bigint | nullable | |
| swap_mb | bigint | nullable | |
| disk_mb | bigint | nullable | |
| total_ram_mb | bigint | nullable | |
| total_swap_mb | bigint | nullable | |
| total_disk_mb | bigint | nullable | |
| temp_c | double precision | nullable | |
| ping_ms | double precision | nullable | |
| delta_t_ms | bigint | nullable | |
| last_kal_ms | bigint | nullable | |
| last_ntp_ms | bigint | nullable | |
| logs | text | nullable | |
| timestamp_ms | bigint | nullable | |
| created_at | timestamp with time zone | nullable | |

Indexes and constraints:

None visible in the captured `\d+` output.

Notes:

- This appears to be a heap backup snapshot of `sensor_status` from 2024-12-15.
- Unlike `sensor_status`, all visible columns are nullable and no defaults are present.
- Decide whether this table should be migrated, archived externally, or dropped from the new schema.
