# ANE DB TimescaleDB Hypertables

Captured source:

```sql
SELECT hypertable_name FROM timescaledb_information.hypertables;
```

Result:

| Hypertable | Status |
| --- | --- |
| sensor_status | Confirmed |

## Captured Table Details

Visible from `\d+ public.sensor_status` output:

| Item | Value |
| --- | --- |
| Time-like indexed column | `timestamp_ms` |
| ID column | `id bigint NOT NULL DEFAULT nextval('sensor_status_id_seq'::regclass)` |
| Visible chunk | `_timescaledb_internal._hyper_26_2_chunk` |
| Index | `idx_sensor_status_mac` on `mac` |
| Index | `idx_sensor_status_mac_timestamp` on `mac, timestamp_ms DESC` |
| Index | `idx_sensor_status_timestamp` on `timestamp_ms DESC` |
| Index | `sensor_status_timestamp_ms_idx` on `timestamp_ms DESC` |

## Dimensions

Source:

```sql
SELECT *
FROM timescaledb_information.dimensions
ORDER BY hypertable_schema, hypertable_name, dimension_number;
```

Result:

| Hypertable schema | Hypertable name | Dimension number | Column name | Column type | Dimension type | Time interval | Integer interval | Integer now func | Num partitions |
| --- | --- | ---: | --- | --- | --- | --- | ---: | --- | --- |
| public | sensor_status | 1 | timestamp_ms | bigint | Time | | 86400000000 | | |

Notes:

- `timestamp_ms` is confirmed as the TimescaleDB time dimension.
- `integer_interval = 86400000000` is 86,400,000,000 milliseconds, which is 1,000 days if `timestamp_ms` is epoch milliseconds, or 1 day if `timestamp_ms` is epoch microseconds. Confirm the actual unit used by ingested data before recreating the hypertable.

## Pending Details

Capture the full TimescaleDB metadata next:

```sql
SELECT *
FROM timescaledb_information.hypertables
ORDER BY hypertable_schema, hypertable_name;
```

Useful follow-up queries:

```sql
SELECT *
FROM timescaledb_information.dimensions
WHERE hypertable_name = 'sensor_status';

SELECT *
FROM timescaledb_information.chunks
WHERE hypertable_name = 'sensor_status'
ORDER BY range_start DESC
LIMIT 20;
```

Modeling note: `sensor_status` should be treated differently from normal relational tables in the new design because it is partitioned by TimescaleDB. Its primary time column is confirmed as `timestamp_ms`. Retention, compression policies, background jobs, and whether it intentionally has no primary key still need to be captured.
