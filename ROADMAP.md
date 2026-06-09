# Roadmap phát triển - YouTube Video Q&A Assistant

Tài liệu này mô tả hướng phát triển mới của dự án sau khi MVP đã có nền tảng RAG, video history và hybrid retrieval baseline.

Mục tiêu không chỉ là làm một chatbot hỏi đáp transcript. Dự án nên được phát triển thành một ứng dụng học tập từ video YouTube có giá trị sử dụng thật, đồng thời đủ nổi bật để trình bày với nhà tuyển dụng.

Tên định hướng sản phẩm:

```text
YouTube Learning Assistant
```

Mô tả ngắn nên dùng khi giới thiệu:

```text
A grounded YouTube learning assistant with transcript-based RAG,
hybrid retrieval, timestamp citations, study tools, and evaluation.
```

## 1. Tầm nhìn sản phẩm

Ứng dụng phục vụ người học qua video YouTube, đặc biệt là sinh viên hoặc người tự học.

Người dùng cần:

```text
- Dán URL video bài giảng.
- Hệ thống tự lấy transcript.
- Hệ thống hiểu và chia nội dung thành các đoạn có timestamp.
- Người dùng hỏi các phần chưa hiểu.
- Câu trả lời có nguồn timestamp để kiểm chứng.
- Hệ thống tạo summary, study notes và quiz.
- Người dùng có thể mở lại video đã xử lý trước đó.
- Người dùng có thể export nội dung học tập ra Markdown.
```

Hướng phát triển sản phẩm:

```text
Video -> Learn -> Ask -> Review -> Export
```

## 2. Trạng thái hiện tại

Các phần đã có:

```text
- Backend FastAPI.
- Frontend React + Vite.
- Nhập URL YouTube.
- Parse video_id từ URL.
- Lấy transcript bằng youtube-transcript-api.
- Chuẩn hóa transcript thành segments.
- Chia transcript thành chunks có timestamp.
- Tokenizer hỗ trợ Unicode và tiếng Việt có dấu.
- Lưu RAG index local bằng JSON.
- Retrieval baseline BM25-style lexical search.
- Local hashing embedding deterministic, không cần API key.
- Local vector store bằng JSON.
- Retrieval modes: bm25, embedding, hybrid.
- Hybrid retrieval kết hợp BM25 score và embedding score.
- Endpoint /api/v1/health.
- Endpoint /api/v1/videos/ingest.
- Endpoint /api/v1/videos.
- Endpoint /api/v1/videos/{video_id}.
- Endpoint DELETE /api/v1/videos/{video_id}.
- Endpoint /api/v1/chat/ask.
- Endpoint /api/v1/videos/{video_id}/summary.
- Endpoint /api/v1/videos/{video_id}/study-notes.
- Endpoint /api/v1/videos/{video_id}/quiz.
- Endpoint /api/v1/debug/retrieve.
- Video metadata store local.
- Cache ingest, không fetch transcript lại nếu video đã index.
- Optional Gemini grounded answer cho chat.
- Fallback extractive answer khi chưa cấu hình LLM hoặc provider lỗi.
- Summary fallback/LLM-ready theo mode short, detailed, timeline.
- Study notes fallback/LLM-ready.
- Cache generated outputs local cho summary và study notes.
- Frontend video history.
- Frontend chọn retrieval mode trước khi hỏi.
- Frontend hiển thị answer, retrieval mode và timestamp sources.
- Frontend tạo summary.
- Frontend tạo study notes.
- Frontend tạo quiz và chấm điểm câu trắc nghiệm.
- Frontend export Markdown với video metadata, summary, study notes, quiz và timestamp sources.
- Frontend RAG Debug View hiển thị chunks, scores, mode, timestamp và latency.
- Generation metadata cho chat, summary và study notes.
- Evaluation runner baseline để so sánh BM25, embedding và hybrid.
- Tests cơ bản cho URL parsing, API routes, RAG store, metadata store, vector store và retrieval.
```

Giới hạn hiện tại:

