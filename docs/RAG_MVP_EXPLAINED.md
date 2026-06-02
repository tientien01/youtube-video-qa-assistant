# Giải thích MVP RAG - YouTube Video Q&A Assistant

Tài liệu này giải thích bản MVP hiện tại theo cách dễ hiểu nhất: chương trình chạy qua những bước nào, file nào phụ trách việc gì, và phần RAG hoạt động ra sao.

## 1. Mục tiêu của MVP

MVP này tạo một luồng hỏi đáp cơ bản trên nội dung transcript của một video YouTube.

Luồng tổng quát:

```text
Người dùng nhập URL YouTube
-> Backend lấy video_id từ URL
-> Backend lấy transcript có sẵn từ YouTube
-> Backend chuẩn hóa transcript thành segments
-> Backend gom segments thành chunks
-> Backend lưu chunks vào index local
-> Người dùng đặt câu hỏi
-> Backend tìm các chunks liên quan nhất
-> Backend tạo câu trả lời từ các chunks đó
-> Frontend hiển thị câu trả lời và timestamp nguồn
```

Điểm quan trọng: bản MVP hiện tại chạy được mà không cần OpenAI API key. Retrieval đang dùng BM25-style, tức là tìm theo từ khóa, chưa phải embedding semantic thật.

## 2. Các thư mục chính

```text
backend/
  app/
    api/
    schemas/
    services/
      extraction/
      rag/
  tests/

frontend/
  src/
    features/
      video/
      chat/
    shared/

docs/
notebooks/
```

Ý nghĩa:

```text
backend/app/api/          định nghĩa endpoint FastAPI
backend/app/schemas/      định nghĩa request/response model
backend/app/services/     chứa logic chính
backend/app/services/rag/ chứa pipeline RAG
frontend/src/features/    chứa UI và API client theo từng chức năng
docs/                     tài liệu hướng dẫn
notebooks/                notebook học và thử nghiệm
```

## 3. Backend hoạt động như thế nào

Backend có 2 API chính cho MVP.

### 3.1. API ingest video

Endpoint:

```http
POST /api/v1/videos/ingest
```

Request:

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

API này dùng để xử lý video trước khi hỏi đáp.

Luồng xử lý:

```text
video.py
-> ingest_video_content()
-> extract_youtube_video_id()
-> fetch_transcript()
-> chunk_transcript()
-> rag_store.upsert_video()
-> trả VideoIngestResponse
```

### 3.2. API hỏi đáp

Endpoint:

```http
POST /api/v1/chat/ask
```

Request:

```json
{
  "video_id": "VIDEO_ID",
  "question": "Video này nói về gì?"
}
```

Luồng xử lý:

```text
chat.py
-> ask_video_question()
-> rag_store.retrieve()
-> generate_answer()
-> trả ChatAskResponse
```

## 4. Các file backend quan trọng

### 4.1. `backend/app/api/router.py`

File này gom các route vào một router chung.

Nó include:

```text
health router
video router
chat router
```

Nhờ vậy app chính chỉ cần include một `api_router`.

### 4.2. `backend/app/api/v1/routes/video.py`

File này định nghĩa endpoint ingest video:

```python
POST /videos/ingest
```

Nhiệm vụ của file này là:

```text
1. Nhận URL từ frontend
2. Gọi service ingest_video_content()
3. Bắt lỗi URL sai hoặc không có transcript
4. Trả response cho frontend
```

Route này không tự xử lý RAG. Nó chỉ nhận request, gọi service, rồi trả response.

### 4.3. `backend/app/api/v1/routes/chat.py`

File này định nghĩa endpoint hỏi đáp:

```python
POST /chat/ask
```

Nhiệm vụ:

```text
1. Nhận video_id và question
2. Kiểm tra câu hỏi không rỗng
3. Gọi ask_video_question()
4. Nếu video chưa được index thì trả lỗi 404
5. Trả answer và sources cho frontend
```

### 4.4. `backend/app/schemas/video.py`

File này định nghĩa dữ liệu cho API ingest.

Model chính:

```text
VideoIngestRequest   request từ frontend, chứa url
VideoIngestResponse  response trả về metadata video
```

Response có các field:

```text
video_id
title
url
duration_seconds
transcript_language
chunk_count
status
```

### 4.5. `backend/app/schemas/chat.py`

File này định nghĩa dữ liệu cho API hỏi đáp.

