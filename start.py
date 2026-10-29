"""
Launcher script for Controlled Emergency Access Blockchain Project.
Runs FastAPI backend on port 8000 and serves Web Dashboard.
"""
import sys
import os
import uvicorn

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    print("=" * 70)
    print("STARTING CONTROLLED EMERGENCY ACCESS BLOCKCHAIN PROTOTYPE")
    print("Project: Blockchain-Based Controlled Emergency Access to Patient Data")
    print("Authors: Unnati Rana, Shruthi Mohan, Sayee Dahake, Sanvi Agarwal")
    print("Web Dashboard: http://127.0.0.1:8000")
    print("Swagger API Docs: http://127.0.0.1:8000/docs")
    print("=" * 70)
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False)
