from sqlalchemy import Column, Integer, String, JSON
from app.database import Base

class Intent(Base):
    __tablename__ = "intents"

    i_id = Column(Integer, primary_key=True, index=True)
    i_name = Column(String(50), unique=True, nullable=False)
    i_keywords = Column(JSON, nullable=False)
    i_endpoint = Column(String(255), nullable=False)
    i_method = Column(String(10), nullable=False)
    i_response_path = Column(String(255), nullable=True)
    i_response_template = Column(String(255), nullable=True)
