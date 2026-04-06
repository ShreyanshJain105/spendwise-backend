"""Small helper to initialize the database from the WSGI app.

Run from the `backend` folder:
    python create_db.py
"""
from app import application
from models.models import db

if __name__ == "__main__":
    with application.app_context():
        db.create_all()
        print("Database tables created (or already exist).")
