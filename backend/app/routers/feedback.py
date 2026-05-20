from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.feedback import Feedback
from app.utils.security import decode_access_token
from typing import List, Optional

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class SubmitFeedbackRequest(BaseModel):
    content: str


class FeedbackItem(BaseModel):
    id: int
    user_id: int
    user_email: str
    user_name: Optional[str]
    content: str
    created_at: str

    class Config:
        from_attributes = True


def get_current_user(
    authorization: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/")
def submit_feedback(
    req: SubmitFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit user feedback."""
    if not req.content or not req.content.strip():
        raise HTTPException(status_code=400, detail="Feedback content is required")

    feedback = Feedback(
        user_id=current_user.id,
        content=req.content.strip(),
    )
    db.add(feedback)
    db.commit()

    return {"message": "Feedback submitted successfully"}


@router.get("/", response_model=List[FeedbackItem])
def list_feedback(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all feedback (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    feedbacks = db.query(Feedback).order_by(Feedback.created_at.desc()).all()

    result = []
    for f in feedbacks:
        result.append({
            "id": f.id,
            "user_id": f.user_id,
            "user_email": f.user.email if f.user else "",
            "user_name": f.user.name if f.user else None,
            "content": f.content,
            "created_at": f.created_at.isoformat() if f.created_at else "",
        })

    return result
