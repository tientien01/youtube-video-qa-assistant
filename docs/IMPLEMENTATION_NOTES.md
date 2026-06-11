# Implementation Notes

File này là bản đọc nhanh để biết project đang ở đâu. Chi tiết kiến trúc nằm ở `docs/architecture/mvp-flow.md`; chi tiết endpoint nằm ở `docs/api/api-contract.md`.

## Mục Tiêu Project

Project là một YouTube Video Q&A Assistant: người dùng dán URL YouTube, backend lấy transcript, chia chunk, lập chỉ mục retrieval, rồi frontend cung cấp workspace học tập gồm Chat, Summary, Study Notes, Quiz, Export và Debug.

Luồng chính:

```text
YouTube URL
-> transcript + metadata
-> chunking
-> BM25 / embedding / vector store
-> retrieval
-> optional Gemini generation
-> answer/summary/notes/quiz có timestamp sources
```

## Trạng Thái Hiện Tại

Đã có:

- Backend FastAPI với API cho video ingest, video history, rebuild index, chat, summary, study notes, quiz và retrieval debug.
- Frontend React dạng learning dashboard: sidebar quản lý video, workspace tabs cho Chat, Summary, Notes, Quiz, Export, Debug.
- Local RAG baseline:
  - BM25 lexical retrieval.
  - Local hashing embedding.
  - Local JSON vector store.
  - Hybrid retrieval.
- Phase I adapter:
  - `sentence-transformers` embedding adapter.
  - ChromaDB vector store adapter.
  - Lexical reranking đơn giản.
- Optional Gemini LLM:
  - Chat grounded answer.
  - Summary.
  - Study Notes.
  - Quiz JSON generation.
  - Fallback local khi thiếu config, lỗi provider, token limit hoặc quota.
- Generated outputs cache local:
  - Summary cache theo video/mode.
  - Study Notes cache theo video/mode/length/learning_goal.
  - Quiz cache theo mode/type/difficulty/count/source chunks.
  - Section cache cho Summary/Notes video dài.
- Chat history backend local JSON và frontend state.
- Export Markdown từ metadata, Summary, Study Notes, Quiz và selected Q&A.

## Frontend Hiện Có

Các màn hình chính:

- Video sidebar:
  - Ingest URL.
  - Video library.
  - Active video metadata.
  - Rebuild index.
- Chat:
  - Hỏi đáp theo transcript.
  - Chọn retrieval mode: `bm25`, `embedding`, `hybrid`.
  - Regenerate answer.
  - Ask again with one source chunk.
  - Include/exclude Q&A in Markdown export.
- Summary:
  - Mode: `short`, `detailed`, `timeline`.
  - Generate/regenerate.
  - Shows cached/new and generation provider.
  - Timestamped transcript sources.
- Study Notes:
  - Mode: `concise`, `detailed`, `timeline`, `exam_review`, `beginner`, `flashcards`, `concept_map`.
  - Length: `short`, `medium`, `long`.
  - Optional learning goal.
- Quiz:
  - Difficulty: `easy`, `medium`, `hard`.
  - Question type: `multiple_choice`, `true_false`, `short_answer`, `mixed`.
  - Mode: `practice`, `exam`, `concept_check`.
  - Check answers, retry missed, generate quiz from missed/source.
- Export:
  - Copy/download Markdown.
- Debug:
  - Inspect retrieved chunks, score and latency.
  - Send retrieved context to Chat.

## Backend Modules

High-level backend layout:

```text
backend/app
├─ api/v1/routes           FastAPI route handlers
├─ schemas                 Pydantic request/response contracts
├─ services/extraction     YouTube metadata and transcript extraction
├─ services/rag            chunking, stores, retrieval, answer generation
├─ services/llm            Gemini client, prompt builders, context budgeting
├─ services/learning       summary, notes, quiz, generated output stores
└─ core/config.py          env/config loading
```

Important services:

- `services/rag/video_index_service.py`: ingest, list/get/delete video, rebuild index, ask question orchestration.
- `services/rag/retrieval_service.py`: BM25/embedding/hybrid retrieval.
- `services/rag/vector_store.py`: local JSON and Chroma vector stores.
- `services/rag/embedding_service.py`: hashing and sentence-transformers embeddings.
- `services/llm/generation.py`: optional LLM wrapper, fallback, quota cooldown.
- `services/llm/gemini_client.py`: Gemini API client.
- `services/llm/context_budget.py`: compact context, split sections, token-limit handling helpers.
- `services/learning/summary_service.py`: summary generation and sectioned long-video flow.
- `services/learning/notes_service.py`: study notes generation and sectioned long-video flow.
- `services/learning/quiz_service.py`: Gemini JSON quiz generation, safe parser, fallback quiz.

## Environment Config

Public config keys are documented in `backend/.env.example`.

Common local defaults:

```text
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
LLM_PROVIDER=fallback
EMBEDDING_PROVIDER=hashing
VECTOR_STORE_PROVIDER=local_json
RERANKER_ENABLED=false
```

To use Gemini:

```text
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your-key>
GEMINI_MODEL=gemini-2.5-flash
LLM_TIMEOUT_SECONDS=20
```

Frontend config:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

For deploy, set `VITE_API_BASE_URL` to the deployed backend URL and set `CORS_ORIGINS` on the backend to the deployed frontend origin.

To use sentence-transformers:

```text
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
```

To use ChromaDB:

```text
VECTOR_STORE_PROVIDER=chroma
CHROMA_PERSIST_DIR=data/vector_store/chroma
```

Do not commit `.env`, `backend/data`, local vector stores, generated outputs, chat history, notebook runtime output or API keys.

## Verification Gần Nhất

Đã chạy gần nhất:

```text
Backend: py_compile selected backend services
Result: pass

Frontend: npm run lint
Frontend: npm run build
Result: pass
```

Không có test mới được thêm trong vòng chỉnh sửa gần đây vì người dùng muốn tự kiểm chứng phần tests.

## Commit Gần Đây

- `535b7c3 Improve adaptive LLM generation workflows`
- `6d6eafd Redesign learning workspace UI`

## Hạn Chế Còn Lại

- Gemini free tier dễ hết quota, nhất là video dài dùng sectioned generation.
- Chưa có streaming response.
- Chưa có background job/task queue cho summary/notes/quiz dài.
- Storage vẫn là local JSON/file, chưa có database production.
- Deploy host không có persistent disk sẽ mất `backend/data` khi service restart.
- Evaluation chính thức chưa làm: chưa có dataset đo retrieval/summary/notes/quiz.
- Reranking còn đơn giản, chưa có cross-encoder reranker.
- Chunking chưa phải semantic/topic-based chunking thật sự.
- Fallback output dùng được nhưng chưa đạt chất lượng như LLM.
- Chưa có auth/multi-user isolation.
- Chưa có Docker/production deployment flow hoàn chỉnh.

## Quy Tắc Docs

Từ bây giờ docs chỉ giữ:

- `docs/IMPLEMENTATION_NOTES.md`: trạng thái hiện tại, cách hiểu nhanh project.
- `docs/architecture/mvp-flow.md`: kiến trúc, luồng xử lý, tradeoff và hạn chế.
- `docs/api/api-contract.md`: API contract hiện tại.

Không tạo thêm docs rải rác nếu nội dung có thể đặt vào một trong ba file trên.
