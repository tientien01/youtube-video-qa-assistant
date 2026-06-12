# YouTube Video Q&A Assistant

YouTube Video Q&A Assistant là ứng dụng hỗ trợ học từ video YouTube. Người dùng dán URL video, hệ thống lấy metadata và transcript, chia transcript thành các đoạn có timestamp, xây dựng index truy xuất, sau đó cung cấp một workspace để hỏi đáp, tóm tắt, tạo ghi chú học tập, tạo quiz, export nội dung và kiểm tra quá trình truy xuất RAG.

Dự án được thiết kế theo hướng MVP dễ chạy local: backend dùng FastAPI, frontend dùng React + Vite, dữ liệu runtime lưu bằng file JSON cục bộ. LLM là tùy chọn. Nếu không cấu hình Gemini, hệ thống vẫn chạy bằng fallback local để demo và kiểm thử luồng chính.

## Tính năng chính

- Ingest video YouTube từ URL.
- Lấy metadata, transcript và chia transcript thành các chunk có timestamp.
- Lưu danh sách video, transcript chunk, lịch sử chat, kết quả sinh nội dung và quiz attempt ở local.
- Hỏi đáp theo nội dung video bằng RAG với nguồn dẫn timestamp.
- Hỗ trợ các chế độ retrieval: `bm25`, `embedding`, `hybrid`.
- Tạo tóm tắt video theo chế độ `short`, `detailed`, `timeline`.
- Tạo study notes theo nhiều chế độ như `concise`, `detailed`, `timeline`, `exam_review`, `beginner`, `flashcards`, `concept_map`.
- Tạo quiz với nhiều độ khó, kiểu câu hỏi và chế độ luyện tập.
- Export nội dung học tập ra Markdown từ chat, summary, notes và quiz.
- Debug retrieval để xem chunk nào được chọn, điểm truy xuất và độ trễ.
- Tự fallback khi LLM chưa cấu hình, lỗi quota, timeout hoặc phản hồi không hợp lệ.

## Kiến trúc tổng quan

Luồng chính của hệ thống:

```text
Frontend React/Vite
-> FastAPI API routes
-> Pydantic schemas
-> Service layer
-> Local stores / vector store / optional Gemini
-> Response có sources, metadata và generation status
-> Learning workspace trên frontend
```

Khi người dùng ingest một video:

```text
YouTube URL
-> parse video_id
-> lấy metadata
-> lấy transcript
-> clean transcript
-> chia transcript thành chunk có timestamp
-> lưu metadata và chunks
-> build retrieval index
-> trả kết quả cho frontend
```

Khi người dùng hỏi hoặc sinh nội dung:

```text
video_id + yêu cầu người dùng
-> chọn transcript chunks phù hợp
-> compact context
-> gọi Gemini nếu được cấu hình
-> fallback local nếu LLM không khả dụng
-> trả answer/summary/notes/quiz kèm nguồn timestamp
```

## Công nghệ sử dụng

Backend:

- Python 3.11+
- FastAPI
- Pydantic
- youtube-transcript-api
- yt-dlp
- httpx, requests
- ChromaDB tùy chọn
- sentence-transformers tùy chọn
- Gemini API tùy chọn

Frontend:

- Node.js 20+
- React
- Vite
- ESLint

Lưu trữ runtime:

- Local JSON store cho metadata, chunks, chat history, generated outputs và quiz attempts.
- Local JSON vector store mặc định.
- Chroma vector store tùy chọn.

## Cấu trúc thư mục

