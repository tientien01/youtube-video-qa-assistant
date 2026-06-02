# Ghi chú hoàn thiện MVP

## Đã làm

- Hoàn thiện backend FastAPI cho luồng RAG MVP:
  - `POST /api/v1/videos/ingest` lấy transcript, chia chunk và lưu index local.
  - `POST /api/v1/chat/ask` truy hồi chunk liên quan và trả lời kèm timestamp.
  - Thêm schema chat, service chunking, local retriever, generation service và test cơ bản.
- Hoàn thiện frontend React:
  - Form nhập URL YouTube.
  - Hiển thị video embed và metadata ingest.
  - Chat UI để đặt câu hỏi, xem câu trả lời và mở timestamp nguồn trên YouTube.
- Thêm notebook bài giảng tại `notebooks/rag_src_code_lecture.ipynb`.

## Cách chạy backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Backend chạy tại:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Cách chạy frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend chạy tại:

```text
http://127.0.0.1:5173
```

## Cách sử dụng

1. Chạy backend.
2. Chạy frontend.
3. Dán URL YouTube có transcript vào form.
4. Chờ trạng thái ingest là `ready`.
5. Nhập câu hỏi trong khung hỏi đáp.
6. Bấm timestamp trong phần nguồn để mở đúng đoạn video trên YouTube.

## Lưu ý kỹ thuật

- MVP hiện dùng local BM25-style retriever để chạy được không cần API key.
- Index runtime được lưu tại `backend/data/vector_store/local_rag_index.json`.
- Có thể thay `backend/app/services/rag/local_store.py` bằng ChromaDB/OpenAI embeddings sau này mà không cần đổi API contract.

## Kiểm thử

Từ thư mục gốc dự án:

```powershell
$env:PYTHONPATH="backend"
python -m unittest discover backend/tests
```

Build frontend:

```powershell
cd frontend
npm run build
```
