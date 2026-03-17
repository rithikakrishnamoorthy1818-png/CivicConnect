import uuid
from datetime import datetime, timedelta
from .models import Voucher

def generate_bus_pass(db, citizen_id: int, pass_type: str):
    # pass_type: "bus_1day" or "bus_7day"
    days = 1 if pass_type == "bus_1day" else 7
    expires_at = datetime.utcnow() + timedelta(days=days)
    
    new_voucher = Voucher(
        citizen_id=citizen_id,
        type=pass_type,
        qr_code=str(uuid.uuid4()),
        status="active",
        expires_at=expires_at
    )
    db.add(new_voucher)
    db.commit()
    return new_voucher
