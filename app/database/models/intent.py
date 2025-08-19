from sqlalchemy import Column, Integer, String, JSON
from app.database import Base

class Intent(Base):
    __tablename__ = "intents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    keywords = Column(JSON, nullable=False)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    response_path = Column(String(255), nullable=True)
    response_template = Column(String(255), nullable=True)