```text
- LLM hiện mới có Gemini optional, chưa có Groq hoặc OpenRouter adapter.
- Embedding hiện là hashing embedding local, chưa phải semantic embedding model.
- Vector store hiện là JSON local, chưa phải ChromaDB hoặc database chuyên dụng.
- Evaluation hiện mới có runner và dataset example, chưa có dataset thật hoặc kết quả thật.
- Chưa có agentic AI thật.
- Quiz hiện là fallback baseline từ transcript chunks, chưa dùng LLM để sinh câu hỏi tốt hơn.
- Export Markdown hiện làm ở frontend, chưa export selected chat answers.
```

## 3. Định vị điểm nổi bật với nhà tuyển dụng

Dự án nên được trình bày như một AI application có grounding và evaluation, không phải một chatbot wrapper.

Điểm mạnh cần làm rõ:

```text
- Full-stack product: React frontend, FastAPI backend, API contract rõ ràng.
- RAG pipeline thật: transcript -> chunking -> indexing -> retrieval -> grounded answer.
- Timestamp citation: câu trả lời có nguồn để kiểm chứng.
- Hybrid retrieval: so sánh BM25, embedding và hybrid.
- Local-first design: app vẫn chạy được khi không có API key.
- Product thinking: summary, notes, quiz, export phục vụ người học thật.
- Engineering discipline: service separation, tests, logging, cache ingest, metadata store.
- Evaluation mindset: debug view và metrics cho retrieval.
```

Mức nổi bật mong muốn khi demo:

```text
1. User ingest một video bài giảng.
2. App tự lưu video vào history.
3. User hỏi một câu cụ thể.
4. App trả lời tự nhiên bằng tiếng Việt, có timestamp nguồn.
5. User mở RAG Debug View để xem chunks, scores, mode và latency.
6. User tạo summary và study notes.
7. User làm quiz từ video.
8. User export notes/summary/quiz ra Markdown.
9. Có bảng evaluation nhỏ so sánh BM25, embedding và hybrid.
```

Nếu hoàn thành các mục trên, project đủ mạnh cho portfolio intern/fresher/junior ở các hướng:

```text
- AI Engineer.
- Backend Engineer with AI/RAG focus.
- Full-stack Engineer building AI applications.
- Applied Machine Learning Engineer.
```

## 4. Nguyên tắc phát triển

Khi thêm tính năng mới, ưu tiên:

```text
1. Ứng dụng thực tế trước, kỹ thuật phức tạp sau.
2. Mỗi tính năng phải giúp người dùng học tốt hơn hoặc tiết kiệm thời gian hơn.
3. Mọi câu trả lời AI nên có nguồn transcript hoặc timestamp.
4. Nếu context không đủ, hệ thống phải nói rõ là không đủ thông tin.
5. Backend service phải tách rõ để dễ thay implementation.
6. Frontend nên là learning workspace, không chỉ là form hỏi đáp.
7. App phải chạy được ở chế độ local/fallback khi không có API key.
8. Không commit dữ liệu runtime, secret hoặc API key.
9. Không đưa logic production vào notebook; thử nghiệm ổn thì chuyển vào service.
```

## 5. Thứ tự phase mới

Vì Phase 0, Phase 1 và một phần Phase 5 đã được thực hiện, thứ tự cũ không còn tối ưu. Thứ tự mới nên là:

```text
Phase A: Stabilize current code
Phase B: LLM grounded answer
Phase C: Summary
Phase D: Study notes
Phase E: Export Markdown
Phase F: Quiz
Phase G: RAG Debug View và evaluation
Phase H: Improve semantic retrieval
Phase I: Agentic AI learning assistant
Phase J: Final polish và demo package
```

Lý do:

```text
- Bạn đã có RAG baseline và video library, nên không cần quay lại làm lại Phase 0/1.
- LLM grounded answer nên làm trước summary/notes/quiz vì các tính năng học tập đều cần generation service.
- Summary, notes và quiz tạo giá trị sản phẩm rõ nhất với người dùng.
- Export nên kéo lên sớm vì dễ demo và hữu ích ngay sau khi có summary/notes.
- Debug/evaluation nên làm trước khi nâng cấp ChromaDB hoặc sentence-transformers để có số liệu so sánh.
- Agentic AI nên làm sau cùng, khi đã có đủ tools thật để agent điều phối.
```

