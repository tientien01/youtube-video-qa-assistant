# Cấu trúc thư mục đề xuất

Mục tiêu của cấu trúc này là dùng lại được cho nhiều đồ án full-stack/AI khác nhau, không chỉ riêng dự án YouTube Video Q&A Assistant. Cách tổ chức ưu tiên tách rõ frontend, backend, tài liệu, notebook thử nghiệm, script tự động hóa và dữ liệu runtime.

```
youtube-video-qa-assistant/
├── frontend/                         # Mã nguồn giao diện React
│   ├── public/                       # Tài nguyên tĩnh được phục vụ trực tiếp
│   ├── src/
│   │   ├── app/                      # Cấu hình cấp ứng dụng: App, router, provider
│   │   │   └── App.jsx
│   │   ├── pages/                    # Các màn hình chính của ứng dụng
│   │   │   ├── HomePage.jsx
│   │   │   └── HistoryPage.jsx
│   │   ├── features/                 # Code chia theo chức năng nghiệp vụ
│   │   │   ├── video/                # Xử lý URL, metadata, YouTube player, timestamp
│   │   │   └── chat/                 # Chat UI, gọi API hỏi đáp, streaming nếu có
│   │   ├── shared/                   # Code dùng chung giữa nhiều feature
│   │   │   ├── components/           # Component UI dùng lại nhiều nơi
│   │   │   ├── hooks/                # Custom hooks dùng chung
│   │   │   ├── services/             # Client gọi API backend
│   │   │   └── utils/                # Hàm tiện ích thuần, dễ test
│   │   ├── assets/                   # Hình ảnh, font, tài nguyên frontend
│   │   ├── styles/                   # CSS global hoặc cấu hình style chung
│   │   │   └── global.css
│   │   └── main.jsx                  # Điểm vào React app
│   ├── .env.example                  # Mẫu biến môi trường cho frontend
│   ├── index.html                    # HTML gốc của Vite
│   ├── package.json                  # Dependency và script frontend
│   └── vite.config.js                # Cấu hình Vite
│
├── backend/                          # Mã nguồn backend FastAPI
│   ├── app/
│   │   ├── api/                      # Định nghĩa API endpoint
│   │   │   └── v1/
│   │   │       ├── routes/           # Route tách theo chức năng
│   │   │       │   ├── video.py      # API xử lý video, metadata, transcript
│   │   │       │   └── chat.py       # API hỏi đáp trên nội dung video
│   │   │       └── router.py         # Gom các route v1
│   │   ├── core/                     # Cấu hình lõi của backend
│   │   │   ├── config.py             # Đọc settings từ biến môi trường
│   │   │   ├── logging.py            # Cấu hình log
│   │   │   └── exceptions.py         # Lỗi dùng chung và error handler
│   │   ├── schemas/                  # Pydantic schema cho request/response
│   │   ├── models/                   # ORM/database model nếu dùng SQL database
│   │   ├── repositories/             # Lớp truy xuất database hoặc vector store
│   │   ├── services/                 # Business logic chính
│   │   │   ├── extraction/           # Lấy metadata, transcript, audio fallback
│   │   │   └── rag/                  # Chunking, embedding, retrieval, generation
│   │   ├── workers/                  # Tác vụ nền nếu sau này dùng queue
│   │   ├── utils/                    # Hàm tiện ích backend
│   │   └── main.py                   # Điểm vào FastAPI app
│   ├── tests/                        # Unit test và integration test backend
│   ├── data/                         # Dữ liệu runtime, không commit lên git
│   │   ├── raw/                      # Dữ liệu thô tải về
│   │   ├── processed/                # Dữ liệu đã làm sạch
│   │   ├── vector_store/             # Dữ liệu ChromaDB hoặc vector database local
│   │   └── temp/                     # File tạm khi xử lý audio/transcript
│   ├── .env.example                  # Mẫu biến môi trường cho backend
│   └── requirements.txt              # Dependency Python
│
├── notebooks/                        # Notebook nghiên cứu và thử nghiệm
│   └── experiments.ipynb             # Chỉ dùng để thử ý tưởng, không chứa logic production
│
├── docs/                             # Tài liệu dự án
│   ├── architecture/                 # Sơ đồ hệ thống, quyết định kiến trúc
│   ├── api/                          # Tài liệu API, OpenAPI export hoặc Postman collection
│   └── decisions/                    # Ghi lại các quyết định kỹ thuật quan trọng
│
├── scripts/                          # Script hỗ trợ setup, chạy dev, kiểm tra code
│   ├── setup_backend.ps1             # Cài môi trường backend trên Windows
│   ├── setup_frontend.ps1            # Cài dependency frontend trên Windows
│   └── run_dev.ps1                   # Chạy frontend và backend khi phát triển
│
├── .gitignore                        # Bỏ qua file rác, .env, cache, data runtime
├── docker-compose.yml                # Cấu hình chạy nhiều service khi cần
├── README.md                         # Giới thiệu, hướng dẫn chạy, mô tả ngắn dự án
└── ROADMAP.md                        # Lộ trình phát triển dự án
```

## Ghi chú sử dụng

- `frontend/src/features/` nên chứa code theo từng chức năng lớn. Với dự án này, hai feature ban đầu nên là `video` và `chat`.
- `frontend/src/shared/` chỉ chứa code thật sự dùng chung. Không nên đưa mọi thứ vào shared quá sớm.
- `backend/app/schemas/` dùng cho Pydantic request/response. `backend/app/models/` chỉ dùng khi có database model thật.
- `backend/app/services/` chứa nghiệp vụ chính. Route chỉ nên nhận request, gọi service, rồi trả response.
- `backend/data/` là dữ liệu runtime và nên nằm trong `.gitignore`.
- `notebooks/` chỉ dùng để thử nghiệm. Khi logic đã ổn, hãy chuyển vào `backend/app/services/`.
- `docs/decisions/` hữu ích khi cần ghi lại vì sao chọn FastAPI, ChromaDB, LlamaIndex, OpenAI, hoặc một hướng triển khai cụ thể.
