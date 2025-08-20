# app/main.py or wherever you initialize FastAPI
from fastapi import FastAPI
from app.routes import assistant_routes
from app.routes.login_routes import router as login_router
from app.routes import pdf_routes  # <-- import your new PDF routes
from app.routes import train_routes

app = FastAPI(title="AIAS Assistant")

# Assistant routes
app.include_router(assistant_routes.router, prefix="/assistant", tags=["Assistant"])

# Login route to get HRMIS token
app.include_router(login_router, prefix="/login", tags=["Login"])

# PDF routes
app.include_router(pdf_routes.router, prefix="/pdf", tags=["PDF Documents"])

# Train AI
app.include_router(train_routes.router, prefix="/train", tags=["Train"])