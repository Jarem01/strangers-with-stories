from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# For development, use SQLite (no setup needed)
# Later, we'll switch to PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stories.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the Story model
class Story(Base):
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)  # NEW
    author_name = Column(String(255), nullable=True)
    author_email = Column(String(255), nullable=True)
    story_text = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
