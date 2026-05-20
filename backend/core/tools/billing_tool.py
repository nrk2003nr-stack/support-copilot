from langchain_core.tools import tool

MOCK_BILLING = {
    "CUST001": {
        "status": "Active",
        "plan": "Pro ($49/month)",
        "next_billing_date": "2026-06-15",
        "outstanding_amount": 0.00,
        "last_payment": "$49.00 on 2026-05-15",
        "payment_method": "Visa ending 4242"
    },
    "CUST002": {
        "status": "Payment Failed",
        "plan": "Enterprise ($299/month)",
        "next_billing_date": "2026-05-20",
        "outstanding_amount": 299.00,
        "last_payment": "Failed on 2026-05-10",
        "payment_method": "Mastercard ending 5555"
    }
}

@tool
def lookup_billing(customer_id: str) -> dict:
    """
    Look up a customer's billing and payment status by customer ID.
    Returns their current plan, billing dates, and payment history.
    """
    data = MOCK_BILLING.get(customer_id)
    if not data:
        return {"error": f"Billing record for {customer_id} not found"}
    return data