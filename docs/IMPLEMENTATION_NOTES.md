# Implementation Notes

File này ghi lại các thay đổi đã thực hiện theo roadmap để dễ theo dõi tiến độ và lý do kỹ thuật.

## 2026-06-05 - Phase 0: Củng cố MVP RAG nền tảng

### Đã thay đổi

- Cập nhật tokenizer trong `backend/app/services/rag/text_processing.py` để hỗ trợ chữ Unicode, bao gồm tiếng Việt có dấu.
- Cập nhật logic chunk overlap để phần overlap giữ timestamp từ segment gốc thay vì bắt đầu ở cuối chunk trước.
- Bổ sung test cho tokenizer tiếng Việt.
- Bổ sung test đảm bảo overlap chunk vẫn trỏ về timestamp nguồn hợp lý.
- Bổ sung test fallback answer khi retrieval không tìm thấy context.

### Lý do

- BM25 hiện tại chỉ là baseline tạm thời, nhưng vẫn cần baseline đủ đúng để so sánh với embedding/hybrid RAG ở Phase 5.
- App định hướng dùng cho người học tiếng Việt, nên tokenization không được bỏ mất chữ có dấu.
- Timestamp là bằng chứng quan trọng của grounded RAG; chunk overlap không nên làm lệch mốc nguồn.

### Chưa làm trong bước này

- Chưa thêm embedding hoặc vector database.
- Chưa thay đổi API contract.
- Chưa thêm LLM provider.
- Chưa chỉnh frontend.

## 2026-06-05 - Phase 0: Chuẩn bị trước Phase 1

### Đã thay đổi

- Thêm logging cơ bản cho backend app, video ingest route, chat route và RAG service.
- Rút gọn `VideoIngestResponse.status` về các trạng thái gần với roadmap tiếp theo: `ready`, `cached`, `failed`.
- Thêm dependency `httpx` để chạy FastAPI `TestClient` trong test endpoint.
- Thêm test endpoint cho `/api/v1/health`.
- Thêm test `/api/v1/videos/ingest` với URL không phải YouTube.
- Thêm test `/api/v1/chat/ask` cho câu hỏi rỗng.
- Thêm test `/api/v1/chat/ask` khi video chưa được index.
- Bổ sung README setup backend, frontend, chạy test và lưu ý không commit dữ liệu runtime hoặc secret.

### Lý do

- Phase 1 sẽ thêm cache ingest và video history, nên cần API baseline có test trước.
- Logging giúp debug rõ hơn khi ingest hoặc ask lỗi.
- `cached` được đưa vào schema sớm để chuẩn bị cho cache ingest ở Phase 1.

### Chưa làm trong bước này

- Chưa implement cache ingest.
- Chưa thêm API danh sách video đã ingest.
- Chưa thêm frontend video history.
- Chưa thêm embedding, vector store hoặc LLM.

## 2026-06-05 - Phase 1: Backend cache ingest tối thiểu

### Đã thay đổi

- Thêm `has_video(video_id)` trong `LocalRagStore`.
- Thêm `get_video_chunk_count(video_id)` trong `LocalRagStore`.
- Cập nhật `ingest_video_content()` để kiểm tra video đã có trong local RAG store trước khi fetch transcript.
- Nếu video đã được index, `/api/v1/videos/ingest` trả `status = cached` và không gọi lại `fetch_transcript`.
- Thêm test service để đảm bảo cache ingest không gọi transcript API.
- Thêm test API để đảm bảo endpoint ingest trả response `cached` đúng contract.

### Lý do

- Video đã ingest không nên xử lý transcript lại, vì thao tác này tốn thời gian và phụ thuộc network/API YouTube transcript.
- Đây là bước nền của Phase 1 trước khi thêm video metadata store và video history trên frontend.
- Cache ingest giúp các bước thử nghiệm RAG sau này nhanh và ổn định hơn.

### Chưa làm trong bước này

