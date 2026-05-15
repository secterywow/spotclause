from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models.contract import ContractRecord
from app.models.user import User
from app.utils.security import decode_access_token

router = APIRouter(prefix="/api/stats", tags=["stats"])


def get_time_label(date: datetime) -> str:
    """Convert datetime to human-readable time label."""
    # created_at is timezone-aware (TIMESTAMPTZ); use a matching now()
    tz = date.tzinfo or timezone.utc
    now = datetime.now(tz)
    diff = now - date

    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            return "Just now"
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.days < 30:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.days < 365:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"


@router.get("/user")
def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    """Get user statistics."""
    # Total analyzes
    total = db.query(func.count(ContractRecord.id)).filter(
        ContractRecord.user_id == user_id
    ).scalar() or 0

    # This week (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    this_week = db.query(func.count(ContractRecord.id)).filter(
        ContractRecord.user_id == user_id,
        ContractRecord.created_at >= week_ago
    ).scalar() or 0

    # High risk count
    high_risk = db.query(func.count(ContractRecord.id)).filter(
        ContractRecord.user_id == user_id,
        ContractRecord.high_risk_count > 0
    ).scalar() or 0

    # Average score
    avg_score = db.query(func.avg(ContractRecord.overall_score)).filter(
        ContractRecord.user_id == user_id,
        ContractRecord.overall_score.is_not(None)
    ).scalar() or 0

    # Last analyze time
    last_record = db.query(ContractRecord).filter(
        ContractRecord.user_id == user_id
    ).order_by(ContractRecord.created_at.desc()).first()

    # Risk type distribution
    risk_distribution = db.query(
        ContractRecord.contract_type,
        func.count(ContractRecord.id).label("count")
    ).filter(
        ContractRecord.user_id == user_id
    ).group_by(ContractRecord.contract_type).all()

    total_with_type = sum(r.count for r in risk_distribution) or 1

    return {
        "totalAnalyzes": total,
        "thisWeekChange": this_week,
        "highRiskFound": high_risk,
        "averageRiskScore": round(float(avg_score)) if avg_score else 0,
        "lastAnalyzeTime": get_time_label(last_record.created_at) if last_record else "Never",
        "riskTypeDistribution": [
            {
                "category": r.contract_type or "Unknown",
                "count": r.count,
                "percentage": round(r.count / total_with_type * 100)
            }
            for r in risk_distribution
        ]
    }
