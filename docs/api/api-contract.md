# API Contract

Base URL when running locally:

```text
http://127.0.0.1:8000/api/v1
```

Frontend should read this from:

```text
VITE_API_BASE_URL
```

All JSON field names use `snake_case`.

Common error shape:

```json
{
  "detail": "Error message"
}
```

Common generation metadata:

```json
{
  "generation_mode": "llm",
  "provider": "gemini",
  "fallback_reason": null
}
```

Allowed `generation_mode` values:

```text
llm
fallback
cached
```

## Health

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

## Videos

### List Videos

```http
GET /videos
```

Response:

```json
[
  {
    "video_id": "VIDEO_ID",
    "title": "Video title",
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "channel_title": "Channel name",
    "thumbnail_url": "https://...",
    "duration_seconds": 600,
    "transcript_language": "en",
    "chunk_count": 24,
    "created_at": "2026-06-11T00:00:00+00:00",
    "updated_at": "2026-06-11T00:00:00+00:00"
  }
]
```

### Ingest Video

```http
POST /videos/ingest
```

Request:

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

Response:

```json
{
  "video_id": "VIDEO_ID",
  "title": "Video title",
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "channel_title": "Channel name",
  "thumbnail_url": "https://...",
  "duration_seconds": 600,
  "transcript_language": "en",
  "chunk_count": 24,
  "status": "ready"
}
```

Allowed `status` values:

```text
ready
cached
failed
```

### Get Video

```http
GET /videos/{video_id}
```

Response:

```json
{
  "video_id": "VIDEO_ID",
  "title": "Video title",
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "channel_title": "Channel name",
  "thumbnail_url": "https://...",
  "duration_seconds": 600,
  "transcript_language": "en",
  "chunk_count": 24,
  "created_at": "2026-06-11T00:00:00+00:00",
  "updated_at": "2026-06-11T00:00:00+00:00"
}
```

### Delete Video

```http
DELETE /videos/{video_id}
```

Response:

```json
{
  "video_id": "VIDEO_ID",
  "deleted": true
}
```

### Rebuild Index

Use this when embedding/vector-store config changes or when index state needs to be recreated from stored chunks.

```http
POST /videos/{video_id}/rebuild-index
```

Response:

```json
{
  "video_id": "VIDEO_ID",
  "rebuilt": true,
  "chunk_count": 24
}
```

## Chat

### Ask Question

```http
POST /chat/ask
```

Request:

```json
{
  "video_id": "VIDEO_ID",
  "question": "What is the main idea?",
  "retrieval_mode": "hybrid",
  "source_chunk_ids": []
}
```

Allowed `retrieval_mode` values:

```text
bm25
embedding
hybrid
```

`source_chunk_ids` is optional. When provided, Chat answers using the selected chunks instead of normal broad retrieval.

Response:

```json
{
  "message_id": "uuid-or-null",
  "answer": "Answer grounded in transcript context.",
  "retrieval_mode": "hybrid",
  "sources": [
    {
      "chunk_id": "VIDEO_ID-0001",
      "text": "Transcript excerpt.",
      "start_seconds": 35.2,
      "end_seconds": 58.7,
      "score": 0.87
    }
  ],
  "generation": {
    "generation_mode": "llm",
    "provider": "gemini",
    "fallback_reason": null
  },
  "groundedness_warning": null
}
```

### Get Chat History

```http
GET /chat/history/{video_id}
```

Response:

```json
{
  "video_id": "VIDEO_ID",
  "messages": [
    {
      "message_id": "uuid",
      "video_id": "VIDEO_ID",
      "question": "Question text",
      "answer": "Answer text",
      "retrieval_mode": "hybrid",
      "sources": [],
      "generation": {
        "generation_mode": "fallback",
        "provider": "fallback",
        "fallback_reason": "LLM provider is not configured."
      },
      "groundedness_warning": null,
      "created_at": "2026-06-11T00:00:00+00:00"
    }
  ]
}
```

### Delete Chat History

```http
DELETE /chat/history/{video_id}
```

Response:

```json
{
  "video_id": "VIDEO_ID",
  "deleted": true
}
```

## Summary

```http
POST /videos/{video_id}/summary
```

Request:

```json
{
  "mode": "short",
  "force": false
}
```

Allowed `mode` values:

```text
short
detailed
timeline
```

`force=true` bypasses cached output and regenerates.

