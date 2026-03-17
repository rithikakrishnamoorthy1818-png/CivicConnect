import os
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import base64

from .database import engine, get_db, Base
from . import models, auth, ai_detection, reward_engine, voucher_engine, notifications

# Initialize Database
models.Base.metadata.create_all(bind=engine)

from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Civic Connect API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# --- AUTH ROUTES ---

@app.post("/citizen/register")
def register_citizen(name: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(models.Citizen).filter(models.Citizen.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = auth.get_password_hash(password)
    new_citizen = models.Citizen(name=name, email=email, password_hash=hashed_pwd)
    db.add(new_citizen)
    db.commit()
    db.refresh(new_citizen)
    return {"message": "Citizen registered successfully"}

@app.post("/citizen/login")
def login_citizen(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.Citizen).filter(models.Citizen.email == email).first()
    if not user or not auth.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = auth.create_access_token(data={"sub": str(user.id), "role": "citizen"})
    return {"access_token": token, "token_type": "bearer", "role": "citizen", "user": {"name": user.name, "email": user.email}}

@app.post("/admin/login")
def login_admin(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.Admin).filter(models.Admin.email == email).first()
    if not user or not auth.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = auth.create_access_token(data={"sub": str(user.id), "role": "admin"})
    return {"access_token": token, "token_type": "bearer", "role": "admin", "user": {"name": user.name, "email": user.email, "department": user.department}}

# --- AI ROUTES ---

@app.post("/detect-image")
async def detect_image(file: UploadFile = File(...)):
    contents = await file.read()
    base64_img = base64.b64encode(contents).decode("utf-8")
    result = ai_detection.detect_issue_from_image(base64_img, file.filename)
    return result

# --- COMPLAINTS ROUTES ---

@app.post("/complaints")
def create_complaint(
    category: str = Form(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    severity: str = Form(...),
    photo_url: str = Form(None),
    ai_detected: bool = Form(False),
    ai_confidence: float = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.check_role("citizen"))
):
    # SLA Logic: 3 days for High/Critical, 7 days for others
    days = 3 if severity in ["High", "Critical"] else 7
    sla_deadline = datetime.utcnow() + timedelta(days=days)
    
    new_complaint = models.Complaint(
        citizen_id=current_user["id"],
        category=category,
        description=description,
        latitude=latitude,
        longitude=longitude,
        severity=severity,
        photo_url=photo_url,
        ai_detected=ai_detected,
        ai_confidence=ai_confidence,
        sla_deadline=sla_deadline,
        stage_timestamps={"0": datetime.utcnow().isoformat()}
    )
    db.add(new_complaint)
    
    # Award base points and update Streak
    reward_engine.award_points(db, current_user["id"], 25, "Complaint submitted")
    reward_engine.update_streak_and_award(db, current_user["id"])
    
    db.commit()
    db.refresh(new_complaint)
    return new_complaint

@app.get("/complaints")
def get_all_complaints(db: Session = Depends(get_db), current_user: dict = Depends(auth.check_role("admin"))):
    return db.query(models.Complaint).all()

@app.get("/complaints/my")
def get_my_complaints(db: Session = Depends(get_db), current_user: dict = Depends(auth.check_role("citizen"))):
    return db.query(models.Complaint).filter(models.Complaint.citizen_id == current_user["id"]).all()

@app.get("/complaints/{id}")
def get_complaint(id: int, db: Session = Depends(get_db), current_user: dict = Depends(auth.get_current_user)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@app.patch("/complaints/{id}/stage")
def advance_complaint_stage(id: int, new_stage: int, db: Session = Depends(get_db), current_user: dict = Depends(auth.check_role("admin"))):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    if new_stage <= complaint.current_stage:
        raise HTTPException(status_code=400, detail="Cannot go backwards in stages")

    complaint.current_stage = new_stage
    
    # Update stage metadata
    timestamps = complaint.stage_timestamps or {}
    timestamps[str(new_stage)] = datetime.utcnow().isoformat()
    complaint.stage_timestamps = timestamps
    
    admissions = complaint.stage_marked_by or {}
    admissions[str(new_stage)] = current_user["id"]
    complaint.stage_marked_by = admissions

    # Status updates
    if new_stage > 0:
        complaint.status = "In-Progress"
    if new_stage == 7:
        complaint.status = "Resolved"
        # Award resolve points
        reward_engine.award_points(db, complaint.citizen_id, 25, f"Complaint #{id} resolved")

    # Email Triggers (2, 4, 7)
    if new_stage in [2, 4, 7]:
        citizen = db.query(models.Citizen).filter(models.Citizen.id == complaint.citizen_id).first()
        # In a real app, we'd send this to EmailJS from frontend or background task
        # Here we just prepare the payload (for demo purposes)
        # payload = notifications.get_email_payload(complaint.id, citizen.name, new_stage)
        pass

    db.commit()
    return complaint

@app.post("/complaints/{id}/upvote")
def upvote_complaint(id: int, db: Session = Depends(get_db), current_user: dict = Depends(auth.check_role("citizen"))):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    if complaint.citizen_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot upvote your own complaint")
    
    complaint.upvotes += 1
    db.commit()
    return {"upvotes": complaint.upvotes}

# --- WORKER ROUTES ---

@app.get("/workers")
def get_workers(db: Session = Depends(get_db), current_user: dict = Depends(auth.check_role("admin"))):
    return db.query(models.Worker).all()

@app.post("/complaints/{id}/team")
def assign_team(id: int, worker_ids: list[int], db: Session = Depends(get_db), current_user: dict = Depends(auth.check_role("admin"))):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    # Clear existing team if any
    if complaint.team:
        db.delete(complaint.team)
    
    new_team = models.Team(complaint_id=id)
    db.add(new_team)
    db.flush()
    
    for idx, w_id in enumerate(worker_ids):
        worker = db.query(models.Worker).filter(models.Worker.id == w_id).first()
        if worker:
            role = "lead" if idx == 0 else "worker"
            member = models.TeamMember(team_id=new_team.id, worker_id=w_id, role=role)
            db.add(member)
            worker.active_job_count += 1
            worker.status = "busy"
            
    db.commit()
    return {"message": "Team assigned successfully"}

# --- REWARDS ROUTES ---

@app.get("/citizen/profile")
def get_profile(db: Session = Depends(get_db), current_user: dict = Depends(auth.check_role("citizen"))):
    citizen = db.query(models.Citizen).filter(models.Citizen.id == current_user["id"]).first()
    point_logs = db.query(models.PointLog).filter(models.PointLog.citizen_id == current_user["id"]).order_by(models.PointLog.timestamp.desc()).limit(10).all()
    vouchers = db.query(models.Voucher).filter(models.Voucher.citizen_id == current_user["id"]).all()
    
    return {
        "id": citizen.id,
        "name": citizen.name,
        "points": citizen.points,
        "level": citizen.level,
        "streak_days": citizen.streak_days,
        "point_history": point_logs,
        "vouchers_count": len(vouchers)
    }

@app.post("/rewards/redeem/{reward_id}")
def redeem_reward(reward_id: int, db: Session = Depends(get_db), current_user: dict = Depends(auth.check_role("citizen"))):
    citizen = db.query(models.Citizen).filter(models.Citizen.id == current_user["id"]).first()
    
    # Reward 1: Priority Boost (50 pts)
    if reward_id == 1:
        if citizen.points < 50:
            raise HTTPException(status_code=400, detail="Insufficient points")
        
        last_complaint = db.query(models.Complaint).filter(models.Complaint.citizen_id == citizen.id).order_by(models.Complaint.created_at.desc()).first()
        if not last_complaint:
            raise HTTPException(status_code=400, detail="No complaints found to boost")
        
        citizen.points -= 50
        last_complaint.priority_boosted = True
        
        redemption = models.Redemption(citizen_id=citizen.id, reward_type="Priority Boost", points_cost=50)
        db.add(redemption)
        
    # Reward 2: 1-Day Bus Pass (150 pts, Silver level)
    elif reward_id == 2:
        if citizen.points < 150: raise HTTPException(status_code=400, detail="Insufficient points")
        if citizen.level not in ["Silver", "Gold", "Diamond"]: raise HTTPException(status_code=400, detail="Silver level required")
        
        citizen.points -= 150
        voucher_engine.generate_bus_pass(db, citizen.id, "bus_1day")
        db.add(models.Redemption(citizen_id=citizen.id, reward_type="1-Day Bus Pass", points_cost=150))
        
    # Reward 3: 7-Day Bus Pass (500 pts, Gold level)
    elif reward_id == 3:
        if citizen.points < 500: raise HTTPException(status_code=400, detail="Insufficient points")
        if citizen.level not in ["Gold", "Diamond"]: raise HTTPException(status_code=400, detail="Gold level required")
        
        citizen.points -= 500
        voucher_engine.generate_bus_pass(db, citizen.id, "bus_7day")
        db.add(models.Redemption(citizen_id=citizen.id, reward_type="7-Day Bus Pass", points_cost=500))
    
    else:
        raise HTTPException(status_code=404, detail="Reward not found")
    
    db.commit()
    return {"message": "Reward redeemed successfully!", "current_points": citizen.points}

@app.get("/citizen/vouchers")
def get_vouchers(db: Session = Depends(get_db), current_user: dict = Depends(auth.check_role("citizen"))):
    return db.query(models.Voucher).filter(models.Voucher.citizen_id == current_user["id"]).all()

# --- ADMIN ANALYTICS ---

@app.get("/admin/analytics")
def get_analytics(db: Session = Depends(get_db), current_user: dict = Depends(auth.check_role("admin"))):
    total = db.query(models.Complaint).count()
    resolved = db.query(models.Complaint).filter(models.Complaint.status == "Resolved").count()
    breached = db.query(models.Complaint).filter(models.Complaint.status == "Breach").count() # Placeholder logic
    
    # Category Distribution
    categories = db.query(models.Complaint.category, models.Complaint.id).all()
    dist = {}
    for c, _id in categories:
        dist[c] = dist.get(c, 0) + 1
        
    return {
        "stats": {
            "total": total,
            "resolved": resolved,
            "breached": breached,
            "active_workers": db.query(models.Worker).filter(models.Worker.status == "busy").count()
        },
        "category_dist": dist
    }
