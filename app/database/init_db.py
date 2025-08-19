# database/init_db.py
from app.database.database import engine, Base
from app.database.models.intent import Intent

def init_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created!")

if __name__ == "__main__":
    init_db()
