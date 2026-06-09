# Next Steps

Tài liệu này ghi các việc nên làm tiếp theo sau khi đã có:

```text
- Video ingest/cache/history.
- BM25, embedding baseline và hybrid retrieval.
- Optional Gemini grounded answer cho chat.
- Summary fallback/LLM-ready.
- Study notes fallback/LLM-ready.
- Export Markdown frontend.
- Quiz fallback từ transcript chunks.
- RAG Debug View.
- Evaluation runner baseline.
```

Hiện tại chưa cần gắn API key. Khi gần demo hoặc cần đánh giá chất lượng generation thật, chỉ cần cấu hình:

```text
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

Nếu chưa có key hoặc provider lỗi, app vẫn fallback.

## 1. Kiểm tra thủ công trước khi làm tiếp

Chạy backend và frontend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

```powershell
cd frontend
npm run dev
```

Kiểm tra workflow:

```text
1. Ingest một video YouTube.
2. Chọn lại video từ history.
3. Hỏi một câu bằng Chat.
4. Tạo Summary ở cả 3 mode: short, detailed, timeline.
5. Tạo Study Notes.
6. Bấm timestamp sources để mở đúng đoạn YouTube.
7. Xóa video và kiểm tra history/current video được cập nhật đúng.
```

## 2. Phase E - Export Markdown

Trạng thái: đã triển khai baseline ở frontend.

Đã có:

```text
- frontend/src/features/export/exportMarkdown.js
- frontend/src/features/export/ExportPanel.jsx
- Copy Markdown.
- Download Markdown.
- Preview Markdown.
- Export video metadata, summary, study notes, quiz và timestamp sources.
```

Việc có thể polish sau:

```text
- Kiểm tra thủ công copy/download trên trình duyệt.
- Có thể thêm selected chat answers nếu cần demo workflow học tập sâu hơn.
```

## 3. Phase F - Quiz

Trạng thái: đã triển khai baseline.

Đã có backend:

```text
backend/app/schemas/quiz.py
backend/app/services/learning/quiz_service.py
backend/app/api/v1/routes/quiz.py
```

Đã có frontend:

```text
frontend/src/features/quiz/
  quizApi.js
  QuizPanel.jsx
```

Baseline hiện có:

```text
- multiple choice.
- true/false.
- short answer.
- mixed mode.
- difficulty: easy, medium, hard.
- explanation từ source chunk.
- timestamp source để xem lại.
- chấm điểm tự động cho câu có options.
- quiz được đưa vào Export Markdown nếu đã tạo.
```

Việc có thể polish sau:

```text
chunks -> grounded quiz prompt -> Gemini -> quiz tốt hơn
fallback -> quiz baseline
- LLM quiz prompt và parser.
- Shuffle tốt hơn theo seed.
- Lưu câu trả lời user nếu cần review lại.
```

## 4. Phase G - RAG Debug View

Trạng thái: đã triển khai baseline.

Mục tiêu:

```text
Chứng minh hệ thống RAG hoạt động thế nào, không chỉ hiển thị answer.
```

Nên hiển thị:

```text
- Question.
- Retrieval mode.
- Retrieved chunks.
- Scores.
- Timestamp sources.
- Whether LLM or fallback was used.
- Latency nếu có thể đo đơn giản.
```

Backend có thể thêm:

```text
POST /api/v1/debug/retrieve
```

Frontend:

```text
frontend/src/features/debug/
  debugApi.js
  RagDebugPanel.jsx
```

Đã có:

```text
- Debug retrieve API.
- Debug UI hiển thị question, retrieval mode, top_k, chunks, scores, timestamp sources và latency.
- Generation metadata cho chat, summary và study notes.
```

## 5. Phase H - Evaluation nhỏ

Trạng thái: đã có runner và report template baseline.

Dataset nhỏ:

```text
3-5 video
10-20 questions
expected timestamp
expected answer ngắn
```

Metrics:

```text
Precision@k
Recall@k
MRR
Latency
```

So sánh:

```text
BM25
Embedding baseline
Hybrid
```

Đã có:

```text
backend/evaluation/eval_dataset.example.json
backend/evaluation/metrics.py
backend/evaluation/run_retrieval_eval.py
docs/EVALUATION_RESULTS.md
```

Việc cần làm thủ công trước khi có kết quả thật:

```text
- Ingest 3-5 video demo.
- Tạo 10-20 câu hỏi thật.
- Gán expected_chunk_ids thủ công.
- Chạy runner và điền docs/EVALUATION_RESULTS.md.
```

## 6. Phase I - Nâng cấp embedding/vector store

Hiện embedding là hashing baseline local. Chỉ nâng cấp sau khi có evaluation để biết nâng cấp có tốt hơn thật không.

Hướng nâng cấp:

```text
1. sentence-transformers local.
2. Gemini embedding API.
3. ChromaDB local.
```

Không nên bỏ BM25, vì BM25 là baseline tốt để so sánh.

## 7. Phase J - Agentic AI

Agent nên để sau khi có nhiều tool thật:

```text
- retrieve chunks
- summarize video
- generate study notes
- generate quiz
- export markdown
```

API dự kiến:

```text
POST /api/v1/agent/run
```

Ví dụ goal:

```text
Hãy giúp tôi học video này trong 30 phút.
```

Agent output:

```text
- Learning plan.
- Summary.
- Key concepts.
- Timestamp review list.
- Quiz suggestion.
```

## 8. Việc nên tránh lúc này

```text
- Chưa cần gắn API key nếu chưa cần kiểm thử chất lượng LLM thật.
- Chưa cần làm agent trước khi có Quiz/Export.
- Chưa cần thay ChromaDB trước khi có evaluation.
- Không commit backend/data.
- Không commit .env hoặc secret.
- Không đưa logic production vào notebook.
```

## 9. Thứ tự khuyến nghị ngắn gọn

```text
1. Test thủ công Chat/Summary/Study Notes/Quiz/Debug.
2. Tạo evaluation dataset nhỏ bằng video đã ingest thật.
3. Chạy evaluation và điền docs/EVALUATION_RESULTS.md.
4. Nâng cấp embedding/vector store nếu evaluation cho thấy cần.
5. Agentic AI.
6. Gắn Gemini API key để polish chất lượng generation trước demo.
```