Model chính:

```text
ChatAskRequest   request hỏi đáp
ChatSource       một đoạn nguồn transcript
ChatAskResponse  câu trả lời và danh sách sources
```

`ChatSource` có timestamp:

```text
chunk_id
text
start_seconds
end_seconds
score
```

Nhờ đó frontend có thể hiển thị nguồn và mở video đúng thời điểm.

## 5. Phần lấy transcript hoạt động như thế nào

File:

```text
backend/app/services/extraction/transcript_service.py
```

Hàm chính:

```python
fetch_transcript(video_id)
```

Nó làm:

```text
1. Gọi youtube-transcript-api
2. Lấy danh sách transcript của video
3. Ưu tiên transcript tiếng Anh hoặc tiếng Việt
4. Nếu có manual transcript thì ưu tiên manual
5. Nếu không có manual thì dùng generated transcript
6. Chuẩn hóa từng raw segment thành TranscriptSegment
```

Raw segment từ YouTube thường có dạng:

```python
{
    "text": "Nội dung phụ đề",
    "start": 10.0,
    "duration": 3.5
}
```

Sau khi chuẩn hóa:

```python
TranscriptSegment(
    text="Nội dung phụ đề",
    start_seconds=10.0,
    end_seconds=13.5,
)
```

Segment là đoạn phụ đề nhỏ do YouTube chia theo timestamp. Code của mình không tự chia segment, chỉ nhận segment từ YouTube và chuẩn hóa lại.

## 6. Phần parse URL hoạt động như thế nào

File:

```text
backend/app/services/extraction/video_url_service.py
```

Hàm chính:

```python
extract_youtube_video_id(url)
```

Nó nhận các dạng URL như:

```text
https://www.youtube.com/watch?v=VIDEO_ID
https://youtu.be/VIDEO_ID
https://www.youtube.com/embed/VIDEO_ID
https://www.youtube.com/shorts/VIDEO_ID
https://www.youtube.com/live/VIDEO_ID
```

Sau đó trả về `video_id`.

Nếu URL không hợp lệ, nó raise `ValueError`. Route sẽ chuyển lỗi này thành HTTP 400.

## 7. Phần RAG nằm ở đâu

Phần RAG nằm trong:

```text
backend/app/services/rag/
```

Các file chính:

```text
models.py
text_processing.py
local_store.py
generation_service.py
video_index_service.py
```

## 8. `models.py` làm gì

File:

```text
backend/app/services/rag/models.py
```

File này định nghĩa object nội bộ cho RAG.

### 8.1. `TranscriptChunk`

Đại diện cho một chunk transcript.

Một chunk có:

```text
chunk_id
video_id
text
start_seconds
end_seconds
```

Ví dụ:

```text
chunk_id: abc123-0001
video_id: abc123
text: đoạn transcript đã gom
start_seconds: 0.0
end_seconds: 42.5
```

### 8.2. `RetrievedChunk`

Đại diện cho một chunk sau khi retrieve.

Nó gồm:

```text
chunk
score
```

`score` là điểm liên quan giữa chunk và câu hỏi.

## 9. `text_processing.py` làm gì

File:

```text
backend/app/services/rag/text_processing.py
```

File này xử lý text trước khi lưu vào index.

Các hàm chính:

```text
clean_text()
tokenize()
chunk_transcript()
_append_chunk()
_build_overlap()
```

### 9.1. `clean_text()`

Hàm này xóa khoảng trắng thừa.

Ví dụ:

```text
"RAG    là\nmột kỹ thuật"
```

thành:

```text
"RAG là một kỹ thuật"
```

### 9.2. `tokenize()`

Hàm này tách text thành các token chữ/số.

Ví dụ:

```text
"RAG kết hợp retrieval và generation."
```

thành gần như:

```python
["rag", "kết", "hợp", "retrieval", "và", "generation"]
```

Tokenize được dùng cho:

```text
1. Đếm số từ khi chia chunk
2. Tính điểm retrieval trong local_store.py
```

### 9.3. `chunk_transcript()`

Đây là hàm chia transcript thành chunks.

Input:

```text
video_id
segments
target_words = 140
overlap_words = 30
```

Nó làm:

