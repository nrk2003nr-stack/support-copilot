from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.database import get_db
from backend.db.models import Ticket, Escalation, Feedback, AgentRunLog, Customer, Notification, Admin
from backend.core.auth import hash_password
from pydantic import BaseModel

router = APIRouter(prefix='/admin', tags=['admin'])

class AdminCreate(BaseModel):
    username: str
    email: str
    password: str

@router.post('/setup')
def create_admin(req: AdminCreate, db: Session = Depends(get_db)):
    if db.query(Admin).filter(Admin.email == req.email).first():
        raise HTTPException(status_code=400, detail='Admin already exists')
    admin = Admin(username=req.username, email=req.email,
                  password=hash_password(req.password))
    db.add(admin)
    db.commit()
    return {'message': f'Admin {req.username} created successfully'}

@router.get('/dashboard')
def admin_dashboard(db: Session = Depends(get_db)):
    total_tickets    = db.query(Ticket).count()
    open_tickets     = db.query(Ticket).filter(Ticket.status == 'open').count()
    resolved_tickets = db.query(Ticket).filter(Ticket.status == 'resolved').count()
    escalated        = db.query(Ticket).filter(Ticket.status == 'escalated').count()
    open_escalations = db.query(Escalation).filter(Escalation.status == 'open').count()
    avg_rating_row   = db.query(func.avg(Feedback.rating)).scalar()
    avg_rating       = round(float(avg_rating_row), 2) if avg_rating_row else 0
    total_customers  = db.query(Customer).count()
    unread_notifs    = db.query(Notification).filter(
        Notification.user_id == 'admin',
        Notification.is_read == False
    ).count()
    return {
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'resolved_tickets': resolved_tickets,
        'escalated_tickets': escalated,
        'open_escalations': open_escalations,
        'avg_satisfaction_rating': avg_rating,
        'total_customers': total_customers,
        'unread_notifications': unread_notifs
    }

@router.get('/customers')
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()

@router.get('/logs')
def get_agent_logs(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(AgentRunLog).order_by(
        AgentRunLog.created_at.desc()
    ).limit(limit).all()