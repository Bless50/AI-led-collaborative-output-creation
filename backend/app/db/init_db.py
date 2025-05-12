from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This function creates all tables defined in the SQLAlchemy models.
    It should be called when the application starts.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)
