from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.database import get_db
from backend.db.models import Feedback, Notification
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix='/feedback', tags=['feedback'])

class FeedbackCreate(BaseModel):
    ticket_id: int
    customer_id: str
    rating: int
    subject: Optional[str] = None
    message: Optional[str] = None

@router.post('/')
def submit_feedback(req: FeedbackCreate, db: Session = Depends(get_db)):
    if not 1 <= req.rating <= 5:
        raise HTTPException(status_code=400, detail='Rating must be 1-5')
    fb = Feedback(**req.model_dump())
    db.add(fb)
    notif = Notification(
        user_id='admin', type='feedback',
        message=f'Ticket #{req.ticket_id} rated {req.rating}/5 by {req.customer_id}'
    )
    db.add(notif)
    db.commit()
    db.refresh(fb)
    return fb

@router.get('/')
def list_feedback(db: Session = Depends(get_db)):
    return db.query(Feedback).order_by(Feedback.created_at.desc()).all()

@router.get('/stats')
def feedback_stats(db: Session = Depends(get_db)):
    feedbacks = db.query(Feedback).all()
    if not feedbacks:
        return {'total': 0, 'average_rating': 0}
    ratings = [f.rating for f in feedbacks]
    breakdown = {f'{r}_star': ratings.count(r) for r in range(1, 6)}
    return {
        'total': len(ratings),
        'average_rating': round(sum(ratings) / len(ratings), 2),
        'rating_breakdown': breakdown
    }