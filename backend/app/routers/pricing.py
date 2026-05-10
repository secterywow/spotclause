from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.pricing import get_pricing_by_country, detect_country_from_ip, init_pricing_data
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/pricing", tags=["pricing"])


@router.on_event("startup")
def startup_init_pricing(db: Session = Depends(get_db)):
    """Initialize pricing data on startup."""
    init_pricing_data(db)


@router.get("/detect")
def detect_pricing(request: Request, db: Session = Depends(get_db)):
    """Detect user's country from IP and return pricing."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    country_code = detect_country_from_ip(client_ip)
    pricing = get_pricing_by_country(db, country_code)

    if not pricing:
        return {"error": "Pricing not available"}

    return {
        "country_code": pricing.country_code,
        "region_name": pricing.region_name,
        "currency": pricing.currency,
        "plans": {
            "free": {
                "name": "Free",
                "price_monthly": 0,
                "price_yearly": 0,
                "features": {
                    "analyze": "1 lifetime (1MB limit)",
                    "compare": "0",
                    "follow_up": False,
                    "export": True,
                }
            },
            "standard": {
                "name": "Standard",
                "price_monthly": float(pricing.standard_monthly),
                "price_yearly": float(pricing.standard_yearly),
                "features": {
                    "analyze": "10 per month",
                    "compare": "10 per month",
                    "follow_up": True,
                    "export": True,
                }
            },
            "pro": {
                "name": "Pro",
                "price_monthly": float(pricing.pro_monthly),
                "price_yearly": float(pricing.pro_yearly),
                "features": {
                    "analyze": "50 per month",
                    "compare": "50 per month",
                    "follow_up": True,
                    "export": True,
                }
            }
        }
    }


@router.get("/{country_code}")
def get_pricing(country_code: str, db: Session = Depends(get_db)):
    """Get pricing for a specific country."""
    pricing = get_pricing_by_country(db, country_code)

    if not pricing:
        return {"error": "Pricing not available for this region"}

    return {
        "country_code": pricing.country_code,
        "region_name": pricing.region_name,
        "currency": pricing.currency,
        "standard_monthly": float(pricing.standard_monthly),
        "standard_yearly": float(pricing.standard_yearly),
        "pro_monthly": float(pricing.pro_monthly),
        "pro_yearly": float(pricing.pro_yearly),
    }
