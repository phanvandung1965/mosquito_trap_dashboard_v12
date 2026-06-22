# ETL Mapping (Raw -> Star Schema)

## Inputs
- `sample_data_areas.csv`
- `sample_data_traps.csv`
- `sample_data_observation.csv`
- `alerts_snapshot.json`

## Mapping chính

### dim_date
- Được tạo từ tất cả các ngày duy nhất có trong `observed_at` của `sample_data_observation.csv`, `install_date`/`last_maintenance_at` của `sample_data_traps.csv`, và `alert_time` của `alerts_snapshot.json`.
- Các thuộc tính ngày/tháng/năm/quý/tuần/thứ trong tuần được tính toán từ trường ngày.

### dim_area
- `area_id` -> `area_id`, `AreaKey` (PK được tạo)
- `area_name` -> `area_name`
- `district` -> `district`
- `ward` -> `ward`
- `latitude/longitude` -> `latitude/longitude`
- `risk_level` -> `risk_level`

### dim_trap
- `trap_id` -> `trap_id`, `TrapKey` (PK được tạo)
- `trap_code` -> `trap_code`
- `area_id` -> `AreaKey` (FK, lookup qua dim_area)
- `install_date` -> `install_date`
- `trap_type` -> `trap_type`
- `status` -> `current_status`
- `last_maintenance_at` -> `last_maintenance_at`
- `battery_level` -> `battery_level`

### dim_status
- Được tạo từ các giá trị `status` duy nhất trong `sample_data_traps.csv`.
- `StatusKey` (PK được tạo) và `status_name`.

### fact_observation
- `observed_at` -> `observed_at`, `DateKey` (FK, lookup qua dim_date)
- `trap_id` -> `TrapKey` (FK, lookup qua dim_trap)
- `AreaKey` (FK, lookup ngược qua dim_trap)
- `mosquito_count` -> `mosquito_count`
- `species` -> `species`
- `temperature_c/humidity_pct/rainfall_mm` -> giữ nguyên

### fact_trap_health
- Từ `sample_data_traps.csv` (dựa trên `last_maintenance_at` hoặc `datetime.now()`)
- `last_maintenance_at` -> `check_time`, `DateKey` (FK, lookup qua dim_date)
- `area_id` -> `AreaKey` (FK, lookup qua dim_area)
- `trap_id` -> `TrapKey` (FK, lookup qua dim_trap)
- `status` -> `StatusKey` (FK, lookup qua dim_status)
- `battery_level` -> `battery_level`
- `signal_strength` -> (hiện tại trống, có thể mở rộng từ nguồn dữ liệu thô nếu có)
- `error_code` -> (hiện tại trống, có thể mở rộng từ nguồn dữ liệu thô nếu có)

### fact_alert
- Từ `alerts_snapshot.json`
- `alert_time` -> `alert_time`, `DateKey` (FK, lookup qua dim_date)
- `area_id` -> `AreaKey` (FK, lookup qua dim_area)
- `trap_id` -> `TrapKey` (FK, lookup qua dim_trap)
- `alert_type/severity/message` -> giữ nguyên
- `resolved/resolved_at` -> giữ nguyên (mặc định `false` và rỗng)

## Output
Thư mục xuất: `star_schema_output/`
- dim_date.csv
- dim_area.csv
- dim_trap.csv
- dim_status.csv
- fact_observation.csv
- fact_trap_health.csv
- fact_alert.csv
- etl_summary.json

## Cơ sở dữ liệu đích
- `data/mosquito_trap_dashboard.db` (SQLite)
