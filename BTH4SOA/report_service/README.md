# BTH5 Report Service

Dịch vụ báo cáo độc lập, chạy cổng `8003`, database PostgreSQL riêng `report_db` (host port `5434`). Dịch vụ gọi API của Auth, Order và Product Service; không truy cập trực tiếp database của các dịch vụ đó.

## Khởi chạy

1. Chạy Docker Desktop, tại thư mục gốc BTH4:

   ```powershell
   docker compose up -d order-db report-db
   ```

2. Cài package và migrate các database. Product Service phải được migrate sau khi bổ sung `cost_price`:

   ```powershell
   # BTH3 Product Service
   cd D:\BTH3SOA\BTH3DIJANGO
   .\venv\Scripts\python.exe manage.py migrate

   # BTH4 Order Service
   cd D:\BTH4DIJANGO\BTH4SOA
   .\.venv\Scripts\python.exe manage.py migrate

   # BTH5 Report Service
   cd .\report_service
   ..\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ..\.venv\Scripts\python.exe manage.py migrate
   ..\.venv\Scripts\python.exe manage.py runserver 8003
   ```

3. Chạy Auth Service bài 2 ở cổng `8000`, Product Service bài 3 ở cổng `8001`, Order Service bài 4 ở cổng `8002`. Điền `cost_price` cho sản phẩm để báo cáo lợi nhuận đầy đủ.

Import `postman/Report-Service.postman_collection.json` và `postman/Report-Service.postman_environment.json`, nhập username/password bài 2, chạy request đăng nhập trước rồi gọi ba request báo cáo.

## API

Tất cả endpoint cần `Authorization: Bearer <token>` hợp lệ từ Auth Service.

| Endpoint | Nội dung |
|---|---|
| `GET /reports/summary` | Tổng tồn kho hiện tại, số lượng bán, doanh thu, giá vốn hàng bán, lợi nhuận |
| `GET /reports/products` | Các chỉ số theo sản phẩm |
| `GET /reports/orders` | Các chỉ số theo đơn hàng |
| `POST /reports/snapshots` | Tạo và lưu snapshot tổng quan vào `report_db` |
| `GET /reports/snapshots` | Xem tối đa 100 snapshot gần nhất |

Có thể lọc khoảng ngày với `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`. Doanh thu, giá vốn và lợi nhuận chỉ tính đơn `completed`; tồn kho là tồn kho hiện tại. Ở đây, chi phí nghĩa là giá vốn của hàng đã bán. Đơn cũ không có snapshot giá vốn trả `cost: null` và `profit: null` để tránh thể hiện số liệu sai. Báo cáo được tổng hợp trực tiếp từ API nguồn; request POST snapshot sẽ lưu kết quả vào `report_db`.
