"""
Encrypted Mock EHR storage with emergency minimum-necessary scoping.
"""
from typing import Dict, Any, Optional
from blockchain_core.crypto_utils import EnvelopeEncryption

class MockEHRDatabase:
    def __init__(self):
        self.patient_keys: Dict[str, EnvelopeEncryption] = {}
        self.encrypted_records: Dict[str, Dict[str, Any]] = {}
        self.patients_meta: Dict[str, Dict[str, Any]] = {}
        self._populate_sample_patients()

    def _populate_sample_patients(self):
        sample_data = [
            {
                "patient_id": "PAT-9082", "full_name": "Alexander Hayes", "dob": "1984-06-14", "gender": "Male",
                "triage_state": "Trauma Victim (Unconscious)",
                "emergency_data": {
                    "blood_group": "O Rh-Negative (Universal Donor)",
                    "allergies": ["Severe Penicillin Allergy (Anaphylaxis)", "Latex Hypersensitivity"],
                    "active_medications": ["Warfarin 5mg daily (Critical: High Anticoagulation Bleeding Risk)", "Lisinopril 10mg daily"],
                    "existing_chronic_conditions": ["Coronary Artery Disease (CAD)", "Hypertension", "Previous Stent Placement (2021)"],
                    "resuscitation_code": "Full Code (CPR / Defibrillation Authorized)",
                    "emergency_contacts": [{"name": "Eleanor Hayes", "relationship": "Spouse", "phone": "+1-555-019-4821"}],
                    "critical_warnings": "PATIENT ON ACTIVE ANTICOAGULANT. REVERSAL AGENT (KCENTRA / VITAMIN K) MAY BE REQUIRED BEFORE EMERGENCY SURGERY."
                },
                "restricted_data": {"psychotherapy_notes": "[MASKED]", "billing": "[MASKED]", "genetics": "[MASKED]"}
            },
            {
                "patient_id": "PAT-4120", "full_name": "Sophia Rodriguez", "dob": "1995-11-23", "gender": "Female",
                "triage_state": "Acute Anaphylaxis / Respiratory Distress",
                "emergency_data": {
                    "blood_group": "A Rh-Positive",
                    "allergies": ["Peanuts (Severe Anaphylaxis)", "Sulfa Drugs", "NSAIDs / Ibuprofen"],
                    "active_medications": ["EpiPen 0.3mg Auto-Injector", "Fluticasone Inhaler", "Levothyroxine 75mcg"],
                    "existing_chronic_conditions": ["Severe Atopic Asthma", "Hypothyroidism"],
                    "resuscitation_code": "Full Code",
                    "emergency_contacts": [{"name": "Carlos Rodriguez", "relationship": "Brother", "phone": "+1-555-014-9932"}],
                    "critical_warnings": "IMMEDIATE INTUBATION ALERT: RAPID AIRWAY SWELLING DURING ANAPHYLACTIC SHOCK."
                },
                "restricted_data": {"psychotherapy_notes": "[MASKED]", "billing": "[MASKED]", "genetics": "[MASKED]"}
            },
            {
                "patient_id": "PAT-7731", "full_name": "Devin Washington", "dob": "1968-03-02", "gender": "Male",
                "triage_state": "Acute ST-Elevation Myocardial Infarction (STEMI)",
                "emergency_data": {
                    "blood_group": "B Rh-Positive",
                    "allergies": ["IV Contrast Dye Hypersensitivity", "Morphine"],
                    "active_medications": ["Atorvastatin 80mg", "Metoprolol 50mg", "Insulin Glargine 24 units"],
                    "existing_chronic_conditions": ["Type 2 Diabetes Mellitus", "Chronic Kidney Disease Stage 3a"],
                    "resuscitation_code": "DNR / DNI (Do Not Resuscitate / Do Not Intubate - Advance Directive on File)",
                    "emergency_contacts": [{"name": "Marcus Washington", "relationship": "Son", "phone": "+1-555-018-7744"}],
                    "critical_warnings": "ADVANCE DIRECTIVE ON FILE: DNR/DNI CONFIRMED 2025."
                },
                "restricted_data": {"psychotherapy_notes": "[MASKED]", "billing": "[MASKED]", "genetics": "[MASKED]"}
            }
        ]
        for p in sample_data:
            pid = p["patient_id"]
            self.patients_meta[pid] = {"patient_id": pid, "full_name": p["full_name"], "dob": p["dob"], "gender": p["gender"], "triage_state": p["triage_state"]}
            cipher = EnvelopeEncryption()
            self.patient_keys[pid] = cipher
            self.encrypted_records[pid] = {
                "emergency_payload": cipher.encrypt_json(p["emergency_data"]),
                "restricted_payload": cipher.encrypt_json(p["restricted_data"])
            }

    def list_all_patients(self):
        return list(self.patients_meta.values())

    def decrypt_emergency_data(self, patient_id: str) -> Dict[str, Any]:
        if patient_id not in self.encrypted_records:
            raise KeyError(f"Patient {patient_id} not found in EHR database.")
        cipher = self.patient_keys[patient_id]
        encrypted_bundle = self.encrypted_records[patient_id]["emergency_payload"]
        decrypted_emergency_data = cipher.decrypt_json(encrypted_bundle)
        return {
            "patient_id": patient_id, "patient_info": self.patients_meta[patient_id],
            "emergency_clinical_profile": decrypted_emergency_data,
            "payload_hash": encrypted_bundle["payload_hash"],
            "privacy_scope": "EMERGENCY_MINIMUM_NECESSARY",
            "restricted_categories_masked": ["Psychotherapy Notes", "Financial Accounts", "Genomic Sequencing"]
        }
