from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import Notification

router = APIRouter(prefix='/notifications', tags=['notifications'])

@router.get('/{user_id}')
def get_notifications(user_id: str, db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).limit(50).all()
    unread = sum(1 for n in notifs if not n.is_read)
    return {'notifications': notifs, 'unread_count': unread}

@router.patch('/{notif_id}/read')
def mark_read(notif_id: int, db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.id == notif_id).first()
    if n:
        n.is_read = True
        db.commit()
    return {'message': 'Marked as read'}

@router.post('/{user_id}/read-all')
def mark_all_read(user_id: str, db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.user_id == user_id
    ).update({'is_read': True})
    db.commit()
    return {'message': 'All marked as read'}