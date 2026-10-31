from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, session, send_from_directory

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILE = BASE_DIR / "data" / "complaints.db"

VALID_STATUSES = {"Open", "In Progress", "Resolved"}
VALID_PRIORITIES = {"Low", "Medium", "High"}


def current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def get_connection(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def create_database(database_path):
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    with get_connection(database_path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                student_department TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


def create_app(test_config=None):
    app = Flask(__name__, static_folder=None)

    app.config.from_mapping(
        DATABASE=str(DATABASE_FILE),
        SECRET_KEY=os.environ.get(
            "SECRET_KEY",
            "change-this-secret-before-real-deployment"
        ),
        ADMIN_USERNAME=os.environ.get("ADMIN_USERNAME", "admin"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "campus123")
    )

    if test_config:
        app.config.update(test_config)

    create_database(app.config["DATABASE"])

    @app.get("/")
    def home():
        return send_from_directory(BASE_DIR / "frontend", "index.html")

    @app.get("/<path:filename>")
    def frontend_files(filename):
        return send_from_directory(BASE_DIR / "frontend", filename)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/complaints")
    def get_complaints():
        status = request.args.get("status")

        with get_connection(app.config["DATABASE"]) as connection:
            if status in VALID_STATUSES:
                rows = connection.execute(
                    "SELECT * FROM complaints WHERE status = ? ORDER BY id DESC",
                    (status,)
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM complaints ORDER BY id DESC"
                ).fetchall()

        return jsonify([dict(row) for row in rows])

    @app.post("/api/complaints")
    def add_complaint():
        data = request.get_json(silent=True) or {}

        required_fields = [
            "student_name",
            "student_department",
            "title",
            "category",
            "location",
            "description"
        ]

        missing_fields = [
            field for field in required_fields
            if not str(data.get(field, "")).strip()
        ]

        if missing_fields:
            return jsonify({
                "error": "Please complete all required fields."
            }), 400

        priority = data.get("priority", "Medium")

        if priority not in VALID_PRIORITIES:
            return jsonify({"error": "Invalid priority."}), 400

        time = current_time()

        values = [str(data[field]).strip() for field in required_fields]

        with get_connection(app.config["DATABASE"]) as connection:
            cursor = connection.execute("""
                INSERT INTO complaints
                (
                    student_name,
                    student_department,
                    title,
                    category,
                    location,
                    description,
                    priority,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Open', ?, ?)
            """, (*values, priority, time, time))

            complaint = connection.execute(
                "SELECT * FROM complaints WHERE id = ?",
                (cursor.lastrowid,)
            ).fetchone()

        return jsonify(dict(complaint)), 201

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}

        correct_username = app.config["ADMIN_USERNAME"]
        correct_password = app.config["ADMIN_PASSWORD"]

        if (
            data.get("username") == correct_username
            and data.get("password") == correct_password
        ):
            session["admin"] = True
            return {"message": "Logged in"}

        return jsonify({
            "error": "Incorrect username or password."
        }), 401

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return {"message": "Logged out"}

    @app.get("/api/auth/me")
    def current_user():
        return {"is_admin": bool(session.get("admin"))}

    @app.patch("/api/complaints/<int:complaint_id>")
    def update_complaint(complaint_id):
        if not session.get("admin"):
            return jsonify({
                "error": "Admin login required."
            }), 401

        data = request.get_json(silent=True) or {}
        status = data.get("status")

        if status not in VALID_STATUSES:
            return jsonify({"error": "Invalid status."}), 400

        with get_connection(app.config["DATABASE"]) as connection:
            connection.execute("""
                UPDATE complaints
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status, current_time(), complaint_id))

            complaint = connection.execute(
                "SELECT * FROM complaints WHERE id = ?",
                (complaint_id,)
            ).fetchone()

        if complaint is None:
            return jsonify({"error": "Complaint not found."}), 404

        return jsonify(dict(complaint))

    return app


if __name__ == "__main__":
    create_app().run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
