# HRMIS AI Assistant

A FastAPI-based AI assistant for interacting with HRMIS services, including leave requests, payslips, attendance, and employee counts. The assistant can also fallback to Groq AI for general queries.

---

## Features

- **Leave Request**: Submit leave requests via HRMIS API.
- **Payslip**: Retrieve payslips for a given user.
- **Attendance**: Check attendance details.
- **Employee Count**: Get the count of active employees.
- **AI Fallback**: For queries not related to HRMIS APIs, uses Groq AI.

---

## Project Structure

app/
├─ models/
│ └─ assistant.py
├─ routes/
│ └─ assistant_routes.py
├─ services/
│ ├─ hrmis_service.py
│ ├─ intent_classifier.py
│ └─ groq_service.py
├─ config.py
main.py
requirements.txt


## HOW TO RUN

Windows:
python -m venv venv

venv\Scripts\activate

uvicorn app.main:app --reload

macOS/Linux:
python -m venv venv

source venv/bin/activate

uvicorn app.main:app --reload