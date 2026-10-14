"""Run a real local API flow with disposable SQLite and no external services."""
import io
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def main():
    with tempfile.TemporaryDirectory(prefix="job-analyzer-demo-") as directory:
        os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(directory) / "demo.db")
        os.environ["AI_PROVIDER"] = "none"
        os.environ["JWT_SECRET"] = secrets.token_urlsafe(48)
        from docx import Document
        from fastapi.testclient import TestClient
        from app.main import app
        from app.db import engine
        doc = Document()
        doc.add_paragraph("Demo Candidate. Python, FastAPI, SQL, Git, Docker.")
        payload = io.BytesIO()
        doc.save(payload)
        def checked(response, expected):
            if response.status_code != expected:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
            return response.json()
        try:
            with TestClient(app) as client:
                account = {"email": "demo@example.com", "password": "LocalDemo123!"}
                checked(client.post("/register", json=account), 201)
                token = checked(client.post("/login", json=account), 200)["access_token"]
                headers = {"Authorization": "Bearer " + token}
                resume = checked(client.post("/resume", headers=headers, files={"file": (
                    "demo.docx", payload.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}), 201)
                result = checked(client.post("/match", headers=headers, json={
                    "resume_id": resume["id"],
                    "vacancy": "Python backend developer: FastAPI, SQL, Docker, Kubernetes."}), 200)
                history = checked(client.get("/analyses", headers=headers), 200)
                print(json.dumps({"mode": "local keyword heuristic; no external AI",
                    "flow": "register -> login -> DOCX upload -> match -> history",
                    "result": result, "history": history}, ensure_ascii=False, indent=2))
        finally:
            engine.dispose()

if __name__ == "__main__":
    main()
