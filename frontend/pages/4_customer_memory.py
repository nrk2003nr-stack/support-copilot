import streamlit as st
import requests

API = "http://localhost:8000"

st.title("🧠 Customer Memory Viewer")
st.write("View what Mem0 has learned about each customer across all their interactions.")

customer_id = st.text_input("Enter Customer ID", value="CUST001")

if st.button("Load Memory"):
    r = requests.get(f"{API}/memory/{customer_id}", timeout=10)
    if r.ok:
        data = r.json()
        memories = data.get("memories", [])
        if not memories:
            st.info(f"No memories stored yet for customer {customer_id}")
        else:
            st.success(f"Found {len(memories)} memories for {customer_id}")
            for i, m in enumerate(memories, 1):
                with st.expander(f"Memory {i}"):
                    st.write(m.get("memory", ""))
                    if m.get("created_at"):
                        st.caption(f"Created: {m['created_at']}")
    else:
        st.error("Could not fetch memories.")

if st.button("🗑️ Delete All Memories (GDPR)", type="secondary"):
    r = requests.delete(f"{API}/memory/{customer_id}", timeout=10)
    if r.ok:
        st.warning(f"All memories deleted for {customer_id}")