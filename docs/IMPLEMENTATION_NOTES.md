# Implementation Notes

File này là index ngắn để đọc nhanh trạng thái hiện tại. Chi tiết lịch sử đã được tách sang `docs/implementation_notes/` để giảm token mỗi lần đọc.

## Current Status

Đã hoàn thành baseline đến:

- Phase A: Stabilize current code.
- Phase B: Optional LLM grounded answer cho chat.
- Phase C: Summary.
- Phase D: Study Notes.
- Phase E: Export Markdown.
- Phase F: Quiz fallback baseline.
- Phase G: RAG Debug View và evaluation runner baseline.
- Phase H: Better Study Experience.
- Workspace polish nhỏ sau Phase H.
- Phase I: Semantic retrieval adapter baseline started.

## Latest Product State

- Backend FastAPI có video ingest/cache/history, chat, summary, study notes, quiz và debug retrieve APIs.
- RAG hiện có BM25, local hashing embedding, local vector store và hybrid retrieval.
- Phase I thêm config/adapter cho sentence-transformers, ChromaDB và reranking, mặc định vẫn dùng baseline cũ.
- Optional Gemini LLM có fallback local khi thiếu key hoặc provider lỗi.
- Frontend là learning workspace dạng tabs: Chat, Summary, Notes, Quiz, Export, Debug.
- Chat history lưu theo từng video bằng `localStorage`.
- Export Markdown hỗ trợ Summary, Study Notes, Quiz và selected Q&A.
- Quiz có review/retry mode.
- RAG Debug View hiển thị retrieved chunks, scores, timestamps và latency.

## Latest Verification

Gần nhất đã chạy:

```text
Backend: .\.venv\Scripts\python.exe -m py_compile app\services\llm\context_budget.py app\services\llm\gemini_client.py app\services\llm\prompt_builder.py app\services\learning\generated_output_store.py app\services\learning\summary_service.py app\services\learning\notes_service.py app\services\learning\quiz_service.py app\services\rag\generation_service.py
Result: pass

Frontend: npm run lint
Frontend: npm run build
Result: pass
```

## Latest Changes

- Added Phase I config/adapters for sentence-transformers, ChromaDB and lexical reranking while keeping hashing/local JSON as defaults.
- Improved Gemini output handling: higher output token limit, truncated-response fallback, tighter Summary/Study Notes prompts.
- Improved Summary UI source display with timestamp ranges and shorter transcript excerpts.
- Improved Study Notes with mode/learning goal controls, regenerate support, cache generation metadata, whole-video context selection, semantic candidates, output validation and section notes for longer videos.
- Added real YouTube oEmbed metadata, rebuild-index API, backend chat history sync, chat regenerate/source-constrained ask, simple groundedness guard and Debug-to-Chat chunk preservation.
- Improved Summary with force regenerate, whole-video/semantic context selection, section fallback and shorter fallback excerpts.
- Improved Study Notes with length control, flashcards/concept-map modes and timestamped fallback bullets.
- Improved Quiz with grounded Gemini JSON generation, safe JSON fallback, quiz attempts, quiz modes and source/wrong-answer based regeneration.
- Added adaptive Gemini context budgeting for Chat/Summary/Study Notes/Quiz: compact prompts, retry on token-limit failures, sectioned generation for long Summary/Study Notes videos and batched section cache writes.
- Improved Gemini error details so HTTP status, timeout or request-level failures are easier to diagnose without exposing API keys.
- Added Gemini quota cooldown guard: after HTTP 429/resource-exhausted responses, later LLM calls fallback immediately until the retry window passes instead of spending more requests.
- Disabled Chroma anonymized telemetry at app/vector-store startup to reduce noisy PostHog telemetry errors in local logs.
- Redesigned the frontend workspace into a cleaner video sidebar plus learning dashboard, refreshed Chat/Summary/Notes/Quiz/Export/Debug panels, and removed mojibake UI text from the frontend.

## Current Limitations

- Evaluation runner đã có nhưng chưa có dataset thật và chưa có số liệu thật trong `docs/EVALUATION_RESULTS.md`.
- Phase I chưa có evaluation chính thức; `docs/EVALUATION_RESULTS.md` sẽ cập nhật sau cùng theo kế hoạch.
- Embedding mặc định vẫn là hashing baseline; sentence-transformers đã có adapter nhưng cần cài dependency/model và bật config để dùng.
- Vector store mặc định vẫn là JSON local; ChromaDB đã có adapter nhưng cần bật config để dùng.
- Summary/Notes/Quiz cached ở backend nhưng frontend chưa tự reload generated outputs khi chọn lại video.
- Chưa lấy title thật từ YouTube metadata.
- Khi chạy backend bằng `--reload`, runtime writes trong `backend/data/` vẫn có thể tạo reload event; section cache writes đã được batch để giảm reload giữa nhiều LLM calls.
- Gemini free tier có request quota thấp; video dài dùng sectioned generation sẽ fallback nếu quota bị hết.

## Archives

- [2026-06-05 Phase 0/1/5 foundation](implementation_notes/2026-06-05-phase-0-1-5-foundation.md)
- [2026-06-09 Phase A-E learning baseline](implementation_notes/2026-06-09-phase-a-e-learning-baseline.md)
- [2026-06-09 Phase F-H workspace](implementation_notes/2026-06-09-phase-f-h-workspace.md)

## Update Rule

- File này chỉ ghi trạng thái hiện tại, latest verification, limitations và link archive.
- Khi hoàn thành phase lớn, ghi chi tiết vào file archive phù hợp hoặc tạo archive mới.
- Tránh để file index này phình dài trở lại.