```text
1. Tạo chunk rỗng
2. Duyệt từng TranscriptSegment
3. Làm sạch text segment
4. Thêm text segment vào chunk hiện tại
5. Cộng số từ
6. Nếu đủ khoảng 140 từ thì đóng chunk
7. Lấy 30 từ cuối làm overlap cho chunk tiếp theo
8. Sau khi duyệt hết, lưu chunk cuối nếu còn text
```

Ví dụ đơn giản:

```text
target_words = 10
overlap_words = 3
```

Transcript:

```text
Segment 1: 4 từ
Segment 2: 4 từ
Segment 3: 4 từ
Segment 4: 4 từ
```

Code chạy:

```text
Gom segment 1 -> 4 từ
Gom segment 2 -> 8 từ
Gom segment 3 -> 12 từ
Đủ >= 10 từ -> tạo chunk 1
Lấy 3 từ cuối chunk 1 làm overlap
Gom tiếp segment 4
Tạo chunk cuối
```

Kết quả:

```text
Chunk 1 = Segment 1 + Segment 2 + Segment 3
Chunk 2 = 3 từ cuối Chunk 1 + Segment 4
```

### 9.4. `_append_chunk()` hoạt động như thế nào

Hàm này nhận các phần text đang gom và tạo thành một `TranscriptChunk`.

Nó làm:

```text
1. Ghép current_parts thành một chuỗi text
2. Làm sạch khoảng trắng
3. Tạo chunk_id theo thứ tự
4. Tạo TranscriptChunk
5. Thêm chunk vào danh sách chunks
```

Ví dụ:

```python
parts = [
    "RAG là kỹ thuật",
    "kết hợp retrieval và generation",
]
```

Sau khi ghép:

```text
RAG là kỹ thuật kết hợp retrieval và generation
```

Chunk được tạo:

```text
chunk_id: VIDEO_ID-0001
video_id: VIDEO_ID
text: RAG là kỹ thuật kết hợp retrieval và generation
start_seconds: timestamp bắt đầu
end_seconds: timestamp kết thúc
```

### 9.5. `_build_overlap()` hoạt động như thế nào

Sau khi tạo xong một chunk, chương trình không bắt đầu chunk mới từ rỗng hoàn toàn. Nó lấy một số từ cuối của chunk cũ để làm phần đầu của chunk mới.

Ví dụ:

```text
Chunk 1:
A B C D E F G H I J

overlap_words = 3
```

Chunk tiếp theo bắt đầu với:

```text
H I J
```

Lý do cần overlap:

```text
Nếu một ý quan trọng nằm ở ranh giới giữa 2 chunk,
retrieval vẫn có đủ ngữ cảnh để tìm đúng đoạn.
```

Điểm cần biết: overlap hiện tại giữ chính xác text, nhưng timestamp của overlap chỉ là mốc tạm. Nếu sau này cần timestamp thật chính xác cho từng từ overlap, nên cải tiến chunking theo segment-level window.

## 10. `local_store.py` làm gì

File:

```text
backend/app/services/rag/local_store.py
```

File này là nơi lưu index local và retrieve chunks.

Nó có class chính:

```python
LocalRagStore
```

Index trong RAM có dạng:

```python
{
    "video_id_1": [chunk1, chunk2, chunk3],
    "video_id_2": [chunk1, chunk2, chunk3],
}
```

### 10.1. Dữ liệu được lưu ở đâu

Index được ghi xuống:

```text
backend/data/vector_store/local_rag_index.json
```

File này giúp backend nhớ video đã ingest sau khi restart.

### 10.2. `upsert_video()`

Hàm này được gọi sau khi ingest xong.

Nó làm:

```text
1. Đảm bảo index đã load
2. Ghi chunks vào self._index theo video_id
3. Lưu self._index xuống file JSON
```

`upsert` nghĩa là:

```text
nếu video chưa có thì thêm mới
nếu video đã có thì ghi đè
```

### 10.3. `_ensure_loaded()`

Hàm này đảm bảo dữ liệu index đã được đọc từ file JSON vào RAM.

Khi backend restart:

```text
RAM mất dữ liệu
file local_rag_index.json vẫn còn
```

`_ensure_loaded()` sẽ đọc file đó lên.

Nó làm:

```text
Nếu đã load rồi:
    không làm gì

Nếu chưa load:
    kiểm tra file local_rag_index.json có tồn tại không
    nếu có thì đọc JSON
    dựng lại các object TranscriptChunk
    đánh dấu _loaded = True
```

