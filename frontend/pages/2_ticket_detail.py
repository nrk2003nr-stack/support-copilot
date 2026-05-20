import streamlit as st
import requests
import json

API = "http://localhost:8000"

st.title("🤖 Ticket Detail & AI Response")

ticket_id = st.session_state.get("selected_ticket_id")

if not ticket_id:
    ticket_id = st.number_input("Enter Ticket ID", min_value=1, step=1, value=1)

try:
    r = requests.get(f"{API}/tickets/{ticket_id}", timeout=5)
    if not r.ok:
        st.error("Ticket not found.")
        st.stop()
    ticket = r.json()
except Exception as e:
    st.error(f"Cannot connect to backend: {e}")
    st.stop()

# --- Ticket Info ---
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader(f"#{ticket['id']}: {ticket['subject']}")
    st.write(f"**Customer:** {ticket['customer_name']} ({ticket['customer_email']})")
    st.write(f"**Customer ID:** `{ticket['customer_id']}`")

with col2:
    status_map = {
        "open": "🟡 Open",
        "in_progress": "🔵 In Progress",
        "resolved": "✅ Resolved",
        "escalated": "🔴 Escalated"
    }
    st.write(f"**Status:** {status_map.get(ticket['status'], ticket['status'])}")
    st.write(f"**Priority:** {ticket['priority'].upper()}")
    st.write(f"**Category:** {ticket['category']}")

st.divider()
st.subheader("Customer Message")
st.info(ticket['description'])

# --- Context Panel ---
if ticket.get("memory_context_used"):
    with st.expander("🧠 Memory Context Used by AI"):
        st.write(ticket["memory_context_used"])

if ticket.get("kb_sources_used"):
    with st.expander("📚 Knowledge Base Sources Used"):
        try:
            sources = json.loads(ticket["kb_sources_used"])
            for s in sources:
                st.write(f"- {s}")
        except Exception:
            st.write(ticket["kb_sources_used"])

# --- AI Response Generation ---
st.divider()
st.subheader("AI Draft Response")

if not ticket.get("ai_draft_response"):
    if st.button("🤖 Generate AI Response", type="primary"):
        with st.spinner("Running AI agent pipeline (RAG + Memory + CRM + Billing)..."):
            r = requests.post(f"{API}/agent/generate/{ticket_id}", timeout=600)
            if r.ok:
                st.success("AI response generated!")
                st.rerun()
            else:
                st.error(f"Error: {r.text}")
else:
    st.success("AI draft response ready:")
    draft = st.text_area(
        "Draft Response (editable):",
        value=ticket["ai_draft_response"],
        height=300,
        key="draft_editor"
    )

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button("✅ Approve & Save Response"):
            r = requests.patch(
                f"{API}/tickets/{ticket_id}",
                json={"agent_final_response": draft, "status": "in_progress"}
            )
            if r.ok:
                st.success("Response saved!")
                st.rerun()

    with col_b:
        if st.button("🔁 Regenerate"):
            r = requests.post(f"{API}/agent/generate/{ticket_id}", timeout=300)
            if r.ok:
                st.rerun()

    with col_c:
        if st.button("✅ Resolve & Save to Memory", type="primary"):
            # This saves the interaction to Mem0 for future personalization
            if ticket.get("agent_final_response") or ticket.get("ai_draft_response"):
                r = requests.post(f"{API}/agent/resolve/{ticket_id}", timeout=300)
                if r.ok:
                    st.success("Ticket resolved! Interaction saved to customer memory 🧠")
                    st.rerun()