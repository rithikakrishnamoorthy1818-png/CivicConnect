from datetime import datetime, timedelta
from .models import Citizen, PointLog

def calculate_citizen_level(points: int) -> str:
    if points < 100:
        return "Bronze"
    elif points < 300:
        return "Silver"
    elif points < 600:
        return "Gold"
    else:
        return "Diamond"

def award_points(db, citizen_id: int, points: int, action: str):
    citizen = db.query(Citizen).filter(Citizen.id == citizen_id).first()
    if not citizen:
        return
    
    citizen.points += points
    citizen.level = calculate_citizen_level(citizen.points)
    
    log = PointLog(citizen_id=citizen_id, action=action, points_earned=points)
    db.add(log)
    db.commit()
    return citizen.level

def update_streak_and_award(db, citizen_id: int):
    citizen = db.query(Citizen).filter(Citizen.id == citizen_id).first()
    if not citizen:
        return
    
    now = datetime.utcnow()
    today = now.date()
    
    if citizen.last_reported:
        last_date = citizen.last_reported.date()
        if last_date == today:
            return # Already reported today, no streak change
        elif last_date == today - timedelta(days=1):
            citizen.streak_days += 1
        else:
            citizen.streak_days = 1
    else:
        citizen.streak_days = 1
    
    citizen.last_reported = now
    
    # Streak Milestones
    bonus = 0
    if citizen.streak_days == 3:
        bonus = 20
    elif citizen.streak_days == 7:
        bonus = 50
    elif citizen.streak_days == 30:
        bonus = 200
    
    if bonus > 0:
        award_points(db, citizen_id, bonus, f"{citizen.streak_days}-day streak bonus")
    
    db.commit()
