# API Contract MVP

Base URL khi chạy local:

```text
http://127.0.0.1:8000/api/v1
```

Tất cả response lỗi nên có dạng thống nhất:

```json
{
  "detail": "Error message"
}
```

## 1. Health Check

Kiểm tra backend còn hoạt động hay không.

```http
GET /health
```

Response `200`:

```json
{
  "status": "ok"
}
```

## 2. Ingest Video

Nhận YouTube URL, lấy transcript và lập chỉ mục nội dung video.

```http
POST /videos/ingest
```

Request body:

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

Response `200`:

```json
{
  "video_id": "VIDEO_ID",
  "title": "Video title",
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "duration_seconds": 600,
  "transcript_language": "en",
  "chunk_count": 24,
  "status": "ready"
}
```

Các trạng thái hợp lệ:

- `ready`: video đã được xử lý và có thể hỏi đáp.
- `transcript_not_found`: không tìm thấy transcript có sẵn.
- `failed`: xử lý thất bại.

Lỗi thường gặp:

```text
400: URL không hợp lệ.
404: Không tìm thấy transcript.
500: Lỗi xử lý nội bộ.
```

## 3. Ask Question

Đặt câu hỏi dựa trên video đã được ingest.

```http
POST /chat/ask
```

Request body:

```json
{
  "video_id": "VIDEO_ID",
  "question": "Video này giải thích khái niệm gì?"
}
```

Response `200`:

```json
{
  "answer": "Câu trả lời dựa trên nội dung transcript.",
  "sources": [
    {
      "chunk_id": "VIDEO_ID-0001",
      "text": "Đoạn transcript liên quan.",
      "start_seconds": 35.2,
      "end_seconds": 58.7,
      "score": 0.87
    }
  ]
}
```

Lỗi thường gặp:

```text
400: Câu hỏi rỗng hoặc video_id không hợp lệ.
404: Video chưa được ingest.
500: Lỗi retrieval hoặc LLM.
```

## 4. Quy ước schema

Tên field dùng `snake_case` ở backend API.

Timestamp dùng đơn vị giây:

```json
{
  "start_seconds": 35.2,
  "end_seconds": 58.7
}
```

Frontend có thể format timestamp sang dạng dễ đọc:

```text
00:35
```

## 5. API chưa làm trong MVP

Các API sau chưa nằm trong phạm vi MVP:

- Đăng nhập.
- Lưu lịch sử chat.
- Xóa video khỏi cache.
- Ingest playlist.
- Streaming response.
- Upload audio.
