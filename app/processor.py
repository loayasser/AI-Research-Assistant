import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def get_embedding_model():
    global _model

    if _model is None:
        try:
            _model = SentenceTransformer(MODEL_NAME)
        except Exception as exc:
            raise RuntimeError(
                "Embedding model could not be loaded. Check internet/proxy access or pre-download "
                f"the Hugging Face model '{MODEL_NAME}'."
            ) from exc

    return _model

def extract_text_from_pdf(file_path: str) -> str:  # <--- Check this spelling!
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    except Exception as e:
        print(f"Error: {e}")
        return ""

def create_embeddings(text: str):  # <--- Check this spelling!
    if not text or not text.strip():
        return [], []

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_text(text)
    if not chunks:
        return [], []

    embeddings = get_embedding_model().encode(chunks)
    return chunks, embeddings
