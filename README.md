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
- Optional semantic retrieval stack với `sentence-transformers`, ChromaDB và reranking.
- Optional LLM grounded answer với Gemini API.
- Fallback extractive answer khi chưa cấu hình API key.
- Summary fallback theo các mode `short`, `detailed`, `timeline`.
- Study notes fallback từ transcript chunks.
- Quiz fallback từ transcript chunks với đáp án, explanation và timestamp source.
- Export Markdown từ video metadata, summary, study notes, quiz và timestamp sources.
- RAG Debug View để xem retrieved chunks, scores và latency.
- Evaluation runner nhỏ để so sánh retrieval modes.
- Chat history theo từng video bằng localStorage.
- Workspace dạng tabs cho Chat, Summary, Notes, Quiz, Export và Debug.
- Export selected Q&A từ lịch sử chat.
- Endpoint `/api/v1/videos/ingest`.
- Endpoint `/api/v1/chat/ask`.
- Endpoint `/api/v1/videos/{video_id}/summary`.
- Endpoint `/api/v1/videos/{video_id}/study-notes`.
- Endpoint `/api/v1/videos/{video_id}/quiz`.
- Endpoint `/api/v1/debug/retrieve`.
- Frontend ingest video, tạo summary, study notes, quiz, export Markdown, RAG debug, chat history theo video và hiển thị sources timestamp.

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

## Optional LLM config

App vẫn chạy được khi không có API key. Khi chưa cấu hình LLM, backend dùng fallback extractive answer từ retrieved chunks.

Backend tự load `backend/.env` cho local development nếu file này tồn tại. Khi deploy, cấu hình các biến này bằng environment variables hoặc secret manager của nền tảng deploy.

Mặc định có thể để:

```powershell
$env:LLM_PROVIDER="fallback"
```

Nếu muốn bật Gemini grounded answer, set environment variables trước khi chạy backend hoặc cấu hình tương đương trong `backend/.env`:

```powershell
$env:LLM_PROVIDER="gemini"
$env:GEMINI_API_KEY="your-api-key"
$env:GEMINI_MODEL="gemini-2.5-flash"
$env:LLM_TIMEOUT_SECONDS="20"
```

Không commit API key hoặc file `.env`.

## Optional semantic retrieval config

Mặc định backend vẫn dùng hashing embedding và local JSON vector store để chạy nhẹ, ổn định và không cần tải model.

Nếu muốn bật Phase I semantic retrieval stack, cài lại backend dependencies rồi set environment variables trước khi chạy backend:

```powershell
$env:EMBEDDING_PROVIDER="sentence_transformers"
$env:EMBEDDING_MODEL_NAME="all-MiniLM-L6-v2"
$env:VECTOR_STORE_PROVIDER="chroma"
$env:CHROMA_PERSIST_DIR="data/vector_store/chroma"
$env:RERANKER_ENABLED="true"
$env:RERANK_TOP_K="12"
```

BM25 vẫn được giữ làm baseline và `hybrid` vẫn kết hợp lexical retrieval với vector retrieval. ChromaDB lưu dữ liệu trong `backend/data/`, không commit thư mục này.

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

Trạng thái hiện tại đã qua MVP nền, video history/cache ingest, hybrid retrieval baseline, optional LLM, summary, study notes, quiz, Export Markdown, RAG Debug View, evaluation runner baseline và Better Study Experience frontend. Thứ tự phát triển tiếp theo:

- Phase I: Nâng cấp semantic retrieval nếu evaluation cho thấy cần.
- Phase J: Agentic AI learning assistant.

Phase kỹ thuật RAG hiện có retrieval baseline:

- Local hashing embedding.
- Local vector store bằng JSON.
- Optional sentence-transformers embedding adapter.
- Optional ChromaDB vector store adapter.
- Optional lexical reranking.
- Hybrid retrieval kết hợp BM25 và embedding score.
