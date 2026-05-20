"""
CRM Tool — simulates CRM lookup.
In production: replace with HubSpot/Salesforce/Zendesk API call.
"""

from langchain_core.tools import tool

# Simulated CRM database
MOCK_CRM = {
    "CUST001": {
        "name": "Alice Johnson",
        "plan": "Pro",
        "since": "2022-03-15",
        "tickets_last_90_days": 2,
        "account_manager": "Bob Smith",
        "health_score": "Good"
    },
    "CUST002": {
        "name": "David Chen",
        "plan": "Enterprise",
        "since": "2020-01-10",
        "tickets_last_90_days": 8,
        "account_manager": "Sarah Lee",
        "health_score": "At Risk"
    }
}

@tool
def lookup_crm(customer_id: str) -> dict:
    """
    Look up a customer's CRM profile by their customer ID.
    Returns their subscription plan, account health, and support history.
    """
    data = MOCK_CRM.get(customer_id)
    if not data:
        return {"error": f"Customer {customer_id} not found in CRM"}
    return data