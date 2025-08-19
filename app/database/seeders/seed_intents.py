# app/database/seeders/seed_intents.py
from ..models.intent import Intent
from ..database import SessionLocal

items = [
    Intent(
        i_name="employee",
        i_keywords=["employee","employees","headcount","active staff"],
        i_endpoint="/index/countactive",
        i_method="GET",
        i_response_path="data.activeCount",
        i_response_template="There are {activeCount} active employees."
    ),
]

with SessionLocal() as db:
    for it in items:
        # Use i_name instead of name
        if not db.query(Intent).filter_by(i_name=it.i_name).first():
            db.add(it)
    db.commit()

print("Seeder completed successfully.")
