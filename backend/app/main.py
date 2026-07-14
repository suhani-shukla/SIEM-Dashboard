from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import router as v1_router
from app.core import redis as redis_core
from app.db.session import engine, async_session_factory
from app.rules.engine import RuleEngine
from app.playbooks.loader import load_playbooks
import logging
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = await redis_core.get_redis_client()
    
    async with async_session_factory() as session:
        rules = await load_playbooks(session)
        
    app.state.rule_engine = RuleEngine(redis_client=redis_client, rules=rules)
    await app.state.rule_engine.start()
    yield
    await app.state.rule_engine.stop()
    await redis_core.close_redis_client()
    await engine.dispose()


app = FastAPI(title="SIEM Dashboard API", version="0.1.0", lifespan=lifespan)
app.include_router(v1_router, prefix="/api/v1")

# in app/main.py, near your FastAPI() app creation
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": str(exc.errors()),
            }
        },
    )


@app.get("/health")
async def health() -> dict:
    db_ok = False
    redis_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    try:
        redis_ok = await redis_core.redis_health_check()
    except Exception:
        pass

    return {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "database": db_ok,
        "redis": redis_ok,
    }
