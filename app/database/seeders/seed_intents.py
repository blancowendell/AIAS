from ..models.intent import Intent
from .. import SessionLocal

items = [
    Intent(
        name="employee",
        keywords=["employee", "employees", "headcount", "active staff"],
        endpoint="/index/countactive",
        method="GET",
        response_path="data.activeCount",  # path to extract from API response
        response_template="There are {activeCount} active employees."  # template for AI reply
    ),
    # You can add more dynamic intents here
]

with SessionLocal() as db:
    for it in items:
        # Check if intent already exists
        existing = db.query(Intent).filter_by(name=it.name).first()
        if not existing:
            db.add(it)
    db.commit()

print("Seeder completed successfully.")
