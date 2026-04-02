# AI-Powered Research Assistant

An API-first research assistant that lets you upload PDF documents, split them into chunks, store embeddings, search across those chunks, and answer questions grounded in the uploaded content.

## Features

- Upload PDF documents through `/upload/`
- Search relevant chunks through `/search/`
- Ask grounded questions through `/ask/`
- List uploaded documents through `/documents/`
- Delete one document through `/documents/{document_id}`
- Reset all uploaded documents through `DELETE /documents/`
- Scope search and question answering to a specific `document_id`

## Stack

- Backend: FastAPI
- Database: PostgreSQL with pgvector in Docker, SQLite fallback for lightweight local development
- ORM: SQLAlchemy
- PDF parsing: PyMuPDF
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- Text generation: Google Gemini via `google-genai`

## Environment Variables

Create a local `.env.local` file based on `.env.example`.

Required for `/ask/`:
- `GOOGLE_API_KEY`

Optional:
- `GOOGLE_MODEL` defaults to `gemini-2.5-flash`
- `DATABASE_URL` defaults to in-memory SQLite locally and PostgreSQL in Docker

## Run Locally

1. Create and activate the virtual environment.
2. Install dependencies from `requirements.txt`.
3. Set `GOOGLE_API_KEY` in your shell or `.env.local`.
4. Start the app:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

5. Open `http://127.0.0.1:8000/docs`

## Run With Docker

1. Make sure Docker Desktop is running.
2. Put your real API key in `.env.local`.
3. Start the stack:

```powershell
docker compose up --build
```

4. Open `http://127.0.0.1:8000/docs`

## Suggested API Test Flow

1. Upload a PDF with `/upload/`
2. Copy the returned `document_id`
3. Use `/documents/` to confirm the upload
4. Call `/search/` with `query` and optionally `document_id`
5. Call `/ask/` with `question` and optionally `document_id`

Using `document_id` is the best way to avoid answers being mixed across multiple uploaded documents.

## Response Notes

- `/upload/` returns the new `document_id`
- `/search/` returns matching chunks with `document_id`, `filename`, and a short `preview`
- `/ask/` returns the generated answer plus a `sources` array so you can see which documents and chunk previews were used
- `DELETE /documents/{document_id}` removes one uploaded document and its chunks
- `DELETE /documents/` clears the full uploaded document set
