from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import Escalation, Ticket, Notification
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix='/escalations', tags=['escalations'])

class EscalationCreate(BaseModel):
    ticket_id: int
    reason: str

class EscalationResolve(BaseModel):
    admin_note: Optional[str] = None

@router.post('/')
def create_escalation(req: EscalationCreate, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == req.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    esc = Escalation(ticket_id=req.ticket_id, reason=req.reason)
    db.add(esc)
    ticket.status = 'escalated'
    notif = Notification(
        user_id='admin', type='escalation',
        message=f'Ticket #{req.ticket_id} escalated: {req.reason[:100]}'
    )
    db.add(notif)
    db.commit()
    db.refresh(esc)
    return esc

@router.get('/')
def list_escalations(status: str = None, db: Session = Depends(get_db)):
    q = db.query(Escalation)
    if status:
        q = q.filter(Escalation.status == status)
    return q.order_by(Escalation.created_at.desc()).all()

@router.patch('/{esc_id}/resolve')
def resolve_escalation(esc_id: int, req: EscalationResolve, db: Session = Depends(get_db)):
    esc = db.query(Escalation).filter(Escalation.id == esc_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail='Not found')
    esc.status = 'resolved'
    esc.admin_note = req.admin_note
    # Also resolve the parent ticket
    ticket = db.query(Ticket).filter(Ticket.id == esc.ticket_id).first()
    if ticket:
        ticket.status = 'resolved'
    db.commit()
    return {'message': 'Escalation resolved', 'escalation_id': esc_id}