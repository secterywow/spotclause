from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.pricing import RegionalPricing
from app.data.initial_pricing import INITIAL_PRICING


def init_pricing_data(db: Session):
    """Initialize regional pricing data if empty."""
    count = db.query(RegionalPricing).count()
    if count > 0:
        return

    for data in INITIAL_PRICING:
        pricing = RegionalPricing(**data)
        db.add(pricing)
    db.commit()


def get_pricing_by_country(db: Session, country_code: str):
    """Get pricing for a specific country."""
    pricing = db.query(RegionalPricing).filter(
        RegionalPricing.country_code == country_code.upper(),
        RegionalPricing.enabled == True
    ).first()

    if not pricing:
        # Fallback to US pricing
        pricing = db.query(RegionalPricing).filter(
            RegionalPricing.country_code == "US"
        ).first()

    return pricing


def get_all_pricing(db: Session):
    """Get all active pricing configurations."""
    return db.query(RegionalPricing).filter(RegionalPricing.enabled == True).all()


def detect_country_from_ip(ip: str) -> str:
    """Detect country from IP address.
    In production, use a GeoIP service.
    For development, return US as default."""
    # TODO: Integrate with GeoIP service (e.g., ipapi, ipinfo)
    # For now, return US as default
    if ip == "127.0.0.1" or ip.startswith("192.168."):
        return "US"
    return "US"
