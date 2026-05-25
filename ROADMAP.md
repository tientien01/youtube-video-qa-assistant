# Roadmap MVP - YouTube Video Q&A Assistant

## 1. Mục tiêu MVP

Phiên bản MVP cần chứng minh được luồng chính của sản phẩm:

```text
Người dùng nhập URL YouTube
-> hệ thống lấy transcript có sẵn
-> hệ thống lập chỉ mục nội dung video
-> người dùng đặt câu hỏi
-> hệ thống trả lời dựa trên nội dung video
-> câu trả lời có timestamp tham chiếu
```

MVP tập trung vào một video tại một thời điểm. Các tính năng nâng cao như đăng nhập, lịch sử người dùng, playlist, agentic AI, fallback Whisper, streaming response và deploy cloud sẽ làm sau.

## 2. Phạm vi MVP

### Có trong MVP

- Frontend React cho phép nhập YouTube URL.
- Backend FastAPI nhận URL và xử lý video.
- Lấy transcript có sẵn bằng `youtube-transcript-api`.
- Làm sạch transcript cơ bản.
- Chia transcript thành các đoạn nhỏ có metadata timestamp.
- Tạo embedding và lưu vào vector store local.
- API hỏi đáp dựa trên video đã được xử lý.
- Câu trả lời trả về kèm nguồn tham chiếu và timestamp.
- Giao diện hiển thị video, câu hỏi, câu trả lời và timestamp.

### Chưa có trong MVP

- Đăng nhập và phân quyền người dùng.
- Lưu lịch sử chat theo tài khoản.
- Hỏi đáp nhiều video hoặc playlist.
- Fallback Speech-to-Text bằng Whisper.
- Task queue bằng Celery/Redis.
- Streaming token bằng SSE/WebSocket.
- Agentic AI.
- Deploy production.

## 3. Công nghệ MVP

- Frontend: React + Vite.
- Backend: FastAPI.
- Transcript: `youtube-transcript-api`.
- Vector database local: ChromaDB.
- RAG: triển khai đơn giản trong service, có thể tích hợp LlamaIndex sau.
- LLM và embedding: OpenAI hoặc provider tương đương.

## 4. Các giai đoạn thực hiện

### Giai đoạn 1: Nền dự án

- [ ] Hoàn thiện cấu trúc thư mục.
- [ ] Tạo `.gitignore` chuẩn.
- [ ] Tạo tài liệu MVP flow.
- [ ] Tạo API contract ban đầu.
- [ ] Tạo backend health check.
- [ ] Tạo frontend chạy được bằng Vite.

Kết quả cần đạt: frontend và backend đều chạy được ở môi trường local.

### Giai đoạn 2: Backend video ingestion

- [ ] Tạo schema nhận YouTube URL.
- [ ] Viết hàm parse và validate YouTube URL.
- [ ] Lấy metadata cơ bản của video.
- [ ] Lấy transcript có sẵn.
- [ ] Chuẩn hóa transcript thành định dạng nội bộ.
- [ ] Tạo endpoint `POST /api/v1/videos/ingest`.

Kết quả cần đạt: gửi URL vào backend và nhận lại thông tin video cùng trạng thái transcript.

### Giai đoạn 3: RAG pipeline

- [ ] Viết service làm sạch transcript.
- [ ] Viết service chia chunk có giữ timestamp.
- [ ] Tạo embedding cho chunk.
- [ ] Lưu chunk và metadata vào ChromaDB.
- [ ] Viết retrieval service lấy top-k chunks theo câu hỏi.
- [ ] Viết generation service tạo câu trả lời từ context.
- [ ] Tạo endpoint `POST /api/v1/chat/ask`.

Kết quả cần đạt: hỏi một câu về video đã ingest và nhận câu trả lời có timestamp.

### Giai đoạn 4: Frontend MVP

- [ ] Tạo form nhập YouTube URL.
- [ ] Gọi API ingest video.
- [ ] Hiển thị trạng thái loading/error.
- [ ] Hiển thị khung video.
- [ ] Tạo chat UI cơ bản.
- [ ] Gọi API ask.
- [ ] Hiển thị câu trả lời và timestamp.

Kết quả cần đạt: người dùng có thể thao tác toàn bộ MVP trên giao diện.

### Giai đoạn 5: Kiểm thử và hoàn thiện

- [ ] Test parse YouTube URL.
- [ ] Test transcript cleaning.
- [ ] Test chunking giữ đúng timestamp.
- [ ] Test API health.
- [ ] Test API ingest.
- [ ] Test API ask với dữ liệu mẫu nhỏ.
- [ ] Refactor route/service/schema nếu cần.
- [ ] Cập nhật README hướng dẫn chạy project.

Kết quả cần đạt: MVP ổn định, dễ demo và dễ mở rộng.

## 5. Hướng mở rộng sau MVP

- Fallback Whisper cho video không có transcript.
- Cache video đã xử lý để tránh ingest lại.
- Streaming response bằng SSE.
- Lưu lịch sử chat.
- Đăng nhập người dùng.
- Multi-video hoặc playlist Q&A.
- Task queue cho tác vụ xử lý audio nặng.
- Docker hóa backend, frontend và vector database.
- Deploy frontend và backend lên cloud.