## 6. Phase A - Stabilize current code

Mục tiêu: làm nền hiện tại ổn định trước khi thêm LLM và tính năng lớn.

Việc cần làm:

```text
- Sửa error handling cho TranscriptNotFoundError ở ingest route.
- Kiểm tra lại API contract hiện tại.
- Đảm bảo /health hoạt động ổn.
- Đảm bảo /videos/ingest xử lý lỗi rõ ràng.
- Đảm bảo /chat/ask trả 404 nếu video chưa ingest.
- Đảm bảo retrieval_mode validate đúng: bm25, embedding, hybrid.
- Đảm bảo backend/data không bị commit.
- Chạy toàn bộ backend tests trong virtualenv đúng dependency.
- Cập nhật README theo trạng thái hiện tại.
- Cập nhật docs/IMPLEMENTATION_NOTES.md sau mỗi mốc lớn.
```

File liên quan:

```text
backend/app/api/v1/routes/video.py
backend/app/api/v1/routes/chat.py
backend/app/services/rag/video_index_service.py
backend/tests/
README.md
docs/IMPLEMENTATION_NOTES.md
```

Kết quả cần đạt:

```text
Code hiện tại chạy ổn, test pass, docs không còn mô tả lệch trạng thái.
```

## 7. Phase B - LLM grounded answer

Mục tiêu: thay câu trả lời extractive hiện tại bằng câu trả lời tự nhiên hơn, nhưng vẫn grounded theo transcript.

Pipeline mong muốn:

```text
question
-> retrieve chunks
-> build grounded prompt
-> call LLM if configured
-> fallback extractive if no API key or provider fails
-> answer in Vietnamese with timestamp sources
```

Provider nên ưu tiên:

```text
1. Gemini API free tier.
2. Groq free plan.
3. OpenRouter free models.
4. Fallback extractive answer.
```

Không đọc hoặc commit API key. Chỉ đọc provider config qua environment khi app chạy.

Thiết kế service:

```text
backend/app/services/llm/
  base.py
  config.py
  gemini_client.py
  groq_client.py
  openrouter_client.py
  prompt_builder.py
```

Nếu muốn giữ đơn giản ở bước đầu:

```text
backend/app/services/rag/llm_generation_service.py
```

Prompt grounded answer phải có quy tắc:

```text
- Chỉ trả lời dựa trên transcript context.
- Nếu transcript không đủ thông tin, nói rõ là không đủ thông tin.
- Trả lời bằng tiếng Việt.
- Không bịa thêm ngoài transcript.
- Giữ câu trả lời ngắn gọn, dễ hiểu.
- Trả về sources riêng từ retrieved chunks, không tự tạo timestamp giả.
```

Kết quả cần đạt:

```text
App trả lời tự nhiên hơn, nhưng vẫn có thể chạy offline bằng fallback extractive.
```

Điểm nổi bật khi demo:

```text
Grounded generation with citation and fallback.
```

## 8. Phase C - Summary

Mục tiêu: giúp user hiểu nhanh nội dung video mà không cần xem toàn bộ ngay.

API đề xuất:

```http
POST /api/v1/videos/{video_id}/summary
```

Request:

```json
{
  "mode": "short"
}
```

Các mode:

```text
short      tóm tắt 5-7 dòng
detailed   tóm tắt chi tiết theo ý chính
timeline   tóm tắt theo timestamp
```

Response:

```json
{
  "video_id": "abc123",
  "mode": "short",
  "summary": "...",
  "sources": []
}
```

Service đề xuất:

```text
backend/app/services/learning/
  summary_service.py
  generated_output_store.py
```

Frontend:

```text
frontend/src/features/summary/
  SummaryPanel.jsx
  summaryApi.js
```

Cache output:

```text
backend/data/generated_outputs/
```

Không commit thư mục runtime này.

Kết quả cần đạt:

```text
User ingest video xong có thể tạo summary ngắn, chi tiết hoặc theo timeline.
```

Điểm nổi bật khi demo:

```text
Video-to-summary with timestamp grounding.
```

## 9. Phase D - Study notes

Mục tiêu: biến transcript thành tài liệu học tập có cấu trúc.

API đề xuất:

```http
POST /api/v1/videos/{video_id}/study-notes
```

Output nên gồm:

```text
- Mục tiêu bài học.
- Khái niệm chính.
- Giải thích dễ hiểu.
- Ví dụ trong video.
- Thuật ngữ quan trọng.
- Timestamp nên xem lại.
```

Service đề xuất:

```text
backend/app/services/learning/
  notes_service.py
```

Frontend:

```text
frontend/src/features/notes/
  NotesPanel.jsx
  notesApi.js
```

Kết quả cần đạt:

```text
User có thể chuyển một video bài giảng thành study notes để ôn tập.
```

Điểm nổi bật khi demo:

```text
Transcript-to-study-notes for real learning workflow.
```

## 10. Phase E - Export Markdown

Mục tiêu: giúp user dùng lại kết quả học tập ngoài app.

Trạng thái hiện tại: đã có baseline frontend cho copy, download và preview Markdown từ video metadata, summary, study notes và timestamp sources.

Nội dung export hiện có:

```text
- Video metadata.
- Summary.
- Study notes.
- Quiz, nếu đã tạo.
- Timestamp links.
```

Việc có thể bổ sung sau:

```text
- Selected chat answers, nếu cần.
- Backend export service nếu cần lưu artifact hoặc chia sẻ server-side.
```

Implementation hiện tại:

```text
frontend/src/features/export/
  exportMarkdown.js
  ExportPanel.jsx
```

Kết quả cần đạt:

```text
User có thể download hoặc copy Markdown notes từ video.
```

Điểm nổi bật khi demo:

```text
End-to-end learning artifact export.
```

## 11. Phase F - Quiz

Mục tiêu: giúp người dùng kiểm tra mức hiểu bài sau khi học video.

Trạng thái hiện tại: đã có baseline backend/frontend tạo quiz từ transcript chunks, gồm multiple choice, true/false, short answer, mixed mode, difficulty, explanation, timestamp source và chấm điểm tự động cho câu có options.

API đề xuất:

```http
POST /api/v1/videos/{video_id}/quiz
```

Request:

```json
{
  "question_count": 10,
  "difficulty": "medium",
  "question_type": "mixed"
}
```

Loại câu hỏi:

```text
multiple_choice
short_answer
true_false
mixed
```

Mỗi câu hỏi nên có:

```text
question
options
correct_answer
explanation
source_timestamp
source_chunk_id
```

Service:

```text
backend/app/services/learning/
  quiz_service.py
```

Frontend:

```text
frontend/src/features/quiz/
  QuizPanel.jsx
  quizApi.js
```

UI nên có:

```text
- Hiển thị từng câu hỏi.
- User chọn đáp án.
- Chấm điểm.
- Hiển thị giải thích.
- Link timestamp để xem lại đoạn liên quan.
```

Kết quả cần đạt:

```text
App không chỉ trả lời, mà còn giúp user ôn tập chủ động.
```

Điểm nổi bật khi demo:

```text
Grounded quiz generation with explanation and timestamp review.
```

Việc có thể nâng cấp sau:

```text
- Prompt LLM grounded quiz khi đã cấu hình provider.
- Parser response LLM an toàn, fallback về quiz baseline nếu lỗi.
- Lưu kết quả làm bài nếu cần review lại.
```

## 12. Phase G - RAG Debug View và evaluation

Mục tiêu: chứng minh bạn hiểu RAG, không chỉ dùng thư viện hoặc API.

Trạng thái hiện tại: đã có baseline Debug API/UI, generation metadata và evaluation runner/report template. Cần tạo dataset thật và điền kết quả evaluation trước khi dùng làm số liệu portfolio.

RAG Debug View nên hiển thị:

```text
- Question.
- Retrieval mode.
- Query tokens, nếu dùng BM25.
- Retrieved chunks.
- BM25 score.
- Embedding score.
- Hybrid score.
- Sources timestamp.
- Prompt gửi cho LLM, có thể ẩn/mở.
- Latency.
- Fallback reason, nếu LLM không được dùng.
```

Frontend:

```text
frontend/src/features/debug/
  RagDebugPanel.jsx
  debugApi.js
```

