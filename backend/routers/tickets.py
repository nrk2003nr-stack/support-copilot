from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.db.database import get_db
from backend.db.models import Ticket
from backend.db.schemas import TicketCreate, TicketUpdate, TicketResponse

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("/", response_model=List[TicketResponse])
def list_tickets(status: str = None, db: Session = Depends(get_db)):
    query = db.query(Ticket)
    if status:
        query = query.filter(Ticket.status == status)
    return query.order_by(Ticket.created_at.desc()).all()


@router.post("/", response_model=TicketResponse)
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    db_ticket = Ticket(**ticket.model_dump())
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(ticket_id: int, update: TicketUpdate, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(ticket, field, value)
    db.commit()
    db.refresh(ticket)
    return ticket