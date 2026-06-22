# WIREFRAME (theo phong cách Power BI tham chiếu)

## Page 1 — Executive Overview
- Header: Tên dashboard + thời gian cập nhật + bộ lọc toàn cục.
- KPI cards (hàng 1): Total Traps, Active, Offline, Total Mosquito Today, 7-day Avg.
- Left panel: Filter (date range, area, trap status, trap type).
- Main panel:
  - Map + heat layer theo area/trap point.
  - Line chart: xu hướng mosquito_count theo ngày.
  - Bar chart: Top 10 khu vực mật độ cao.
  - Alert table: cảnh báo mới nhất.

## Page 2 — Trap Detail
- Trap selector + metadata (vị trí, ngày lắp, trạng thái, pin).
- Trend chart theo trap (24h/7d/30d).
- Health chart (battery, signal, downtime).
- Event timeline (maintenance + alert history).

## Page 3 — Area Monitoring
- Ranking area theo mức rủi ro.
- So sánh area-to-area (bar/boxplot).
- Contribution chart: area nào đóng góp nhiều nhất vào tổng muỗi.
- SLA vận hành theo area: thời gian xử lý cảnh báo trung bình.

## UI/UX nguyên tắc
- Ưu tiên nền sáng, màu cảnh báo rõ (vàng/đỏ).
- Số liệu quan trọng luôn ở vị trí đầu trang.
- Filter nhất quán giữa các trang.
- Tooltip giải thích chỉ số và ngưỡng cảnh báo.
