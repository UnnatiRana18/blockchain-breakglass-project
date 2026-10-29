"""
Permissioned Blockchain Ledger & Smart Contract VM.
"""
import time
import json
import uuid
import copy
from typing import List, Dict, Any, Optional
from .crypto_utils import sha256, hash_dict, build_merkle_tree

class Transaction:
    def __init__(self, tx_type: str, sender: str, payload: Dict[str, Any], timestamp: Optional[float] = None, tx_id: Optional[str] = None):
        self.tx_type = tx_type
        self.sender = sender
        self.payload = payload
        self.timestamp = timestamp or time.time()
        self.tx_id = tx_id or self.calculate_hash()
        self.signature = sha256(f"{self.sender}:{self.tx_id}:{self.timestamp}")

    def calculate_hash(self) -> str:
        return sha256(f"{self.tx_type}:{self.sender}:{hash_dict(self.payload)}:{self.timestamp}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "tx_type": self.tx_type,
            "sender": self.sender,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "signature": self.signature
        }

class Block:
    def __init__(self, index: int, transactions: List[Transaction], previous_hash: str, validator: str = "HOSPITAL_CONSORTIUM_VALIDATOR_01", timestamp: Optional[float] = None):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.validator = validator
        self.timestamp = timestamp or time.time()
        tx_hashes = [tx.tx_id for tx in transactions]
        self.merkle_root, self.merkle_tree = build_merkle_tree(tx_hashes)
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        header = f"{self.index}:{self.previous_hash}:{self.merkle_root}:{self.validator}:{self.timestamp}"
        return sha256(header)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "hash": self.hash,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "validator": self.validator,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions]
        }

