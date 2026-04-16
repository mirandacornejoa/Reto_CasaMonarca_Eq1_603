import logging
import warnings
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.core.database import Base, engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)

    # Startup checks
    if not settings.smtp_configured:
        warnings.warn(
            "SMTP no está configurado (faltan SMTP_HOST, SMTP_USER o SMTP_PASSWORD). "
            "El sistema usará MODO DEMO para correos. Los enlaces de activación y códigos OTP "
            "estarán disponibles solo a través de los endpoints de demo.",
            stacklevel=2,
        )
        logger.warning(
            "SMTP no configurado — modo demo activo para correos "
            "(activación y 2FA). Configure SMTP_HOST, SMTP_USER y SMTP_PASSWORD "
            "en .env para enviar correos reales."
        )
    yield


def create_application() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    def healthcheck() -> dict:
        return {"status": "ok"}

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_application()
