# Blockchain-Based Controlled Emergency Access to Patient Data

A permissioned "break-glass" system where smart contracts — not administrators — grant, log, and automatically expire emergency access to critical patient data.

**Authors:**
- Unnati Rana (ENG23CS0670)
- Shruthi Mohan (ENG23CS0186)
- Sayee Dahake (ENG23CS0448)
- Sanvi Agarwal (Eng23CS0650)  
*Department of Computer Science and Engineering*

---

## 1. Project Overview

In medical emergencies (unconscious trauma patient, anaphylaxis, cardiac arrest), clinical teams cannot wait for patient consent. However, traditional "break-glass" access mechanisms rely on centralized databases where an administrator has full control over logs, manual revocation permits lingering access, and blanket disclosures expose sensitive non-emergency data.

This project delivers a **smart-contract governed permissioned blockchain system** that enforces:
1. **Deterministic Time-Bound Auto-Expiry:** The smart contract automatically revokes access when the pre-set emergency window expires ($t_{\text{now}} > t_{\text{expiry}}$) with **zero manual intervention**.
2. **Provable Tamper-Evidence:** Every emergency request, data decryption, and expiration event is recorded in a cryptographically chained Merkle audit trail.
3. **Emergency Scoped Decryption:** AES-256-GCM envelope encryption decrypts emergency-critical triage fields (allergies, blood type, active medications, vitals) while masking sensitive non-emergency records (psychotherapy notes, billing data).
4. **Dual Role-Based Portals:** Dedicated web UI flows for **Attending Physicians** (break-glass trigger & live countdown timer) and **Patients / Auditors** (tamper verifier, block explorer, and audit trail).

---

## 2. Directory Structure

```
blockchain-breakglass-project/
├── start.py                         # Application launcher script
├── requirements.txt                 # Python dependencies
├── README.md                        # Documentation
├── contracts/
│   └── EmergencyAccessControl.sol   # Solidity smart contract
├── blockchain_core/
│   ├── crypto_utils.py              # SHA-256, Merkle Tree, AES-256-GCM cipher
│   └── ledger.py                    # Permissioned blockchain VM & tamper verifier
├── backend/
│   ├── app.py                       # FastAPI REST API & static file server
│   └── mock_ehr.py                  # Encrypted EHR database with emergency scoping
├── frontend/static/
│   ├── index.html                   # Clinical Web UI (Doctor & Auditor portals)
│   ├── style.css                    # Responsive medical UI styling
│   └── app.js                       # Frontend client logic & countdown clock
├── benchmarks/
│   └── run_benchmarks.py            # Automated 100-cycle latency benchmark suite
├── tests/
│   └── test_system.py               # 9-point unit & security test suite
└── .vscode/
    ├── launch.json                  # VS Code Run/Debug configurations
    ├── tasks.json                   # VS Code tasks
    └── settings.json                # VS Code workspace settings
```

---

## 3. How to Run in VS Code

### Step 1: Open in VS Code
Open VS Code, choose **File -> Open Folder...**, and select the `blockchain-breakglass-project` folder.

### Step 2: Run via VS Code Run & Debug
1. Click the **Run and Debug** icon on the sidebar (`Ctrl+Shift+D` or `Cmd+Shift+D`).
2. Select **"Run FastAPI Web Server (Break-Glass Portal)"** and press **F5**.
3. Open your browser to:
   - **Interactive Web Dashboard:** `http://127.0.0.1:8000`
   - **Interactive API Documentation:** `http://127.0.0.1:8000/docs`

### Step 3: Run via Terminal
```bash
# 1. Install dependencies (if needed)
pip install -r requirements.txt

# 2. Launch the application
python3 start.py

# 3. Run the automated test suite
python3 tests/test_system.py

# 4. Run the benchmark suite
python3 benchmarks/run_benchmarks.py
```
