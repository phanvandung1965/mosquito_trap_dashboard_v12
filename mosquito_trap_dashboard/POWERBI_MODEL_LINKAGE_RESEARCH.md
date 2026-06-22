# Nghiên cứu mô hình tổ chức liên kết dữ liệu (theo cách Power BI report thường áp dụng)

## 0) Ghi chú truy cập
Liên kết Power BI đã được thử truy cập tự động để đọc metadata nhưng môi trường hiện tại không có browser khả dụng và không đọc trực tiếp được model nội bộ report qua web fetch. Vì vậy tài liệu này tổng hợp theo:
- Mẫu tổ chức dữ liệu chuẩn của Power BI (star schema + semantic model)
- Đối chiếu với cấu trúc dashboard bẫy muỗi đang triển khai
- Suy luận cách liên kết dữ liệu hợp lý để tái tạo gần nhất mô hình trang tham chiếu

---

## 1) Cấu trúc mô hình dữ liệu mà Power BI thường dùng

### 1.1 Star schema (khuyến nghị và phổ biến)
- **Fact table**: chứa số đo, phát sinh theo thời gian (event/transaction).
- **Dimension table**: chứa thuộc tính mô tả để lọc và nhóm.
- Quan hệ chuẩn: `Dimension (1) -> (N) Fact`, filter direction thường **Single**.

### 1.2 Date dimension trung tâm
Hầu hết report Power BI dùng 1 bảng ngày chuẩn để:
- time intelligence (YTD/MTD/WTD, rolling 7/30 ngày)
- đồng nhất lọc thời gian giữa nhiều fact.

### 1.3 Semantic layer (DAX measures)
Report thường không dùng cột tính trực tiếp trong visual, mà dùng measure:
- `Total`, `Average`, `%Uptime`, `AlertCount`, `Trend`, `TopN`...

---

## 2) Mô hình liên kết dữ liệu đề xuất (áp dụng cho dashboard bẫy muỗi)

## 2.1 Bảng dimension
1. `dim_date`
   - DateKey (PK, yyyymmdd)
   - Date, Year, Quarter, Month, Week, DayOfWeek

2. `dim_area`
   - AreaKey (PK)
   - area_id, area_name, district, ward, lat, lon, risk_level

3. `dim_trap`
   - TrapKey (PK)
   - trap_id, trap_code, area_id/AreaKey, trap_type, install_date, current_status

4. `dim_status` (tuỳ chọn)
   - StatusKey (PK)
   - status_name (active/offline/maintenance)

## 2.2 Bảng fact
1. `fact_observation` (grain: 1 trap tại 1 timestamp)
   - ObservationKey (PK)
   - DateKey, TrapKey, AreaKey
   - observed_at
   - mosquito_count
   - species, temperature, humidity, rainfall (nếu có)

2. `fact_trap_health` (grain: 1 lần health-check/trap)
   - HealthKey
   - DateKey, TrapKey, AreaKey, StatusKey
   - battery_level, signal_strength, downtime_minutes

3. `fact_alert` (grain: 1 alert event)
   - AlertKey
   - DateKey, TrapKey (nullable), AreaKey (nullable)
   - alert_type, severity, resolved_flag, resolve_time

## 2.3 Quan hệ khuyến nghị
- `dim_date[DateKey] (1) -> fact_observation[DateKey] (N)`
- `dim_date[DateKey] (1) -> fact_trap_health[DateKey] (N)`
- `dim_date[DateKey] (1) -> fact_alert[DateKey] (N)`
- `dim_area[AreaKey] (1) -> fact_observation[AreaKey] (N)`
- `dim_area[AreaKey] (1) -> fact_trap_health[AreaKey] (N)`
- `dim_area[AreaKey] (1) -> fact_alert[AreaKey] (N)`
- `dim_trap[TrapKey] (1) -> fact_observation[TrapKey] (N)`
- `dim_trap[TrapKey] (1) -> fact_trap_health[TrapKey] (N)`
- `dim_trap[TrapKey] (1) -> fact_alert[TrapKey] (N)`

**Filter direction:** Single (Dimension -> Fact), chỉ dùng Both khi thật sự cần.

---

## 3) Cách trang Power BI thường tổ chức visual theo model

### 3.1 KPI cards
Nguồn từ measure trên fact:
- Total Traps (count distinct trap)
- Active Traps (lọc status=active)
- Total Mosquito (sum observation)
- Avg/Active Trap

### 3.2 Trend chart theo thời gian
Trục X: `dim_date[Date]` hoặc `fact_observation[observed_at]` đã bucket.
Trục Y: measure tổng muỗi.

### 3.3 Heatmap/Map theo khu vực
- Dùng `dim_area` làm location dimension
- Measure từ `fact_observation` để tô màu và kích thước.

### 3.4 Alert table
Dùng `fact_alert` + dimension area/trap/date để drilldown.

---

## 4) Anti-pattern cần tránh (hay gặp trong report Power BI)
- Nối nhiều bảng fact trực tiếp với nhau (fact-to-fact) gây mơ hồ filter.
- Many-to-many không có bridge table.
- Dùng bi-directional bừa bãi gây sai số KPI.
- Thiếu dim_date chuẩn nên time-intelligence không ổn định.

---

## 5) Blueprint DAX measure (gợi ý)
```DAX
Total Mosquito = SUM(fact_observation[mosquito_count])

Active Traps =
CALCULATE(
    DISTINCTCOUNT(dim_trap[TrapKey]),
    dim_trap[current_status] = "active"
)

Avg Mosquito per Active Trap = DIVIDE([Total Mosquito], [Active Traps], 0)

Offline Alerts =
CALCULATE(
    COUNTROWS(fact_alert),
    fact_alert[alert_type] = "offline"
)
```

---

## 6) Cách kiểm chứng đúng-sai với report tham chiếu (khi có quyền truy cập trực tiếp)
1. Mở report trong Power BI Service/Desktop có quyền chỉnh sửa.
2. Vào **Model view** kiểm tra relationship/cardinality/filter direction.
3. Dùng **Performance Analyzer** xem query visual nào chạm bảng nào.
4. Đối chiếu số KPI card với measure definitions.
5. Chạy test filter chéo area/time/trap để xác nhận propagation đúng.

---

## 7) Kết luận thực thi
Mô hình liên kết dữ liệu mà trang kiểu Power BI nhiều khả năng áp dụng là:
- **Star schema nhiều fact dùng chung dimension Date/Area/Trap**
- **Single direction filtering**
- **Measure-centric semantic model (DAX)**

Đây là kiến trúc tối ưu để tái tạo dashboard tham chiếu cho bài toán bẫy muỗi hiện tại, đồng thời dễ mở rộng forecast/alert/geo trong các phiên bản tiếp theo.
