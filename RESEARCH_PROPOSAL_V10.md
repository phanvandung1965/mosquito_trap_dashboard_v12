# Mosquito Trap Dashboard V10 - Research Proposal

## 1. Phân tích hiện trạng (V9.01)

### Frontend (`dashboard_v9.01.html`)
- **Tải thư viện**: Đang sử dụng CDN (jsdelivr, unpkg) cho Chart.js, date-fns, Leaflet, Leaflet.markercluster. Việc này khiến dashboard phụ thuộc vào tốc độ mạng bên ngoài và có thể bị chậm/fail nếu CDN gặp sự cố hoặc tải trong môi trường mạng kín.
- **Xử lý dữ liệu**:
  - Load toàn bộ dữ liệu qua API `/api/data` trong một lần (có thể là dung lượng lớn).
  - Trình duyệt phải phân tích chuỗi JSON, ánh xạ lại trường dữ liệu (`mapAPIDataToDashboard`), và giữ toàn bộ dữ liệu trong bộ nhớ.
  - Các thao tác filter, sort, tính toán KPI, gộp nhóm (aggregateBySpecies) và chuẩn bị dữ liệu cho chart/map đều diễn ra ở client-side (trình duyệt). Điều này gây gánh nặng cho thiết bị di động hoặc máy tính cấu hình thấp khi tập dữ liệu lớn.
- **Render UI**:
  - Bảng hiển thị render lại toàn bộ hàng qua DOM manipulation mỗi khi sort/filter, điều này kém hiệu quả.
  - Map sử dụng MarkerCluster để gom nhóm, đây là điểm tốt cho tập dữ liệu lớn nhưng việc truyền toàn bộ dữ liệu điểm xuống client vẫn tốn kém.

### Backend (`api_server.py`)
- **Kiến trúc**: Flask application, dùng SQLite.
- **Truy vấn**:
  - Dữ liệu được lấy toàn bộ từ bảng `raw_data` và trả về một mảng JSON.
  - Có cơ chế cache in-memory (`_api_cache`) kết quả nén gzip, giúp giảm tải CPU khi có nhiều request lấy cùng một dữ liệu.
  - Tuy nhiên, cache này là cache cứng (toàn bộ payload), không hỗ trợ server-side pagination (phân trang), filtering hay sorting ở server.
- **Điểm yếu**:
  - Nếu dữ liệu tiếp tục tăng, payload trả về sẽ quá lớn (dù đã nén) và làm nghẽn băng thông, đồng thời gây tràn bộ nhớ trình duyệt client.
  - Chưa tận dụng được sức mạnh query của SQLite (WHERE, GROUP BY, LIMIT/OFFSET) để xử lý dữ liệu động.

---

## 2. Đề xuất giải pháp nâng cấp (Phase 3 - V10)

### Giải pháp 1: Tự host (Self-host) CDN JS/CSS
- **Hành động**: Tải các thư viện tĩnh (Chart.js, Leaflet, MarkerCluster) về lưu cục bộ trong thư mục tĩnh (`static/` hoặc tương đương) của dự án.
- **Lợi ích**:
  - Giảm phụ thuộc vào kết nối Internet tới CDN ngoài.
  - Cải thiện tốc độ load ban đầu (đặc biệt khi chạy ở local hoặc mạng intranet).
  - Tăng tính bảo mật và ổn định.

### Giải pháp 2: Chuyển đổi sang Server-side Processing (Filtering/Pagination)
- **Hành động**:
  - Sửa đổi API backend để nhận các tham số (ví dụ: `?area=X&trap=Y&page=1&limit=50`).
  - Sử dụng SQLite để thực hiện các thao tác:
    - Filter bằng clause `WHERE`.
    - Tính KPI/Summary bằng `COUNT`, `SUM`, `GROUP BY` trực tiếp trên database và trả về kết quả đã tổng hợp.
    - Phân trang cho bảng hiển thị (dùng `LIMIT` và `OFFSET`).
- **Lợi ích**:
  - Giảm kích thước payload trả về từ MBs xuống vài chục/trăm KBs.
  - Giảm thiểu hoàn toàn tình trạng treo trình duyệt khi xử lý mảng lớn.
  - Xử lý mượt mà ngay cả khi dữ liệu lên tới hàng triệu record.

### Giải pháp 3: Tối ưu hoá Map Render và Data Visualization
- **Hành động**:
  - Áp dụng kỹ thuật Geo-spatial clustering ở backend (nếu có thể, sử dụng ST_Cluster hoặc các phép gom nhóm theo Grid/Geohash) thay vì đẩy hết xuống client và dùng Leaflet.markercluster xử lý.
  - Hoặc, chỉ trả về các marker nằm trong bounding box hiện tại của bản đồ (`?bbox=...`). Khi người dùng zoom/pan, gọi API lấy điểm mới.
  - Cập nhật các biểu đồ: Giao việc tính toán dữ liệu chart (GROUP BY ngày, GROUP BY khu vực) cho SQLite, client chỉ nhận mảng kết quả cuối cùng để vẽ Chart.js.
- **Lợi ích**:
  - Map render tức thời.
  - API sẽ chỉ trả về số lượng điểm rất nhỏ cần hiển thị trên viewport hiện tại, tiết kiệm băng thông tối đa.

### Giải pháp 4: Cải tiến UI/UX Table
- **Hành động**: Thay thế cách render DOM thủ công (`tr.innerHTML = ...`) bằng các thư viện Virtual DOM/DataGrid nhẹ (như Tabulator, Grid.js) hoặc giữ nguyên vanilla JS nhưng chỉ render dữ liệu của trang hiện tại (pagination view).

---

## 3. Lộ trình thực hiện dự kiến
1. **Bước 1**: Viết script download các asset từ CDN về thư mục `static/` và cập nhật đường dẫn trong thẻ `<script>`/`<link>` của `dashboard.html`.
2. **Bước 2**: Viết lại `api_server.py`:
   - Thêm endpoints `/api/kpi`, `/api/chart/bar`, `/api/chart/line`, `/api/table`.
   - Viết các câu query SQLite có hỗ trợ tham số linh hoạt.
3. **Bước 3**: Cập nhật file HTML (`dashboard_v10.html`):
   - Thay đổi logic `getFiltered()` hiện tại thành gọi API `fetch(...)` bất đồng bộ với query params.
   - Thêm UI phân trang (Prev/Next buttons) cho table.
4. **Bước 4**: Thêm tính năng Bounding Box filter cho map (tuỳ chọn nâng cao).
5. **Bước 5**: Test hiệu năng và release V10.