- Chưa lưu metadata video riêng như `duration_seconds`, `transcript_language`, `created_at`, `updated_at`.
- Response cached hiện chỉ trả `duration_seconds = null` và `transcript_language = null` vì local store hiện mới lưu chunks.
- Chưa thêm `GET /api/v1/videos`.
- Chưa thêm `GET /api/v1/videos/{video_id}`.
- Chưa thêm frontend localStorage hoặc video history panel.

## 2026-06-05 - Phase 1: Video library và cache ingest đầy đủ

### Đã thay đổi

- Thêm `LocalVideoMetadataStore` để lưu metadata video vào JSON local.
- Metadata lưu các trường: `video_id`, `url`, `title`, `duration_seconds`, `transcript_language`, `chunk_count`, `created_at`, `updated_at`.
- Khi ingest video mới, backend lưu cả chunks và metadata.
- Khi ingest video đã cache, backend trả lại metadata đã lưu thay vì chỉ trả `duration_seconds = null`.
- Thêm `GET /api/v1/videos` để lấy danh sách video đã ingest.
- Thêm `GET /api/v1/videos/{video_id}` để lấy metadata một video.
- Thêm `DELETE /api/v1/videos/{video_id}` để xóa video khỏi local RAG store và metadata store.
- Thêm test API cho list/get/delete video history.
- Thêm test service cho metadata store và cached ingest có metadata.
- Thêm frontend API client cho list/get/delete video.
- Thêm `videoStorage.js` để lưu video hiện tại và lịch sử video vào `localStorage`.
- Thêm `VideoHistory.jsx` để hiển thị video đã xử lý, chọn lại video cũ và xóa video.
- Cập nhật `App.jsx` để load history khi mở app, lưu video sau ingest và cho phép hỏi tiếp video đã chọn lại.

### Lý do

- App không còn chỉ là demo một lần; user có thể mở lại video đã xử lý trước đó.
- Backend cache ingest giảm phụ thuộc vào YouTube transcript API khi video đã có index.
- Metadata store là nền để các phase sau cache summary, notes, quiz và evaluation theo từng video.

### Chưa làm trong bước này

- Chưa lấy title thật từ YouTube metadata; title hiện vẫn là `YouTube video {video_id}`.
- Chưa lưu lịch sử chat theo từng video.
- Chưa có database thật; metadata và chunks vẫn là local JSON.
- Chưa có frontend route riêng cho history page.
- Chưa thêm summary, notes, quiz, LLM hoặc embedding.

## 2026-06-05 - Phase 5: Semantic RAG baseline và hybrid retrieval

### Đã thay đổi

- Thêm `HashingEmbeddingService` để tạo embedding vector local, deterministic, không cần API key.
- Thêm `LocalVectorStore` để lưu vector index local bằng JSON.
- Khi ingest video mới, backend lưu chunks vào cả BM25 local store và vector store.
- Khi ingest video đã cache, backend tự build vector index nếu chunks đã có nhưng vector index chưa có.
- Khi xóa video, backend xóa cả chunks, metadata và vectors.
- Thêm `retrieval_service.py` để gom logic chọn retrieval mode.
- Thêm retrieval modes:
  - `bm25`
  - `embedding`
  - `hybrid`
- `hybrid` kết hợp BM25 score và embedding score sau khi normalize.
- Cập nhật `/api/v1/chat/ask` để nhận `retrieval_mode`.
- Cập nhật response chat để trả `retrieval_mode` đã dùng.
- Cập nhật frontend Chat panel để chọn retrieval mode trước khi hỏi.
- Cập nhật frontend answer card để hiển thị mode đã dùng.
- Thêm tests cho vector store, hybrid retrieval và chat API với retrieval mode.

### Lý do

- BM25 vẫn được giữ làm baseline để so sánh với semantic retrieval.
- Embedding retrieval làm pipeline RAG giống thực tế hơn: chunk text -> embedding -> vector search.
- Hybrid retrieval là hướng thực tế hơn cho demo vì tận dụng cả keyword matching và vector similarity.
- Implementation hiện dùng local hashing embedding để ổn định, chạy offline và không cần tải model lớn.

### Giới hạn hiện tại

