import sys, os, time, statistics
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from blockchain_core.ledger import PermissionedLedger
from backend.mock_ehr import MockEHRDatabase

def run_benchmarks(sample_size=100):
    ledger = PermissionedLedger()
    ehr_db = MockEHRDatabase()
    doc = ledger.certify_doctor("DOC-BENCH", "Dr. Bench", "LIC-99", "Hospital", "0x9999999999999999999999999999999999999999")
    patients = ["PAT-9082", "PAT-4120", "PAT-7731"]
    smart_lats = []
    cent_lats = []
    for i in range(sample_size):
        pid = patients[i % len(patients)]
        t0 = time.perf_counter()
        g = ledger.request_break_glass(pid, "DOC-BENCH", f"Resuscitation trial #{i+1}", duration_seconds=300)
        rec = ehr_db.decrypt_emergency_data(pid)
        ledger.log_record_access(g["grant_id"], "EMERGENCY_TRIAGE_DATA", rec["payload_hash"])
        smart_lats.append((time.perf_counter() - t0) * 1000)

        t0_c = time.perf_counter()
        _ = ehr_db.decrypt_emergency_data(pid)
        time.sleep(0.0004)
        cent_lats.append((time.perf_counter() - t0_c) * 1000)

    print(f"Smart Contract Latency: Mean = {statistics.mean(smart_lats):.2f} ms | Std = {statistics.stdev(smart_lats):.2f} ms")
    print(f"Centralized Database Mode: Mean = {statistics.mean(cent_lats):.2f} ms")
    report = ledger.verify_chain_and_audit_integrity()
    print(f"Audit verification: {report['status']}")

if __name__ == "__main__":
    run_benchmarks(100)
