from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from datetime import datetime, timedelta

app = FastAPI()

# ==== Database setup ====
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS licenses (
    license_key TEXT PRIMARY KEY,
    hwid TEXT,
    expiry DATE
)""")
conn.commit()

# ==== Models ====
class VerifyRequest(BaseModel):
    license_key: str
    hwid: str

class CreateLicenseRequest(BaseModel):
    license_key: str
    duration_days: int

# ==== Endpoints ====
@app.post("/verify")
def verify(req: VerifyRequest):
    c.execute("SELECT hwid, expiry FROM licenses WHERE license_key=?", (req.license_key,))
    result = c.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="License not found")
    
    hwid_db, expiry = result
    expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
    if datetime.now() > expiry_date:
        raise HTTPException(status_code=403, detail="License expired")
    
    if hwid_db != "" and hwid_db != req.hwid:
        raise HTTPException(status_code=403, detail="HWID mismatch")
    
    # Bind HWID if not set
    if hwid_db == "":
        c.execute("UPDATE licenses SET hwid=? WHERE license_key=?", (req.hwid, req.license_key))
        conn.commit()
    
    return {"status": "valid", "expiry": expiry}

@app.post("/create_license")
def create_license(req: CreateLicenseRequest):
    expiry_date = (datetime.now() + timedelta(days=req.duration_days)).strftime("%Y-%m-%d")
    try:
        c.execute("INSERT INTO licenses (license_key, hwid, expiry) VALUES (?, '', ?)", 
                  (req.license_key, expiry_date))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="License key already exists")
    return {"status": "created", "expiry": expiry_date}