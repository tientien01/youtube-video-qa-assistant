# YouTube Video Q&A Assistant

Huong dan nay chi tap trung vao cach chay chuong trinh o local.

## Yeu Cau

- Python 3.11+
- Node.js 20+
- npm

## 1. Chay Backend

Mo terminal tai thu muc `backend`:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Tao file moi:

```text
backend/.env
```

Noi dung toi thieu de chay local:

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
LLM_PROVIDER=fallback
SCRAPER_API_KEY=
EMBEDDING_PROVIDER=hashing
VECTOR_STORE_PROVIDER=local_json
RERANKER_ENABLED=false
```

Neu muon dung Gemini, them/sua:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
LLM_TIMEOUT_SECONDS=20
```

Neu backend deploy bi YouTube chan IP khi lay transcript, thu ScraperAPI Proxy Mode:

```env
SCRAPER_API_KEY=your_scraperapi_key
```

Chay backend:

```powershell
uvicorn app.main:app --reload
```

Backend se chay tai:

```text
http://127.0.0.1:8000
```

Kiem tra backend:

```text
http://127.0.0.1:8000/api/v1/health
```

## 2. Chay Frontend

Mo terminal khac tai thu muc `frontend`:

```powershell
cd frontend
npm install
```

Tao file moi:

```text
frontend/.env
```

Noi dung:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Chay frontend:

```powershell
npm run dev
```

Frontend se chay tai:

```text
http://localhost:5173
```

## 3. Cach Su Dung

1. Mo `http://localhost:5173`.
2. Dan URL YouTube vao o ingest.
3. Doi backend lay transcript va tao index.
4. Dung cac tab:
   - Chat
   - Summary
   - Notes
   - Quiz
   - Export
   - Debug

## 4. Cau Hinh Deploy

Khi deploy frontend, set:

```env
VITE_API_BASE_URL=https://your-backend-domain.com/api/v1
```

Khi deploy backend, set:

```env
CORS_ORIGINS=https://your-frontend-domain.com
SCRAPER_API_KEY=your_scraperapi_key
```

Backend start command tren Render/Railway:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 5. Luu Y

- Khong commit file `.env`.
- Khong commit thu muc `backend/data`.
- Neu doi `EMBEDDING_PROVIDER` hoac `VECTOR_STORE_PROVIDER`, hay rebuild index cua video trong giao dien.
- Gemini free tier co quota thap; neu gap loi quota, chuong trinh se fallback local.
