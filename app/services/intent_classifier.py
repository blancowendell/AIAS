import string
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def classify_intent(message: str) -> str:
    """
    Classify the user's message into an HRMIS intent.
    """
    msg = message.lower().translate(str.maketrans("", "", string.punctuation))
    logger.debug(f"Classifying intent for message: {msg}")

    if "leave" in msg:
        logger.debug("Intent classified as leave_request")
        return "leave_request"

    if "payslip" in msg or "salary" in msg:
        logger.debug("Intent classified as payslip")
        return "payslip"

    if "attendance" in msg or "time in" in msg or "time out" in msg:
        logger.debug("Intent classified as attendance")
        return "attendance"

    employee_keywords = ["employee", "employees", "staff", "active staff", 
                         "headcount", "count employee", "total employees"]
    if any(word in msg for word in employee_keywords):
        logger.debug("Intent classified as employee")
        return "employee"

    logger.debug("Intent classified as general")
    return "general"
