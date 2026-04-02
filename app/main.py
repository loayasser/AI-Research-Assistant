from pathlib import Path
from math import sqrt
import os
import shutil

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from google import genai

from . import database, models, processor
from .processor import create_embeddings, extract_text_from_pdf

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
_genai_client = None

app = FastAPI()


@app.on_event("startup")
def startup() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    models.Base.metadata.create_all(bind=database.engine)


def get_genai_client():
    global _genai_client

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GOOGLE_API_KEY is not configured.")

    if _genai_client is None:
        _genai_client = genai.Client(api_key=api_key)

    return _genai_client


def safe_filename(filename: str) -> str:
    cleaned = Path(filename).name.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    return cleaned


def resolve_upload_path(filename: str) -> Path:
    target = UPLOAD_DIR / filename
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    counter = 1
    while True:
        candidate = UPLOAD_DIR / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def l2_distance(left: list[float], right: list[float]) -> float:
    return sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def get_document_or_404(db: Session, document_id: int) -> models.Document:
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} was not found.")
    return document


def chunk_preview(content: str, limit: int = 220) -> str:
    text = " ".join(content.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def find_top_chunks(
    db: Session,
    query_vector: list[float],
    limit: int = 3,
    document_id: int | None = None,
):
    if database.IS_SQLITE:
        chunks_query = db.query(models.DocumentChunk)
        if document_id is not None:
            chunks_query = chunks_query.filter(models.DocumentChunk.document_id == document_id)
        chunks = chunks_query.all()
        ranked = sorted(
            (
                chunk
                for chunk in chunks
                if isinstance(chunk.embedding, list) and len(chunk.embedding) == len(query_vector)
            ),
            key=lambda chunk: l2_distance(chunk.embedding, query_vector),
        )
        return ranked[:limit]

    query = db.query(models.DocumentChunk)
    if document_id is not None:
        query = query.filter(models.DocumentChunk.document_id == document_id)

    return query.order_by(models.DocumentChunk.embedding.l2_distance(query_vector)).limit(limit).all()


@app.get("/")
async def root():
    return {
        "message": "Research Assistant API is running.",
        "docs_url": "/docs",
    }


@app.get("/documents/")
async def list_documents(db: Session = Depends(database.get_db)):
    documents = db.query(models.Document).order_by(models.Document.id.desc()).all()
    return [
        {
            "id": document.id,
            "filename": document.filename,
            "file_path": document.file_path,
            "chunk_count": len(document.chunks),
        }
        for document in documents
    ]


@app.delete("/documents/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(database.get_db)):
    document = get_document_or_404(db, document_id)
    filename = document.filename
    file_path = Path(document.file_path)

    db.delete(document)
    db.commit()

    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass

    return {
        "message": f"Deleted document {document_id}.",
        "document_id": document_id,
        "filename": filename,
    }


@app.delete("/documents/")
async def delete_all_documents(db: Session = Depends(database.get_db)):
    documents = db.query(models.Document).all()
    deleted_count = len(documents)

    for document in documents:
        file_path = Path(document.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass
        db.delete(document)

    db.commit()

    return {
        "message": "Deleted all uploaded documents.",
        "documents_deleted": deleted_count,
    }


@app.post("/upload/")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    filename = safe_filename(file.filename)
    file_location = resolve_upload_path(filename)

    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    text = extract_text_from_pdf(str(file_location))
    chunks, embeddings = create_embeddings(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No readable text was found in the uploaded PDF.")

    new_doc = models.Document(filename=filename, file_path=str(file_location))
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    for content, embedding in zip(chunks, embeddings):
        chunk_entry = models.DocumentChunk(
            document_id=new_doc.id,
            content=content,
            embedding=embedding.tolist(),
        )
        db.add(chunk_entry)

    db.commit()

    return {
        "message": f"Successfully processed {len(chunks)} chunks for {file_location.name}",
        "document_id": new_doc.id,
        "filename": new_doc.filename,
        "chunks_created": len(chunks),
    }


@app.post("/search/")
async def search_documents(
    query: str,
    document_id: int | None = Query(default=None),
    db: Session = Depends(database.get_db),
):
    if document_id is not None:
        get_document_or_404(db, document_id)

    try:
        query_vector = processor.get_embedding_model().encode(query).tolist()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    results = find_top_chunks(db, query_vector, document_id=document_id)
    return [
        {
            "document_id": r.document_id,
            "filename": r.document.filename if r.document else None,
            "content": r.content,
            "preview": chunk_preview(r.content),
            "message": "I found this relevant part:",
        }
        for r in results
    ]


@app.post("/ask/")
async def ask_assistant(
    question: str,
    document_id: int | None = Query(default=None),
    db: Session = Depends(database.get_db),
):
    if document_id is not None:
        document = get_document_or_404(db, document_id)
    else:
        document = None

    try:
        query_vector = processor.get_embedding_model().encode(question).tolist()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    results = find_top_chunks(db, query_vector, document_id=document_id)
    if not results:
        return {
            "answer": "I don't know based on the documents currently uploaded.",
            "sources_used": 0,
        }

    context_text = "\n\n".join([r.content for r in results])

    prompt = f"""
    You are a helpful Research Assistant. 
    Use the following pieces of context to answer the user's question.
    If the answer is not in the context, say that you don't know based on the documents.
    
    CONTEXT:
    {context_text}
    
    QUESTION:
    {question}
    """

    client = get_genai_client()
    response = client.models.generate_content(
        model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
        contents=prompt
    )

    return {
        "answer": response.text,
        "sources_used": len(results),
        "document_scope": document.filename if document is not None else "all documents",
        "sources": [
            {
                "document_id": result.document_id,
                "filename": result.document.filename if result.document else None,
                "preview": chunk_preview(result.content),
            }
            for result in results
        ],
    }
