from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine_kwargs = (
    {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    if DATABASE_URL == "sqlite://"
    else (
        {"connect_args": {"check_same_thread": False}}
        if IS_SQLITE
        else {}
    )
)
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Helper to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