- Embedding hiện là hashing embedding local, chưa phải sentence-transformers hoặc embedding model từ provider.
- Vector store hiện là JSON local, chưa phải ChromaDB.
- Chưa có reranker.
- Chưa có evaluation dataset để đo BM25 vs embedding vs hybrid.
- Chưa có RAG Debug View để hiển thị score chi tiết theo từng retriever.

### Bước tiếp theo nên làm

- Nếu cần bám sát production RAG hơn, thay `LocalVectorStore` bằng ChromaDB adapter.
- Nếu máy đủ tài nguyên, thay `HashingEmbeddingService` bằng sentence-transformers local.
- Kéo một phần Phase 7 lên sớm để thêm evaluation và debug view.

## 2026-06-09 - Stabilize current code

### Đã thay đổi

- Cập nhật `ROADMAP.md` theo thứ tự phase mới phù hợp với trạng thái hiện tại của dự án.
- Sửa error handling trong `backend/app/api/v1/routes/video.py` để `TranscriptNotFoundError` được xử lý ở endpoint ingest.
- Loại bỏ nhánh catch `TranscriptNotFoundError` khỏi endpoint delete vì delete không fetch transcript.
- Thêm test API đảm bảo `/api/v1/videos/ingest` trả `404` khi transcript không có.

### Lý do

- Route ingest là nơi có thể phát sinh lỗi transcript unavailable, nên lỗi này cần được map sang response rõ ràng tại đúng endpoint.
- Endpoint delete chỉ thao tác local store, metadata store và vector store, không nên chứa error handling của transcript extraction.
- Đây là bước dọn nền trước khi thêm LLM grounded answer, summary, notes và các tính năng học tập.

### Kiểm tra

- Đã chạy `python -m py_compile app\api\v1\routes\video.py tests\test_api_routes.py`.
- Đã chạy `python -m unittest tests.test_video_url_service`.
- Đã tạo virtualenv backend tại `backend/.venv` và cài dependency từ `backend/requirements.txt`.
- Đã chạy `.\.venv\Scripts\python.exe -m unittest discover -s tests`.
- Kết quả: 25 tests pass.

## 2026-06-09 - Phase B: LLM grounded answer baseline

### Đã thay đổi

