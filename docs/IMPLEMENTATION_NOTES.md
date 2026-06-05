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
