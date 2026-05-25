# MVP Flow

Tài liệu này mô tả luồng xử lý chính của MVP. Mục tiêu là giữ phạm vi đủ nhỏ để có thể hoàn thành, kiểm thử và mở rộng sau.

## 1. Luồng tổng quan

```text
User
-> Frontend React
-> Backend FastAPI
-> YouTube transcript extraction
-> Transcript cleaning
-> Chunking
-> Embedding
-> Vector store
-> Retrieval
-> LLM generation
-> Response with timestamps
-> Frontend display
```

## 2. Luồng ingest video

```text
1. User nhập YouTube URL trên frontend.
2. Frontend gọi POST /api/v1/videos/ingest.
3. Backend validate URL và lấy video_id.
4. Backend lấy metadata cơ bản của video.
5. Backend lấy transcript có sẵn.
6. Backend làm sạch transcript.
7. Backend chia transcript thành chunks.
8. Backend tạo embedding cho từng chunk.
9. Backend lưu chunk, embedding và metadata vào vector store.
10. Backend trả về thông tin video và trạng thái ingest.
```

Metadata tối thiểu cần giữ:

- `video_id`
- `title`
- `url`
- `duration_seconds`
- `transcript_language`
- `chunk_count`
- `created_at`

Metadata tối thiểu trên mỗi chunk:

- `video_id`
- `chunk_id`
- `text`
- `start_seconds`
- `end_seconds`

## 3. Luồng hỏi đáp

```text
1. User nhập câu hỏi trên frontend.
2. Frontend gọi POST /api/v1/chat/ask.
3. Backend validate video_id và question.
4. Backend tạo embedding cho câu hỏi.
5. Backend retrieve top-k chunks từ vector store.
6. Backend tạo prompt từ question và retrieved chunks.
7. Backend gọi LLM để sinh câu trả lời.
8. Backend trả answer và sources về frontend.
9. Frontend hiển thị câu trả lời và timestamp tham chiếu.
```

## 4. Ranh giới trách nhiệm

Frontend chịu trách nhiệm:

- Nhận input từ người dùng.
- Gọi API backend.
- Hiển thị trạng thái loading/error.
- Hiển thị video, chat và timestamp.

Backend route chịu trách nhiệm:

- Nhận request.
- Validate schema.
- Gọi service phù hợp.
- Trả response theo API contract.

Backend service chịu trách nhiệm:

- Xử lý nghiệp vụ chính.
- Lấy transcript.
- Làm sạch dữ liệu.
- Chunking.
- Embedding.
- Retrieval.
- Gọi LLM.

Repository chịu trách nhiệm:

- Làm việc với vector store hoặc database.
- Ẩn chi tiết lưu trữ khỏi service.

## 5. Quyết định cho MVP

- Chỉ hỗ trợ một video tại một thời điểm.
- Ưu tiên transcript có sẵn, chưa làm fallback Whisper.
- Chưa cần đăng nhập người dùng.
- Chưa cần task queue.
- Chưa cần streaming response.
- Có thể lưu vector store local trong `backend/data/vector_store/`.

## 6. Rủi ro chính

- Video không có transcript.
- Transcript sai ngôn ngữ hoặc thiếu timestamp.
- Chunk quá dài hoặc quá ngắn làm giảm chất lượng retrieval.
- LLM trả lời ngoài context nếu prompt không chặt.
- Vector store local cần cache theo `video_id` để tránh ingest lặp.

Các rủi ro này chưa cần giải quyết toàn bộ trong ngày đầu, nhưng nên được ghi nhận để thiết kế service dễ mở rộng.
