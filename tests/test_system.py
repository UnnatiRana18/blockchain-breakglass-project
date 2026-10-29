import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from blockchain_core.ledger import PermissionedLedger
from backend.mock_ehr import MockEHRDatabase

def run_tests():
    ledger = PermissionedLedger()
    ehr_db = MockEHRDatabase()

    print("[TEST 1] Certify Doctor...")
    doc = ledger.certify_doctor("DOC-TEST", "Dr. Test", "LIC-1", "Hosp", "0x1111111111111111111111111111111111111111")
    assert doc["is_certified"]

    print("[TEST 2] Reject Uncertified...")
    try:
        ledger.request_break_glass("PAT-9082", "ROGUE", "Reason", duration_seconds=60)
        assert False
    except PermissionError:
        pass

    print("[TEST 3] Break-Glass Request...")
    g = ledger.request_break_glass("PAT-9082", "DOC-TEST", "Severe anaphylaxis", duration_seconds=60)
    assert g["patient_id"] == "PAT-9082"

    print("[TEST 4] Decrypt & Scoping...")
    rec = ehr_db.decrypt_emergency_data("PAT-9082")
    assert rec["emergency_clinical_profile"]["blood_group"] is not None

    print("[TEST 5] Log Access...")
    entry = ledger.log_record_access(g["grant_id"], "TRIAGE", rec["payload_hash"])
    assert entry["action"] == "RECORD_DECRYPTED"

    print("[TEST 6] Auto-Expiry...")
    qg = ledger.request_break_glass("PAT-4120", "DOC-TEST", "Short window", duration_seconds=1)
    time.sleep(1.1)
    st = ledger.check_access_validity(qg["grant_id"])
    assert st["status"] == "EXPIRED"

    print("[TEST 7] Early Revocation...")
    eg = ledger.request_break_glass("PAT-7731", "DOC-TEST", "STEMI triage", duration_seconds=600)
    ledger.revoke_grant_early(eg["grant_id"], "DOC-TEST", "Stabilized")
    assert ledger.check_access_validity(eg["grant_id"])["status"] == "REVOKED_EARLY"

    print("[TEST 8] Audit Integrity...")
    rep = ledger.verify_chain_and_audit_integrity()
    assert rep["is_valid"]

    print("[TEST 9] Tamper Detection...")
    ledger.simulate_tamper(1, "reason", "TAMPERED")
    assert not ledger.verify_chain_and_audit_integrity()["is_valid"]
    ledger.restore_tamper()
    assert ledger.verify_chain_and_audit_integrity()["is_valid"]

    print("ALL 9 TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
