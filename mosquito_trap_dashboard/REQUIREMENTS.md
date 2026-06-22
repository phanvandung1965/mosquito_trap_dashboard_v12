# REQUIREMENTS — Mosquito Trap Dashboard

## 1) Mục tiêu nghiệp vụ
Dashboard giúp theo dõi tổng thể hoạt động bẫy muỗi theo thời gian thực/gần thời gian thực:
- Biết khu vực nào đang có mật độ muỗi cao.
- Biết bẫy nào đang lỗi hoặc cần bảo trì.
- Biết xu hướng tăng/giảm theo ngày, tuần, tháng.
- Hỗ trợ quyết định tái phân bổ bẫy và lịch xử lý thực địa.

## 2) Nhóm người dùng
- Quản lý chương trình kiểm soát muỗi.
- Nhân viên vận hành hiện trường.
- Lãnh đạo địa phương/ban y tế cộng đồng.

## 3) Câu hỏi chính cần trả lời
1. Hôm nay có bao nhiêu bẫy đang hoạt động/lỗi/bảo trì?
2. Khu vực nào có số muỗi ghi nhận cao nhất?
3. 7 ngày gần nhất xu hướng muỗi tăng hay giảm?
4. Bẫy nào có hiệu suất thấp bất thường?
5. Khu vực nào cần ưu tiên can thiệp trong 24–72h?

## 4) KPI chính
- Total Traps
- Active Traps
- Trap Uptime (%)
- Total Mosquito Count (Today / 7d / 30d)
- Avg Mosquito per Active Trap
- Hotspot Areas (Top N)
- Alert Count (trap offline, spike muỗi)

## 5) Phạm vi MVP
- Data import từ CSV/Google Sheet/API nội bộ.
- Bộ lọc: thời gian, khu vực, trạng thái bẫy.
- 1 trang tổng quan + 1 trang chi tiết bẫy + 1 trang khu vực.
- Bản đồ điểm đặt bẫy + heatmap mật độ muỗi.
- Cảnh báo rule-based đơn giản.

## 6) Ngoài phạm vi MVP (phase sau)
- Dự báo mật độ muỗi (forecast/ML).
- Tối ưu lịch điều phối đội hiện trường.
- Cảnh báo đa kênh Telegram/Zalo/SMS tự động theo ngưỡng thông minh.
