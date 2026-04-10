from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

Base = declarative_base()

is_sqlite = settings.resolved_database_url.startswith("sqlite")
engine = create_engine(
    settings.resolved_database_url,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