- Thêm package `backend/app/services/llm/` cho LLM abstraction.
- Thêm `LlmClient` protocol và `LlmError` để tách generation khỏi provider cụ thể.
- Thêm config đọc từ environment variables: `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `LLM_TIMEOUT_SECONDS`.
- Thêm Gemini REST client dùng endpoint `generateContent`.
- Thêm prompt builder cho grounded answer dựa trên transcript context.
- Cập nhật `generation_service.py` để ưu tiên LLM nếu đã cấu hình, nhưng fallback về extractive answer nếu thiếu key, provider lỗi hoặc response rỗng.
- Cập nhật README với hướng dẫn cấu hình Gemini optional.
- Thêm test cho LLM client mock và fallback khi LLM lỗi.
- Cập nhật test chat API để không vô tình gọi network nếu máy có `GEMINI_API_KEY`.

### Lý do

- Phase B cần câu trả lời tự nhiên hơn nhưng app vẫn phải chạy được khi sinh viên chưa có API key.
- Gemini được tích hợp trước vì phù hợp với học tập, có free tier và dễ bật qua Google AI Studio.
- Fallback extractive giữ app ổn định cho local development, test và demo offline.

### Chưa làm trong bước này

- Chưa thêm UI hiển thị answer đang dùng provider nào.
- Chưa thêm provider Groq hoặc OpenRouter.
- Chưa cache LLM answer.
- Chưa có endpoint riêng cho debug prompt hoặc latency.

### Kiểm tra

- Đã chạy `.\.venv\Scripts\python.exe -m py_compile app\services\llm\base.py app\services\llm\config.py app\services\llm\prompt_builder.py app\services\llm\gemini_client.py app\services\rag\generation_service.py tests\test_rag_services.py`.
- Đã chạy `.\.venv\Scripts\python.exe -m unittest discover -s tests`.
- Kết quả: 27 tests pass.

## 2026-06-09 - Phase C: Summary fallback baseline

### Đã thay đổi

- Thêm schema summary với các mode `short`, `detailed`, `timeline`.
- Thêm `LocalGeneratedOutputStore` để cache generated outputs local bằng JSON.
- Thêm `summary_service.py` tạo summary fallback từ transcript chunks, chưa cần API key.
- Thêm endpoint `POST /api/v1/videos/{video_id}/summary`.
- Khi xóa video, backend xóa cả generated outputs liên quan để tránh cache mồ côi.
- Thêm frontend `SummaryPanel` và `summaryApi.js`.
- Cập nhật `App.jsx` để user tạo summary sau khi ingest/chọn video.
- Thêm tests cho summary service, summary API, generated output cache và delete cleanup.

### Lý do

- Summary là bước đầu của learning workspace, giúp user hiểu nhanh video mà chưa cần LLM thật.
- Cache generated outputs giúp tránh generate lại cùng một summary mode nhiều lần.
- Làm fallback trước giúp tiếp tục phát triển sản phẩm mà chưa cần gắn API key.

### Kiểm tra

- Đã chạy `.\.venv\Scripts\python.exe -m unittest discover -s tests`.
- Đã chạy `npm run build`.
- Đã chạy `npm run lint`.
- Kết quả backend: 36 tests pass.

## 2026-06-09 - Phase D: Study notes fallback baseline

### Đã thay đổi

- Thêm schema study notes response với `notes`, `sources` và `cached`.
- Thêm `notes_service.py` tạo study notes fallback từ transcript chunks.
- Thêm endpoint `POST /api/v1/videos/{video_id}/study-notes`.
- Dùng lại `LocalGeneratedOutputStore` để cache study notes theo video.
- Thêm frontend `NotesPanel` và `notesApi.js`.
- Cập nhật `App.jsx` để user tạo study notes sau khi ingest/chọn video.
- Thêm tests cho notes service và notes API.

### Lý do

- Study notes là bước tiếp theo sau summary để biến app thành learning workspace.
- Làm fallback trước giúp hoàn thiện workflow mà chưa cần API key.
- Khi bật LLM sau này, service có thể nâng chất lượng nội dung mà không đổi API/frontend contract.

### Kiểm tra

- Đã chạy `.\.venv\Scripts\python.exe -m unittest discover -s tests`.
- Đã chạy `npm run build`.
- Đã chạy `npm run lint`.
- Kết quả backend: 40 tests pass.

## 2026-06-09 - Phase B/C/D: Optional LLM cho chat, summary và study notes

### Đã thay đổi

- Thêm `app.services.llm.generation` để dùng chung logic gọi LLM optional và fallback.
- Cập nhật chat generation để dùng helper chung thay vì tự build Gemini client trong RAG service.
- Thêm prompt builder cho summary và study notes.
- Cập nhật `summary_service.py` để gọi LLM nếu đã cấu hình API key, fallback về summary extractive nếu thiếu key hoặc LLM lỗi.
- Cập nhật `notes_service.py` để gọi LLM nếu đã cấu hình API key, fallback về notes extractive nếu thiếu key hoặc LLM lỗi.
- Thêm tests cho summary và study notes khi dùng mock LLM client.
- Thêm tests cho fallback khi LLM lỗi.

### Lý do

- Project có thể tiếp tục phát triển mà chưa cần API key.
- Khi gần hoàn thiện, chỉ cần set `LLM_PROVIDER=gemini` và `GEMINI_API_KEY` là chat, summary và study notes đều dùng LLM.
- Nếu provider lỗi, hết quota hoặc key sai, app vẫn hoạt động bằng fallback.

### Kiểm tra

- Đã chạy `.\.venv\Scripts\python.exe -m py_compile app\services\llm\generation.py app\services\llm\prompt_builder.py app\services\rag\generation_service.py app\services\learning\summary_service.py app\services\learning\notes_service.py tests\test_api_routes.py tests\test_rag_services.py`.
- Đã chạy `.\.venv\Scripts\python.exe -m unittest discover -s tests`.
- Kết quả backend: 44 tests pass.
