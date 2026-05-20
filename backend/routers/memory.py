from fastapi import APIRouter, HTTPException
from backend.core.memory_engine import get_all_customer_memories, delete_customer_memory

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{customer_id}")
def get_customer_memory(customer_id: str):
    """Retrieve all Mem0 memories stored for a customer."""
    memories = get_all_customer_memories(customer_id)
    return {
        "customer_id": customer_id,
        "memories":    memories,
        "count":       len(memories),
    }


@router.delete("/{customer_id}")
def clear_customer_memory(customer_id: str):
    """Delete all memories for a customer (GDPR compliance)."""
    delete_customer_memory(customer_id)
    return {"message": f"All memories deleted for customer {customer_id}"}