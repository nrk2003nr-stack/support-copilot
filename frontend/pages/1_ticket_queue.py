import streamlit as st
import requests
import pandas as pd

API = "http://localhost:8000"

st.title("📋 Ticket Queue")

status_filter = st.selectbox(
    "Filter by Status",
    ["All", "open", "in_progress", "resolved", "escalated"]
)

if st.button("🔄 Refresh"):
    st.rerun()

url = f"{API}/tickets/"
if status_filter != "All":
    url += f"?status={status_filter}"

try:
    r = requests.get(url, timeout=5)
    tickets = r.json()

    if not tickets:
        st.info("No tickets found for this filter.")
    else:
        for ticket in tickets:
            priority_colors = {
                "urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"
            }
            icon = priority_colors.get(ticket["priority"], "⚪")
            ai_ready = "🤖 AI Draft Ready" if ticket["ai_draft_response"] else "⏳ Needs AI Draft"

            with st.expander(
                f"{icon} [{ticket['id']}] {ticket['subject']} — {ticket['customer_name']} | {ai_ready}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Customer:** {ticket['customer_name']}")
                    st.write(f"**Email:** {ticket['customer_email']}")
                    st.write(f"**Customer ID:** {ticket['customer_id']}")
                with col2:
                    st.write(f"**Status:** {ticket['status']}")
                    st.write(f"**Priority:** {ticket['priority']}")
                    st.write(f"**Category:** {ticket['category']}")

                st.write(f"**Issue:** {ticket['description'][:200]}...")

                if st.button(f"Open Ticket #{ticket['id']}", key=f"open_{ticket['id']}"):
                    st.session_state["selected_ticket_id"] = ticket["id"]
                    st.switch_page("pages/2_ticket_detail.py")

except Exception as e:
    st.error(f"Cannot connect to backend: {e}")

# Separator: create new ticket
st.divider()
st.subheader("Create Test Ticket")

with st.form("new_ticket_form"):
    col1, col2 = st.columns(2)
    with col1:
        cust_id = st.text_input("Customer ID", value="CUST001")
        cust_name = st.text_input("Customer Name", value="Alice Johnson")
        cust_email = st.text_input("Customer Email", value="alice@example.com")
    with col2:
        subject = st.text_input("Subject", value="Cannot access my account")
        priority = st.selectbox("Priority", ["low", "medium", "high", "urgent"])
        category = st.selectbox("Category", ["billing", "technical", "account", "general"])

    description = st.text_area(
        "Customer Message",
        value="Hi, I've been unable to log into my account for the past 2 days. I've tried resetting my password but the link isn't arriving in my email. Please help urgently."
    )

    submitted = st.form_submit_button("Submit Ticket")
    if submitted:
        payload = {
            "customer_id": cust_id,
            "customer_name": cust_name,
            "customer_email": cust_email,
            "subject": subject,
            "description": description,
            "priority": priority,
            "category": category
        }
        r = requests.post(f"{API}/tickets/", json=payload)
        if r.ok:
            st.success(f"Ticket #{r.json()['id']} created successfully!")
            st.rerun()
        else:
            st.error(f"Error: {r.text}")