```text
.
+-- backend/
|   +-- app/
|   |   +-- api/
|   |   |   +-- v1/routes/          # API routes: health, video, chat, summary, notes, quiz, debug
|   |   +-- core/                   # Cấu hình backend và biến môi trường
|   |   +-- schemas/                # Pydantic schemas cho API contract
|   |   +-- services/
|   |       +-- extraction/          # Xử lý URL, metadata và transcript YouTube
|   |       +-- rag/                 # Chunking, embedding, vector store, retrieval, rerank
|   |       +-- llm/                 # Prompt, context budget, Gemini client, fallback wrapper
|   |       +-- learning/            # Summary, notes, quiz, cache generated outputs
|   +-- evaluation/                  # Script và metric đánh giá retrieval
|   +-- tests/                       # Unit/API tests
|   +-- requirements.txt
+-- frontend/
|   +-- src/
|   |   +-- features/
|   |   |   +-- video/              # Ingest, history, video result
|   |   |   +-- chat/               # Chat với RAG sources
|   |   |   +-- summary/            # Tạo tóm tắt
|   |   |   +-- notes/              # Tạo study notes
|   |   |   +-- quiz/               # Tạo và làm quiz
|   |   |   +-- export/             # Export Markdown
|   |   |   +-- debug/              # Debug retrieval
|   |   +-- shared/                 # API config, request helper, tiện ích thời gian
|   |   +-- App.jsx
|   |   +-- main.jsx
|   +-- package.json
+-- docs/
|   +-- api/api-contract.md          # API contract chi tiết
|   +-- architecture/mvp-flow.md     # Ghi chú kiến trúc MVP
+-- notebooks/                       # Notebook thử nghiệm RAG và demo
+-- README.md
```

Lưu ý: `backend/data/` được tạo trong lúc chạy để lưu dữ liệu runtime. Thư mục này không nên commit.

## Yêu cầu môi trường

- Python 3.11 hoặc mới hơn.
- Node.js 20 hoặc mới hơn.
- npm.
- Có transcript cho video YouTube cần ingest. Nếu video không có transcript hoặc transcript bị chặn, backend có thể không ingest được.
- Gemini API key nếu muốn dùng LLM thật. Nếu không có key, dùng `LLM_PROVIDER=fallback`.

## Chạy backend local

Mở terminal tại thư mục `backend`:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Tạo file `backend/.env` với cấu hình tối thiểu:

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
LLM_PROVIDER=fallback
SCRAPER_API_KEY=
EMBEDDING_PROVIDER=hashing
VECTOR_STORE_PROVIDER=local_json
RERANKER_ENABLED=false
```

Chạy backend:

```powershell
uvicorn app.main:app --reload
```

Backend chạy mặc định tại:

```text
http://127.0.0.1:8000
```

Kiểm tra health check:

```text
http://127.0.0.1:8000/api/v1/health
```

## Chạy frontend local

Mở terminal khác tại thư mục `frontend`:

```powershell
cd frontend
npm install
```

Tạo file `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Chạy frontend:

```powershell
npm run dev
```

Frontend chạy mặc định tại:

```text
http://localhost:5173
```

## Cách sử dụng

1. Mở `http://localhost:5173`.
2. Dán URL YouTube vào form ingest.
3. Chờ backend lấy transcript, chia chunk và build retrieval index.
4. Chọn video trong history nếu đã ingest trước đó.
5. Dùng các tab trong workspace:
   - `Chat`: hỏi đáp dựa trên transcript.
   - `Summary`: tạo tóm tắt ngắn, chi tiết hoặc timeline.
   - `Notes`: tạo ghi chú học tập theo mục tiêu học.
   - `Quiz`: tạo câu hỏi luyện tập hoặc kiểm tra.
   - `Export`: xuất nội dung học tập sang Markdown.
   - `Debug`: xem kết quả retrieval và dùng chunk debug để hỏi lại trong Chat.

## Cấu hình LLM

Mặc định hệ thống có thể chạy không cần LLM:

```env
LLM_PROVIDER=fallback
```

