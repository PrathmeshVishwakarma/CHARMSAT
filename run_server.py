import sys
import uvicorn
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

if __name__ == "__main__":
    print("=" * 65)
    print("  CHARMSAT — DELTAV IO ALLOCATION & INDEPENDENT VERIFIER")
    print("  CODE APEX 3.0 // VIT PUNE // TEAM lost_in_the_shine")
    print("=" * 65)
    print("  * Serving API & Cyber UI at: http://127.0.0.1:8000")
    print("  * CP-SAT Solver: ONLINE")
    print("  * Independent Verifier: ACTIVE")
    print("=" * 65)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
