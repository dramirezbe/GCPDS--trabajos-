# ANE DB Starter Diagram

This diagram is built step by step from pasted `psql` output. It includes confirmed entities, the first captured columns, and relationships backed by visible constraints.

## Confirmed ERD In Progress

```mermaid
erDiagram
    ANTENNAS {
        integer id PK
        varchar(255) name
        varchar(100) type
        bigint frequency_min_hz
        bigint frequency_max_hz
        numeric_5_2 gain_db
        text description
        bigint created_at
        bigint updated_at
        integer created_by
        integer updated_by
        varchar(255) inventory_code
    }

    AUDIT_LOGS {
        integer id PK
        integer user_id FK
        varchar(100) action
        jsonb details
        timestamp created_at
    }

    CAMPAIGN_SENSORS {
        integer id PK
        integer campaign_id FK
        varchar(17) sensor_mac FK
        timestamp created_at
    }

    CAMPAIGNS {
        integer id PK
        varchar(255) name
        text description
        varchar(50) status
        date start_date
        date end_date
        time start_time
        time end_time
        integer interval_seconds
        numeric_10_3 start_freq_mhz
        numeric_10_3 end_freq_mhz
        numeric_10_3 bandwidth_mhz
        numeric_10_3 resolution_khz
        varchar(50) preset
        jsonb config
        timestamp created_at
        timestamp updated_at
        integer updated_by
        integer created_by FK
    }

    COMPLIANCE_REPORTS_CACHE {
        integer id PK
        integer campaign_id FK
        jsonb report_data
        timestamptz created_at
        timestamptz updated_at
    }
    SENSOR_ANTENNAS {
        integer id PK
        integer sensor_id FK
        integer antenna_id FK
        integer port
        integer is_active
        bigint created_at
        integer created_by
        bigint updated_at
        integer updated_by
    }

    SENSOR_CONFIGURATIONS {
        integer id PK
        varchar(17) mac FK
        bigint start_freq_hz
        bigint end_freq_hz
        integer resolution_hz
        integer antenna_port
        varchar(50) window
        numeric_5_2 overlap
        integer sample_rate_hz
        integer lna_gain
        integer vga_gain
        integer antenna_amp
        varchar(50) demod_type
        integer demod_bandwidth_hz
        integer demod_center_freq_hz
        integer demod_with_metrics
        varchar(100) demod_port_socket
        integer is_active
        bigint created_at
        bigint updated_at
        varchar(50) filter_type
        integer filter_bw_hz
        integer filter_order
        bigint filter_start_freq_hz
        bigint filter_end_freq_hz
        integer is_monitoring
    }

    SENSOR_DATA {
        integer id PK
        varchar(17) mac FK
        integer campaign_id
        text pxx
        bigint start_freq_hz
        bigint end_freq_hz
        bigint timestamp
        numeric_10_7 lat
        numeric_10_7 lng
        numeric_15_3 excursion_peak_to_peak_hz
        numeric_15_3 excursion_peak_deviation_hz
        numeric_15_3 excursion_rms_deviation_hz
        numeric_10_6 depth_peak_to_peak
        numeric_10_6 depth_peak_deviation
        numeric_10_6 depth_rms_deviation
        bigint created_at
    }

    SENSOR_GPS {
        integer id PK
        varchar(17) mac FK
        numeric_10_7 lat
        numeric_10_7 lng
        numeric_10_2 alt
        bigint created_at
    }

    SENSOR_HISTORY_ALERT {
        integer id PK
        varchar(17) sensor_mac FK
        varchar(50) alert_type
        text description
        bigint timestamp
        bigint created_at
    }

    SENSOR_STATUS {
        bigint id
        varchar mac
        double_precision cpu_0
        double_precision cpu_1
        double_precision cpu_2
        double_precision cpu_3
        bigint ram_mb
        bigint swap_mb
        bigint disk_mb
        bigint total_ram_mb
        bigint total_swap_mb
        bigint total_disk_mb
        double_precision temp_c
        double_precision ping_ms
        bigint delta_t_ms
        bigint last_kal_ms
        bigint last_ntp_ms
        text logs
        bigint timestamp_ms
        timestamptz created_at
    }

    SENSOR_STATUS_BACKUP_20241215 {
        bigint id
        varchar mac
        double_precision cpu_0
        double_precision cpu_1
        double_precision cpu_2
        double_precision cpu_3
        bigint ram_mb
        bigint swap_mb
        bigint disk_mb
        bigint total_ram_mb
        bigint total_swap_mb
        bigint total_disk_mb
        double_precision temp_c
        double_precision ping_ms
        bigint delta_t_ms
        bigint last_kal_ms
        bigint last_ntp_ms
        text logs
        bigint timestamp_ms
        timestamptz created_at
    }

    SENSORS {
        integer id PK
        varchar mac UK
        varchar(255) name
        text description
        numeric_10_7 lat
        numeric_10_7 lng
        numeric_10_2 alt
        varchar(50) status
        bigint created_at
        bigint updated_at
        integer created_by
        integer updated_by
        varchar(50) status_admin
    }

    SYSTEM_CONFIGURATIONS {
        varchar(100) key PK
        text value
        text description
        timestamp updated_at
    }

    USERS {
        integer id PK
        varchar(100) username UK
        varchar(255) password
        varchar(255) full_name
        varchar(255) email UK
        varchar(50) role
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    USERS |o--o{ AUDIT_LOGS : writes
    USERS |o--o{ CAMPAIGNS : creates
    CAMPAIGNS ||--o{ CAMPAIGN_SENSORS : includes
    CAMPAIGNS ||--o| COMPLIANCE_REPORTS_CACHE : caches
    SENSORS ||--o{ CAMPAIGN_SENSORS : assigned_by_mac
    ANTENNAS ||--o{ SENSOR_ANTENNAS : used_by
    SENSORS ||--o{ SENSOR_ANTENNAS : has
    SENSORS ||--o{ SENSOR_CONFIGURATIONS : configures_by_mac
    SENSORS ||--o{ SENSOR_DATA : records_by_mac
    SENSORS ||--o{ SENSOR_GPS : locates_by_mac
    SENSORS ||--o{ SENSOR_HISTORY_ALERT : raises_by_mac
```