Response:

```json
{
  "video_id": "VIDEO_ID",
  "mode": "short",
  "summary": "Generated summary text.",
  "sources": [
    {
      "chunk_id": "VIDEO_ID-0001",
      "text": "Transcript excerpt.",
      "start_seconds": 0,
      "end_seconds": 30
    }
  ],
  "cached": false,
  "generation": {
    "generation_mode": "llm",
    "provider": "gemini",
    "fallback_reason": null
  }
}
```

## Study Notes

```http
POST /videos/{video_id}/study-notes
```

Request:

```json
{
  "mode": "concise",
  "length": "medium",
  "learning_goal": "exam review",
  "force": false
}
```

Allowed `mode` values:

```text
concise
detailed
timeline
exam_review
beginner
flashcards
concept_map
```

Allowed `length` values:

```text
short
medium
long
```

Response:

```json
{
  "video_id": "VIDEO_ID",
  "mode": "concise",
  "length": "medium",
  "learning_goal": "exam review",
  "notes": "Generated study notes.",
  "sources": [
    {
      "chunk_id": "VIDEO_ID-0001",
      "text": "Transcript excerpt.",
      "start_seconds": 0,
      "end_seconds": 30
    }
  ],
  "cached": false,
  "generation": {
    "generation_mode": "llm",
    "provider": "gemini",
    "fallback_reason": null
  }
}
```

## Quiz

```http
POST /videos/{video_id}/quiz
```

Request:

```json
{
  "question_count": 5,
  "difficulty": "medium",
  "question_type": "mixed",
  "mode": "practice",
  "force": false,
  "source_chunk_ids": []
}
```

Allowed `difficulty` values:

```text
easy
medium
hard
```

Allowed `question_type` values:

```text
multiple_choice
true_false
short_answer
mixed
```

Allowed `mode` values:

```text
practice
exam
concept_check
```

Response:

```json
{
  "video_id": "VIDEO_ID",
  "difficulty": "medium",
  "question_type": "mixed",
  "mode": "practice",
  "attempt_id": "uuid",
  "questions": [
    {
      "question_id": "VIDEO_ID-0001-llm-q1",
      "question_type": "multiple_choice",
      "question": "Question text?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A",
      "explanation": "Explanation grounded in transcript.",
      "source": {
        "chunk_id": "VIDEO_ID-0001",
        "text": "Transcript excerpt.",
        "start_seconds": 0,
        "end_seconds": 30
      }
    }
  ],
  "sources": [
    {
      "chunk_id": "VIDEO_ID-0001",
      "text": "Transcript excerpt.",
      "start_seconds": 0,
      "end_seconds": 30
    }
  ],
  "cached": false,
  "generation": {
    "generation_mode": "llm",
    "provider": "gemini",
    "fallback_reason": null
  }
}
```

Notes:

- `question_count` must be between 1 and 20.
- `source_chunk_ids` can restrict quiz generation to selected transcript chunks.
- Frontend uses `source_chunk_ids` for quiz-from-source and quiz-from-missed workflows.

## Debug

### Retrieval Debug

```http
POST /debug/retrieve
```

Request:

```json
{
  "video_id": "VIDEO_ID",
  "question": "What concept is explained?",
  "retrieval_mode": "hybrid",
  "top_k": 4
}
```

Response:

```json
{
  "video_id": "VIDEO_ID",
  "question": "What concept is explained?",
  "retrieval_mode": "hybrid",
  "top_k": 4,
  "latency_ms": 12.34,
  "chunks": [
    {
      "chunk_id": "VIDEO_ID-0001",
      "text": "Transcript excerpt.",
      "start_seconds": 0,
      "end_seconds": 30,
      "score": 0.87
    }
  ]
}
```

## Common HTTP Errors

Typical errors:

```text
400 invalid request or invalid YouTube URL
404 video not indexed / transcript not found
422 Pydantic validation error
500 unexpected backend error
```

LLM provider failures usually do not return HTTP 500 for learning outputs. The service prefers returning a fallback output with:

```json
{
  "generation_mode": "fallback",
  "provider": "gemini",
  "fallback_reason": "Gemini request failed with HTTP 429..."
}
```

## Timestamp Rules

API timestamps use seconds:

```json
{
  "start_seconds": 35.2,
  "end_seconds": 58.7
}
```

Frontend formats them as:

```text
00:35
```
