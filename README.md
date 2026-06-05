# YouTube Video Q&A Assistant

Ứng dụng full-stack giúp người dùng hỏi đáp trên transcript video YouTube. Backend lấy transcript, chia chunk, tạo index local và trả lời câu hỏi kèm timestamp nguồn. Frontend hiển thị video, trạng thái ingest và khu vực hỏi đáp.

## Trạng thái hiện tại

MVP hiện có:

- Backend FastAPI.
- Frontend React + Vite.
- Parse URL YouTube.
- Lấy transcript bằng `youtube-transcript-api`.
- Chunk transcript có timestamp.
- Lưu RAG index local bằng JSON.
- Retrieval baseline theo BM25-style lexical search.
- Retrieval modes: `bm25`, `embedding`, `hybrid`.
- Endpoint `/api/v1/videos/ingest`.
- Endpoint `/api/v1/chat/ask`.
- Frontend ingest video, chat và hiển thị sources timestamp.

## Setup backend

Chạy trong thư mục `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Chạy backend:

```powershell
uvicorn app.main:app --reload
```

Backend mặc định chạy tại:

```text
http://127.0.0.1:8000
```

Kiểm tra health endpoint:

```text
GET http://127.0.0.1:8000/api/v1/health
```

## Setup frontend

Chạy trong thư mục `frontend`:

```powershell
npm install
npm run dev
```

Frontend mặc định chạy tại:

```text
http://localhost:5173
```

## Chạy test backend

Sau khi đã activate virtual environment trong `backend`:

```powershell
python -m unittest discover -s tests
```

## Lưu ý dữ liệu và bảo mật

- Không commit `.env`, `.env.*`, secret, credential hoặc API key.
- Không commit `backend/data/`, vì đây là dữ liệu runtime như local RAG index hoặc vector store.
- Không đưa logic production vào notebook. Khi thử nghiệm ổn, chuyển logic vào `backend/app/services/`.

## Lộ trình gần nhất

Trước khi qua Phase 1, cần đảm bảo Phase 0 ổn:

- Backend tests chạy được.
- API lỗi cơ bản rõ ràng.
- Logging cơ bản cho ingest và ask.
- Baseline BM25 đủ ổn để so sánh với semantic/hybrid RAG sau này.

Phase kỹ thuật RAG hiện đã có semantic retrieval baseline:

- Local hashing embedding.
- Local vector store bằng JSON.
- Hybrid retrieval kết hợp BM25 và embedding score.
