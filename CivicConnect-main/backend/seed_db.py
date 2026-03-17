from backend.database import SessionLocal, engine
from backend import models
from backend.auth import get_password_hash
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

def seed():
    db = SessionLocal()
    # Clear existing data
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)

    # 1. 2 Admin accounts
    admins = [
        models.Admin(name="Admin One", email="admin@civicconnect.app", password_hash=get_password_hash("admin123"), department="General"),
        models.Admin(name="Head of Roads", email="roads@civicconnect.app", password_hash=get_password_hash("admin123"), department="Roads")
    ]
    db.add_all(admins)

    # 2. 5 Sample Workers
    workers = [
        models.Worker(name="John Doe", department="Roads", phone="1234567890", status="free"),
        models.Worker(name="Jane Smith", department="Sanitation", phone="0987654321", status="free"),
        models.Worker(name="Mike Ross", department="Electrical", phone="1122334455", status="busy", active_job_count=1),
        models.Worker(name="Harvey Specter", department="Water", phone="5566778899", status="free"),
        models.Worker(name="Donna Paulsen", department="Roads", phone="6677889900", status="off_duty")
    ]
    db.add_all(workers)

    # 3. 3 Sample Citizens
    citizens = [
        models.Citizen(name="Alice Citizen", email="alice@example.com", password_hash=get_password_hash("password123"), points=50, level="Bronze", streak_days=2),
        models.Citizen(name="Bob Burger", email="bob@example.com", password_hash=get_password_hash("password123"), points=120, level="Silver", streak_days=5),
        models.Citizen(name="Charlie Day", email="charlie@example.com", password_hash=get_password_hash("password123"), points=350, level="Gold", streak_days=10)
    ]
    db.add_all(citizens)
    db.flush()

    # 4. 10 Sample Complaints
    categories = ["Pothole", "Garbage", "Street Light", "Water Leakage", "Road Damage"]
    filenames = ["pothole.png", "garbage.png", "streetlight.png", "water.png", "roaddamage.png"]
    for i in range(10):
        cat_idx = i % 5
        filename = filenames[cat_idx]
        c = models.Complaint(
            citizen_id=citizens[i % 3].id,
            category=categories[cat_idx],
            description=f"Issue description for complaint {i+1}",
            photo_url=f"http://localhost:8000/static/{filename}",
            latitude=12.9716 + (i * 0.001),
            longitude=77.5946 + (i * 0.001),
            status="Pending" if i < 5 else "In-Progress",
            current_stage=0 if i < 5 else 3,
            severity="Medium" if i % 2 == 0 else "High",
            sla_deadline=datetime.utcnow() + timedelta(days=5),
            stage_timestamps={"0": datetime.utcnow().isoformat()}
        )
        db.add(c)

    db.commit()
    print("Database seeded successfully!")

if __name__ == "__main__":
    seed()
