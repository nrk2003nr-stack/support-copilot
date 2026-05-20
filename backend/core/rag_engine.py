import os
from typing import List, Dict
from dotenv import load_dotenv

from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHAT_MODEL         = os.getenv("CHAT_MODEL", "llama3.2")
EMBEDDING_MODEL    = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

_embeddings   = None
_vector_store = None


def get_embeddings() -> OllamaEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_BASE_URL,
        )
    return _embeddings


def get_vector_store() -> Chroma:
    global _vector_store
    if _vector_store is None:
        _vector_store = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=get_embeddings(),
            collection_name="support_knowledge_base",
        )
    return _vector_store


def load_document(file_path: str) -> List[Document]:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext in (".docx", ".doc"):
        loader = Docx2txtLoader(file_path)
    elif ext in (".txt", ".md"):
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return loader.load()


def ingest_document(file_path: str, filename: str) -> int:
    """Load, chunk, embed and store a document in ChromaDB. Returns chunk count."""
    docs = load_document(file_path)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(docs)
    for chunk in chunks:
        chunk.metadata["source_file"] = filename

    vector_store = get_vector_store()
    vector_store.add_documents(chunks)
    return len(chunks)


def search_knowledge_base(query: str, k: int = 4) -> Dict:
    """Retrieve relevant KB docs and generate an answer using Ollama via LCEL chain."""
    vector_store = get_vector_store()
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    docs      = retriever.invoke(query)

    if not docs:
        return {
            "answer": "No relevant information found in the knowledge base.",
            "sources": [],
        }

    context = "\n\n".join(doc.page_content for doc in docs)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "You are a helpful customer support assistant.\n"
                "Answer the question based ONLY on the context below.\n"
                "If the context does not contain the answer, say: "
                "'I could not find relevant information in the knowledge base.'\n\n"
                "Context:\n{context}"
            ),
        ),
        ("human", "{question}"),
    ])

    chain    = prompt | llm
    response = chain.invoke({"context": context, "question": query})

    sources: List[str] = []
    for doc in docs:
        src = doc.metadata.get("source_file", "Unknown")
        if src not in sources:
            sources.append(src)

    return {"answer": response.content, "sources": sources}


def get_collection_count() -> int:
    try:
        return get_vector_store()._collection.count()
    except Exception:
        return 0