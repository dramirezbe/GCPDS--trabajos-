# ANE DB Constraints

This file records constraints from pasted `psql` output.

Constraint type codes from `pg_constraint.contype`:

| Code | Meaning |
| --- | --- |
| p | Primary key |
| u | Unique constraint |
| f | Foreign key |

## Full Constraint Snapshot

Source:

```sql
SELECT
  conrelid::regclass AS table_name,
  conname AS constraint_name,
  contype AS constraint_type,
  pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
ORDER BY conrelid::regclass::text, conname;
```

Result: 30 rows.

| Table | Constraint | Type | Definition |
| --- | --- | --- | --- |
| antennas | antennas_pkey | p | `PRIMARY KEY (id)` |
| audit_logs | audit_logs_pkey | p | `PRIMARY KEY (id)` |
| audit_logs | audit_logs_user_id_fkey | f | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` |
| campaign_sensors | campaign_sensors_pkey | p | `PRIMARY KEY (id)` |
| campaign_sensors | campaign_sensors_campaign_id_sensor_mac_key | u | `UNIQUE (campaign_id, sensor_mac)` |
| campaign_sensors | campaign_sensors_campaign_id_fkey | f | `FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE` |
| campaign_sensors | campaign_sensors_sensor_mac_fkey | f | `FOREIGN KEY (sensor_mac) REFERENCES sensors(mac) ON DELETE CASCADE` |
| campaigns | campaigns_pkey | p | `PRIMARY KEY (id)` |
| campaigns | fk_campaigns_created_by | f | `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL` |
| compliance_reports_cache | compliance_reports_cache_campaign_id_fkey | f | `FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE` |
| compliance_reports_cache | compliance_reports_cache_campaign_id_key | u | `UNIQUE (campaign_id)` |
| compliance_reports_cache | compliance_reports_cache_pkey | p | `PRIMARY KEY (id)` |
| sensor_antennas | sensor_antennas_antenna_id_fkey | f | `FOREIGN KEY (antenna_id) REFERENCES antennas(id) ON DELETE CASCADE` |
| sensor_antennas | sensor_antennas_pkey | p | `PRIMARY KEY (id)` |
| sensor_antennas | sensor_antennas_sensor_id_fkey | f | `FOREIGN KEY (sensor_id) REFERENCES sensors(id) ON DELETE CASCADE` |
| sensor_antennas | sensor_antennas_sensor_id_port_key | u | `UNIQUE (sensor_id, port)` |
| sensor_configurations | sensor_configurations_mac_fkey | f | `FOREIGN KEY (mac) REFERENCES sensors(mac) ON UPDATE CASCADE ON DELETE CASCADE` |
| sensor_configurations | sensor_configurations_pkey | p | `PRIMARY KEY (id)` |
| sensor_data | sensor_data_mac_fkey | f | `FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE` |
| sensor_data | sensor_data_pkey | p | `PRIMARY KEY (id)` |
| sensor_gps | sensor_gps_mac_fkey | f | `FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE` |
| sensor_gps | sensor_gps_pkey | p | `PRIMARY KEY (id)` |
| sensor_history_alert | sensor_history_alert_pkey | p | `PRIMARY KEY (id)` |
| sensor_history_alert | sensor_history_alert_sensor_mac_fkey | f | `FOREIGN KEY (sensor_mac) REFERENCES sensors(mac) ON DELETE CASCADE` |
| sensors | sensors_pkey | p | `PRIMARY KEY (id)` |
| sensors | sensors_mac_key | u | `UNIQUE (mac)` |
| system_configurations | system_configurations_pkey | p | `PRIMARY KEY (key)` |
| users | users_email_key | u | `UNIQUE (email)` |
| users | users_pkey | p | `PRIMARY KEY (id)` |
| users | users_username_key | u | `UNIQUE (username)` |

## Open Items

- Confirm whether the absence of `sensor_status` primary key and foreign keys is intentional in the old design.
- Confirm whether `sensor_data.campaign_id` intentionally has no foreign key to `campaigns(id)`.
- Confirm whether `sensor_configurations.antenna_port` should reference `sensor_antennas.port` or is only a configuration value.
- Confirm whether `campaigns.updated_by`, `sensors.created_by`, and `sensors.updated_by` are intentionally indexed without foreign keys to `users`.