Nhờ vậy backend có thể hỏi tiếp video cũ nếu frontend hoặc API gửi đúng `video_id`.

Lưu ý: frontend hiện tại chưa tự khôi phục video cũ sau khi refresh. Backend nhớ index, nhưng UI chưa nhớ video_id gần nhất.

### 10.4. `retrieve()`

Đây là hàm tìm chunks liên quan đến câu hỏi.

Input:

```text
video_id
question
top_k = 4
```

Nó làm:

```text
1. Load index nếu cần
2. Lấy chunks của video_id
3. Tokenize câu hỏi
4. Tokenize từng chunk
5. Tính document frequency
6. Tính độ dài trung bình của chunk
7. Tính BM25 score cho từng chunk
8. Sort chunks theo score giảm dần
9. Trả tối đa top_k chunks có score > 0
```

Ví dụ:

```text
Question: "retrieval hoạt động như thế nào"
```

Chunk A:

```text
"Retrieval tìm các đoạn transcript liên quan đến câu hỏi"
```

Chunk B:

```text
"Video này nói về nấu ăn"
```

Chunk A có nhiều từ liên quan hơn, nên score cao hơn và được retrieve trước.

### 10.5. `_bm25_score()`

Đây là hàm tính điểm liên quan giữa câu hỏi và một chunk.

Nó xét:

```text
Từ trong câu hỏi có xuất hiện trong chunk không
Xuất hiện bao nhiêu lần
Từ đó hiếm hay phổ biến trong toàn bộ chunks
Chunk dài hay ngắn
```

Từ càng đặc trưng và xuất hiện trong chunk thì score càng cao.

Điểm quan trọng: BM25 là lexical retrieval. Nó cần từ trong câu hỏi và transcript có độ trùng khớp. Nếu người dùng hỏi bằng từ đồng nghĩa nhưng transcript dùng từ khác, retrieval có thể chưa tốt bằng embedding semantic.

## 11. `generation_service.py` làm gì

File:

```text
backend/app/services/rag/generation_service.py
```

File này tạo câu trả lời cuối cùng từ các retrieved chunks.

Hàm chính:

```python
generate_answer(question, retrieved_chunks)
```

Nếu không tìm thấy chunk liên quan, nó trả lời:

```text
Mình chưa tìm thấy đoạn transcript đủ liên quan...
```

Nếu có chunks, nó lấy tối đa 3 chunks đầu và tạo câu trả lời dạng extractive.

Ví dụ output:

```text
Dựa trên các đoạn transcript liên quan nhất...
- [00:35] đoạn transcript liên quan 1
- [01:12] đoạn transcript liên quan 2

Câu hỏi gốc: ...
```

Hiện tại chưa dùng LLM thật. Nếu sau này dùng OpenAI, LlamaIndex hoặc model local, đây là file hợp lý để thay logic generation.

## 12. `video_index_service.py` làm gì

File:

```text
backend/app/services/rag/video_index_service.py
```

Đây là file điều phối chính của RAG.

### 12.1. `ingest_video_content()`

Luồng:

```text
1. Parse URL ra video_id
2. Fetch transcript
3. Chunk transcript
4. Lưu chunks vào rag_store
5. Trả metadata video
```

Đây là nơi nối extraction với RAG indexing.

### 12.2. `ask_video_question()`

Luồng:

```text
1. Nhận video_id và question
2. Gọi rag_store.retrieve()
3. Gọi generate_answer()
4. Convert retrieved chunks thành ChatSource
5. Trả ChatAskResponse
```

Đây là nơi nối retrieval với generation.

## 13. Frontend hoạt động như thế nào

Frontend có 2 feature chính:

```text
video
chat
```

### 13.1. `frontend/src/App.jsx`

Đây là component chính.

State chính:

```text
video       video đã ingest
messages    lịch sử câu hỏi/câu trả lời trong phiên hiện tại
error       lỗi ingest
chatError   lỗi hỏi đáp
isLoading   trạng thái ingest
isAsking    trạng thái đang hỏi
```

Khi user ingest:

```text
handleIngest()
-> gọi ingestVideo()
-> setVideo(response)
-> reset messages
```

Khi user hỏi:

```text
handleAsk()
-> gọi askVideoQuestion()
-> thêm answer vào messages
```

### 13.2. `frontend/src/features/video/videoApi.js`

File này gọi API ingest:

```http
POST http://127.0.0.1:8000/api/v1/videos/ingest
```

Nó gửi:

```json
{
  "url": "..."
}
```

và trả response cho UI.

### 13.3. `frontend/src/features/video/VideoIngestForm.jsx`

Form nhập URL YouTube.

Nó làm:

```text
1. Nhận URL từ người dùng
2. Trim khoảng trắng
3. Nếu URL không rỗng thì gọi onSubmit(url)
```

### 13.4. `frontend/src/features/video/VideoResult.jsx`

Hiển thị:

```text
YouTube iframe
Video ID
Title
Status
Chunk count
Transcript language
Duration
```

### 13.5. `frontend/src/features/chat/chatApi.js`

File này gọi API hỏi đáp:

```http
POST http://127.0.0.1:8000/api/v1/chat/ask
```

Nó gửi:

```json
{
  "video_id": "...",
  "question": "..."
}
```

### 13.6. `frontend/src/features/chat/ChatPanel.jsx`

Component giao diện hỏi đáp.

Nó hiển thị:

```text
Form nhập câu hỏi
Danh sách câu trả lời
Danh sách sources
Timestamp có thể bấm để mở YouTube đúng đoạn
```

### 13.7. `frontend/src/shared/utils/time.js`

File tiện ích xử lý timestamp.

Nó có:

```text
formatTimestamp()
buildYouTubeTimestampUrl()
```

Ví dụ:

```text
35 giây -> 00:35
video_id + 35 giây -> https://www.youtube.com/watch?v=VIDEO_ID&t=35s
```

## 14. Notebook bài giảng

File:

```text
notebooks/rag_src_code_lecture.ipynb
```

Notebook này giải thích pipeline RAG theo từng cell:

```text
1. Chuẩn bị import backend source
2. Parse YouTube URL
3. Tạo transcript mẫu
4. Chia chunk
5. Lưu index local và retrieve
6. Sinh câu trả lời
7. Gợi ý chạy transcript thật
```

Mục tiêu của notebook là giúp bạn học source code bằng cách chạy từng phần nhỏ.

## 15. Tests đã thêm

Thư mục:

```text
backend/tests/
```

Có test cho:

```text
parse YouTube URL
chunk transcript giữ timestamp
local_store retrieve chunk liên quan
```

Chạy test:

```powershell
$env:PYTHONPATH="backend"
backend\venv\Scripts\python.exe -m unittest discover backend\tests
```

## 16. Cách chạy project

### 16.1. Chạy backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

### 16.2. Chạy frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://127.0.0.1:5173
```

## 17. Giới hạn hiện tại của MVP

Bản MVP hiện tại đã chạy được luồng hỏi đáp, nhưng vẫn còn giới hạn:

```text
1. Retrieval dùng BM25-style, chưa dùng embedding semantic
2. Generation chưa dùng LLM thật
3. Frontend chưa khôi phục video đã ingest sau khi refresh
4. Ingest chưa skip xử lý nếu video đã có trong cache
5. Chưa có lịch sử chat persistent
6. Chưa có fallback Whisper nếu video không có transcript
```

## 18. Hướng nâng cấp tiếp theo

Các bước hợp lý tiếp theo:

```text
1. Backend kiểm tra cache trước khi ingest lại video
2. Frontend lưu video gần nhất vào localStorage
3. Thay BM25 bằng ChromaDB + embedding
4. Thay generation extractive bằng OpenAI hoặc model local
5. Lưu lịch sử chat
6. Thêm test integration cho API ingest và chat
```

## 19. Tóm tắt ngắn gọn

```text
video.py                 nhận URL ingest
chat.py                  nhận câu hỏi
transcript_service.py    lấy transcript từ YouTube
video_url_service.py     parse video_id
text_processing.py       clean text, tokenize, chia chunk
local_store.py           lưu index local và retrieve chunks
generation_service.py    tạo câu trả lời từ retrieved chunks
video_index_service.py   điều phối toàn bộ RAG pipeline
App.jsx                  điều phối frontend
ChatPanel.jsx            giao diện hỏi đáp
VideoResult.jsx          hiển thị video và metadata
```

Nếu chỉ nhớ một câu: MVP này lấy transcript YouTube, gom thành chunks có timestamp, lưu vào index local, tìm chunk liên quan bằng BM25-style, rồi tạo câu trả lời từ các chunk đó.
