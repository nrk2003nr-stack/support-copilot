import streamlit as st

st.set_page_config(
    page_title="AI Support Copilot",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎧 AI Customer Support Copilot")
st.markdown("""
Welcome to the **AI-Powered Support Copilot**.

Use the sidebar to navigate:
- 📋 **Ticket Queue** — View and manage all open tickets
- 🤖 **Ticket Detail** — Generate AI responses for individual tickets  
- 📚 **Knowledge Base** — Upload support documents for RAG
- 🧠 **Customer Memory** — View what the AI remembers about customers

**Tech Stack:** FastAPI · ChromaDB · Mem0 · LangGraph · SQLite
""")

# Show system stats
col1, col2, col3 = st.columns(3)

import requests

try:
    r = requests.get("http://localhost:8000/knowledge/stats", timeout=2)
    kb_stats = r.json()
    tickets_r = requests.get("http://localhost:8000/tickets/?status=open", timeout=2)
    open_tickets = len(tickets_r.json()) if tickets_r.ok else 0

    with col1:
        st.metric("KB Vectors Indexed", kb_stats.get("total_vectors", 0))
    with col2:
        st.metric("Open Tickets", open_tickets)
    with col3:
        st.metric("API Status", "✅ Online")
except Exception:
    st.warning("⚠️ Backend not running. Start with: `uvicorn backend.main:app --reload`")