## Inferred Domain Grouping

```mermaid
flowchart LR
    subgraph Identity
        USERS[users]
    end

    subgraph SensorCore[Sensor Core]
        SENSORS[sensors]
        ANTENNAS[antennas]
        SENSOR_ANTENNAS[sensor_antennas]
        SENSOR_CONFIGURATIONS[sensor_configurations]
    end

    subgraph TimeSeries[Likely Time-Series]
        SENSOR_DATA[sensor_data]
        SENSOR_GPS[sensor_gps]
        SENSOR_STATUS[sensor_status]
        SENSOR_HISTORY_ALERT[sensor_history_alert]
    end

    subgraph Campaigns
        CAMPAIGNS[campaigns]
        CAMPAIGN_SENSORS[campaign_sensors]
    end

    subgraph Operations
        AUDIT_LOGS[audit_logs]
        SYSTEM_CONFIGURATIONS[system_configurations]
        COMPLIANCE_REPORTS_CACHE[compliance_reports_cache]
        SENSOR_STATUS_BACKUP[sensor_status_backup_20241215]
    end
```

## Relationship Backlog

These are still pending or intentionally absent in the captures:

| Possible relationship | Why it is suspected | Status |
| --- | --- | --- |
| `sensors` to `sensor_status` | `sensor_status` has `mac` indexes, but no FK exists in the captured constraint query | Not enforced by DB |
| `campaigns` to `sensor_data` | `sensor_data.campaign_id` exists, but no FK exists in the captured constraint query | Not enforced by DB |
| `sensor_antennas.port` to `sensor_configurations.antenna_port` | Column names suggest a relationship, but no FK appeared in `\d+ public.sensor_configurations` | Unconfirmed |
| `antennas.created_by` to `users.id` | `created_by` has an index, but no FK appeared in `\d antennas` | Unconfirmed |
| `antennas.updated_by` to `users.id` | `updated_by` has an index, but no FK appeared in `\d antennas` | Unconfirmed |
| `sensor_antennas.created_by` to `users.id` | `created_by` has an index, but no FK appeared in `\d+ public.sensor_antennas` | Unconfirmed |
| `sensor_antennas.updated_by` to `users.id` | `updated_by` has an index, but no FK appeared in `\d+ public.sensor_antennas` | Unconfirmed |
| `campaigns.updated_by` to `users.id` | `updated_by` has an index, but no FK appeared in the `\d+ public.campaigns` output | Unconfirmed |
| `sensors.created_by` to `users.id` | `created_by` has an index, but no FK appeared in the `\d+ public.sensors` output | Unconfirmed |
| `sensors.updated_by` to `users.id` | `updated_by` has an index, but no FK appeared in the `\d+ public.sensors` output | Unconfirmed |
