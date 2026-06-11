# Project Architecture

Tài liệu này mô tả kiến trúc hiện tại của YouTube Video Q&A Assistant. Mục tiêu là giúp người đọc hiểu hệ thống hoạt động như thế nào, dữ liệu đi qua đâu, module nào chịu trách nhiệm gì và các giới hạn kỹ thuật hiện còn tồn tại.

## 1. Product Flow

User workflow:

```text
1. Dán YouTube URL.
2. Backend ingest video: metadata, transcript, chunks, retrieval index.
3. User chọn video trong library.
4. User dùng Chat / Summary / Notes / Quiz / Export / Debug.
5. Mọi output quan trọng đều trả timestamp sources để kiểm chứng.
```

System workflow:

```text
Frontend React
-> FastAPI routes
-> Pydantic schemas
-> service layer
-> local stores / vector store / optional Gemini
-> response with generation metadata and sources
-> frontend dashboard
```

## 2. Runtime Components

```text
frontend/
  React + Vite learning dashboard

backend/
  FastAPI API server
  local JSON stores
  optional Chroma vector store
  optional Gemini API client

backend/data/
  local runtime data
  generated outputs
  chat history
  local RAG/vector indexes
```

`backend/data/` là runtime data, không nên commit.

## 2.1 Deploy Shape

Recommended MVP deployment:

```text
Frontend React build
-> Vercel / Netlify

Backend FastAPI
-> Render / Railway / similar Python host

Runtime data
-> persistent disk for MVP
-> database later for production
```

Required deploy env:

```text
Frontend:
VITE_API_BASE_URL=https://your-backend-domain.com/api/v1

Backend:
CORS_ORIGINS=https://your-frontend-domain.com
SCRAPER_API_KEY=your-scraperapi-key-if-needed
```

Backend start command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

For first deploy, keep the lightweight retrieval defaults:

```text
EMBEDDING_PROVIDER=hashing
VECTOR_STORE_PROVIDER=local_json
RERANKER_ENABLED=false
```

Enable ChromaDB and sentence-transformers only after the host has enough CPU/RAM and persistent storage.

## 3. Backend Layers

### API routes

Location: `backend/app/api/v1/routes`

Route files are intentionally thin. They:

- receive HTTP requests,
- validate request/response through Pydantic schemas,
- call services,
- translate known service errors to HTTP errors.

They should not contain retrieval, prompt or storage logic.

### Schemas

Location: `backend/app/schemas`

Schemas define the public API contract. Field names use `snake_case` because this is backend API style. Frontend adapts fields where needed.

Important shared schema:

```text
GenerationMetadata
  generation_mode: llm | fallback | cached
  provider: gemini | fallback | cached | injected
  fallback_reason: optional string
```

This metadata lets frontend show whether an output came from Gemini, local fallback or cache.

### Service layer

Location: `backend/app/services`

The service layer owns business logic:

- extracting metadata/transcript,
- chunking transcript,
- storing local data,
- retrieving chunks,
- building prompts,
- calling optional LLM,
- generating fallback outputs,
- caching generated outputs.

## 4. Video Ingest Flow

```text
POST /api/v1/videos/ingest
-> parse YouTube video_id
-> fetch YouTube oEmbed metadata
-> fetch transcript
-> clean transcript
-> split transcript into timestamped chunks
-> store chunks locally
-> upsert video metadata
-> build vector index if enabled
-> return VideoIngestResponse
```

If `SCRAPER_API_KEY` is set, transcript requests are routed through ScraperAPI proxy mode. This is intended for Render/cloud deployments where YouTube blocks cloud-provider IPs.

Stored video metadata:

```text
video_id
title
url
channel_title
thumbnail_url
duration_seconds
transcript_language
chunk_count
created_at
updated_at
```

Stored transcript chunk:

```text
chunk_id
video_id
text
start_seconds
end_seconds
```

## 5. Retrieval Architecture

The project supports three retrieval modes:

```text
bm25       lexical baseline
embedding  vector similarity
hybrid     combine lexical and vector scores
```

Current retrieval stack:

- BM25-like lexical retrieval over local chunks.
- Hashing embedding baseline.
- Optional sentence-transformers embedding adapter.
- Local JSON vector store baseline.
- Optional ChromaDB vector store.
- Optional lexical reranking.

Default config keeps the project runnable without heavy dependencies:

```text
EMBEDDING_PROVIDER=hashing
VECTOR_STORE_PROVIDER=local_json
RERANKER_ENABLED=false
```

Higher-quality config:

```text
EMBEDDING_PROVIDER=sentence_transformers
VECTOR_STORE_PROVIDER=chroma
RERANKER_ENABLED=true
```

When changing embedding or vector store provider, rebuild the video index because old vectors may not match the new embedding space.

## 6. Chat Flow

```text
POST /api/v1/chat/ask
-> validate video_id/question
-> retrieve chunks using bm25/embedding/hybrid
-> run simple groundedness check
-> compact retrieved context
-> build grounded answer prompt
-> call Gemini if configured
-> fallback if Gemini unavailable/fails/quota-limited
-> save chat message locally
-> return answer + sources + generation metadata
```

Important behavior:

- If `source_chunk_ids` is provided, chat can ask using selected chunks.
- Frontend can regenerate an answer from the same question/source.
- Debug results can be sent to Chat.
- Chat history is synced through backend local JSON and also represented in frontend state.

## 7. Summary Flow

Summary modes:

```text
short
detailed
timeline
```

Direct flow for normal videos:

