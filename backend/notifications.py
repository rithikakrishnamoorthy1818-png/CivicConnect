import os
from dotenv import load_dotenv

load_dotenv()

def get_email_payload(complaint_id: int, citizen_name: str, stage: int, eta: str = "TBD"):
    template_params = {
        "complaint_id": complaint_id,
        "to_name": citizen_name,
        "eta": eta,
        "tracking_link": f"civicconnect.app/citizen/track/{complaint_id}"
    }

    if stage == 2:
        subject = f"Team Assigned to Your Complaint #{complaint_id}"
        message = f"A team has been assembled and assigned to your complaint. Current ETA for resolution is {eta}."
    elif stage == 4:
        subject = f"Work Has Started on Your Complaint #{complaint_id}"
        message = f"Our team has arrived on site and started working on your reported issue."
    elif stage == 7:
        subject = f"Your Complaint #{complaint_id} is Resolved!"
        message = "We are happy to inform you that your reported issue has been resolved. Thank you for helping us keep the city smart!"
    else:
        return None

    return {
        "service_id": os.getenv("EMAILJS_SERVICE_ID"),
        "template_id": os.getenv("EMAILJS_TEMPLATE_ID"),
        "user_id": os.getenv("EMAILJS_PUBLIC_KEY"),
        "template_params": {
            **template_params,
            "subject": subject,
            "message": message
        }
    }