Backend có thể mở rộng response hoặc thêm endpoint:

```http
POST /api/v1/debug/retrieve
```

Implementation hiện tại:

```text
backend/app/schemas/debug.py
backend/app/api/v1/routes/debug.py
frontend/src/features/debug/debugApi.js
frontend/src/features/debug/RagDebugPanel.jsx
```

Evaluation nhỏ:

```text
3-5 video
10-20 câu hỏi
expected timestamp
expected answer ngắn
```

Metrics:

```text
Precision@k
Recall@k
Mean reciprocal rank
Latency
Answer groundedness manual check
```

So sánh:

```text
BM25
Embedding
Hybrid
```

Thư mục đề xuất:

```text
backend/evaluation/
  eval_dataset.example.json
  run_retrieval_eval.py
  metrics.py
```

Report template:

```text
docs/EVALUATION_RESULTS.md
```

Không commit dataset lớn. Nếu có dataset nhỏ tự tạo để demo, giữ gọn và không chứa dữ liệu nhạy cảm.

Kết quả cần đạt:

```text
Có bảng nhỏ chứng minh hybrid retrieval hoạt động thế nào so với BM25 và embedding.
```

Điểm nổi bật khi demo:

```text
Observable and evaluated RAG pipeline.
```

## 13. Phase H - Improve semantic retrieval

Mục tiêu: nâng retrieval từ baseline local lên semantic retrieval thực tế hơn.

Chỉ nên làm phase này sau khi có Debug View hoặc evaluation nhỏ. Nếu không có số liệu, rất khó biết nâng cấp có thật sự tốt hơn không.

Hướng nâng cấp:

```text
1. Thay HashingEmbeddingService bằng sentence-transformers local.
2. Thêm adapter cho Gemini embedding nếu muốn dùng API.
3. Thay LocalVectorStore JSON bằng ChromaDB local.
4. Giữ interface retrieval_service.py ổn định để không ảnh hưởng route/frontend.
5. Thêm reranking nếu còn thời gian.
```

Thiết kế nên giữ adapter:

```text
backend/app/services/rag/
  embedding_service.py
  vector_store.py
  retrieval_service.py
```

Không nên xóa BM25:

```text
- BM25 là baseline tốt.
- Hybrid thường thực tế hơn embedding-only.
- Evaluation cần baseline để so sánh.
```

Kết quả cần đạt:

```text
User hỏi bằng từ khác transcript vẫn tìm được đoạn liên quan tốt hơn.
```

Điểm nổi bật khi demo:

```text
Hybrid retrieval with measurable improvement.
```

## 14. Phase I - Agentic AI learning assistant

Mục tiêu: biến app từ Q&A thành trợ lý học tập có khả năng điều phối nhiều công cụ.

Không nên làm agent quá sớm. Agent chỉ nổi bật khi đã có tool thật để gọi:

```text
retrieve_chunks(question)
summarize_video(video_id)
generate_study_notes(video_id)
generate_quiz(video_id)
find_timestamps(topic)
export_markdown(content)
```

API đề xuất:

```http
POST /api/v1/agent/run
```

Request:

```json
{
  "video_id": "abc123",
  "goal": "Hãy giúp tôi học video này trong 30 phút"
}
```

Response:

```json
{
  "goal": "...",
  "plan": [],
  "result": {},
  "sources": []
}
```

Service:

```text
backend/app/services/agentic_ai/
  agent_service.py
  tools.py
  prompts.py
  schemas.py
```

Workflow ban đầu:

```text
1. Nhận goal.
2. Phân loại goal: summary, notes, quiz, learning_plan, explain_segment.
3. Gọi tool tương ứng.
4. Tổng hợp kết quả.
5. Trả về sources.
```

Workflow nâng cao:

```text
1. Agent lập plan nhiều bước.
2. Thực thi từng step.
3. Quan sát output của tool.
4. Quyết định bước tiếp theo.
5. Trả final answer.
```

Frontend:

```text
frontend/src/features/assistant/
  AssistantPanel.jsx
  assistantApi.js
```

Kết quả cần đạt:

```text
User có thể nhập mục tiêu học tập, app tự gọi summary, notes, quiz và timestamp tools để tạo kế hoạch học.
```