Nếu muốn dùng Gemini:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
LLM_TIMEOUT_SECONDS=20
```

Khi `LLM_PROVIDER=gemini` nhưng thiếu `GEMINI_API_KEY`, backend sẽ tự chuyển về fallback. Khi Gemini lỗi quota, timeout hoặc trả phản hồi không dùng được, service sẽ trả output fallback kèm `generation.fallback_reason`.

## Cấu hình retrieval

Cấu hình nhẹ, dễ chạy local:

```env
EMBEDDING_PROVIDER=hashing
VECTOR_STORE_PROVIDER=local_json
RERANKER_ENABLED=false
```

Cấu hình chất lượng cao hơn, cần tài nguyên tốt hơn:

```env
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
VECTOR_STORE_PROVIDER=chroma
RERANKER_ENABLED=true
RERANK_TOP_K=8
```

Nếu thay đổi `EMBEDDING_PROVIDER` hoặc `VECTOR_STORE_PROVIDER`, nên rebuild index cho video trong giao diện hoặc gọi endpoint rebuild index để tránh dùng vector cũ không cùng embedding space.

## API chính

Base URL local:

```text
http://127.0.0.1:8000/api/v1
```

Các endpoint chính:

```text
GET    /health
GET    /videos
POST   /videos/ingest
GET    /videos/{video_id}
DELETE /videos/{video_id}
POST   /videos/{video_id}/rebuild-index
POST   /chat/ask
GET    /chat/history/{video_id}
DELETE /chat/history/{video_id}
POST   /videos/{video_id}/summary
POST   /videos/{video_id}/study-notes
POST   /videos/{video_id}/quiz
POST   /debug/retrieve
```

API contract chi tiết nằm ở `docs/api/api-contract.md`.

## Kiểm thử

Chạy backend tests từ thư mục `backend`:

```powershell
pytest
```

Chạy lint frontend từ thư mục `frontend`:

```powershell
npm run lint
```

Build frontend:

```powershell
npm run build
```

## Đánh giá retrieval

Thư mục `backend/evaluation` chứa metric và script đánh giá retrieval. File `eval_dataset.example.json` là mẫu dataset để tham khảo cấu trúc. Khi có dataset thật, có thể chạy script đánh giá từ thư mục `backend` theo hướng của module evaluation.

## Deploy

Frontend có thể deploy lên Vercel, Netlify hoặc host static tương tự. Cần cấu hình:

```env
VITE_API_BASE_URL=https://your-backend-domain.com/api/v1
```

Backend có thể deploy lên Render, Railway hoặc host Python tương tự. Cần cấu hình:

```env
CORS_ORIGINS=https://your-frontend-domain.com
LLM_PROVIDER=fallback
EMBEDDING_PROVIDER=hashing
VECTOR_STORE_PROVIDER=local_json
RERANKER_ENABLED=false
```

Start command gợi ý:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Nếu backend chạy trên cloud bị YouTube chặn khi lấy transcript, có thể cấu hình ScraperAPI proxy mode:

```env
SCRAPER_API_KEY=your_scraperapi_key
```

Với MVP, nên gắn persistent disk cho `backend/data/` nếu muốn giữ video history, generated outputs, chat history và vector index sau khi redeploy.

## Dữ liệu runtime

Backend lưu dữ liệu runtime trong `backend/data/`, ví dụ:

```text
backend/data/vector_store/local_rag_index.json
backend/data/vector_store/local_video_metadata.json
backend/data/generated_outputs/local_generated_outputs.json
backend/data/chat_history/local_chat_history.json
backend/data/quiz_attempts/local_quiz_attempts.json
```

Các file này phục vụ demo/MVP local, không phải giải pháp production. Nếu phát triển tiếp, nên chuyển metadata, chat history, generated outputs và quiz attempts sang SQLite hoặc PostgreSQL, đồng thời dùng vector DB phù hợp cho môi trường production.

## Giới hạn hiện tại

- Chưa có user account và phân quyền dữ liệu theo người dùng.
- Chưa có database production.
- Chưa có background job queue cho tác vụ dài.
- Chưa có streaming response cho Chat.
- Chưa có Whisper fallback cho video không có transcript.
- Chất lượng fallback thấp hơn LLM thật.
- Gemini free tier có quota thấp, có thể fallback khi bị rate limit.
- Local JSON storage phù hợp demo/MVP nhưng không phù hợp tải cao hoặc nhiều người dùng.

## Hướng phát triển tiếp

- Hoàn thiện dataset và quy trình đánh giá retrieval.
- Cải thiện chunking theo chủ đề hoặc semantic segmentation.
- Thêm background jobs cho Summary, Notes và Quiz trên video dài.
- Thêm streaming cho Chat và tác vụ sinh nội dung dài.
- Chuyển storage sang SQLite/PostgreSQL.
- Thêm Whisper fallback cho video không có transcript.
- Thêm reranker mạnh hơn để cải thiện chất lượng nguồn.
- Thêm user accounts nếu mở rộng thành ứng dụng nhiều người dùng.

## Lưu ý khi phát triển

- Không commit file `.env`.
- Không commit `backend/data/`.
- Không commit virtual environment, build output hoặc dependency folder.
- Khi thay đổi API schema, cập nhật cả frontend API wrapper và `docs/api/api-contract.md`.
- Khi thay đổi retrieval config, rebuild index của video đã ingest.
- Giữ route mỏng, đưa logic nghiệp vụ vào service layer để dễ kiểm thử và bảo trì.