class PermissionedLedger:
    def __init__(self, validator_id: str = "HOSPITAL_CONSORTIUM_NODE_01"):
        self.validator_id = validator_id
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.certified_doctors: Dict[str, Dict[str, Any]] = {}
        self.access_grants: Dict[str, Dict[str, Any]] = {}
        self.patient_grants: Dict[str, List[str]] = {}
        self.audit_trail: List[Dict[str, Any]] = []
        self.patient_audit_logs: Dict[str, List[Dict[str, Any]]] = {}
        self.last_log_hash = sha256("GENESIS_BREAK_GLASS_AUDIT_LOG_ROOT")
        self._backup_chain: Optional[List[Block]] = None
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis_tx = Transaction("SYSTEM_INIT", "0x0000000000000000000000000000000000000000", {"message": "Genesis Block"})
        genesis_block = Block(0, [genesis_tx], "0" * 64, self.validator_id, 1700000000.0)
        self.chain.append(genesis_block)

    def commit_block(self) -> Block:
        if not self.pending_transactions:
            return self.chain[-1]
        new_block = Block(len(self.chain), self.pending_transactions, self.chain[-1].hash, self.validator_id)
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block

    def certify_doctor(self, doctor_id: str, name: str, license_number: str, hospital: str, wallet_address: str) -> Dict[str, Any]:
        doc_record = {
            "doctor_id": doctor_id, "name": name, "license_number": license_number,
            "hospital": hospital, "wallet_address": wallet_address, "is_certified": True, "certified_at": time.time()
        }
        self.certified_doctors[doctor_id] = copy.deepcopy(doc_record)
        self.certified_doctors[wallet_address.lower()] = copy.deepcopy(doc_record)
        tx = Transaction("CERTIFY_DOCTOR", "ADMIN_HOSPITAL_CONSORTIUM", copy.deepcopy(doc_record))
        self.pending_transactions.append(tx)
        self.commit_block()
        return doc_record

    def request_break_glass(self, patient_id: str, doctor_id: str, reason: str, urgency: str = "CRITICAL_RESUSCITATION", duration_seconds: int = 1800) -> Dict[str, Any]:
        doctor = self.certified_doctors.get(doctor_id) or self.certified_doctors.get(doctor_id.lower())
        if not doctor or not doctor.get("is_certified"):
            raise PermissionError(f"Access Denied: Doctor '{doctor_id}' is not certified in permissioned registry.")
        if not reason or len(reason.strip()) < 8:
            raise ValueError("Clinical justification required (minimum 8 characters).")

        duration_seconds = max(1, min(duration_seconds, 3600))
        current_time = time.time()
        expires_at = current_time + duration_seconds
        grant_id = sha256(f"{patient_id}:{doctor_id}:{current_time}:{reason}:{uuid.uuid4()}")
        reason_hash = sha256(reason)

        grant_payload = {
            "grant_id": grant_id, "patient_id": patient_id, "doctor_id": doctor["doctor_id"],
            "doctor_name": doctor["name"], "license_number": doctor["license_number"],
            "hospital": doctor["hospital"], "urgency": urgency, "reason": reason,
            "reason_hash": reason_hash, "granted_at": current_time, "duration_seconds": duration_seconds,
            "expires_at": expires_at, "is_revoked": False,
            "scope": ["ALLERGIES", "BLOOD_GROUP", "CURRENT_MEDICATIONS", "ACUTE_VITALS", "EMERGENCY_CONTACTS"]
        }
        self.access_grants[grant_id] = copy.deepcopy(grant_payload)
        self.patient_grants.setdefault(patient_id, []).append(grant_id)

        tx = Transaction("REQUEST_BREAK_GLASS", doctor["wallet_address"], copy.deepcopy(grant_payload))
        self.pending_transactions.append(tx)

        self._append_audit_log(grant_id, patient_id, doctor["doctor_id"], doctor["name"], "BREAK_GLASS_TRIGGERED", "GRANT_AUTHORIZATION", reason_hash, f"Urgency: {urgency}")
        self.commit_block()
        return grant_payload

    def check_access_validity(self, grant_id: str) -> Dict[str, Any]:
        grant = self.access_grants.get(grant_id)
        if not grant:
            return {"is_valid": False, "status": "NON_EXISTENT", "remaining_seconds": 0}
        if grant["is_revoked"]:
            return {"is_valid": False, "status": "REVOKED_EARLY", "remaining_seconds": 0, "grant": grant}
        now = time.time()
        if now > grant["expires_at"]:
            return {"is_valid": False, "status": "EXPIRED", "remaining_seconds": 0, "overdue_by_seconds": round(now - grant["expires_at"], 2), "grant": grant}
        return {"is_valid": True, "status": "ACTIVE", "remaining_seconds": round(grant["expires_at"] - now, 1), "grant": grant}

    def log_record_access(self, grant_id: str, data_category: str, payload_hash: str) -> Dict[str, Any]:
        validity = self.check_access_validity(grant_id)
        if not validity["is_valid"]:
            raise PermissionError(f"Access Denied: Grant is {validity['status']}. Cannot decrypt or access records.")
        grant = validity["grant"]
        audit_entry = self._append_audit_log(grant_id, grant["patient_id"], grant["doctor_id"], grant["doctor_name"], "RECORD_DECRYPTED", data_category, payload_hash, f"Decrypted {data_category}")
        tx = Transaction("LOG_DATA_ACCESS", grant["doctor_id"], copy.deepcopy(audit_entry))
        self.pending_transactions.append(tx)
        self.commit_block()
        return audit_entry

    def revoke_grant_early(self, grant_id: str, doctor_or_admin: str, reason: str) -> Dict[str, Any]:
        grant = self.access_grants.get(grant_id)
        if not grant:
            raise ValueError("Grant ID not found.")
        grant["is_revoked"] = True
        grant["revoked_at"] = time.time()
        grant["revoke_reason"] = reason
        self._append_audit_log(grant_id, grant["patient_id"], doctor_or_admin, grant["doctor_name"], "SESSION_EARLY_CLOSED", "REVOCATION", sha256(reason), reason)
        tx = Transaction("REVOKE_ACCESS", doctor_or_admin, {"grant_id": grant_id, "reason": reason})
        self.pending_transactions.append(tx)
        self.commit_block()
        return grant

    def _append_audit_log(self, grant_id: str, patient_id: str, doctor_id: str, doctor_name: str, action: str, data_category: str, payload_hash: str, details: str) -> Dict[str, Any]:
        current_time = time.time()
        log_id = sha256(f"{self.last_log_hash}:{grant_id}:{patient_id}:{action}:{current_time}:{payload_hash}")
        entry = {
            "log_id": log_id, "grant_id": grant_id, "patient_id": patient_id, "doctor_id": doctor_id,
            "doctor_name": doctor_name, "timestamp": current_time, "action": action, "data_category": data_category,
            "payload_hash": payload_hash, "previous_log_hash": self.last_log_hash, "details": details
        }
        self.audit_trail.append(entry)
        self.patient_audit_logs.setdefault(patient_id, []).append(entry)
        self.last_log_hash = log_id
        return entry

    def verify_chain_and_audit_integrity(self) -> Dict[str, Any]:
        block_issues = []
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]
            if current.previous_hash != prev.hash:
                block_issues.append({"block_index": current.index, "error": "PREVIOUS_HASH_MISMATCH"})
            if current.hash != current.calculate_hash():
                block_issues.append({"block_index": current.index, "error": "BLOCK_HASH_CORRUPTED"})
            for tx in current.transactions:
                if tx.calculate_hash() != tx.tx_id:
                    block_issues.append({"block_index": current.index, "error": "TRANSACTION_PAYLOAD_TAMPERED", "tx_id": tx.tx_id})
            tx_hashes = [tx.tx_id for tx in current.transactions]
            recomputed_merkle, _ = build_merkle_tree(tx_hashes)
            if current.merkle_root != recomputed_merkle:
                block_issues.append({"block_index": current.index, "error": "MERKLE_ROOT_MISMATCH"})

        audit_issues = []
        expected_prev_hash = sha256("GENESIS_BREAK_GLASS_AUDIT_LOG_ROOT")
        for idx, entry in enumerate(self.audit_trail):
            if entry["previous_log_hash"] != expected_prev_hash:
                audit_issues.append({"audit_index": idx, "error": "AUDIT_CHAIN_BROKEN"})
            expected_prev_hash = entry["log_id"]

        is_valid = (len(block_issues) == 0 and len(audit_issues) == 0)
        return {
            "is_valid": is_valid, "total_blocks": len(self.chain), "total_audit_logs": len(self.audit_trail),
            "block_issues": block_issues, "audit_issues": audit_issues,
            "status": "PASS: All cryptographic proofs verified intact" if is_valid else "FAIL: Tampering or corruption detected!"
        }

    def simulate_tamper(self, block_index: int = 1, altered_field: str = "reason", malicious_val: str = "UNAUTHORIZED_SNOOPING") -> Dict[str, Any]:
        if len(self.chain) <= block_index:
            raise IndexError("Block index out of bounds for tamper simulation.")
        if self._backup_chain is None:
            self._backup_chain = copy.deepcopy(self.chain)
        target_block = self.chain[block_index]
        target_tx = target_block.transactions[0]
        original_val = target_tx.payload.get(altered_field, "N/A")
        target_tx.payload[altered_field] = malicious_val
        return {"status": "TAMPER_INJECTED", "block_index": block_index, "altered_field": altered_field, "original": original_val, "malicious": malicious_val}

    def restore_tamper(self) -> Dict[str, Any]:
        if self._backup_chain:
            self.chain = copy.deepcopy(self._backup_chain)
            self._backup_chain = None
            return {"status": "RESTORED", "message": "Blockchain state restored."}
        return {"status": "NO_CHANGE"}

    def get_audit_trail(self, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.patient_audit_logs.get(patient_id, []) if patient_id else self.audit_trail
