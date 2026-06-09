# Next Steps

Tài liệu này ghi các việc nên làm tiếp theo sau khi đã có:

```text
- Video ingest/cache/history.
- BM25, embedding baseline và hybrid retrieval.
- Optional Gemini grounded answer cho chat.
- Summary fallback/LLM-ready.
- Study notes fallback/LLM-ready.
- Export Markdown frontend.
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
- Export video metadata, summary, study notes và timestamp sources.
```

Việc có thể polish sau:

```text
- Kiểm tra thủ công copy/download trên trình duyệt.
- Có thể thêm quiz vào export sau Phase F.
- Có thể thêm selected chat answers nếu cần demo workflow học tập sâu hơn.
```

## 3. Phase F - Quiz

Đây là bước nên làm tiếp theo.

Backend dự kiến:

```text
backend/app/schemas/quiz.py
backend/app/services/learning/quiz_service.py
backend/app/api/v1/routes/quiz.py
```

Frontend dự kiến:

```text
frontend/src/features/quiz/
  quizApi.js
  QuizPanel.jsx
```

Fallback quiz ban đầu có thể tạo từ transcript chunks:

```text
- multiple choice đơn giản.
- true/false đơn giản.
- explanation từ source chunk.
- timestamp source để xem lại.
```

Sau này khi có API key:

```text
chunks -> grounded quiz prompt -> Gemini -> quiz tốt hơn
fallback -> quiz baseline
```

## 4. Phase G - RAG Debug View

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

## 5. Phase H - Evaluation nhỏ

Chỉ làm sau khi có Debug View hoặc retrieval output rõ ràng.

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
1. Test thủ công Chat/Summary/Study Notes.
2. Test thủ công Export Markdown.
3. Phase F: Quiz.
4. Phase G: RAG Debug View.
5. Phase H: Evaluation nhỏ.
6. Nâng cấp embedding/vector store nếu evaluation cho thấy cần.
7. Agentic AI.
8. Gắn Gemini API key để polish chất lượng generation trước demo.
```
