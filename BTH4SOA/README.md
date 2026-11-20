# Order Management Service — Bài thực hành 4

Dịch vụ Django REST Framework độc lập, lắng nghe cổng `8002`, dùng database PostgreSQL `order_db` riêng. Service xác thực Bearer JWT bằng endpoint `POST /auth/` của bài 2 và kiểm tra tên, giá, tồn kho qua Product Service.

## 1. Chạy PostgreSQL

Cần Docker Desktop đang chạy. Tại thư mục `order_service`:

```powershell
docker compose up -d
```

PostgreSQL trong compose được ánh xạ sang `127.0.0.1:5433`, tách biệt với database của bài 2.

## 2. Cấu hình và khởi chạy Django

Mở terminal tại `D:\BTH2DIJANGO\django_project\order_service`:

```powershell
..\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Mặc định service dùng cấu hình trong `settings.py`; nếu thông tin DB/service khác thì đặt biến môi trường trước khi chạy:

```powershell
$env:DB_NAME="order_db"
$env:DB_USER="postgres"
$env:DB_PASSWORD="123456"
$env:DB_HOST="127.0.0.1"
$env:DB_PORT="5433"
$env:AUTH_SERVICE_URL="http://127.0.0.1:8000/auth/"
$env:PRODUCT_SERVICE_URL="http://127.0.0.1:8001/products/{id}/"
python manage.py migrate
python manage.py runserver 8002
```

Bài 2 phải chạy ở cổng `8000`. `PRODUCT_SERVICE_URL` cần trả JSON có `id`, `name`, `price`, `quantity` (có thể nằm trong object `product`); service gửi tiếp Bearer token sang Product Service. Ví dụ URL mặc định `/products/{id}/` có thể sửa theo route bài 3. Nếu service sản phẩm dùng `/products/{id}` không có dấu `/` cuối, chỉnh biến URL tương ứng.

## 3. Endpoint

Mọi endpoint yêu cầu header `Authorization: Bearer <token>` hợp lệ từ bài 2.

| Method | Endpoint | Mục đích |
|---|---|---|
| GET, POST | `/orders` | Danh sách / tạo order cùng danh sách `items` |
| GET, PUT, PATCH, DELETE | `/orders/{id}` | Xem, cập nhật riêng `status`, xóa order |
| GET, POST | `/order_items` | Danh sách / thêm item vào order pending |
| GET, PUT, PATCH, DELETE | `/order_items/{id}` | Xem, cập nhật, xóa item |

POST `/orders` nhận ví dụ:

```json
{
  "customer_name": "Nguyen Van A",
  "customer_email": "a@example.com",
  "items": [{"product_id": 1, "quantity": 2}]
}
```

Giá và tên sản phẩm luôn lấy từ Product Service; `total_amount` và `total_price` được tính phía server. Trạng thái hợp lệ: `pending`, `completed`, `cancelled`. Xóa order tự xóa các item liên quan.

## 4. Kiểm tra bằng Postman

Import hai file trong `postman/`: `Order-Management.postman_collection.json` và `Order-Management.postman_environment.json`. Chọn environment, điền `username`, `password` bài 2 và một `productId` còn hàng từ bài 3. Đảm bảo auth, product, PostgreSQL và order service đang chạy. Chạy request `0. Đăng nhập bài 2` trước để lưu token, sau đó chạy tuần tự nhóm `1. Orders` rồi nhóm `2. Order items`. Mỗi request có assertion trong tab **Scripts → Post-response**; có thể chạy cả collection bằng Collection Runner.

Các giá trị mặc định của database phục vụ môi trường thực hành local. Không dùng mật khẩu mẫu và `SECRET_KEY` mặc định khi triển khai thật.
