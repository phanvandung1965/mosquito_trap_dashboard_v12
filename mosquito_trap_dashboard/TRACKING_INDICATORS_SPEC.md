# Tracking Indicators Spec (chuẩn theo yêu cầu)

## Bộ chỉ tiêu theo dõi chính
1. `date` — ngày/giờ ghi nhận
2. `area` — khu vực đặt bẫy
3. `trap` — mã bẫy
4. `mosquito_name` — tên/loài muỗi
5. `number_of_mosquitoes` — số lượng muỗi ghi nhận

## Mapping vào mô hình hiện tại
- `date` <- `fact_observation.observed_at` (hoặc `dim_date.Date` nếu cần mức ngày)
- `area` <- `dim_area.area_name` (key: `AreaKey`)
- `trap` <- `dim_trap.trap_code` (key: `TrapKey`)
- `mosquito_name` <- `fact_observation.species`
- `number_of_mosquitoes` <- `fact_observation.mosquito_count`

## Khuyến nghị hiển thị dashboard
- Filter bắt buộc: `date`, `area`, `trap`, `mosquito_name`
- KPI bắt buộc: `sum(number_of_mosquitoes)`
- Drilldown: `area -> trap -> mosquito_name -> date`

## Chuẩn dữ liệu đề nghị
- `date`: ISO timestamp (`YYYY-MM-DD HH:mm:ss`)
- `area`: text
- `trap`: text (mã duy nhất)
- `mosquito_name`: text (Aedes/Culex/...)
- `number_of_mosquitoes`: integer >= 0
