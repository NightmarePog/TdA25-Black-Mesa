from .models import db

def create_tables():
    db.create_all()
