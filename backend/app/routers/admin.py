from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.contract import ContractRecord
from app.models.pricing import RegionalPricing
from app.models.rule import RiskRule
from app.models.subscription import Subscription
from app.data.initial_pricing import INITIAL_PRICING
from app.data.initial_rules import INITIAL_RULES
import json

router = APIRouter(prefix="/api/admin", tags=["admin"])


def check_admin(user_id: int, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/dashboard")
def get_dashboard(user_id: int, db: Session = Depends(get_db)):
    check_admin(user_id, db)

    total_users = db.query(func.count(User.id)).scalar()
    total_contracts = db.query(func.count(ContractRecord.id)).scalar()
    total_subscriptions = db.query(func.count(Subscription.id)).filter(
        Subscription.status == "active"
    ).scalar()

    # Revenue calculation (simplified)
    subs = db.query(Subscription).filter(Subscription.status == "active").all()
    monthly_revenue = sum(
        float(s.plan == "pro" and 24.90 or 12.90)
        for s in subs
    )

    return {
        "totalUsers": total_users,
        "totalContracts": total_contracts,
        "activeSubscriptions": total_subscriptions,
        "monthlyRevenue": round(monthly_revenue, 2),
        "recentUsers": [
            {"id": u.id, "email": u.email, "name": u.name, "plan": u.plan, "createdAt": u.created_at}
            for u in db.query(User).order_by(User.created_at.desc()).limit(10).all()
        ]
    }


@router.get("/pricing")
def get_all_pricing(user_id: int, db: Session = Depends(get_db)):
    check_admin(user_id, db)
    pricing = db.query(RegionalPricing).all()
    return pricing


@router.put("/pricing/{country_code}")
def update_pricing(country_code: str, data: dict, user_id: int, db: Session = Depends(get_db)):
    check_admin(user_id, db)
    pricing = db.query(RegionalPricing).filter(
        RegionalPricing.country_code == country_code.upper()
    ).first()

    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing not found")

    for key, value in data.items():
        if hasattr(pricing, key):
            setattr(pricing, key, value)

    db.commit()
    db.refresh(pricing)
    return pricing


@router.get("/users")
def get_users(user_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    check_admin(user_id, db)
    users = db.query(User).offset(skip).limit(limit).all()
    return {
        "users": [
            {"id": u.id, "email": u.email, "name": u.name, "role": u.role,
             "plan": u.plan, "createdAt": u.created_at}
            for u in users
        ],
        "total": db.query(func.count(User.id)).scalar()
    }


@router.post("/users/{target_user_id}/toggle")
def toggle_user(target_user_id: int, user_id: int, db: Session = Depends(get_db)):
    check_admin(user_id, db)
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.role = "user" if target.role == "admin" else "admin"
    db.commit()
    return {"message": f"User role updated to {target.role}"}


@router.get("/rules")
def get_rules(user_id: int, db: Session = Depends(get_db)):
    check_admin(user_id, db)
    rules = db.query(RiskRule).all()
    return rules


@router.post("/rules/seed")
def seed_rules(user_id: int, db: Session = Depends(get_db)):
    check_admin(user_id, db)

    for rule_data in INITIAL_RULES:
        existing = db.query(RiskRule).filter(RiskRule.rule_id == rule_data["rule_id"]).first()
        if not existing:
            rule = RiskRule(**rule_data)
            db.add(rule)

    db.commit()
    return {"message": f"Seeded {len(INITIAL_RULES)} rules"}


@router.put("/rules/{rule_id}")
def update_rule(rule_id: str, data: dict, user_id: int, db: Session = Depends(get_db)):
    check_admin(user_id, db)
    rule = db.query(RiskRule).filter(RiskRule.rule_id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    for key, value in data.items():
        if hasattr(rule, key):
            setattr(rule, key, value)

    db.commit()
    db.refresh(rule)
    return rule
