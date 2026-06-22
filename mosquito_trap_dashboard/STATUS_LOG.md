# STATUS LOG

## 2026-03-27
- Trạng thái: **Hoàn thành nâng cấp pipeline v5.1 (Star Schema + SQLite)**
- Mô tả: Bổ sung bước nạp star schema vào SQLite, cập nhật tài liệu dữ liệu và kiểm thử pipeline end-to-end thành công.
- Đã hoàn thành:
  - Tích hợp `load_star_schema_to_sqlite.py` vào `run_pipeline.sh` sau bước ETL.
  - Sửa lỗi cú pháp f-string trong `load_star_schema_to_sqlite.py` để nạp dữ liệu ổn định.
  - Chạy lại pipeline thành công với đầy đủ các bước: ETL -> Load SQLite -> KPI -> Generate Dashboard.
  - Xác nhận DB đích: `data/mosquito_trap_dashboard.db` có dữ liệu ở tất cả bảng dim/fact.
  - Cập nhật tài liệu:
    - `runbook.md` (thêm bước `load_to_sqlite` trong pipeline chuẩn)
    - `DATA_MODEL.md` (mô tả star schema đầy đủ)
    - `ETL_MAPPING.md` (chuẩn hóa mapping raw -> star schema -> SQLite)
- Kết quả kiểm thử gần nhất:
  - `dim_date`: 10 rows
  - `dim_area`: 3 rows
  - `dim_trap`: 4 rows
  - `dim_status`: 3 rows
  - `fact_observation`: 6 rows
  - `fact_trap_health`: 4 rows
  - `fact_alert`: 1 rows

## 2026-03-24
- Trạng thái: **Hoàn thành**
- Mô tả: Dự án đã hoàn thành tất cả các yêu cầu về chức năng và giao diện người dùng. Phiên bản cuối cùng là `dashboard_v9.html`.
- Đã hoàn thành trong phiên gần nhất:
  - **Cải tiến UI/UX:**
    - `dashboard_v8.html`: Bổ sung chỉ báo sắp xếp (mũi tên lên/xuống và làm nổi bật cột) trên tiêu đề bảng để cải thiện trải nghiệm người dùng.
  - **Chức năng chính:**
    - `dashboard_v9.html`: Thêm chức năng cho phép người dùng tải xuống các biểu đồ (đường và cột) dưới dạng file ảnh PNG.
- Tổng kết các chức năng đã hoàn thành:
  - [x] Tải và phân tích dữ liệu từ `tracking_view.csv`.
  - [x] Hiển thị các chỉ số KPI chính (Tổng muỗi, Số bản ghi, Khu vực, Bẫy).
  - [x] Lọc dữ liệu theo nhiều chiều (Ngày, Khu vực, Bẫy, Tên muỗi) và tìm kiếm tự do.
  - [x] Sắp xếp dữ liệu trong bảng theo từng cột, có chỉ báo trực quan.
  - [x] Trực quan hóa dữ liệu qua biểu đồ đường (xu hướng theo thời gian) và biểu đồ cột (tổng số theo khu vực).
  - [x] Xuất dữ liệu đã được lọc ra file CSV.
  - [x] Xuất các biểu đồ ra file ảnh PNG.
- File bàn giao cuối cùng:
  - `dashboard_v9.html`
  - `tracking_view.csv`
  - `STATUS_LOG.md`

## 2026-03-24
- Trạng thái: **Hoàn thành**
- Mô tả: Dự án đã hoàn thành tất cả các yêu cầu về chức năng và giao diện người dùng. Phiên bản cuối cùng là `dashboard_v9.html`.
- Đã hoàn thành trong phiên gần nhất:
  - **Cải tiến UI/UX:**
    - `dashboard_v8.html`: Bổ sung chỉ báo sắp xếp (mũi tên lên/xuống và làm nổi bật cột) trên tiêu đề bảng để cải thiện trải nghiệm người dùng.
  - **Chức năng chính:**
    - `dashboard_v9.html`: Thêm chức năng cho phép người dùng tải xuống các biểu đồ (đường và cột) dưới dạng file ảnh PNG.
- Tổng kết các chức năng đã hoàn thành:
  - [x] Tải và phân tích dữ liệu từ `tracking_view.csv`.
  - [x] Hiển thị các chỉ số KPI chính (Tổng muỗi, Số bản ghi, Khu vực, Bẫy).
  - [x] Lọc dữ liệu theo nhiều chiều (Ngày, Khu vực, Bẫy, Tên muỗi) và tìm kiếm tự do.
  - [x] Sắp xếp dữ liệu trong bảng theo từng cột, có chỉ báo trực quan.
  - [x] Trực quan hóa dữ liệu qua biểu đồ đường (xu hướng theo thời gian) và biểu đồ cột (tổng số theo khu vực).
  - [x] Xuất dữ liệu đã được lọc ra file CSV.
  - [x] Xuất các biểu đồ ra file ảnh PNG.
- File bàn giao cuối cùng:
  - `dashboard_v9.html`
  - `tracking_view.csv`
  - `STATUS_LOG.md`
