# Evaluation Results

Tài liệu này dùng để ghi kết quả retrieval evaluation nhỏ cho portfolio/demo.

## Trạng thái hiện tại

Đã có baseline evaluation runner:

```text
backend/evaluation/eval_dataset.example.json
backend/evaluation/metrics.py
backend/evaluation/run_retrieval_eval.py
```

Dataset hiện tại là file mẫu, chưa phải kết quả đánh giá thật. Trước khi báo cáo, thay `video_id` và `expected_chunk_ids` bằng các video đã ingest local.

## Cách chạy

Chạy trong thư mục `backend`:

```powershell
.\.venv\Scripts\python.exe evaluation\run_retrieval_eval.py --dataset evaluation\eval_dataset.example.json --top-k 4
```

Có thể chỉ chạy một vài mode:

```powershell
.\.venv\Scripts\python.exe evaluation\run_retrieval_eval.py --modes bm25 hybrid
```

## Metrics

```text
Precision@k: tỷ lệ retrieved chunks đúng trong top-k.
Recall@k: tỷ lệ expected chunks được tìm thấy trong top-k.
MRR: vị trí xuất hiện đầu tiên của chunk đúng.
Latency: thời gian retrieve trung bình.
```

## Bảng kết quả

Chưa có kết quả thật. Sau khi tạo dataset nhỏ, điền bảng này:

| Mode | Precision@k | Recall@k | MRR | Avg latency |
| --- | ---: | ---: | ---: | ---: |
| BM25 | TBD | TBD | TBD | TBD |
| Embedding | TBD | TBD | TBD | TBD |
| Hybrid | TBD | TBD | TBD | TBD |

## Nhận xét

TBD sau khi chạy trên dataset thật.

## Hạn chế evaluation

- Dataset nên nhỏ nhưng phải có câu hỏi thật, không chỉ câu hỏi khớp keyword.
- `expected_chunk_ids` cần được kiểm tra thủ công.
- Kết quả chỉ phản ánh các video đã chọn, chưa đại diện mọi video YouTube.