Điểm nổi bật khi demo:

```text
Tool-using learning assistant over video transcript.
```

## 15. Phase J - Final polish và demo package

Mục tiêu: hoàn thiện app để demo rõ, chạy ổn và dễ đánh giá.

Việc cần làm:

```text
- Loading state rõ ràng.
- Empty state rõ ràng.
- Error message dễ hiểu.
- Timestamp dễ bấm.
- Layout responsive.
- Text không tràn UI.
- Không dùng icon nếu rule project không cho phép.
- Không commit backend/data.
- Không commit .env hoặc secret.
- README có setup, architecture, feature list, demo script.
- Có screenshots hoặc GIF demo nếu cần.
- Có phần evaluation result ngắn.
```

Demo script đề xuất:

```text
1. Chạy backend và frontend.
2. Ingest một video bài giảng.
3. Chọn retrieval mode hybrid.
4. Hỏi một câu cụ thể.
5. Mở timestamp source để kiểm chứng.
6. Mở RAG Debug View để xem chunks và scores.
7. Tạo summary.
8. Tạo study notes.
9. Tạo quiz và trả lời thử.
10. Export Markdown.
11. Chạy agent với goal: "Hãy giúp tôi học video này trong 30 phút".
12. Mở evaluation result so sánh BM25, embedding và hybrid.
```

README cuối nên có:

```text
- Problem statement.
- Features.
- Architecture diagram bằng text hoặc Mermaid.
- Tech stack.
- RAG pipeline.
- Grounding and fallback strategy.
- Evaluation result.
- How to run.
- Limitations.
- Future work.
```

## 16. Thứ tự ưu tiên thực tế

Nếu thời gian hạn chế, làm theo thứ tự:

```text
1. Stabilize current code.
2. LLM grounded answer.
3. Summary.
4. Study notes.
5. Export Markdown.
6. Quiz.
7. RAG Debug View.
8. Evaluation nhỏ.
9. Improve semantic retrieval.
10. Agentic AI đơn giản.
```

Nếu muốn nổi bật hơn về sản phẩm:

```text
1. LLM grounded answer.
2. Summary.
3. Study notes.
4. Quiz.
5. Export Markdown.
6. Assistant tab.
```

Nếu muốn nổi bật hơn về kỹ thuật RAG:

```text
1. RAG Debug View.
2. Evaluation dataset.
3. BM25 vs embedding vs hybrid comparison.
4. ChromaDB adapter.
5. sentence-transformers embedding.
6. Reranking.
```

Khuyến nghị cho dự án hiện tại:

```text
Stabilize
-> LLM grounded answer
-> Summary
-> Study notes
-> Export
-> Quiz
-> Debug/Evaluation
-> Better semantic retrieval
-> Agent
```

Tính đến 2026-06-09, các bước đến RAG Debug View và evaluation runner đã có baseline. Bước tiếp theo nên là tạo dataset evaluation thật rồi quyết định có nâng embedding/vector store hay không.

## 17. Kiến trúc mục tiêu

Frontend:

```text
React + Vite
  -> Video workspace
  -> Video history
  -> Chat tab
  -> Summary tab
  -> Notes tab
  -> Quiz tab
  -> Assistant tab
  -> Debug tab
  -> Export controls
```

Backend:

```text
FastAPI
  -> Health API
  -> Video API
  -> Chat API
  -> Summary API
  -> Notes API
  -> Quiz API
  -> Debug API
  -> Agent API
```

Services:

```text
Extraction service
  -> video_url_service.py
  -> transcript_service.py

RAG service
  -> text_processing.py
  -> local_store.py
  -> embedding_service.py
  -> vector_store.py
  -> retrieval_service.py
  -> generation_service.py

LLM service
  -> provider adapter
  -> prompt builder
  -> fallback handling

Learning service
  -> summary_service.py
  -> notes_service.py
  -> quiz_service.py
  -> export_service.py
  -> generated_output_store.py

Agentic AI service
  -> agent_service.py
  -> tools.py
  -> prompts.py
```

## 18. File/folder mục tiêu

Backend:

