from fastapi import FastAPI
from app.routes import assistant_routes
from app.routes.login_routes import router as login_router  

app = FastAPI(title="AIAS Assistant")

# Assistant routes
app.include_router(assistant_routes.router, prefix="/assistant", tags=["Assistant"])

# Login route to get HRMIS token
app.include_router(login_router, prefix="/login", tags=["Login"])
