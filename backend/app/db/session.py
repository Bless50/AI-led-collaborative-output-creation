from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Only needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency for FastAPI endpoints to get a database session.
    
    Yields:
        Session: SQLAlchemy database session
        
    Example:
        ```
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
