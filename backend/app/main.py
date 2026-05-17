from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, pricing, stripe, contract, follow_up, stats, admin, dodo
from app.middleware.logging import LoggingMiddleware
from app.logger import setup_logging
from app.database import engine, Base

settings = get_settings()

# Setup structured logging
setup_logging()

# Auto-create tables on startup (no manual migration needed on Render free tier)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description="AI-powered contract review and comparison",
    version="1.0.0",
    debug=settings.debug,
)

# Logging middleware
app.add_middleware(LoggingMiddleware)

# CORS
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://spotclause.app",
    "https://www.spotclause.app",
]
# Allow Vercel preview deployments
import os
if os.environ.get("VERCEL_URL"):
    origins.append(f"https://{os.environ['VERCEL_URL']}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(pricing.router)
app.include_router(stripe.router)
app.include_router(contract.router)
app.include_router(follow_up.router)
app.include_router(stats.router)
app.include_router(admin.router)
app.include_router(dodo.router)


@app.get("/health")
def health_check():
    import redis
    import psycopg2
    from app.config import get_settings

    settings = get_settings()
    checks = {"api": True, "database": False, "redis": False}

    # Check database
    try:
        conn = psycopg2.connect(settings.database_url.replace("+psycopg2", ""))
        conn.close()
        checks["database"] = True
    except:
        pass

    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = True
    except:
        pass

    all_ok = all(checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "service": settings.app_name,
        "version": "1.0.0",
        "checks": checks,
    }


@app.get("/")
def root():
    return {"message": f"Welcome to {settings.app_name} API"}
