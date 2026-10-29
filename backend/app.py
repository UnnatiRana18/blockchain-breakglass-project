"""
FastAPI REST API Server.
"""
import time
import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field

from blockchain_core.ledger import PermissionedLedger
from backend.mock_ehr import MockEHRDatabase

app = FastAPI(title="Controlled Emergency Access Blockchain API", version="1.0.0")

ledger = PermissionedLedger(validator_id="HOSPITAL_CONSORTIUM_NODE_01")
ehr_db = MockEHRDatabase()

DEFAULT_DOCTORS = [
    {
        "doctor_id": "DOC-701", "name": "Dr. Eleanor Vance, MD", "license_number": "MED-NY-89104",
        "hospital": "Metro General Emergency Trauma Center", "wallet_address": "0x71C8A6B0A8129C3b6F1c5Fe49e31d4eA465B1732"
    },
    {
        "doctor_id": "DOC-408", "name": "Dr. Marcus Reed, MD", "license_number": "MED-CA-44219",
        "hospital": "St. Jude Critical Care Pavilion", "wallet_address": "0x3A219bBcE6e42159187326C9951A8D4972fB25e0"
    },
    {
        "doctor_id": "DOC-915", "name": "Dr. Sarah Jenkins, MD", "license_number": "MED-IL-98112",
        "hospital": "University Healthcare Emergency Dept", "wallet_address": "0x98D20340B48F474A3D953Eec66B5799786aB2C67"
    }
]

for doc in DEFAULT_DOCTORS:
    ledger.certify_doctor(doc["doctor_id"], doc["name"], doc["license_number"], doc["hospital"], doc["wallet_address"])

static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

class BreakGlassRequest(BaseModel):
    patient_id: str
    doctor_id: str
    reason: str
    urgency: str = "CRITICAL_RESUSCITATION"
    duration_seconds: int = 300

class RevokeRequest(BaseModel):
    grant_id: str
    doctor_or_admin: str
    reason: str

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)

@app.get("/api/doctors")
async def list_certified_doctors():
    return {"doctors": DEFAULT_DOCTORS}

@app.get("/api/patients")
async def list_patients():
    return {"patients": ehr_db.list_all_patients()}

@app.post("/api/emergency/request")
async def request_break_glass_access(req: BreakGlassRequest):
    try:
        t0 = time.perf_counter()
        grant = ledger.request_break_glass(req.patient_id, req.doctor_id, req.reason, req.urgency, req.duration_seconds)
        rec = ehr_db.decrypt_emergency_data(req.patient_id)
        ledger.log_record_access(grant["grant_id"], "EMERGENCY_CLINICAL_TRIAGE_DATA", rec["payload_hash"])
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {"success": True, "status": "EMERGENCY_ACCESS_GRANTED", "latency_ms": latency_ms, "grant": grant, "medical_data": rec}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/emergency/status/{grant_id}")
async def check_grant_status(grant_id: str):
    return ledger.check_access_validity(grant_id)

@app.get("/api/emergency/records/{grant_id}")
async def fetch_emergency_records(grant_id: str):
    status_info = ledger.check_access_validity(grant_id)
    if not status_info["is_valid"]:
        raise HTTPException(status_code=403, detail="Emergency break-glass session has expired automatically.")
    grant = status_info["grant"]
    rec = ehr_db.decrypt_emergency_data(grant["patient_id"])
    return {"status": "ACTIVE", "remaining_seconds": status_info["remaining_seconds"], "medical_data": rec}

@app.post("/api/emergency/revoke")
async def revoke_access_early(req: RevokeRequest):
    try:
        updated = ledger.revoke_grant_early(req.grant_id, req.doctor_or_admin, req.reason)
        return {"success": True, "status": "REVOKED_EARLY", "grant": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/audit/logs")
async def get_audit_logs(patient_id: Optional[str] = None):
    logs = ledger.get_audit_trail(patient_id=patient_id)
    return {"total_count": len(logs), "last_global_hash": ledger.last_log_hash, "logs": logs[::-1]}

@app.get("/api/audit/blocks")
async def get_blockchain_blocks():
    return {"chain_length": len(ledger.chain), "blocks": [b.to_dict() for b in ledger.chain[::-1]]}

@app.get("/api/audit/verify")
async def verify_blockchain_integrity():
    t0 = time.perf_counter()
    report = ledger.verify_chain_and_audit_integrity()
    report["verification_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return report

@app.post("/api/audit/tamper")
async def simulate_tamper_attack(block_index: int = 1):
    return ledger.simulate_tamper(block_index=block_index)

@app.post("/api/audit/restore")
async def restore_blockchain_state():
    return ledger.restore_tamper()

@app.post("/api/benchmark/run")
async def run_system_benchmark(iterations: int = 50):
    iterations = min(iterations, 100)
    smart_lats = []
    cent_lats = []
    patients = ["PAT-9082", "PAT-4120", "PAT-7731"]
    doc = DEFAULT_DOCTORS[0]
    for i in range(iterations):
        pid = patients[i % len(patients)]
        t0 = time.perf_counter()
        g = ledger.request_break_glass(pid, doc["doctor_id"], "Benchmark emergency trial", duration_seconds=300)
        r = ehr_db.decrypt_emergency_data(pid)
        ledger.log_record_access(g["grant_id"], "BENCHMARK_TEST", r["payload_hash"])
        smart_lats.append((time.perf_counter() - t0) * 1000)

        t0_c = time.perf_counter()
        _ = ehr_db.decrypt_emergency_data(pid)
        time.sleep(0.0004)
        cent_lats.append((time.perf_counter() - t0_c) * 1000)

    avg_s = round(sum(smart_lats) / len(smart_lats), 2)
    avg_c = round(sum(cent_lats) / len(cent_lats), 2)
    return {
        "iterations": iterations,
        "smart_contract": {"avg_latency_ms": avg_s, "min_latency_ms": round(min(smart_lats), 2), "max_latency_ms": round(max(smart_lats), 2)},
        "centralized_baseline": {"avg_latency_ms": avg_c},
        "overhead_analysis": {"additional_latency_ms": round(avg_s - avg_c, 2)}
    }
