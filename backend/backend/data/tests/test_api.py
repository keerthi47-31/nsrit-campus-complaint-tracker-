import tempfile
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

from app import create_app


def create_test_client():
    database = tempfile.NamedTemporaryFile(
        suffix=".db",
        delete=False
    )

    database.close()

    app = create_app({
        "TESTING": True,
        "DATABASE": database.name,
        "SECRET_KEY": "test-secret",
        "ADMIN_PASSWORD": "test-password"
    })

    return app.test_client()


def sample_complaint():
    return {
        "student_name": "Anjali",
        "student_department": "CSE",
        "title": "Broken classroom fan",
        "category": "Classroom Facilities",
        "location": "Block A, Room 204",
        "description": "The fan does not turn on.",
        "priority": "Medium"
    }


def test_student_can_submit_complaint():
    client = create_test_client()

    response = client.post(
        "/api/complaints",
        json=sample_complaint()
    )

    assert response.status_code == 201

    complaints = client.get("/api/complaints").get_json()

    assert complaints[0]["status"] == "Open"


def test_only_admin_can_update_complaint():
    client = create_test_client()

    complaint = client.post(
        "/api/complaints",
        json=sample_complaint()
    ).get_json()

    response = client.patch(
        f"/api/complaints/{complaint['id']}",
        json={"status": "Resolved"}
    )

    assert response.status_code == 401

    client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "test-password"
        }
    )

    response = client.patch(
        f"/api/complaints/{complaint['id']}",
        json={"status": "Resolved"}
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "Resolved"
