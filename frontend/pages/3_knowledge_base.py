import streamlit as st
import requests

API = "http://localhost:8000"

st.title("📚 Knowledge Base Management")

# Stats
r = requests.get(f"{API}/knowledge/stats", timeout=5)
if r.ok:
    stats = r.json()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Vectors in ChromaDB", stats["total_vectors"])
    with col2:
        st.metric("KB Status", stats["status"].upper())

st.divider()

# Upload
st.subheader("Upload Support Documents")
st.write("Supported formats: PDF, DOCX, TXT, Markdown")

uploaded_file = st.file_uploader(
    "Choose a file",
    type=["pdf", "docx", "txt", "md"]
)

if uploaded_file and st.button("Upload & Index"):
    with st.spinner(f"Indexing {uploaded_file.name}..."):
        files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
        r = requests.post(f"{API}/knowledge/upload", files=files, timeout=60)
        if r.ok:
            result = r.json()
            st.success(f"✅ {result['filename']} indexed with {result['chunks_indexed']} chunks!")
        else:
            st.error(f"Upload failed: {r.text}")

st.divider()

# Document list
st.subheader("Indexed Documents")
r = requests.get(f"{API}/knowledge/documents", timeout=5)
if r.ok:
    docs = r.json()
    if not docs:
        st.info("No documents indexed yet. Upload some support docs above.")
    for doc in docs:
        st.write(f"📄 **{doc['filename']}** — {doc['chunk_count']} chunks — {doc['status']}")