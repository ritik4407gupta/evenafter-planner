import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

db_url = settings.database_url
# If running in Vercel or AWS Lambda with the default relative sqlite URL, route to writable /tmp
if (os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")) and db_url == "sqlite:///./everafter.db":
    db_url = "sqlite:////tmp/everafter.db"

# Convert postgres:// to postgresql:// if needed for SQLAlchemy 2.0
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

_tables_initialized = False

def init_tables():
    global _tables_initialized
    if not _tables_initialized:
        Base.metadata.create_all(bind=engine)
        _tables_initialized = True

def get_db():
    init_tables()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