```text
backend/app/services/llm/
  base.py
  config.py
  gemini_client.py
  groq_client.py
  openrouter_client.py
  prompt_builder.py

backend/app/services/rag/
  text_processing.py
  local_store.py
  metadata_store.py
  embedding_service.py
  vector_store.py
  retrieval_service.py
  generation_service.py

backend/app/services/learning/
  summary_service.py
  notes_service.py
  quiz_service.py
  export_service.py
  generated_output_store.py

backend/app/services/agentic_ai/
  agent_service.py
  tools.py
  prompts.py
  schemas.py

backend/app/api/v1/routes/
  health.py
  video.py
  chat.py
  summary.py
  notes.py
  quiz.py
  debug.py
  agent.py

backend/evaluation/
  eval_dataset.example.json
  run_retrieval_eval.py
  metrics.py
```

Frontend:

```text
frontend/src/features/video/
  VideoIngestForm.jsx
  VideoResult.jsx
  VideoHistory.jsx
  videoApi.js
  videoStorage.js

frontend/src/features/chat/
  ChatPanel.jsx
  chatApi.js

frontend/src/features/summary/
  SummaryPanel.jsx
  summaryApi.js

frontend/src/features/notes/
  NotesPanel.jsx
  notesApi.js

frontend/src/features/quiz/
  QuizPanel.jsx
  quizApi.js

frontend/src/features/debug/
  RagDebugPanel.jsx
  debugApi.js

frontend/src/features/assistant/
  AssistantPanel.jsx
  assistantApi.js

frontend/src/features/export/
  ExportPanel.jsx
  exportMarkdown.js
```

## 19. Cách học song song khi làm

Thứ tự học nên đi cùng thứ tự implement:

```text
1. FastAPI route, schema, service.
2. Transcript extraction và chunking.
3. BM25 retrieval.
4. Prompting và grounded generation.
5. LLM provider adapter và fallback.
6. Summary/notes/quiz generation.
7. Embedding và vector search.
8. Hybrid retrieval scoring.
9. RAG evaluation.
10. Agent tool calling.
```

Mỗi khi thêm tính năng, tự trả lời:

```text
- User được lợi gì?
- Backend cần API nào?
- Service nào xử lý logic?
- Data có cần cache không?
- Frontend hiển thị ở đâu?
- Có cần timestamp/source không?
- Có fallback khi LLM lỗi không?
- Test tối thiểu là gì?
- Demo feature này trong 30 giây như thế nào?
```

## 20. Tiêu chí hoàn thành portfolio

Mức tối thiểu để demo tốt:

```text
- Ingest video.
- Video history.
- Chat grounded answer bằng LLM hoặc fallback.
- Timestamp sources.
- Summary.
- Study notes.
- Export Markdown.
- README rõ ràng.
```

Mức mạnh để gây ấn tượng tốt:

```text
- Quiz có explanation và timestamp.
- RAG Debug View.
- Evaluation nhỏ BM25 vs embedding vs hybrid.
- Hybrid retrieval có số liệu.
- Agent đơn giản gọi summary/notes/quiz tools.
```

Mức rất mạnh nếu còn thời gian:

```text
- ChromaDB adapter.
- sentence-transformers embedding.
- Reranker.
- Learning plan agent nhiều bước.
- Demo video hoặc GIF.
```

## 21. Kết luận

Roadmap mới tập trung vào hai mục tiêu:

```text
1. Tạo một ứng dụng học tập từ video có giá trị sử dụng thật.
2. Tạo một portfolio project thể hiện năng lực full-stack, RAG, grounding, evaluation và product thinking.
```

Điểm không nên làm quá sớm:

```text
- Agentic AI trước khi có summary, notes, quiz tools.
- ChromaDB trước khi có debug/evaluation.
- Reranking trước khi baseline retrieval được đo.
```

Điểm nên làm sớm:

```text
- LLM grounded answer.
- Summary.
- Study notes.
- Export.
- RAG Debug View.
- Evaluation nhỏ.
```

Nếu đi theo thứ tự này, dự án sẽ không chỉ là chatbot hỏi đáp transcript, mà trở thành một hệ thống học tập từ video có kiến trúc rõ, demo thuyết phục và có điểm nổi bật kỹ thuật.
