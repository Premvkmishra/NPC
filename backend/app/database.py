from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Handle relative sqlite path nicely
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///./"):
    # Ensure database path is anchored to BASE_DIR if relative
    from app.config import BASE_DIR
    relative_path = db_url.replace("sqlite:///./", "")
    db_file = BASE_DIR / relative_path
    connect_url = f"sqlite:///{db_file}"
else:
    connect_url = db_url

engine = create_engine(
    connect_url,
    connect_args={"check_same_thread": False} if "sqlite" in connect_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