```text
select timeline + semantic chunks
-> compact context
-> Gemini prompt
-> validate output
-> cache result
-> fallback if needed
```

Long-video flow:

```text
all chunks
-> split into sections
-> compact each section
-> summarize each section
-> cache section summaries
-> merge section summaries
-> cache final summary
```

Why sectioned generation exists:

- A single prompt for a long video can exceed token limits.
- Sectioned generation improves coverage across the whole video.
- It costs more requests, so the system uses it only when video/context is large.

## 8. Study Notes Flow

Study Notes modes:

```text
concise
detailed
timeline
exam_review
beginner
flashcards
concept_map
```

Length:

```text
short
medium
long
```

Study Notes cache key includes:

```text
video_id
mode
length
learning_goal hash
```

For long videos, Study Notes use the same sectioned pattern as Summary:

```text
section notes
-> merge final notes
-> fallback if Gemini fails
```

Fallback notes are generated from representative chunks and timestamps. They are usable as a safety net but lower quality than LLM output.

## 9. Quiz Flow

Quiz parameters:

```text
question_count: 1..20
difficulty: easy | medium | hard
question_type: multiple_choice | true_false | short_answer | mixed
mode: practice | exam | concept_check
source_chunk_ids: optional selected context
```

Flow:

```text
select source chunks
-> compact context
-> ask Gemini for strict JSON
-> parse JSON safely
-> validate source_chunk_id and answer shape
-> fallback to local quiz if parsing/generation fails
-> save quiz attempt metadata
-> cache generated quiz
```

Quiz can be regenerated from:

- normal timeline-selected chunks,
- selected source chunk,
- missed-answer source chunks.

Current grading:

- Multiple choice and true/false are auto-checked.
- Short answer is shown with a sample answer for manual comparison.

## 10. LLM Architecture

The LLM layer is optional.

```text
LLM_PROVIDER=fallback  -> no external LLM, local fallback only
LLM_PROVIDER=gemini    -> use Gemini when API key exists
```

The wrapper in `services/llm/generation.py` returns `OptionalLlmResult` instead of throwing provider errors upward. This keeps product features working even when Gemini fails.

Handled cases:

- provider not configured,
- empty LLM response,
- HTTP errors,
- timeout,
- token-limit truncation,
- quota/rate limit.

Gemini quota guard:

```text
Gemini returns HTTP 429
-> backend records cooldown until retry window
-> later LLM calls fallback immediately
-> avoids spending more requests during quota lockout
```

Context budgeting:

- compact transcript chunks before prompting,
- retry with smaller context after token-limit failure,
- split long Summary/Notes into sections,
- batch section cache writes to reduce reload noise.

## 11. Local Storage

Current storage is local-file based:

```text
backend/data/vector_store/local_rag_index.json
backend/data/vector_store/local_video_metadata.json
backend/data/generated_outputs/local_generated_outputs.json
backend/data/chat_history/local_chat_history.json
backend/data/quiz_attempts/local_quiz_attempts.json
```

This is good for MVP/demo but not production-ready.

Production direction:

- SQLite or PostgreSQL for metadata, chat, generated outputs and attempts.
- ChromaDB or managed vector DB for vectors.
- Migration/versioning for generated output schema changes.
- User accounts and per-user data isolation.

## 12. Frontend Architecture

Frontend is a React + Vite app.

Important files:

```text
frontend/src/App.jsx
frontend/src/App.css
frontend/src/index.css
frontend/src/features/video/*
frontend/src/features/chat/*
frontend/src/features/summary/*
frontend/src/features/notes/*
frontend/src/features/quiz/*
frontend/src/features/export/*
frontend/src/features/debug/*
frontend/src/shared/utils/time.js
```

State currently lives mostly in `App.jsx`:

- active video,
- video history,
- chat messages,
- summary,
- notes,
- quiz,
- debug result,
- loading/error states.

Each feature folder owns its panel and API wrapper. This keeps the UI easy to extend without introducing a global state library too early.

## 13. Error Handling Strategy

Backend:

- Known domain errors become HTTP errors.
- LLM errors become fallback outputs where possible.
- Responses include generation metadata.

Frontend:

- Displays per-panel errors.
- Shows cached/new/llm/fallback badges.
- Keeps workspace usable when one feature fails.

## 14. Design Tradeoffs

Chosen for MVP:

- Local JSON storage instead of database.
- Optional Gemini instead of mandatory LLM.
- Hashing embedding default instead of requiring ML dependencies.
- Chroma and sentence-transformers as adapters, not defaults.
- Sectioned generation only for long/heavy Summary and Notes.

Tradeoffs:

- Easy to run locally, but not production-grade storage.
- Works without API keys, but fallback quality is lower.
- Video-long outputs are more reliable, but can spend more Gemini requests.
- Debuggability is high because sources, scores and generation metadata are visible.

## 15. Main Limitations

- Gemini quota can stop LLM generation temporarily.
- No streaming responses.
- No background job queue for long-running tasks.
- No formal evaluation dataset/results yet.
- No semantic/topic chunking yet.
- No cross-encoder reranker yet.
- No production DB/auth/multi-user isolation.
- No Whisper fallback for videos without transcript.

## 16. Next Technical Priorities

Recommended order:

1. Add formal evaluation dataset and metrics for retrieval quality.
2. Improve chunking with semantic/topic segmentation.
3. Add background jobs for long Summary/Notes/Quiz generation.
4. Add streaming for Chat and long generation tasks.
5. Add production storage.
6. Add Whisper fallback for missing transcripts.
7. Add stronger reranker.
8. Add user accounts if this becomes multi-user.
