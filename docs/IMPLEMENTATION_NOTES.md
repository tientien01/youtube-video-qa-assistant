# Implementation Notes

File này ghi lại các thay đổi đã thực hiện theo roadmap để dễ theo dõi tiến độ và lý do kỹ thuật.

## 2026-06-05 - Phase 0: Củng cố MVP RAG nền tảng

### Đã thay đổi

- Cập nhật tokenizer trong `backend/app/services/rag/text_processing.py` để hỗ trợ chữ Unicode, bao gồm tiếng Việt có dấu.
- Cập nhật logic chunk overlap để phần overlap giữ timestamp từ segment gốc thay vì bắt đầu ở cuối chunk trước.
- Bổ sung test cho tokenizer tiếng Việt.
- Bổ sung test đảm bảo overlap chunk vẫn trỏ về timestamp nguồn hợp lý.
- Bổ sung test fallback answer khi retrieval không tìm thấy context.

### Lý do

- BM25 hiện tại chỉ là baseline tạm thời, nhưng vẫn cần baseline đủ đúng để so sánh với embedding/hybrid RAG ở Phase 5.
- App định hướng dùng cho người học tiếng Việt, nên tokenization không được bỏ mất chữ có dấu.
- Timestamp là bằng chứng quan trọng của grounded RAG; chunk overlap không nên làm lệch mốc nguồn.

### Chưa làm trong bước này

- Chưa thêm embedding hoặc vector database.
- Chưa thay đổi API contract.
- Chưa thêm LLM provider.
- Chưa chỉnh frontend.
