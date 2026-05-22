
# Distributed Doc Edit – Vector Clocks for Conflict Detection

Hệ thống API mô phỏng chỉnh sửa tài liệu phân tán (multi-master), sử dụng **Vector Clock** để phát hiện conflict nhân quả giữa các cập nhật từ nhiều site.

## 🚀 Tính năng chính

- Tạo, đọc, cập nhật các fragment văn bản kèm vector clock.
- So sánh hai vector clock → phân loại `CAUSAL`, `CONCURRENT`, `EQUAL`.
- Phân tích toàn bộ document: liệt kê các cặp concurrent (conflict) và causal.
- Giao diện web trực quan hiển thị conflict bằng màu sắc.
- Script tự động tạo kịch bản conflict (`demo_conflict.py`).

## 🛠 Công nghệ sử dụng

- **Backend**: FastAPI (Python)
- **Vector Clock**: Class tự implement trong `app/vector_clock.py`
- **Lưu trữ**: In-memory (danh sách các fragment, có thể mở rộng với database)
- **Deployment**: Docker, docker-compose hoặc chạy trực tiếp với uvicorn

## 📦 Cài đặt và chạy

### Yêu cầu
- Python 3.8+
- pip

### Các bước

1. Clone repository:
   ```bash
   git clone <repo-url>
   cd distributed-doc-edit
   ```

2. Cài đặt dependencies:
   ```bash
   pip install fastapi uvicorn requests
   ```

3. Khởi động server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Hoặc dùng Docker:
   ```bash
   docker-compose up
   ```

4. Truy cập Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

5. Tạo dữ liệu mẫu:
   ```bash
   python seed_demo.py
   ```

6. Chạy kịch bản conflict tự động:
   ```bash
   python demo_conflict.py
   ```

7. Xem giao diện demo: [http://localhost:8000/demo/demo_doc](http://localhost:8000/demo/demo_doc)
